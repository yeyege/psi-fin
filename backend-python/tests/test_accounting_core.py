"""会计内核测试 — 科目树构建 / 非明细科目拒绝记账 / 凭证状态机 / 期间锁定

覆盖 openspec/changes/oss-finance-ai-platform/specs/finance/accounting-core/spec.md:
- 科目树:子科目编码前缀约束、新增下级自动置父科目非明细、类别/方向一致性
- 非明细科目与停用科目拒绝挂分录(422)
- 凭证借贷平衡、单边挂账拦截、posted 禁改删(409)、红字冲销双向关联
- closed 期间拒写(409)、结账前草稿检查、反结账倒序约束
"""
from datetime import date

import pytest

from app.common.errors import BusinessError
from app.models.accounting import (
    Account, Voucher,
    VOUCHER_DRAFT, VOUCHER_POSTED, VOUCHER_REVERSED,
    PERIOD_CLOSED,
)
from app.services import accounting_service as svc


# ============ 辅助 ============

@pytest.fixture()
def coa(db_session):
    """最小科目树:

    1002 银行存款(明细)
    6602 管理费用(非明细) → 660201 工资福利(明细) / 660202 办公费(明细)
    2202 应付账款(非明细) → 220201 外部供应商(明细, aux SUPPLIER)
    """
    bank = svc.create_account(db_session, code="1002", name="银行存款",
                              category="ASSET", direction="DEBIT")
    admin_exp = svc.create_account(db_session, code="6602", name="管理费用",
                                   category="EXPENSE", direction="DEBIT")
    salary = svc.create_account(db_session, code="660201", name="工资福利",
                                category="EXPENSE", direction="DEBIT",
                                parent_id=admin_exp.id)
    office = svc.create_account(db_session, code="660202", name="办公费",
                                category="EXPENSE", direction="DEBIT",
                                parent_id=admin_exp.id)
    ap = svc.create_account(db_session, code="2202", name="应付账款",
                            category="LIABILITY", direction="CREDIT")
    ap_vendor = svc.create_account(db_session, code="220201", name="外部供应商",
                                   category="LIABILITY", direction="CREDIT",
                                   parent_id=ap.id, aux_dimensions="SUPPLIER")
    db_session.commit()
    return {"bank": bank, "admin_exp": admin_exp, "salary": salary,
            "office": office, "ap": ap, "ap_vendor": ap_vendor}


def _line(account, direction, amount, **aux):
    return {"accountId": account.id, "direction": direction, "amount": amount, **aux}


def _balanced_payment_voucher(db, coa, amount=1000.0):
    """借 管理费用-工资福利 / 贷 银行存款 的平衡草稿。"""
    return svc.create_voucher(
        db, voucher_date=date(2026, 9, 15),
        lines=[_line(coa["salary"], "D", amount), _line(coa["bank"], "C", amount)],
        memo="支付 9 月工资",
    )


# ============ 科目树构建 ============

def test_create_child_account_flips_parent_to_non_leaf(db_session, coa):
    admin_exp = db_session.get(Account, coa["admin_exp"].id)
    assert admin_exp.is_leaf is False          # 挂了 660201/660202 后自动非明细
    assert admin_exp.level == 1
    assert [c.code for c in admin_exp.children] == ["660201", "660202"]
    assert admin_exp.children[0].level == 2
    assert admin_exp.children[0].parent_id == admin_exp.id


def test_top_level_account_starts_as_leaf(db_session, coa):
    ap = db_session.get(Account, coa["ap"].id)
    assert ap.parent_id is None and ap.level == 1
    # 2202 已有下级 220201 → 非明细;而新建的顶级明细科目仍是明细
    new_leaf = svc.create_account(db_session, code="1001", name="库存现金",
                                  category="ASSET", direction="DEBIT")
    db_session.commit()
    assert new_leaf.is_leaf is True


def test_child_code_must_start_with_parent_code(db_session, coa):
    with pytest.raises(BusinessError, match="必须以父科目编码"):
        svc.create_account(db_session, code="999901", name="编码不匹配",
                           category="EXPENSE", direction="DEBIT",
                           parent_id=coa["admin_exp"].id)


def test_child_must_keep_parent_category_and_direction(db_session, coa):
    with pytest.raises(BusinessError, match="类别必须与父科目一致"):
        svc.create_account(db_session, code="660203", name="类别错了",
                           category="ASSET", direction="DEBIT",
                           parent_id=coa["admin_exp"].id)
    with pytest.raises(BusinessError, match="余额方向必须与父科目一致"):
        svc.create_account(db_session, code="660204", name="方向错了",
                           category="EXPENSE", direction="CREDIT",
                           parent_id=coa["admin_exp"].id)


def test_duplicate_code_and_invalid_enums_rejected(db_session, coa):
    with pytest.raises(BusinessError):
        svc.create_account(db_session, code="1002", name="重复编码",
                           category="ASSET", direction="DEBIT")
    with pytest.raises(BusinessError, match="科目类别不合法"):
        svc.create_account(db_session, code="8888", name="怪类别",
                           category="FOX", direction="DEBIT")
    with pytest.raises(BusinessError, match="余额方向不合法"):
        svc.create_account(db_session, code="8889", name="怪方向",
                           category="ASSET", direction="UP")


# ============ 非明细科目拒绝记账 ============

def test_voucher_line_on_non_leaf_account_rejected(db_session, coa):
    """spec: 分录引用非明细科目 → 拒绝保存(422),提示选择下级明细。"""
    with pytest.raises(BusinessError) as ei:
        svc.create_voucher(
            db_session, voucher_date=date(2026, 9, 15),
            lines=[_line(coa["admin_exp"], "D", 500.0), _line(coa["bank"], "C", 500.0)],
        )
    assert ei.value.status == 422
    assert "非明细科目" in ei.value.message
    # 拒绝后不得留下半成品凭证
    assert db_session.query(Voucher).count() == 0


def test_voucher_line_on_inactive_account_rejected(db_session, coa):
    coa["salary"].status = "INACTIVE"
    db_session.flush()
    with pytest.raises(BusinessError) as ei:
        svc.create_voucher(
            db_session, voucher_date=date(2026, 9, 15),
            lines=[_line(coa["salary"], "D", 100.0), _line(coa["bank"], "C", 100.0)],
        )
    assert ei.value.status == 422
    assert "停用" in ei.value.message


# ============ 凭证状态机 ============

def test_balanced_voucher_posts_and_rejects_unbalanced(db_session, coa):
    ok = _balanced_payment_voucher(db_session, coa)
    assert ok.status == VOUCHER_DRAFT
    assert ok.voucher_no.startswith("JV-")
    assert ok.period_code == "2026-09"
    posted = svc.post_voucher(db_session, ok.id)
    assert posted.status == VOUCHER_POSTED

    bad = svc.create_voucher(
        db_session, voucher_date=date(2026, 9, 15),
        lines=[_line(coa["salary"], "D", 100.0), _line(coa["bank"], "C", 99.5)],
    )
    with pytest.raises(BusinessError, match="借贷不平衡"):
        svc.post_voucher(db_session, bad.id)
    assert db_session.get(Voucher, bad.id).status == VOUCHER_DRAFT


def test_single_line_voucher_cannot_post(db_session, coa):
    solo = svc.create_voucher(
        db_session, voucher_date=date(2026, 9, 15),
        lines=[_line(coa["bank"], "D", 100.0)],
    )
    with pytest.raises(BusinessError, match="单边挂账"):
        svc.post_voucher(db_session, solo.id)


def test_posted_voucher_is_immutable(db_session, coa):
    """spec: posted 凭证改删 → 409,提示走冲销。"""
    v = _balanced_payment_voucher(db_session, coa)
    svc.post_voucher(db_session, v.id)
    with pytest.raises(BusinessError) as ei:
        svc.delete_draft_voucher(db_session, v.id)
    assert ei.value.status == 409
    with pytest.raises(BusinessError) as ei2:
        svc.post_voucher(db_session, v.id)  # 重复过账同样拒绝
    assert ei2.value.status == 409


def test_reverse_voucher_creates_negative_twins_with_bidirectional_link(db_session, coa):
    """spec: 红字冲销 — 同科目同维度金额取负、直接过账、双向单号关联、原凭证置 REVERSED。"""
    origin = _balanced_payment_voucher(db_session, coa, amount=800.0)
    origin = svc.post_voucher(db_session, origin.id)

    red = svc.reverse_voucher(db_session, origin.id, reverse_date=date(2026, 9, 20))

    assert red.status == VOUCHER_POSTED
    assert red.reverses_voucher_no == origin.voucher_no
    db_session.refresh(origin)
    assert origin.status == VOUCHER_REVERSED
    assert origin.reversed_voucher_no == red.voucher_no
    # 分录镜像:科目/方向一致、金额取负
    origin_lines = sorted(origin.lines, key=lambda l: l.seq)
    red_lines = sorted(red.lines, key=lambda l: l.seq)
    assert [(l.account_id, l.direction, l.amount) for l in red_lines] == \
           [(l.account_id, l.direction, -l.amount) for l in origin_lines]
    # 冲销对余额净影响为零
    balances = svc.account_balances(db_session)
    assert balances[coa["salary"].id]["debit"] == pytest.approx(0.0)
    assert balances[coa["bank"].id]["credit"] == pytest.approx(0.0)

    with pytest.raises(BusinessError, match="不得重复冲销"):
        svc.reverse_voucher(db_session, origin.id)


# ============ 期间与结账锁定 ============

def test_closed_period_rejects_voucher_write(db_session, coa):
    """spec: closed 期间凭证创建/过账 → 409。"""
    v = _balanced_payment_voucher(db_session, coa)
    svc.post_voucher(db_session, v.id)
    svc.close_period(db_session, "2026-09")
    assert svc.ensure_period(db_session, date(2026, 9, 1)).status == PERIOD_CLOSED

    with pytest.raises(BusinessError) as ei:
        svc.create_voucher(
            db_session, voucher_date=date(2026, 9, 28),
            lines=[_line(coa["salary"], "D", 10.0), _line(coa["bank"], "C", 10.0)],
        )
    assert ei.value.status == 409
    assert "已结账" in ei.value.message


def test_close_period_blocked_by_draft_then_succeeds(db_session, coa):
    draft = _balanced_payment_voucher(db_session, coa)
    with pytest.raises(BusinessError, match="未过账草稿"):
        svc.close_period(db_session, "2026-09")
    svc.post_voucher(db_session, draft.id)
    assert svc.close_period(db_session, "2026-09").status == PERIOD_CLOSED


def test_reopen_must_follow_reverse_order(db_session, coa):
    oct_v = svc.create_voucher(
        db_session, voucher_date=date(2026, 10, 10),
        lines=[_line(coa["office"], "D", 50.0), _line(coa["bank"], "C", 50.0)],
    )
    svc.post_voucher(db_session, oct_v.id)
    svc.ensure_period(db_session, date(2026, 9, 1))  # 9 月无任何单据时需先建立期间
    svc.close_period(db_session, "2026-09")
    svc.close_period(db_session, "2026-10")

    # 2026-10 仍关闭时不允许跳过反结账 2026-09
    with pytest.raises(BusinessError, match="倒序"):
        svc.reopen_period(db_session, "2026-09")
    svc.reopen_period(db_session, "2026-10")
    sep = svc.reopen_period(db_session, "2026-09")
    assert sep.status == "OPEN"
