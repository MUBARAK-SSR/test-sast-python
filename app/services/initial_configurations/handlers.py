from typing import List, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import select, and_, insert, or_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timezone, datetime, date
from uuid import UUID, uuid4
from sqlalchemy.orm import joinedload, contains_eager, selectinload
from starlette import status

from app.common.auth import JWTBearer
from app.common.models.Activity import Activity
from app.common.models.Client import Client
from app.common.models.Operator import Operator
from app.common.models.PaymentAccount import PaymentAccount
from app.common.models.SubClient import SubClient
from app.common.models.SubClientActivity import SubClientActivity
from app.common.models.SubClientUser import SubClientUser
from app.common.models.User import User
from app.common.pagination import PaginatedResponse, paginate
from app.common.s3 import upload_file_to_s3
from app.services.cycle_configurations.constants import PaymentType, PaymentAccountType
from app.services.initial_configurations.schemas import ClientCreateSchema, ClientResponseSchema, CreateUserSchema, \
    ClientResponseSchemaOut, CreateUserOutSchema, ClientSchema, ClientResponseOut, SubClientCreateSchema, \
    SubClientResponse, OperatorCreateSchema, SubClientPaymentAccountSchema, UserPaymentAccountSchema, \
    OperatorResponseSchema, PaymentAccountResponseSchema, ActivityOut, MerchantPaymentAccountSchema, \
    SubClientActivitiesSchema


async def create_client_with_sub_client(data: ClientCreateSchema, db: AsyncSession) -> ClientResponseSchema:
    try:
        new_client = Client(**data.model_dump(exclude={"sub_clients"}))
        db.add(new_client)
        await db.flush()
        for entry in data.sub_clients:
            # 1. Créer le user
            sub_client = SubClient(**entry.model_dump(), client_id=new_client.id)
            db.add(sub_client)
            await db.flush()
        await db.commit()
        # Fetch client with sub_clients eagerly loaded
        result = await db.execute(
            select(Client).where(Client.id == new_client.id).options(joinedload(Client.sub_clients)))
        client = result.scalars().first()
        return ClientResponseSchema.from_orm(client)
    except IntegrityError as e:
        await db.rollback()
        if "sub_clients_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A sub client with name '{entry.name}' already exist.")
        if "sub_clients_common_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A sub client with common_id '{entry.common_id}' already exist.")
        if "sub_clients_code_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A sub client with code '{entry.code}' already exist.")
        if "clients_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A client with name '{data.name}' already exist.")
        if "clients_common_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A client with common_id '{data.common_id}' already exist.")
        if "clients_code_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A client with code '{data.code}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_sub_client(data: SubClientCreateSchema, db: AsyncSession) -> SubClientCreateSchema:
    try:
        # Vérifier que le client existe
        client_result = await db.execute(select(Client).where(Client.id == data.client_id,
                                                              Client.is_active == True))
        client = client_result.scalars().first()
        if not client:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client not found")

        sub_client = SubClient(**data.model_dump())
        db.add(sub_client)
        await db.commit()
        return SubClientResponse.from_orm(sub_client)
    except IntegrityError as e:
        await db.rollback()
        if "sub_clients_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A sub client with name '{data.name}' already exist.")
        if "sub_clients_code_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A sub client with code '{data.code}' already exist.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# async def update_client_with_sub_client(data: ClientCreateSchema, db: AsyncSession, id: UUID) -> ClientResponseSchema:
#     try:
#         result = await db.execute(select(Client).where(Client.id == id, Client.is_active == True)
#                                   .options(joinedload(Client.sub_clients)))
#         client = result.unique().scalars().first()
#         if not client:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Client not found")
#
#         for key, value in data.model_dump(exclude_unset=True, exclude={"sub_clients"}).items():
#             setattr(client, key, value)
#         client.updated_at = datetime.now(timezone.utc)
#
#         # Fetch existing sub-clients (non-deleted)
#         existing_sub_clients = {sc.id: sc for sc in client.sub_clients if sc.deleted_at is None}
#         new_sub_client_data = {entry.code: entry for entry in data.sub_clients}  # Use code as key for matching
#
#         # Identify sub-clients to delete (soft deletion)
#         for sub_client_id, sub_client in existing_sub_clients.items():
#             if sub_client.code not in new_sub_client_data:
#                 # await db.execute(delete(SubClient).where(SubClient.id == sub_client_id, SubClient.is_active == True))
#                 sub_client.deleted_at = datetime.now(timezone.utc)
#                 sub_client.updated_at = datetime.now(timezone.utc)
#                 db.add(sub_client)
#
#         # Update or create sub-clients
#         for entry in data.sub_clients:
#             existing_sub_client = next(
#                 (sc for sc in existing_sub_clients.values() if sc.code == entry.code and sc.deleted_at is None),
#                 None
#             )
#             if existing_sub_client:
#                 # Update existing sub-client
#                 for key, value in entry.model_dump().items():
#                     setattr(existing_sub_client, key, value)
#                 existing_sub_client.updated_at = datetime.now(timezone.utc)
#                 db.add(existing_sub_client)
#             else:
#                 # Create new sub-client
#                 new_sub_client = SubClient(
#                     **entry.model_dump(),
#                     client_id=client.id,
#                 )
#                 db.add(new_sub_client)
#
#         db.add(client)
#         await db.commit()
#         await db.refresh(client)
#         # Fetch client with sub_clients for response
#         result = await db.execute(select(Client).where(Client.id == id, Client.is_active == True)
#                                   .options(joinedload(Client.sub_clients)))
#         client = result.unique().scalars().first()
#         return ClientResponseSchema.from_orm(client)
#     except IntegrityError as e:
#         await db.rollback()
#         if "sub_clients_name_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A sub client with name '{entry.name}' already exist.")
#         if "sub_clients_code_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A sub client with code '{entry.code}' already exist.")
#         if "sub_clients_common_id_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A sub client with common id '{entry.common_id}' already exist.")
#         if "clients_name_cycle_id_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A client with name '{data.name}' already exist.")
#         if "clients_code_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A client with code '{data.code}' already exist.")
#         if "clients_common_id_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A client with common id '{entry.common_id}' already exist.")
#         else:
#             raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                                 "Database integrity error occured.")
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_client(data: ClientSchema, db: AsyncSession, client_id: UUID) -> ClientResponseOut:
    try:
        # Vérifier que le client existe
        client_result = await db.execute(select(Client).where(Client.id == client_id,
                                                              Client.is_active == True))
        client = client_result.scalars().first()
        if not client:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client not found")

        for field, value in data.model_dump().items():
            setattr(client, field, value)
        client.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return ClientResponseOut.from_orm(client)

    except IntegrityError as e:
        await db.rollback()
        if "clients_name_cycle_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A client with name '{data.name}' already exist.")
        if "clients_code_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A client with code '{data.code}' already exist.")
        if "clients_common_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A client with common id '{data.common_id}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_sub_client(data: SubClientCreateSchema, db: AsyncSession, sub_client_id: UUID) -> SubClientResponse:
    try:
        # Vérifier que le client existe
        client_result = await db.execute(select(Client).where(Client.id == data.client_id,
                                                              Client.is_active == True))
        client = client_result.scalars().first()
        if not client:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client not found")

        # Vérifie que le sous client existe
        result = await db.execute(
            select(SubClient).where(SubClient.id == sub_client_id, SubClient.is_active == True))
        existing = result.scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub client not found")

        for field, value in data.model_dump().items():
            setattr(existing, field, value)
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return SubClientResponse.from_orm(existing)
    except IntegrityError as e:
        await db.rollback()
        if "sub_clients_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A sub client with name '{data.name}' already exist.")
        if "sub_clients_code_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A sub client with code '{date.code}' already exist.")
        if "sub_clients_common_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A sub client with common id '{data.common_id}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def toggle_activation_client(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(select(Client).where(Client.id == id))
        client = result.scalars().first()
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Client not found")

        # Toggle client activation state
        client.is_active = not client.is_active
        new_status = client.is_active

        # Update all associated subclients
        subclients_result = await db.execute(select(SubClient).where(SubClient.client_id == id))
        subclients = subclients_result.scalars().all()
        for subclient in subclients:
            subclient.is_active = new_status

        await db.commit()
        state = "activated" if new_status else "deactivated"
        return {"message": f"Client and its subclients {state} successfully"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def toggle_activation_sub_client(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(select(SubClient).where(SubClient.id == id))
        sub_client = result.scalars().first()
        if not sub_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sub client not found")

        sub_client.is_active = not sub_client.is_active
        await db.commit()

        state = "activated" if sub_client.is_active else "deactivated"
        return {"message": f"Sub client {state} successfully"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_client(db: AsyncSession, page: int, size: int, base_url: str, id: UUID) -> \
        PaginatedResponse[ClientResponseSchemaOut]:
    try:
        query = (
            select(Client)
            .where(Client.is_active == True)
            .outerjoin(SubClient, and_(Client.id == SubClient.client_id, SubClient.is_active == True))
            .options(contains_eager(Client.sub_clients))
        )
        if id is not None:
            query = query.where(Client.id == id)
        return await paginate(db, query, ClientResponseSchemaOut, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def register_users(sub_client_id: UUID, data: List[CreateUserSchema], db: AsyncSession) -> dict:
    try:
        result = await db.execute(
            select(SubClient).where(SubClient.common_id == sub_client_id, SubClient.is_active == True))
        sub_client = result.scalar_one_or_none()
        if not sub_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub client not found")

        created_users = []
        for entry in data:
            result = await db.execute(
                select(User).where(User.email == entry.email))
            existing_user = result.scalar_one_or_none()

            if not existing_user:
                # 1. Créer le user
                user = User(email=entry.email, phone_number=entry.phone_number, is_active=True, name=entry.name)
                db.add(user)
                await db.flush()
                user_id = user.id
            else:
                user_id = existing_user.id

            result = await db.execute(
                select(SubClientUser).where(SubClientUser.user_id == user_id,
                                            SubClientUser.sub_client_id == sub_client.id))
            existing_user_sub_client = result.scalar_one_or_none()
            if existing_user_sub_client:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="User attached to this subsclient already exist")
            await db.execute(insert(SubClientUser).values(user_id=user_id, sub_client_id=sub_client.id,
                                                          member_nui=entry.member_niu))
            await db.flush()

            created_users.append({"member_niu": entry.member_niu, "user_id": user_id})
        await db.commit()
        return {"message": "Souscripteurs enregistrés avec succès", "data": created_users}

    except IntegrityError as e:
        await db.rollback()
        if "sub_client_user_member_nui_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A user with member_nui '{entry.member_niu}' already exist in this service.")
        if "users_phone_number_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A user with phone '{entry.phone_number}' already exist in this service.")
        if "users_email_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A user with email '{entry.email}' already exist in this service.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def toggle_activation_user(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(select(User).where(User.id == id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"user not found")

        user.is_active = not user.is_active
        await db.commit()

        state = "activated" if user.is_active else "deactivated"
        return {"message": f"User {state} successfully"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_users(db: AsyncSession, page: int, size: int, base_url: str, state: bool, id: UUID) -> \
        PaginatedResponse[CreateUserOutSchema]:
    try:
        query = select(User).where(User.is_active == True)
        # Add filters conditionally
        if state is not None:
            query = query.where(User.is_active == state)
        if id is not None:
            query = query.where(User.id == id)

        return await paginate(db, query, CreateUserOutSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# async def create_type_operator(data: TypeOperatorCreateSchema, db: AsyncSession) -> TypeOperator:
#     try:
#         type = TypeOperator(**data.model_dump())
#         db.add(type)
#         await db.commit()
#         await db.refresh(type)
#         return type
#     except IntegrityError as e:
#         await db.rollback()
#         if "type_operators_name_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A type operator with name '{data.name}' already exist.")
#         if "type_operators_common_id_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A type operator with common id '{data.common_id}' already exist.")
#         else:
#             raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                                 "Database integrity error occured.")
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
#
#
# async def update_type_operator(data: TypeOperatorCreateSchema, db: AsyncSession, common_id: str) -> TypeOperator:
#     try:
#         result = await db.execute(
#             select(TypeOperator).where(TypeOperator.common_id == common_id, TypeOperator.is_active == True))
#         type_operator = result.scalar_one_or_none()
#         if not type_operator:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Type operator not found")
#
#         for key, value in data.model_dump(exclude_unset=True).items():
#             setattr(type_operator, key, value)
#         type_operator.updated_at = datetime.now(timezone.utc)
#         db.add(type_operator)
#         await db.commit()
#         await db.refresh(type_operator)
#         return type_operator
#     except IntegrityError as e:
#         await db.rollback()
#         if "type_operators_name_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A type operator with name '{data.name}' already exist.")
#         if "type_operators_common_id_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A type operator with common id '{data.common_id}' already exist.")
#         else:
#             raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                                 "Database integrity error occured.")
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
#
#
# async def list_type_operator(db: AsyncSession, page: int, size: int, base_url: str) -> \
#         PaginatedResponse[TypeOperatorResponseSchema]:
#     try:
#         query = select(TypeOperator).where(TypeOperator.is_active == True)
#         return await paginate(db, query, TypeOperatorResponseSchema, page, size, base_url)
#     except Exception as e:
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
#
#
# async def toggle_activation_type_operator(db: AsyncSession, common_id: str) -> dict:
#     
#     try:
#         result = await db.execute(
#             select(TypeOperator).where(TypeOperator.common_id == common_id, TypeOperator.is_active == True))
#         type_op = result.scalars().first()
#
#         if not type_op:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Type operator not found")
#
#         type_op.deleted_at = datetime.now(timezone.utc)
#         await db.commit()
#
#         return {"message": "Type operator deleted successfully"}
#     except IntegrityError as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                             "Database integrity error occured.")
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_operator(data: OperatorCreateSchema, db: AsyncSession) -> Operator:
    try:
        # # Vérifier que le type d’opération existe
        # type_op_result = await db.execute(select(TypeOperator).where(TypeOperator.common_id == data.type_operator_id,
        #                                                              TypeOperator.is_active == True))
        # type_op = type_op_result.scalars().first()
        # if not type_op:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type operator not found")

        operator = Operator(**data.model_dump())
        db.add(operator)
        await db.commit()
        await db.refresh(operator)
        return operator
    except IntegrityError as e:
        await db.rollback()
        if "operators_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"An operator with name '{data.name}' already exist.")
        if "operators_common_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"An operator with common id '{data.common_id}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_operator(data: OperatorCreateSchema, db: AsyncSession, common_id: str) -> Operator:
    try:
        # # Vérifier que le type d’opération existe
        # type_op_result = await db.execute(select(TypeOperator).where(TypeOperator.common_id == data.type_operator_id,
        #                                                              TypeOperator.is_active == True))
        # type_op = type_op_result.scalars().first()
        # if not type_op:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Type operator not found")

        # Vérifie que l'operateur existe
        result = await db.execute(
            select(Operator).where(Operator.common_id == common_id, Operator.is_active == True))
        existing_operator = result.scalar_one_or_none()
        if not existing_operator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")

        for field, value in data.model_dump().items():
            setattr(existing_operator, field, value)
        existing_operator.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return existing_operator
    except IntegrityError as e:
        await db.rollback()
        if "operators_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"An operator with name '{data.name}' already exist.")
        if "operators_common_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"An operator with common id '{data.common_id}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def toggle_activation_operator(db: AsyncSession, common_id: str) -> dict:
    try:
        result = await db.execute(
            select(Operator).where(Operator.common_id == common_id))
        operator = result.scalars().first()
        if not operator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Operator not found")

        operator.is_active = not operator.is_active
        await db.commit()

        state = "activated" if operator.is_active else "deactivated"
        return {"message": f"Operator {state} successfully"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_operator(db: AsyncSession, page: int, size: int, base_url: str, active: bool, id: UUID) -> \
        PaginatedResponse[OperatorResponseSchema]:
    try:
        query = select(Operator)
        if active is not None:
            query = query.where(Operator.is_active == active)
        if id is not None:
            query = query.where(Client.id == id)
        return await paginate(db, query, OperatorResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def validate_payment_account_data(data: SubClientPaymentAccountSchema | UserPaymentAccountSchema,
                                        db: AsyncSession, operation: str, id: UUID = None):
    # Vérifie que l'operateur existe
    result = await db.execute(
        select(Operator).where(Operator.id == data.operator_id, Operator.is_active == True))
    operator = result.scalar_one_or_none()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")

    validation_errors = []
    if operator.type_operator == PaymentType.bank:
        # mobile_number must not be provided
        if data.mobile_number is not None:
            validation_errors.append("mobile_number must not be provided when type_operator is 'bank'.")
        # All other fields must be provided
        required_fields = ["bank_account_number", "agency_number", "payment_counter", "key"]
        missing_fields = [field for field in required_fields if
                          getattr(data, field) is None or getattr(data, field).strip() is ""]
        # if data.rib is None:
        #     missing_fields.append("rib")
        if missing_fields:
            validation_errors.append(
                f"The following fields are required when type_operator is 'bank': {', '.join(missing_fields)}.")
        # Raise all validation errors at once
        if validation_errors:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="; ".join(validation_errors))

        query = select(PaymentAccount).where(PaymentAccount.bank_account_number == data.bank_account_number,
                                             PaymentAccount.agency_number == data.agency_number,
                                             PaymentAccount.payment_counter == data.payment_counter,
                                             PaymentAccount.key == data.key)
        result = await db.execute(query)
        existing_account = result.scalar_one_or_none()

        if existing_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This Bank account already exist")
    elif operator.type_operator == PaymentType.mopay:
        # Only mobile_number must be provided
        if data.mobile_number is None or data.mobile_number.strip() is "":
            validation_errors.append("mobile_number is required when type_operator is 'mopay'.")
        # All other fields must not be provided
        forbidden_fields = ["rib", "bank_account_number", "agency_number", "payment_counter", "key"]
        provided_fields = [field for field in forbidden_fields if
                           getattr(data, field) is not None and (field != "rib" or getattr(data, field) != None)]
        if provided_fields:
            validation_errors.append(
                f"The following fields must not be provided when type_operator is 'mopay': {', '.join(provided_fields)}.")

        # Raise all validation errors at once
        if validation_errors:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="; ".join(validation_errors))
        query = select(PaymentAccount).where(PaymentAccount.mobile_number == data.mobile_number)

        result = await db.execute(query)
        existing_account = result.scalar_one_or_none()
        if existing_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This Mopay account already exist for a user")


async def create_merchant_account(data: MerchantPaymentAccountSchema, db: AsyncSession, token: str,
                                  merchant_code_type: str):
    try:
        # Vérifie que le sous client existe
        result = await db.execute(
            select(SubClient).where(SubClient.id == data.sub_client_id, SubClient.is_active == True))
        sub_client = result.scalar_one_or_none()
        if not sub_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub Client not found")

        # Vérifie que l'operateur existe et est de type mopay
        result = await db.execute(
            select(Operator).where(Operator.id == data.operator_id, Operator.is_active == True,
                                   Operator.type_operator == PaymentType.mopay))
        operator = result.scalar_one_or_none()
        if not operator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator of type mopay not found")

        account_type = PaymentAccountType.sim_mere if merchant_code_type == "mere" else PaymentAccountType.sim_fille
        new_account = PaymentAccount(**data.model_dump(), account_type=account_type,
                                     configured_by=JWTBearer.decode_jwt(token).get("user_id"), )
        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)
        message = "Parent" if merchant_code_type == "mere" else "Child"
        return {"message": f"{message} SIM card payment account successfully registered"}
    except IntegrityError as e:
        await db.rollback()
        if "payment_accounts_merchant_code_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,f"This merchant code already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_merchant_account(data: MerchantPaymentAccountSchema, db: AsyncSession, token: str, id: UUID,
                                  merchant_code_type: str):
    try:
        account_type = PaymentAccountType.sim_mere if merchant_code_type == "mere" else PaymentAccountType.sim_fille
        # Vérifie que le compte bancaire existe
        result = await db.execute(
            select(PaymentAccount).where(PaymentAccount.id == id, PaymentAccount.sub_client_id == data.sub_client_id,
                                         PaymentAccount.account_type == account_type,
                                         PaymentAccount.is_active == True))
        existing_account = result.scalar_one_or_none()
        message = "Parent" if merchant_code_type == "mere" else "Child"
        if not existing_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"{message} SIM card payment account not found for this sub client")

        # Vérifie que l'operateur existe et est de type mopay
        result = await db.execute(
            select(Operator).where(Operator.id == data.operator_id, Operator.is_active == True,
                                   Operator.type_operator == PaymentType.mopay))
        operator = result.scalar_one_or_none()
        if not operator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator of type mopay not found")

        for field, value in data.model_dump().items():
            setattr(existing_account, field, value)
        existing_account.configured_by = JWTBearer.decode_jwt(token).get("user_id")
        existing_account.updated_at = datetime.now(timezone.utc)

        await db.commit()

        account_type = PaymentAccountType.sim_mere if merchant_code_type == "mere" else PaymentAccountType.sim_fille
        new_account = PaymentAccount(**data.model_dump(), account_type=account_type,
                                     configured_by=JWTBearer.decode_jwt(token).get("user_id"), )

        for field, value in data.model_dump(exclude={"rib"}).items():
            setattr(existing_account, field, value)
        existing_account.configured_by = JWTBearer.decode_jwt(token).get("user_id")
        existing_account.updated_at = datetime.now(timezone.utc)

        return {"message": f"{message} SIM card payment account successfully updated"}
    except IntegrityError as e:
        await db.rollback()
        if "payment_accounts_merchant_code_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,f"This merchant code already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_sub_client_payment_account(data: SubClientPaymentAccountSchema, db: AsyncSession, token: str):
    try:
        # Vérifie que le sous client existe
        result = await db.execute(
            select(SubClient).where(SubClient.id == data.sub_client_id, SubClient.is_active == True))
        sub_client = result.scalar_one_or_none()
        if not sub_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub Client not found")

        await validate_payment_account_data(data, db, "create")

        uploaded_files_url = None
        uploaded_files_name = None
        if data.rib:
            if data.rib.content_type not in ("image/png", "image/jpeg", "application/pdf"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type de fichier non supporté.")
            s3_url, key = await upload_file_to_s3(data.rib, "rib_sub_clients", f"rib_{str(uuid4())}")
            if s3_url:
                uploaded_files_url = s3_url
                uploaded_files_name = key

        new_account = PaymentAccount(**data.model_dump(exclude={"rib"}), account_type=PaymentAccountType.sub_client,
                                     configured_by=JWTBearer.decode_jwt(token).get("user_id"),
                                     rib_file_name=uploaded_files_name if uploaded_files_name else None,
                                     rib_file_url=uploaded_files_url if uploaded_files_url else None,
                                     )
        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)
        return {"message": "Sub client payment account successfully registered"}
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_sub_client_payment_account(data: SubClientPaymentAccountSchema, db: AsyncSession, token: str,
                                            id: UUID):
    try:
        # Vérifie que le compte bancaire existe
        result = await db.execute(
            select(PaymentAccount).where(PaymentAccount.id == id, PaymentAccount.sub_client_id == data.sub_client_id,
                                         PaymentAccount.account_type == PaymentAccountType.sub_client,
                                         PaymentAccount.is_active == True))
        existing_account = result.scalar_one_or_none()
        if not existing_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Payment account not found for this sub client")

        await validate_payment_account_data(data, db, "update", id)

        if data.rib:
            if data.rib.content_type not in ("image/png", "image/jpeg", "application/pdf"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type de fichier non supporté.")
            s3_url, key = await upload_file_to_s3(data.rib, "rib_sub_clients", f"rib_{str(uuid4())}")
            if s3_url:
                existing_account.rib_file_name = key
                existing_account.rib_file_url = s3_url
        else:
            existing_account.rib_file_name = None
            existing_account.rib_file_url = None

        for field, value in data.model_dump(exclude={"rib"}).items():
            setattr(existing_account, field, value)
        existing_account.configured_by = JWTBearer.decode_jwt(token).get("user_id")
        existing_account.updated_at = datetime.now(timezone.utc)

        await db.commit()
        return {"message": "Sub client payment account successfully updated"}
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_user_payment_account(data: UserPaymentAccountSchema, db: AsyncSession, token: str):
    try:

        result = await db.execute(
            select(User).where(User.id == data.user_id, User.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or inactive")

        await validate_payment_account_data(data, db, "create")

        uploaded_files_url = None
        uploaded_files_name = None
        if data.rib:
            if data.rib.content_type not in ("image/png", "image/jpeg", "application/pdf"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type de fichier non supporté.")
            s3_url, key = await upload_file_to_s3(data.rib, "rib_users", f"rib_{str(uuid4())}")
            if s3_url:
                uploaded_files_url = s3_url
                uploaded_files_name = key

        new_account = PaymentAccount(**data.model_dump(exclude={"rib"}), account_type=PaymentAccountType.user,
                                     configured_by=JWTBearer.decode_jwt(token).get("user_id"),
                                     rib_file_name=uploaded_files_name if uploaded_files_name else None,
                                     rib_file_url=uploaded_files_url if uploaded_files_url else None,
                                     )
        db.add(new_account)
        await db.commit()
        return {"message": "User payment account successfully created"}
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_user_payment_account(data: UserPaymentAccountSchema, db: AsyncSession, token: str, id: UUID):
    try:
        # Vérifie que le compte bancaire existe
        result = await db.execute(
            select(PaymentAccount).where(PaymentAccount.id == id, PaymentAccount.user_id == data.user_id,
                                         PaymentAccount.account_type == PaymentAccountType.user,
                                         PaymentAccount.is_active == True))
        existing_account = result.scalar_one_or_none()
        if not existing_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment account not found for this user")

        await validate_payment_account_data(data, db, "update", id)

        if data.rib:
            if data.rib.content_type not in ("image/png", "image/jpeg", "application/pdf"):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type de fichier non supporté.")
            s3_url, key = await upload_file_to_s3(data.rib, "rib_users", f"rib_{str(uuid4())}")
            if s3_url:
                existing_account.rib_file_name = key
                existing_account.rib_file_url = s3_url
        else:
            existing_account.rib_file_name = None
            existing_account.rib_file_url = None

        for field, value in data.model_dump().items():
            setattr(existing_account, field, value)
        existing_account.configured_by = JWTBearer.decode_jwt(token).get("user_id")
        existing_account.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return {"message": "User payment account successfully updated"}
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def toggle_activation_payment_account(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(select(PaymentAccount).where(PaymentAccount.id == id))
        payment_account = result.scalars().first()
        if not payment_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment account not found")

        payment_account.is_active = not payment_account.is_active
        await db.commit()

        state = "activated" if payment_account.is_active else "deactivated"
        return {"message": f"Payment account {state} successfully"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_payment_account(db: AsyncSession, page: int, size: int, base_url: str, user_id: UUID,
                               sub_client_id: UUID, account_type: PaymentAccountType) -> \
        PaginatedResponse[PaymentAccountResponseSchema]:
    try:
        query = select(PaymentAccount).where(PaymentAccount.is_active == True)
        # Add filters conditionally
        if user_id is not None:
            query = query.where(PaymentAccount.user_id == user_id)
        if sub_client_id is not None:
            query = query.where(PaymentAccount.sub_client_id == sub_client_id)
        if account_type is not None:
            query = query.where(PaymentAccount.account_type == account_type)

        return await paginate(db, query, PaymentAccountResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_activities(db: AsyncSession, page: int, size: int, base_url: str, id: UUID) -> \
        PaginatedResponse[ActivityOut]:
    try:
        query = select(Activity).where(Activity.is_active == True)
        # Add filters conditionally
        if id is not None:
            query = query.where(Activity.id == id)
        return await paginate(db, query, ActivityOut, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def sub_client_activities(sub_client_id: UUID, data: SubClientActivitiesSchema, db: AsyncSession) -> dict:
    try:
        result = await db.execute(
            select(SubClient).where(SubClient.id == sub_client_id, SubClient.is_active == True))
        sub_client = result.scalar_one_or_none()
        if sub_client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Sub client not found or inactive.")

        results = await db.execute(select(Activity).where(Activity.id.in_(data.activities_id),
                                                          Activity.is_active == True))
        existing_activities = {str(act.id) for act in results.scalars().all()}

        # Check that all requested IDs exist
        for activity_id in data.activities_id:
            if str(activity_id) not in existing_activities:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Activity with id '{activity_id}' not found or inactive.")

        current_result = await db.execute(
            select(SubClientActivity.activity_id).where(SubClientActivity.sub_client_id == sub_client_id)
        )
        current_activity_ids = {str(act_id) for act_id, in current_result.all()}

        # Determine which to remove and which to add
        activity_ids_to_delete = current_activity_ids - set(str(aid) for aid in data.activities_id)
        activity_ids_to_add = set(str(aid) for aid in data.activities_id) - current_activity_ids

        # Delete removed activities
        if activity_ids_to_delete:
            await db.execute(delete(SubClientActivity).where(
                    SubClientActivity.sub_client_id == sub_client_id,
                    SubClientActivity.activity_id.in_(activity_ids_to_delete)
                ))

        # Add new activities
        for activity_id in activity_ids_to_add:
            sub_client_activity = SubClientActivity(sub_client_id=sub_client_id,activity_id=activity_id)
            db.add(sub_client_activity)

        await db.commit()
        return {"message": "sub client activities registered sucessfully"}
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
