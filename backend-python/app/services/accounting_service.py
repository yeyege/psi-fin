"""会计内核服务 — 科目树 / 凭证生命周期 / 期间管理

对应 openspec/changes/oss-finance-ai-platform/specs/finance/accounting-core/spec.md:
- 仅明细科目可挂分录(拒绝保存 422)
- posted 凭证禁改删(409),更正走红字冲销,双向单号关联
- closed 期间拒写凭证(409);反结账仅允许按期间倒序

凭证号沿用单据号体系:JV-YYYYMMDD-XXX(generate_order_no)。
金额服务层统一 round(...,2),借贷平衡比较用 EPS 容差。
"""
from calendar import monthrange
from datetime import date, datetime

from sqlalchemy import func

from app.common.errors import BusinessError
from app.common.order_no import generate_order_no
from app.models.accounting import (
    Account, Period, Voucher, VoucherLine,
    ACCOUNT_CATEGORIES, BALANCE_DIRECTIONS, LINE_DIRECTIONS, LINE_DEBIT, LINE_CREDIT,
    VOUCHER_DRAFT, VOUCHER_POSTED, VOUCHER_REVERSED,
    PERIOD_OPEN, PERIOD_CLOSED, SOURCE_MANUAL,
)

EPS = 1e-6


# ============ 科目表(COA) ============

def create_account(db, *, code: str, name: str, category: str, direction: str,
                   parent_id: int | None = None, aux_dimensions: str = "") -> Account:
    """创建科目并维护树结构:

    - code 全表唯一;有父科目时编码必须以父编码为前缀(如 2202 → 220201)
    - 新增子科目时父科目自动置为非明细(is_leaf=False)
    - 子科目类别/余额方向必须与父科目一致,避免树内口径混乱
    """
    code = (code or "").strip()
    name = (name or "").strip()
    if not code or not name:
        raise BusinessError("科目编码与名称不能为空")
    if category not in ACCOUNT_CATEGORIES:
        raise BusinessError(f"科目类别不合法: {category},可选 {ACCOUNT_CATEGORIES}")
    if direction not in BALANCE_DIRECTIONS:
        raise BusinessError(f"余额方向不合法: {direction},可选 {BALANCE_DIRECTIONS}")
    if db.query(Account).filter(Account.code == code).first():
        raise BusinessError(f"科目编码已存在: {code}", status=409)

    level = 1
    parent = None
    if parent_id is not None:
        parent = db.get(Account, parent_id)
        if parent is None:
            raise BusinessError(f"父科目不存在: id={parent_id}")
        if not code.startswith(parent.code):
            raise BusinessError(f"子科目编码 {code} 必须以父科目编码 {parent.code} 开头")
        if parent.category != category:
            raise BusinessError(f"子科目类别必须与父科目一致({parent.category})")
        if parent.direction != direction:
            raise BusinessError(f"子科目余额方向必须与父科目一致({parent.direction})")
        level = parent.level + 1

    account = Account(
        code=code, name=name, category=category, direction=direction,
        parent_id=parent_id, level=level, is_leaf=True,
        aux_dimensions=aux_dimensions or "",
    )
    db.add(account)
    if parent is not None and parent.is_leaf:
        parent.is_leaf = False  # 有了下级科目即非明细
    db.flush()
    return account


def get_account_by_code(db, code: str) -> Account:
    account = db.query(Account).filter(Account.code == code).first()
    if account is None:
        raise BusinessError(f"科目不存在: {code}")
    return account


def assert_postable(db, account_id: int) -> Account:
    """凭证分录取数校验:科目存在、启用、且必须是明细科目。"""
    account = db.get(Account, account_id)
    if account is None:
        raise BusinessError(f"分录引用了不存在的科目: id={account_id}")
    if account.status != "ACTIVE":
        raise BusinessError(f"科目已停用,不得记账: {account.code} {account.name}", status=422)
    if not account.is_leaf:
        raise BusinessError(
            f"非明细科目不得直接记账,请选择其下级明细科目: {account.code} {account.name}",
            status=422,
        )
    return account


# ============ 会计期间 ============

def period_code_of(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def ensure_period(db, d: date) -> Period:
    """按日期取整自然月期间,不存在则创建为 OPEN。"""
    code = period_code_of(d)
    period = db.query(Period).filter(Period.code == code).first()
    if period is None:
        period = Period(
            code=code,
            start_date=date(d.year, d.month, 1),
            end_date=date(d.year, d.month, monthrange(d.year, d.month)[1]),
            status=PERIOD_OPEN,
        )
        db.add(period)
        db.flush()
    return period


def assert_period_open(db, d: date) -> Period:
    period = ensure_period(db, d)
    if period.status == PERIOD_CLOSED:
        raise BusinessError(f"期间 {period.code} 已结账锁定,禁止凭证写入", status=409)
    return period


def close_period(db, code: str) -> Period:
    """结账:该期间不得有 DRAFT 凭证,通过后锁定。"""
    period = db.query(Period).filter(Period.code == code).first()
    if period is None:
        raise BusinessError(f"期间不存在: {code}")
    if period.status == PERIOD_CLOSED:
        raise BusinessError(f"期间 {code} 已结账,无需重复操作")
    drafts = (
        db.query(Voucher)
        .filter(Voucher.period_code == code, Voucher.status == VOUCHER_DRAFT)
        .count()
    )
    if drafts:
        raise BusinessError(f"期间 {code} 存在 {drafts} 张未过账草稿凭证,请先过账或删除")
    period.status = PERIOD_CLOSED
    period.closed_at = datetime.now()
    db.flush()
    return period


def reopen_period(db, code: str) -> Period:
    """反结账:仅允许按期间倒序——不得存在更晚且仍 closed 的期间。"""
    period = db.query(Period).filter(Period.code == code).first()
    if period is None:
        raise BusinessError(f"期间不存在: {code}")
    if period.status == PERIOD_OPEN:
        raise BusinessError(f"期间 {code} 未结账,无需反结账")
    later_closed = (
        db.query(Period)
        .filter(Period.code > code, Period.status == PERIOD_CLOSED)
        .count()
    )
    if later_closed:
        raise BusinessError(f"存在更晚的已结账期间,必须先反结账后期(倒序),不可跳过")
    period.status = PERIOD_OPEN
    period.closed_at = None
    db.flush()
    return period


# ============ 凭证生命周期 ============

def create_voucher(db, *, voucher_date: date, lines: list[dict],
                   memo: str = "", source_type: str = SOURCE_MANUAL,
                   created_by: str | None = None) -> Voucher:
    """创建草稿凭证。

    lines: [{accountId, direction(D/C), amount, auxType?, auxId?, auxName?, memo?}]
    保存即校验:方向合法、科目必须为可记账明细科目(spec: 非明细科目拒绝记账)。
    先校验后落库,任一行不合法整单拒绝,不产生半成品凭证。
    借贷平衡在过账时校验(post_voucher)。
    """
    if not lines:
        raise BusinessError("凭证至少需要一条分录")
    assert_period_open(db, voucher_date)

    prepared = []
    for seq, line in enumerate(lines, start=1):
        direction = line.get("direction")
        if direction not in LINE_DIRECTIONS:
            raise BusinessError(f"第 {seq} 行分录方向不合法: {direction}(应为 D/C)")
        account = assert_postable(db, line["accountId"])
        amount = round(float(line.get("amount", 0)), 2)
        if amount == 0:
            raise BusinessError(f"第 {seq} 行分录金额不得为 0")
        prepared.append((seq, account, direction, amount, line))

    voucher = Voucher(
        voucher_no=generate_order_no(db, Voucher, "JV", no_col="voucher_no"),
        voucher_date=voucher_date,
        period_code=period_code_of(voucher_date),
        status=VOUCHER_DRAFT,
        source_type=source_type,
        memo=memo,
        created_by=created_by,
    )
    db.add(voucher)
    db.flush()

    for seq, account, direction, amount, line in prepared:
        voucher.lines.append(VoucherLine(
            seq=seq,
            account_id=account.id,
            direction=direction,
            amount=amount,
            aux_type=line.get("auxType"),
            aux_id=line.get("auxId"),
            aux_name=line.get("auxName"),
            memo=line.get("memo"),
        ))
    db.flush()
    return voucher


def post_voucher(db, voucher_id: int) -> Voucher:
    """过账:DRAFT → POSTED,强制借贷平衡 + 至少两条分录 + 期间开放。"""
    voucher = db.get(Voucher, voucher_id)
    if voucher is None:
        raise BusinessError(f"凭证不存在: id={voucher_id}")
    if voucher.status != VOUCHER_DRAFT:
        raise BusinessError(f"凭证 {voucher.voucher_no} 状态为 {voucher.status},仅草稿可过账", status=409)
    assert_period_open(db, voucher.voucher_date)

    if len(voucher.lines) < 2:
        raise BusinessError(f"凭证 {voucher.voucher_no} 至少需要两条分录,不得单边挂账")
    total_debit = sum(l.amount for l in voucher.lines if l.direction == LINE_DEBIT)
    total_credit = sum(l.amount for l in voucher.lines if l.direction == LINE_CREDIT)
    if abs(total_debit - total_credit) > EPS:
        raise BusinessError(
            f"凭证借贷不平衡: 借 {round(total_debit, 2)} ≠ 贷 {round(total_credit, 2)}",
            status=422,
        )
    voucher.status = VOUCHER_POSTED
    db.flush()
    return voucher


def assert_updatable(voucher: Voucher) -> None:
    """posted/reversed 凭证禁止改删(spec: 过账后拒绝修改)。"""
    if voucher.status != VOUCHER_DRAFT:
        raise BusinessError(
            f"凭证 {voucher.voucher_no} 已过账,禁止修改或删除,请使用红字冲销",
            status=409,
        )


def delete_draft_voucher(db, voucher_id: int) -> None:
    voucher = db.get(Voucher, voucher_id)
    if voucher is None:
        raise BusinessError(f"凭证不存在: id={voucher_id}")
    assert_updatable(voucher)
    db.delete(voucher)
    db.flush()


def reverse_voucher(db, voucher_id: int, *, reverse_date: date | None = None,
                    created_by: str | None = None) -> Voucher:
    """红字冲销:生成同科目同维度、金额取负的新凭证并直接过账。

    冲销凭证记入当前开放期间(默认今天);若原期间已 closed 不影响冲销。
    双向关联:新凭证 reverses_voucher_no ↔ 原凭证 reversed_voucher_no。
    """
    origin = db.get(Voucher, voucher_id)
    if origin is None:
        raise BusinessError(f"凭证不存在: id={voucher_id}")
    if origin.status == VOUCHER_REVERSED or origin.reversed_voucher_no:
        raise BusinessError(f"凭证 {origin.voucher_no} 已被冲销,不得重复冲销", status=409)
    if origin.status != VOUCHER_POSTED:
        raise BusinessError(f"凭证 {origin.voucher_no} 状态为 {origin.status},仅已过账凭证可冲销", status=409)

    rdate = reverse_date or date.today()
    red_lines = [{
        "accountId": l.account_id,
        "direction": l.direction,
        "amount": -l.amount,
        "auxType": l.aux_type,
        "auxId": l.aux_id,
        "auxName": l.aux_name,
        "memo": l.memo,
    } for l in origin.lines]

    red = create_voucher(
        db, voucher_date=rdate, lines=red_lines,
        memo=f"冲销凭证 {origin.voucher_no}",
        source_type=origin.source_type, created_by=created_by,
    )
    red.reverses_voucher_no = origin.voucher_no
    origin.reversed_voucher_no = red.voucher_no
    origin.status = VOUCHER_REVERSED
    post_voucher(db, red.id)
    db.refresh(red)
    return red


# ============ 查询辅助(余额/试算的最小口径) ============

def account_balances(db, period_code: str | None = None) -> dict[int, dict]:
    """按科目汇总已生效凭证(POSTED,排除被冲销对)的借/贷发生额。

    返回 {account_id: {"debit": x, "credit": y}};reversed 原凭证与其红字冲销
    凭证金额天然对冲,故一并纳入汇总即可保证平衡。
    """
    query = (
        db.query(
            VoucherLine.account_id,
            VoucherLine.direction,
            func.coalesce(func.sum(VoucherLine.amount), 0.0),
        )
        .join(Voucher, VoucherLine.voucher_id == Voucher.id)
        .filter(Voucher.status.in_([VOUCHER_POSTED, VOUCHER_REVERSED]))
    )
    if period_code:
        query = query.filter(Voucher.period_code == period_code)
    rows = query.group_by(VoucherLine.account_id, VoucherLine.direction).all()

    balances: dict[int, dict] = {}
    for account_id, direction, total in rows:
        bucket = balances.setdefault(account_id, {"debit": 0.0, "credit": 0.0})
        key = "debit" if direction == LINE_DEBIT else "credit"
        bucket[key] = round(bucket[key] + float(total), 2)
    return balances
