from sqlalchemy import insert , delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_instance
import json
from datetime import datetime , timezone
from fastapi.responses import JSONResponse

from app.common.models.model_permission import Permission , PolicyPermission , Policy
from app.common.models.Role import Role



async def truncate_database_for_seeder (db: AsyncSession = get_db_instance , global_seeding= False)->None:
    
    try:
        
        await db.execute(delete(PolicyPermission))
        await db.commit()
        await db.execute(delete(Policy))
        await db.commit()
        await db.execute(delete(Permission))
        await db.commit()
        await db.execute(delete(Role))
        await db.commit()
    except Exception as exception:
        await db.rollback()
        print (f"seeder ko . permission_seeder: {str(exception)}")

    print ("seeder ok!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(truncate_database_for_seeder())