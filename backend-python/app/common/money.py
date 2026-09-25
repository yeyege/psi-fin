"""金额唯一强制转换入口 — 见 AGENTS.md §4「金额一律 Numeric(18,2) + Decimal，禁止浮点」

所有金额在「进入 service」与「离开 service」时都必须过 money()，除此之外禁止
在金额上做算术以外的转换。原因：

- Decimal 与 float 混算会直接 TypeError（`Decimal("1.00") + 0.0`），不是精度问题；
- 数据库聚合(`func.sum`)在不同方言下返回类型不一致：PostgreSQL/MySQL 返回 Decimal，
  SQLite 返回 float，所以聚合结果必须先 money() 收敛再参与比较；
- 本模块用 ROUND_HALF_UP，而迁移前服务层用的 Python round() 是银行家舍入
  （round(0.125, 2) == 0.12，money(0.125) == Decimal("0.13")）。业务上以四舍五入为准。
"""
from decimal import Decimal, ROUND_HALF_UP

# 金额统一 2 位小数，与 Numeric(18, 2) 对齐
MONEY_SCALE = Decimal("0.01")
ZERO = Decimal("0.00")


def money(value) -> Decimal:
    """把任意边界输入（None/int/float/str/Decimal）收敛为 2 位小数的 Decimal。

    float 先转 str 再构造 Decimal：`Decimal(0.1)` 会把二进制噪声全带进来
    （0.1000000000000000055511151231257827021181583404541015625），
    `Decimal(str(0.1))` 才是人看到的 0.1。
    """
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        decimal_value = value
    else:
        decimal_value = Decimal(repr(value) if isinstance(value, float) else str(value))
    return decimal_value.quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)
