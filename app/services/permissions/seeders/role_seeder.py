from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_instance
import json
from datetime import datetime , timezone
from fastapi.responses import JSONResponse

from app.common.models.Role import Role

async def update_system_roles (db: AsyncSession, global_seeding= False)->None:
    
    try:
        roles = [
            {'label' : 'Role1' , 'name' : 'Role1' ,'level' : 2 ,'configured_by' : 'azerty', 'code' : 'R1', 'state': 1},
            {'label' : 'role2' , 'name' : 'Role2' ,'level' : 2 ,'configured_by' : 'azerty','code' : 'R2' , 'state': 1},
            {'label' : 'Role4' , 'name' : 'Role3' ,'level' : 2 ,'configured_by' : 'azerty','code' : 'R3' , 'state': 1},
            {'label' : 'Role5' , 'name' : 'Role4' ,'level' : 2 ,'configured_by' : 'azerty','code' : 'R4' , 'state': 1},
            {'label' : 'Role6' , 'name' : 'Role5' ,'level' : 2 ,'configured_by' : 'azerty','code' : 'R5' , 'state': 1},
            {'label' : 'Role7' , 'name' : 'Role6' ,'level' : 2 ,'configured_by' : 'azerty','code' : 'R6' , 'state': 1},
            {'label' : 'Role7' , 'name' : 'Role7' ,'level' : 2 ,'configured_by' : 'azerty','code' : 'R7' , 'state': 1},
            {'label' : 'Role8' , 'name' : 'Role8' ,'level' : 2 ,'configured_by' : 'azerty','code' : 'R8' , 'state': 1},
        ]

        statment = insert(Role).values(roles)
        
        await db.execute(statment)
        await db.commit()
    except Exception as exception:
        await db.rollback()
        print (f"seeder ko . role_seeder: {str(exception)}")

    print ("seeder ok!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(update_system_roles())