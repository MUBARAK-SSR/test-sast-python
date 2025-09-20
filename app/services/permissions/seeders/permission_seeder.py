from sqlalchemy import insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_instance
import json
from datetime import datetime, timezone
from fastapi.responses import JSONResponse

from app.common.models.model_permission import Permission


async def update_system_permissions(db: AsyncSession = get_db_instance, global_seeding=False) -> None:
    try:
        permissions = [
            {'label': 'Permission1', 'code': 'P1', 'state': 1},
            {'label': 'Permission2', 'code': 'P2', 'state': 1},
            {'label': 'Permission3', 'code': 'P3', 'state': 1},
            {'label': 'Permission4', 'code': 'P4', 'state': 1},
            {'label': 'Permission5', 'code': 'P5', 'state': 1},
            {'label': 'Permission6', 'code': 'P6', 'state': 1},
            {'label': 'Permission7', 'code': 'P7', 'state': 1},
            {'label': 'Permission8', 'code': 'P8', 'state': 1},
            {'label': 'Permission9', 'code': 'P9', 'state': 1},
            {'label': 'decaisser', 'code': 'DCS', 'state': 1}
        ]

        stmt = insert(Permission).values(permissions)

        await db.execute(stmt)
        await db.commit()
    except Exception as exception:
        await db.rollback()
        print(f"seeder ko . permission_seeder: {str(exception)}")

    print("seeder ok!")


if __name__ == "__main__":
    import asyncio

    asyncio.run(update_system_permissions())
