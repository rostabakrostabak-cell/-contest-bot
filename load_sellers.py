#!/usr/bin/env python3
"""Загрузка продавцов из CSV в БД."""
import csv
import sys
sys.path.insert(0, '/app')

import asyncio
from app.db import SessionFactory
from app.models.shop import Shop
from app.models.seller import Seller, SellerCategory, SellerSource


ROLE_MAP = {
    "Дневной продавец": SellerCategory.DAY,
    "Ночной продавец": SellerCategory.NIGHT,
    "Старший продавец": SellerCategory.DAY,
}


async def main():
    async with SessionFactory() as db:
        # Сначала соберём магазины
        shops = {}
        result = await db.execute("SELECT id, name FROM shops")
        for row in result:
            shops[row.name] = row.id

        print(f"Найдено магазинов: {len(shops)}")

        # Добавим новые магазины из CSV
        csv_shops = set()
        sellers_to_add = []

        with open('/tmp/sellers.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                shop_name = row['Магазин'].strip()
                seller_name = row['Сотрудник'].strip()
                role = row['Роль'].strip()

                if shop_name not in csv_shops:
                    csv_shops.add(shop_name)

                if shop_name not in shops:
                    # Новый магазин
                    shop = Shop(name=shop_name, is_active=True)
                    db.add(shop)
                    await db.flush()
                    shops[shop_name] = shop.id
                    print(f"Добавлен магазин: {shop_name}")

                category = ROLE_MAP.get(role, SellerCategory.DAY)

                # Проверяем, есть ли уже продавец
                result = await db.execute(
                    "SELECT id FROM sellers WHERE full_name = :name LIMIT 1",
                    {"name": seller_name}
                )
                existing = result.fetchone()

                if not existing:
                    seller = Seller(
                        full_name=seller_name,
                        shop_id=shops[shop_name],
                        category=category,
                        source=SellerSource.PRELOAD,
                    )
                    db.add(seller)
                    sellers_to_add.append(seller_name)

        await db.commit()
        print(f"\nДобавлено продавцов: {len(sellers_to_add)}")
        for name in sellers_to_add:
            print(f"  - {name}")


if __name__ == '__main__':
    asyncio.run(main())
