from sqlalchemy import insert , delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_instance
import json
from datetime import datetime , timezone
from datetime import datetime , timezone

from app.common.models.User import User
from app.common.models.SubClient import SubClient as Customer
from app.common.models.SubClientUser import SubClientUser as CustomerUser





async def create_fake_users (db: AsyncSession = get_db_instance , global_seeding= False)->None:
    
    try:
        customers = [
            {
                'common_id' : 'customer_organization_1' , 
                'code' : 'customer_organization_1' ,
                'name' : 'customer_organization_1' , 
                'client_id' : 'e786a3a2-f79d-4e05-be7a-6d6a8b36f1d1' , 
                'slug' : 'tzezezez', 
                'domain' : 'zezezez', 
                'subscription_tier' : 'zezezez', 
                'subscription_expires_at' : datetime.now()
            }
        ]
        
        customer_statment = insert(Customer).values(customers)
        await db.execute(customer_statment)
        await db.commit()

        users = [
            {'name' : 'Therry' , 'email' : 'therrynaganga5@gmail.com', 'login' : 'therry', 'gender' : 'MA', 'phone' : 692674567  , 'state': 1},
            {'name' : 'Munich' , 'email' : 'merveille@gmail.com', 'login' : 'merveille', 'gender' : 'MA', 'phone' : 698764656  , 'state': 1},
            {'name' : 'Celine' , 'email' : 'celine@gmail.com', 'login' : 'celine', 'gender' : 'FI', 'phone' : 699876543  , 'state': 1},
        ]

        stmt = insert(User).values(users)
        
        await db.execute(stmt)
        await db.commit()


        customer_users_statement  = [
            {'sub_client_id' : "e786a3a2-f79d-4e05-be7a-6d6a8b36f1d1" , 'user_id' : 1, 'state': 1},
            {'sub_client_id' : "e786a3a2-f79d-4e05-be7a-6d6a8b36f1d1" , 'user_id' : 2, 'state': 1},
            {'sub_client_id' : "e786a3a2-f79d-4e05-be7a-6d6a8b36f1d1" , 'user_id' : 3, 'state': 1},
        ]

        result = insert(CustomerUser).values(customer_users_statement)

        await db.execute(result)
        await db.commit()

    except Exception as exception:
        await db.rollback()
        print (f"seeder ko . user_seeder: {str(exception)}")

    print ("seeder ok!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_fake_users())