"""
初始化示例数据（对标领星跨境仓储系统）

结构：仓库 → 库区（正品区/残次品区）→ 库位（带优先级）→ 商品 SKU
仅当商品表为空时执行，保证「一键启动」即可看到完整功能。
会计科目表（COA）独立初始化：仅当 accounts 表为空时预置最小科目集。
"""
from app.database import SessionLocal, Base, engine
from app.models import Product, Customer, Warehouse, Zone, Location


def init_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Product).count() > 0:
        print("示例数据已存在，跳过初始化")
        db.close()
        return

    print("初始化示例数据...")

    # ============ 商品 SKU（含 FNSKU 与箱规） ============
    products = [
        Product(name="蓝牙耳机 Pro", sku="SKU-001", fns_ku="X0007EL2Q1", case_qty=20,
                unit="个", width=6, height=4, length=12, weight=0.05),
        Product(name="Type-C 数据线", sku="SKU-002", fns_ku="X0008FN3T2", case_qty=100,
                unit="条", width=1, height=1, length=100, weight=0.02),
        Product(name="无线充电板", sku="SKU-003", fns_ku="X0009GH4U3", case_qty=12,
                unit="个", width=9, height=0.8, length=9, weight=0.08),
        Product(name="手机壳 透明款", sku="SKU-004", fns_ku="X0010IJ5V4", case_qty=50,
                unit="个", width=8, height=1, length=16, weight=0.03),
        Product(name="屏幕保护膜", sku="SKU-005", fns_ku="X0011KL6W5", case_qty=200,
                unit="张", width=6, height=0.1, length=14, weight=0.01),
    ]
    db.add_all(products)
    db.flush()

    # ============ 客户（分层 A/B/C） ============
    customers = [
        Customer(code="CUST-A01", name="领星科技（深圳）有限公司", tier="A",
                 contact="张经理", phone="13800138001"),
        Customer(code="CUST-B02", name="湾区跨境贸易有限公司", tier="B",
                 contact="李主管", phone="13800138002"),
        Customer(code="CUST-C03", name="个体卖家陈先生", tier="C",
                 contact="陈先生", phone="13800138003"),
    ]
    db.add_all(customers)
    db.flush()

    # ============ 仓库 ============
    wh_a = Warehouse(code="WH-A", name="广州主仓")
    wh_b = Warehouse(code="WH-B", name="深圳保税仓")
    db.add_all([wh_a, wh_b])
    db.flush()

    # ============ 库区（正品区/残次品区） ============
    zones = [
        Zone(warehouse_id=wh_a.id, code="A-GOODS", name="A 正品区", zone_type="GOODS"),
        Zone(warehouse_id=wh_a.id, code="A-DEFECT", name="A 残次品区", zone_type="DEFECT"),
        Zone(warehouse_id=wh_b.id, code="B-GOODS", name="B 正品区", zone_type="GOODS"),
        Zone(warehouse_id=wh_b.id, code="B-DEFECT", name="B 残次品区", zone_type="DEFECT"),
    ]
    db.add_all(zones)
    db.flush()
    a_goods, a_defect, b_goods, b_defect = zones

    # ============ 库位（priority 越大越优先推荐上架） ============
    locations = [
        # WH-A 正品区
        Location(zone_id=a_goods.id, warehouse_id=wh_a.id, code="A-01-01", priority=5),
        Location(zone_id=a_goods.id, warehouse_id=wh_a.id, code="A-01-02", priority=4),
        Location(zone_id=a_goods.id, warehouse_id=wh_a.id, code="A-02-01", priority=3),
        # WH-A 残次品区
        Location(zone_id=a_defect.id, warehouse_id=wh_a.id, code="A-D-01", priority=1),
        # WH-B 正品区
        Location(zone_id=b_goods.id, warehouse_id=wh_b.id, code="B-01-01", priority=3),
        Location(zone_id=b_goods.id, warehouse_id=wh_b.id, code="B-01-02", priority=2),
    ]
    db.add_all(locations)

    db.commit()
    db.close()
    print("示例数据初始化完成")


def init_admin():
    """保证存在默认管理员账号（admin / admin123），仅当 users 表为空时。"""
    from app.models import User
    from app.services.auth_service import hash_password

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin"))
            db.commit()
            print("默认管理员已创建: admin / admin123")
    finally:
        db.close()


# 预置最小科目集（spec: accounting-core「预置最小科目集」，管理会计口径）：
# (code, name, category, direction, parent_code, aux_dimensions)
_PRESET_ACCOUNTS = [
    ("1001", "库存现金", "ASSET", "DEBIT", None, ""),
    ("1002", "银行存款", "ASSET", "DEBIT", None, ""),
    ("1122", "应收账款", "ASSET", "DEBIT", None, ""),
    ("112201", "客户应收", "ASSET", "DEBIT", "1122", "CUSTOMER"),
    ("1405", "库存商品", "ASSET", "DEBIT", None, "WAREHOUSE"),
    ("2202", "应付账款", "LIABILITY", "CREDIT", None, ""),
    ("220201", "外部供应商", "LIABILITY", "CREDIT", "2202", "SUPPLIER"),
    ("220202", "入库暂估", "LIABILITY", "CREDIT", "2202", "SUPPLIER"),
    ("2221", "应交税费", "LIABILITY", "CREDIT", None, ""),
    ("222101", "待销项税额", "LIABILITY", "CREDIT", "2221", ""),
    ("222102", "待进项税额", "LIABILITY", "CREDIT", "2221", ""),
    ("4103", "本年利润", "EQUITY", "CREDIT", None, ""),
    ("6001", "主营业务收入", "REVENUE", "CREDIT", None, ""),
    ("6401", "主营业务成本", "EXPENSE", "DEBIT", None, ""),
    ("6602", "管理费用", "EXPENSE", "DEBIT", None, ""),
    ("660201", "工资福利", "EXPENSE", "DEBIT", "6602", ""),
    ("660202", "办公费", "EXPENSE", "DEBIT", "6602", ""),
    ("660203", "差旅费", "EXPENSE", "DEBIT", "6602", ""),
]


def init_coa():
    """预置最小会计科目集，仅当 accounts 表为空时执行。"""
    from app.models import Account
    from app.services import accounting_service

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Account).count() > 0:
            return
        by_code = {}
        for code, name, category, direction, parent_code, aux in _PRESET_ACCOUNTS:
            parent = by_code.get(parent_code) if parent_code else None
            account = accounting_service.create_account(
                db, code=code, name=name, category=category,
                direction=direction,
                parent_id=parent.id if parent else None,
                aux_dimensions=aux,
            )
            by_code[code] = account
        db.commit()
        print(f"会计科目表已预置 {len(_PRESET_ACCOUNTS)} 个科目")
    finally:
        db.close()


if __name__ == "__main__":
    init_data()
    init_admin()
    init_coa()
