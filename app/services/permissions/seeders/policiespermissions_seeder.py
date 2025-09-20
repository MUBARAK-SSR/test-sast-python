from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_instance
import json
from datetime import datetime , timezone
from fastapi.responses import JSONResponse

from app.common.models.model_permission import PolicyPermission

async def update_system_policies_permission (db: AsyncSession, global_seeding= False)->None:
    
    # creation of permissions

    try:

        policies_permissions = [
            {'policy_id' : '0a55a4a3-c0e6-42b2-82d0-2788340dd4f6' , 'permission_id' : '63f02a50-91b9-44cd-8a59-2af4ecb6ac9a' , 'state': 1},
            {'policy_id' : '0a55a4a3-c0e6-42b2-82d0-2788340dd4f6' , 'permission_id' : '91fb19a5-ba42-4cc1-bb00-6992eb58bf5a' , 'state': 1},
            {'policy_id' : '0a55a4a3-c0e6-42b2-82d0-2788340dd4f6' , 'permission_id' : 'b60ab9f4-19eb-4a10-8ecc-55e895ae2a97' , 'state': 1},
            {'policy_id' : '181aa2ab-880f-4547-989a-da5505ac6a90' , 'permission_id' : '63f02a50-91b9-44cd-8a59-2af4ecb6ac9a' , 'state': 1},
            {'policy_id' : '181aa2ab-880f-4547-989a-da5505ac6a90' , 'permission_iFd' : 'c953cdda-b34e-4c56-817b-abbd66f030c2' , 'state': 1},
            {'policy_id' : '63379ec4-8f1e-4138-b55f-fd914cf40a91' , 'permission_id' : '91fb19a5-ba42-4cc1-bb00-6992eb58bf5a' , 'state': 1},
            {'policy_id' : '63379ec4-8f1e-4138-b55f-fd914cf40a91' , 'permission_id' : '7ba4d2bf-1c9e-42d8-a650-41675a0c8358' , 'state': 1},
            {'policy_id' : '8f9ca4b7-f566-49ae-8e3a-e5203b79b505' , 'permission_id' : '7ba4d2bf-1c9e-42d8-a650-41675a0c8358' , 'state': 1},
            {'policy_id' : '8f9ca4b7-f566-49ae-8e3a-e5203b79b505' , 'permission_id' : '63f02a50-91b9-44cd-8a59-2af4ecb6ac9a' , 'state': 1},

            {'policy_id' : 'b77683b1-6011-48b0-91df-939486295545' , 'permission_id' : '7ba4d2bf-1c9e-42d8-a650-41675a0c8358' , 'state': 1},
            {'policy_id' : 'b77683b1-6011-48b0-91df-939486295545' , 'permission_id' : 'd38e2626-762d-4e3c-8b72-bd566dacae9f' , 'state': 1},
            {'policy_id' : 'b77683b1-6011-48b0-91df-939486295545' , 'permission_id' : 'd3cac979-04f7-49fb-b3c8-6333423fa89a' , 'state': 1},
            {'policy_id' : 'dd7ba0e7-47ff-4ff0-8e77-f228782b1b66' , 'permission_id' : 'd4e9dd58-b43a-49a3-ace8-c68d587f5f11' , 'state': 1},
            {'policy_id' : 'dd7ba0e7-47ff-4ff0-8e77-f228782b1b66' , 'permission_id' : 'd4e9dd58-b43a-49a3-ace8-c68d587f5f11' , 'state': 1},

            {'policy_id' : 'e53ce66f-74bd-4af4-b56e-33e6f2412d21' , 'permission_id' : '91fb19a5-ba42-4cc1-bb00-6992eb58bf5a' , 'state': 1},
            {'policy_id' : 'e53ce66f-74bd-4af4-b56e-33e6f2412d21' , 'permission_id' : 'b60ab9f4-19eb-4a10-8ecc-55e895ae2a97' , 'state': 1},
            {'policy_id' : 'fd59a6b5-bb9d-476b-a42f-43b6936af2e9' , 'permission_id' : 'c953cdda-b34e-4c56-817b-abbd66f030c2' , 'state': 1},
            {'policy_id' : 'fd59a6b5-bb9d-476b-a42f-43b6936af2e9' , 'permission_id' : 'd3cac979-04f7-49fb-b3c8-6333423fa89a' , 'state': 1}

        ]

        statment = insert(PolicyPermission).values(policies_permissions)
        
        await db.execute(statment)
        await db.commit()
    except Exception as exception:
        await db.rollback()
        print (f"seeder ko . policiespermissions_seeder: {str(exception)}")

    print ("seeder ok!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(update_system_policies_permission())
