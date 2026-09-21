"""业务状态 / 类型枚举 — 单一事实来源

设计要点：
1. 一律继承 ``enum.StrEnum``（Python 3.11+），成员本身就是 str：
   - 写入 SQLAlchemy ``String`` 列时按普通字符串持久化（存 "PENDING" 而非枚举 repr）；
   - 与数据库读回的裸字符串 ``==`` 比较恒等；
   - JSON / Pydantic 序列化直接得到字符串值。
   因此引入枚举**无需数据迁移、不改变响应字节**。
2. 覆盖此前散落在各 service 的重复常量（PENDING/COMPLETED 等）与裸字符串字面量，
   改状态名只需改这一处。
"""
from enum import StrEnum


class OrderStatus(StrEnum):
    """仓储单据通用生命周期状态（入库/出库/退货/移库/调整/盘点 各取其子集）。"""

    PENDING = "PENDING"      # 待处理（待收货/待拣货/待盘点）
    COMPLETED = "COMPLETED"  # 已完成
    PICKED = "PICKED"        # 出库：已拣货（库存已锁定）
    REVIEWED = "REVIEWED"    # 出库：已复核
    SHIPPED = "SHIPPED"      # 出库：已发货（扣减锁定量）
    RECEIVED = "RECEIVED"    # 退货：已收货登记
    DONE = "DONE"            # 退货：处理完成


class WaveStatus(StrEnum):
    """波次状态机：CREATED → PICKING → COMPLETED。"""

    CREATED = "CREATED"
    PICKING = "PICKING"
    COMPLETED = "COMPLETED"


class PickingStatus(StrEnum):
    """拣货单状态机：CREATED → PICKED。"""

    CREATED = "CREATED"
    PICKED = "PICKED"


class SalesOrderStatus(StrEnum):
    """销售订单状态机：DRAFT → CONFIRMED → SHIPPED → COMPLETED / CANCELLED。"""

    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EntryType(StrEnum):
    """财务台账分录类型。"""

    RECEIVABLE = "RECEIVABLE"  # 应收
    PAYABLE = "PAYABLE"        # 应付


class FlowType(StrEnum):
    """库存流水类型（对应 InventoryFlow.flow_type）。"""

    INBOUND = "INBOUND"          # 入库（+available）
    OUTBOUND = "OUTBOUND"        # 出库发货（-locked）
    PICK_LOCK = "PICK_LOCK"      # 拣货锁定（-available +locked）
    MOVE_OUT = "MOVE_OUT"        # 移库出（-available）
    MOVE_IN = "MOVE_IN"          # 移库入（+available）
    ADJUST_IN = "ADJUST_IN"      # 调整盘盈（+available）
    ADJUST_OUT = "ADJUST_OUT"    # 调整盘亏（-available）
    RETURN_IN = "RETURN_IN"      # 退货收货（+available）


class OrderType(StrEnum):
    """库存流水来源单据类型（对应 InventoryFlow.order_type）。"""

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    TRANSFER = "TRANSFER"
    ADJUSTMENT = "ADJUSTMENT"
    RETURN = "RETURN"


class CountScope(StrEnum):
    """盘点范围类型（对应 CycleCount.scope_type）。"""

    ALL = "ALL"
    LOCATION = "LOCATION"
    ZONE = "ZONE"
    PRODUCT = "PRODUCT"


class ReturnSource(StrEnum):
    """退货来源（对应 ReturnOrder.source）。"""

    FBA = "FBA"
    SELLER = "SELLER"
    CARRIER = "CARRIER"


class Disposition(StrEnum):
    """退货处理方式（对应 ReturnOrderItem.disposition）。"""

    RESELL = "RESELL"    # 转正品（累加库存）
    RELABEL = "RELABEL"  # 换标后转正品（累加库存）
    SCRAP = "SCRAP"      # 报废（不累加库存）


class ActiveStatus(StrEnum):
    """基础数据启用/软删除状态（商品/客户/仓库通用）。"""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class LocationStatus(StrEnum):
    """库位占用状态（对应 Location.status）。"""

    FREE = "FREE"
    OCCUPIED = "OCCUPIED"


class ZoneType(StrEnum):
    """库区类型（对应 Zone.zone_type）。"""

    GOODS = "GOODS"    # 正品区
    DEFECT = "DEFECT"  # 残次品区
