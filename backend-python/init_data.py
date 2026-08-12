"""
初始化示例数据（对标领星WMS）

结构：仓库 → 库区（正品区/残次品区）→ 库位（带优先级）→ 商品 SKU
仅当商品表为空时执行，保证「一键启动」即可看到完整功能。
"""
from app.database import SessionLocal, Base, engine
from app.models import Product, Warehouse, Zone, Location


def init_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Product).count() > 0:
        print("示例数据已存在，跳过初始化")
        db.close()
        return

    print("初始化示例数据...")

    # ============ 商品 SKU ============
    products = [
        Product(name="蓝牙耳机 Pro", sku="SKU-001", unit="个",
                width=6, height=4, length=12, weight=0.05),
        Product(name="Type-C 数据线", sku="SKU-002", unit="条",
                width=1, height=1, length=100, weight=0.02),
        Product(name="无线充电板", sku="SKU-003", unit="个",
                width=9, height=0.8, length=9, weight=0.08),
        Product(name="手机壳 透明款", sku="SKU-004", unit="个",
                width=8, height=1, length=16, weight=0.03),
        Product(name="屏幕保护膜", sku="SKU-005", unit="张",
                width=6, height=0.1, length=14, weight=0.01),
    ]
    db.add_all(products)
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


if __name__ == "__main__":
    init_data()
