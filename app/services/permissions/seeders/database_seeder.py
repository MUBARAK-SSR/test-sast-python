from app.config.database import get_db_instance
from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.permissions.seeders.permission_seeder import update_system_permissions
from app.services.permissions.seeders.role_seeder import update_system_roles
from app.services.permissions.seeders.policies_seeder import update_system_policies
from app.services.permissions.seeders.policiespermissions_seeder import update_system_policies_permission
from app.services.permissions.seeders.truncatedatabase_seeder import truncate_database_for_seeder
from app.services.permissions.seeders.user_seeder import create_fake_users


async def updat_all_database(db: AsyncSession = Depends(get_db_instance)):
    try:

        await truncate_database_for_seeder(db, global_seeding=True)
        await update_system_permissions(db, global_seeding=True)
        await update_system_roles(db, global_seeding=True)
        await update_system_policies(db, global_seeding=True)
        await update_system_policies_permission(db, global_seeding=True)
        await create_fake_users(db, global_seeding=True)

    except Exception as exception:
        return JSONResponse(
            status_code=500,
            content=[
                {
                    'status_code': 500,
                    'status': 'error',
                    'message': "seeder failled",
                    'data': [f"{str(exception)}"]
                }
            ]
        )

    return JSONResponse(
        status_code=500,
        content=[
            {
                'status_code': 201,
                'status': 'success',
                'message': "seeders successful",
                'data': []
            }
        ]
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(updat_all_database())
