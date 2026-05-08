"""
初始化示例数据
"""
from app.database import SessionLocal, engine, Base
from app.models import Product, Warehouse, Location, Inventory


def init_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Product).count() > 0:
        print("示例数据已存在，跳过初始化")
        db.close()
        return

    print("初始化示例数据...")

    # 商品
    p1 = Product(name="蓝牙耳机 Pro", sku="SKU-001", unit="个")
    p2 = Product(name="Type-C 数据线", sku="SKU-002", unit="条")
    p3 = Product(name="无线充电板", sku="SKU-003", unit="个")
    p4 = Product(name="手机壳 透明款", sku="SKU-004", unit="个")
    p5 = Product(name="屏幕保护膜", sku="SKU-005", unit="张")
    db.add_all([p1, p2, p3, p4, p5])
    db.flush()

    # 仓库
    wh1 = Warehouse(code="WH-A", name="广州主仓")
    wh2 = Warehouse(code="WH-B", name="深圳保税仓")
    db.add_all([wh1, wh2])
    db.flush()

    # 库位
    loc1 = Location(warehouse_id=wh1.id, code="WH-A-01-01", status="OCCUPIED")
    loc2 = Location(warehouse_id=wh1.id, code="WH-A-01-02", status="OCCUPIED")
    loc3 = Location(warehouse_id=wh1.id, code="WH-A-02-01", status="FREE")
    loc4 = Location(warehouse_id=wh2.id, code="WH-B-01-01", status="FREE")
    db.add_all([loc1, loc2, loc3, loc4])
    db.flush()

    # 库存
    db.add_all([
        Inventory(product_id=p1.id, location_code=loc1.code, quantity=150),
        Inventory(product_id=p1.id, location_code=loc2.code, quantity=80),
        Inventory(product_id=p2.id, location_code=loc1.code, quantity=300),
        Inventory(product_id=p3.id, location_code=loc2.code, quantity=5),
        Inventory(product_id=p4.id, location_code=loc1.code, quantity=8),
    ])

    db.commit()
    db.close()
    print(f"示例数据初始化完成")


if __name__ == "__main__":
    init_data()
