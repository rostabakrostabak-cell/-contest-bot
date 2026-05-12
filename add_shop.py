import asyncio
import sys
sys.path.insert(0, '/app')

from app.db import SessionFactory
from app.models.shop import Shop

async def main():
    async with SessionFactory() as s:
        s.add(Shop(name="Test Shop", is_active=True))
        await s.commit()
    print("Done")

asyncio.run(main())
