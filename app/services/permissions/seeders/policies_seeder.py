from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_instance
import json
from datetime import datetime , timezone
from fastapi.responses import JSONResponse

from app.common.models.model_permission import Policy

async def update_system_policies (db: AsyncSession, global_seeding= False)->None:
    
    try:
        policies = [
            {'label' : 'polyce1' , 'code' : 'PP1' , 'state': 1},
            {'label' : 'polyce2' , 'code' : 'PP2' , 'state': 1},
            {'label' : 'polyce4' , 'code' : 'PP3' , 'state': 1},
            {'label' : 'polyce5' , 'code' : 'PP4' , 'state': 1},
            {'label' : 'polyce6' , 'code' : 'PP5' , 'state': 1},
            {'label' : 'polyce7' , 'code' : 'PP6' , 'state': 1},
            {'label' : 'polyce7' , 'code' : 'PP7' , 'state': 1},
            {'label' : 'polyce8' , 'code' : 'PP8' , 'state': 1},
        ]

        statment = insert(Policy).values(policies)
        
        await db.execute(statment)
        await db.commit()
    except Exception as exception:
        await db.rollback()
        print (f"seeder ko . policies_seeder: {str(exception)}")

    print ("seeder ok!")
        

if __name__ == "__main__":
    import asyncio
    asyncio.run(update_system_policies())
    