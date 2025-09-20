from fastapi import HTTPException
from sqlalchemy import select, insert, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timezone, datetime
from uuid import UUID

from sqlalchemy.orm import selectinload
from starlette import status
from app.common.auth import JWTBearer
from app.common.models.Activity import Activity
from app.common.models.CyclePaymentAccount import CyclePaymentAccount
from app.common.models.PaymentAccount import PaymentAccount
from app.common.models.Cycle import Cycle
from app.common.models.CycleConfig import CycleConfig
from app.common.models.FinancialAccount import FinancialAccount
from app.common.models.Guarantee import Guarantee
from app.common.models.LoanConfig import LoanConfig
from app.common.models.UserCycleRole import UserCycleRole
from app.common.models.PenaltyCategory import PenaltyCategory
from app.common.models.PenaltySanctionConfig import PenaltySanctionConfig
from app.common.models.Role import Role
from app.common.models.SubClient import SubClient
from app.common.models.SubClientActivity import SubClientActivity
from app.common.models.User import User
from app.common.models.UserCycle import UserCycle
from app.common.models.ValidatorConfig import ValidatorConfig
from app.common.pagination import PaginatedResponse, paginate
from app.services.cycle_configurations.constants import FinancialAccountType, CycleState
from app.services.cycle_configurations.schemas import CycleCreateSchema, CycleConfigCreateSchema, \
    LoanConfigCreateSchema, ValidatorConfigCreateSchema, \
    PenaltyCategoryCreateSchema, PenaltySanctionConfigCreateSchema, CycleResponseSchema, CreateOfficeSchema, \
    GuaranteeCreateSchema, LoanConfigResponseSchema, ValidatorConfigResponseSchema, \
    PenaltyCategoryResponseSchema, PenaltySanctionConfigResponseSchema, GuaranteeResponseSchema, OfficeResponseSchema, \
    CycleConfigResponseSchema, PenaltySanctionConfigCreateBase, PenaltySanctionConfigUpdateSchema, RoleResponseSchema, \
    RoleCreateSchema


async def create_cycle(data: CycleCreateSchema, db: AsyncSession) -> CycleResponseSchema:
    try:
        result = await db.execute(
            select(SubClientActivity)
            .options(selectinload(SubClientActivity.activity))
            .join(SubClient, SubClientActivity.sub_client_id == SubClient.id)
            .join(Activity, SubClientActivity.activity_id == Activity.id)
            .where(
                SubClientActivity.sub_client_id == data.sub_client_id,
                SubClientActivity.activity_id == data.activity_id,
                SubClient.is_active == True,
                Activity.is_active == True
            )
        )
        sub_client_activity = result.scalar_one_or_none()
        if sub_client_activity is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Activity not found for this Sub client or either subclient or activity is inactive.")
        # Création du cycle
        cycle = Cycle(sub_client_activity_id=sub_client_activity.id,
                      **data.model_dump(exclude={"payment_account_ids", "activity_id", "sub_client_id"}))
        db.add(cycle)
        await db.flush()

        # Config des comptes de paiement du cycle
        results = await db.execute(select(PaymentAccount).where(PaymentAccount.id.in_(data.payment_account_ids),
                                                                PaymentAccount.sub_client_id == data.sub_client_id,
                                                                PaymentAccount.is_active == True))
        existing_accounts = {str(account.id) for account in results.scalars().all()}
        for payment_account in data.payment_account_ids:
            if str(payment_account) not in existing_accounts:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Payment account with id '{payment_account}' not found")
            await db.execute(
                insert(CyclePaymentAccount).values(payment_account_id=payment_account, cycle_id=cycle.id))

        # Crée le compte d'épargne ou placement du cycle
        account_type = FinancialAccountType.saving if sub_client_activity.activity.title == FinancialAccountType.saving else FinancialAccountType.placement
        current_account = FinancialAccount(account_type=account_type, cycle_id=cycle.id)
        db.add(current_account)
        await db.commit()

        result = await db.execute(
            select(CyclePaymentAccount.payment_account_id).where(CyclePaymentAccount.cycle_id == cycle.id)
        )
        payment_account_ids = [str(pid) for pid in result.scalars().all()]
        cycle_data = {
            "id": cycle.id,
            "name": cycle.name,
            "description": cycle.description,
            "sub_client_activity_id": cycle.sub_client_activity_id,
            "start_date": cycle.start_date,
            "end_date": cycle.end_date,
            "start_time": cycle.start_time,
            "end_time": cycle.end_time,
            "day_number": cycle.day_number,
            "frequency_cycle": cycle.frequency_cycle,
            "frequency_week": cycle.frequency_week,
            "week_day": cycle.week_day,
            "currency": cycle.currency,
            "configured_by": cycle.configured_by,
            "state": cycle.state,
            "created_at": cycle.created_at,
            "payment_account_ids": payment_account_ids
        }
        return CycleResponseSchema.model_validate(cycle_data)
    except IntegrityError as e:
        await db.rollback()
        if "cycles_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A cycle with name '{data.name}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_inactive_cycle(data: CycleCreateSchema, db: AsyncSession, id: UUID, token: str) -> Cycle:
    try:
        result = await db.execute(
            select(Cycle).filter(Cycle.id == id, Cycle.state != CycleState.open))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found or Cycle already active")

        # Vérifie que l'activité existe
        result = await db.execute(select(Activity).where(Activity.id == data.activity_id))
        activity = result.scalar_one_or_none()
        if activity is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Activity not found.")

        result = await db.execute(
            select(SubClient).where(SubClient.id == data.sub_client_id, SubClient.is_active == True))
        sub_client = result.scalar_one_or_none()
        if sub_client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Sub client not found.")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(cycle, key, value)
        cycle.configured_by = JWTBearer.decode_jwt(token).get("user_id")
        cycle.updated_at = datetime.now(timezone.utc)

        # Vérification de l'existance des comptes de paiement
        results = await db.execute(select(PaymentAccount).where(PaymentAccount.id.in_(data.payment_account_ids),
                                                                PaymentAccount.is_active == True))
        existing_accounts = {str(account.id) for account in results.scalars().all()}
        for payment_account in data.payment_account_ids:
            if str(payment_account) not in existing_accounts:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Payment account with id '{payment_account}' not found")

        # 1. Get currently assigned payment_account IDs for the cycle
        existing_associations_result = await db.execute(
            select(CyclePaymentAccount.payment_account_id).where(CyclePaymentAccount.cycle_id == id)
        )
        existing_payment_account_ids = {payment_account for payment_account, in existing_associations_result.all()}

        # 2. Delete payment_accounts that are currently assigned but not in the new list
        payment_account_ids_to_delete = existing_payment_account_ids - set(data.payment_account_ids)
        if payment_account_ids_to_delete:
            await db.execute(delete(CyclePaymentAccount).where(CyclePaymentAccount.cycle_id == id,
                                                               CyclePaymentAccount.payment_account_id.in_(
                                                                   payment_account_ids_to_delete)))

        # 3. Add payment_account that are in the new list but not currently assigned
        payment_account_ids_to_add = set(data.payment_account_ids) - existing_payment_account_ids

        # Update des comptes de paiement du cycle
        for payment_account in payment_account_ids_to_add:
            await db.execute(
                insert(CyclePaymentAccount).values(payment_account_id=payment_account, cycle_id=cycle.id))
            await db.flush()

        await db.commit()
        await db.refresh(cycle)
        return cycle
    except IntegrityError as e:
        await db.rollback()
        if "cycles_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A cycle with name '{data.name}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# async def toggle_activation_inactive_cycle(db: AsyncSession, id: UUID) -> dict:
#     
#     try:
#         result = await db.execute(
#             select(Cycle).filter(Cycle.id == id, Cycle.state == False, Cycle.deleted_at.is_(None)))
#         cycle = result.scalar_one_or_none()
#         if not cycle:
#             raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found or Cycle already active")
#
#         cycle.deleted_at = datetime.now(timezone.utc)
#         await db.commit()
#
#         return {"message": "Cycle deleted successfully"}
#     except IntegrityError as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                             "Database integrity error occured.")
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_cycles(db: AsyncSession, page: int, size: int, base_url: str, state: CycleState, id: UUID,
                      office: bool) -> \
        PaginatedResponse[CycleResponseSchema]:
    try:
        query = select(Cycle)
        # Add filters conditionally
        if state is not None:
            query = query.where(Cycle.state == state)
        if id is not None:
            query = query.where(Cycle.id == id)
        # if office is not None:
        #     query = query.where()

        return await paginate(db, query, CycleResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_or_update_cycle_config(data: CycleConfigCreateSchema, db: AsyncSession, token: str) -> CycleConfig:
    try:
        # Vérifie que le cycle existe
        result = await db.execute(select(Cycle).options(
            selectinload(Cycle.sub_client_activity).selectinload(SubClientActivity.activity)
        ).where(Cycle.id == data.cycle_id, Cycle.state == CycleState.not_open))
        cycle = result.scalar_one_or_none()
        if cycle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Cycle not found or already open.")

        if cycle.sub_client_activity.activity.title == FinancialAccountType.placement and data.contribution_mandatory:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"When cycle activity is 'placement', contribution_mandatory must not be provided.")

        # Vérifier si un CycleConfig existe déjà pour ce cycle
        result = await db.execute(select(CycleConfig).where(CycleConfig.cycle_id == data.cycle_id, CycleConfig.is_active == True))
        existing_config = result.scalars().first()

        if existing_config:
            existing_config.is_active = False
            existing_config.configured_by = JWTBearer.decode_jwt(token).get("user_id")
            existing_config.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing_config)

        # Normalise withdrawal_dates (convert date -> str)
        withdrawal_dates = None
        if data.withdrawal_dates:
            withdrawal_dates = [d.isoformat() for d in data.withdrawal_dates]

        # Création
        cycle_config = CycleConfig(configured_by=JWTBearer.decode_jwt(token).get("user_id"), **data.model_dump(exclude={"withdrawal_dates"}),
            withdrawal_dates=withdrawal_dates)
        db.add(cycle_config)
        await db.commit()
        await db.refresh(cycle_config)
        return cycle_config
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# async def toggle_activation_cycle_config(db: AsyncSession, id: UUID) -> dict:
#     try:
#         result = await db.execute(select(CycleConfig).where(CycleConfig.id == id))
#         cycle_config = result.scalars().first()
#
#         if not cycle_config:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cycle config not found")
#
#         cycle_config.is_active = not cycle_config.is_active
#         await db.commit()
#
#         state = "activated" if cycle_config.is_active else "deactivated"
#         return {"message": f"Cycle config {state} successfully"}
#     except IntegrityError as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                             "Database integrity error occured.")
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_cycle_config(db: AsyncSession, page: int, size: int, base_url: str, cycle_id: UUID) -> \
        PaginatedResponse[CycleConfigResponseSchema]:
    try:
        query = select(CycleConfig).where(CycleConfig.is_active == True)
        # Add filters conditionally
        if cycle_id is not None:
            query = query.where(CycleConfig.cycle_id == cycle_id)

        return await paginate(db, query, CycleConfigResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_role(data: RoleCreateSchema, db: AsyncSession, token: str) -> Role:
    try:
        # Vérifie que le subclient existe
        result = await db.execute(select(SubClient).where(SubClient.id == data.sub_client_id, SubClient.is_active == True))
        sub_client = result.scalar_one_or_none()
        if not sub_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SubClient not found or inactive")

        # Création
        role = Role(configured_by=JWTBearer.decode_jwt(token).get("user_id"),**data.model_dump())
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role
    except IntegrityError as e:
        await db.rollback()
        if "roles_name_sub_client_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A role with name '{data.name}' already exists for this sub client.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                str(e))
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_role(data: RoleCreateSchema, db: AsyncSession, token: str, id: UUID) -> Role:
    try:
        # Vérifie que le subclient existe
        result = await db.execute(select(SubClient).where(SubClient.id == data.sub_client_id, SubClient.is_active == True))
        sub_client = result.scalar_one_or_none()
        if not sub_client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SubClient not found or inactive")

        result_role = await db.execute(select(Role).where(Role.sub_client_id == data.sub_client_id, Role.id == id))
        role = result_role.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(role, key, value)

        role.configured_by = JWTBearer.decode_jwt(token).get("user_id")
        role.updated_at = datetime.now(timezone.utc)
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role
    except IntegrityError as e:
        await db.rollback()
        if "roles_name_sub_client_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A role with name '{data.name}' already exists for this sub client.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                "Database integrity error occurred.")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def toggle_activation_role(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(select(Role).where(Role.id == id))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        role.is_active = not role.is_active
        await db.commit()
        state = "activated" if role.is_active else "deactivated"
        return {"message": f"Role {state} successfully"}
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occurred.")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_roles(db: AsyncSession, page: int, size: int, base_url: str, sub_client_id: UUID, not_for_sub_client: bool) -> \
        PaginatedResponse[RoleResponseSchema]:
    try:
        query = select(Role).where(Role.is_active == True)
        if sub_client_id is not None:
            query = query.where(Role.sub_client_id == sub_client_id)
        if not_for_sub_client is not None:
            query = query.where(Role.sub_client_id.is_(None))

        return await paginate(db, query, RoleResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_office_member(data: CreateOfficeSchema, db: AsyncSession, token: str):
    try:
        result = await db.execute(
            select(UserCycle)
            .join(User, UserCycle.user_id == User.id)
            .join(Cycle, UserCycle.cycle_id == Cycle.id)
            .where(
                UserCycle.user_id == data.user_id,
                UserCycle.cycle_id == data.cycle_id,
                User.is_active == True,
                Cycle.state != CycleState.closed
            )
        )
        user_cycle = result.scalar_one_or_none()
        if user_cycle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"User not found in this cycle or either user or cycle is inactive.")

        # Vérification de l'existance des comptes de paiement
        results = await db.execute(select(Role).where(Role.id.in_(data.role_ids),
                                                                Role.is_active == True))
        existing_roles = {str(role.id) for role in results.scalars().all()}
        for role in data.role_ids:
            if str(role) not in existing_roles:
                raise HTTPException(status.HTTP_404_NOT_FOUND,
                                    f"Role with id '{role}' not found")

        # 1. Get currently assigned role IDs for the user of a cycle
        existing_associations_result = await db.execute(
            select(UserCycleRole.role_id).where(UserCycleRole.user_cycle_id == user_cycle.id)
        )
        existing_role_ids = {role for role, in existing_associations_result.all()}

        # 2. Delete roles that are currently assigned but not in the new list
        role_ids_to_delete = existing_role_ids - set(data.role_ids)
        if role_ids_to_delete:
            await db.execute(delete(UserCycleRole).where(UserCycleRole.user_cycle_id == user_cycle.id,
                                                               UserCycleRole.role_id.in_(
                                                                   role_ids_to_delete)))

        # 3. Add role that are in the new list but not currently assigned
        role_ids_to_add = set(data.role_ids) - existing_role_ids

        # Update roles of users of the cycle.
        for role in role_ids_to_add:
            await db.execute(
                insert(UserCycleRole).values(user_cycle_id=user_cycle.id, role_id=role,
                                 configured_by=JWTBearer.decode_jwt(token).get("user_id")))
            await db.flush()
        await db.commit()
        return {"message": "Role successfully affected to user"}
    except IntegrityError as e:
        await db.rollback()
        if "user_cycle_roles_role_id_user_cycle_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"The user of this cycle is already having the role'{role}' .")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# async def update_office_member(user_cycle_role_id: UUID, data: CreateOfficeSchema, db: AsyncSession, token: str):
#     try:
#         # # Vérifie que le cycle existe
#         # result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
#         # cycle = result.scalar_one_or_none()
#         # if not cycle:
#         #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found or already closed")
#         result = await db.execute(
#             select(UserCycle)
#             .join(User, UserCycle.user_id == User.id)
#             .join(Cycle, UserCycle.cycle_id == Cycle.id)
#             .where(
#                 UserCycle.user_id == data.user_id,
#                 UserCycle.cycle_id == data.cycle_id,
#                 User.is_active == True,
#                 Cycle.state != CycleState.closed
#             )
#         )
#         user_cycle = result.scalar_one_or_none()
#         if user_cycle is None:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
#                                 detail=f"User not found in this cycle or either user or cycle is inactive.")
#
#         # Vérifie que le rôle existe
#         result = await db.execute(
#             select(UserCycleRole).where(UserCycleRole.user_cycle_id == user_cycle.id, UserCycleRole.id == user_cycle_role_id))
#         user_cycle_role = result.scalar_one_or_none()
#         if not user_cycle_role:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user role not found")
#
#         # result = await db.execute(select(User).where(User.id == data.user_id, User.is_active == True))
#         # user = result.scalar_one_or_none()
#         # if not user:
#         #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"user not found or inactive.")
#
#         # Mise à jour des champs
#
#         user_cycle_role.user_id = data.role_id
#         user_cycle_role.updated_at = datetime.now(timezone.utc)
#         user_cycle_role.configured_by = JWTBearer.decode_jwt(token).get("user_id")
#
#         await db.commit()
#         return {"message": "User role successfully updated" }
#     except IntegrityError as e:
#         await db.rollback()
#         if "user_cycle_roles_role_id_user_cycle_id_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"The user of this cycle is already having the role'{data.role_id}' .")
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                             "Database integrity error occured.")
#     except Exception as e:
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# async def toggle_activation_office_member(db: AsyncSession, id: UUID) -> dict:
#     try:
#         result = await db.execute(select(OfficeRole).where(OfficeRole.id == id))
#         office_role = result.scalars().first()
#         if not office_role:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Office role not found")
#
#         office_role.is_active = not office_role.is_active
#         await db.commit()
#         state = "activated" if office_role.is_active else "deactivated"
#         return {"message": f"Office role {state} successfully"}
#     except IntegrityError as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                             "Database integrity error occured.")
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_office_members(db: AsyncSession, page: int, size: int, base_url: str, user_id: UUID, role_id: UUID) -> \
        PaginatedResponse[OfficeResponseSchema]:
    try:
        query = select(UserCycleRole)

        # Add filters conditionally
        if user_id is not None:
            query = query.join(UserCycle, UserCycleRole.user_cycle_id == UserCycle.id).where(UserCycle.user_id == user_id)

        if role_id is not None:
            query = query.where(UserCycleRole.role_id == role_id)

        return await paginate(db, query, OfficeResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_or_update_validator_config(data: ValidatorConfigCreateSchema, db: AsyncSession,
                                            token: str) -> ValidatorConfig:
    try:
        configured_by = JWTBearer.decode_jwt(token).get("user_id")
        # Convert UUIDs in validators_id to strings
        data.validators_id = {k: str(v) for k, v in data.validators_id.items()}

        # Vérifie que le cycle existe
        result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found or already closed")

        # Verify each validator_id exists in users table / each are member of the cycle
        validation_errors = []
        for key, validator_id in data.validators_id.items():
            result = await db.execute(
                select(UserCycle)
                .join(User, User.id == UserCycle.user_id)
                .where(
                    UserCycle.cycle_id == data.cycle_id,
                    UserCycle.user_id == validator_id,
                    User.is_active == True
                )
            )
            user_cycle = result.scalar_one_or_none()
            if not user_cycle:
                validation_errors.append(validator_id)
            # result = await db.execute(
            #     select(User).where(User.id == validator_id, User.is_active == True)
            # )
            # user = result.scalar_one_or_none()
            # if not user:
            #     validation_errors.append(f"Validator ID {validator_id} for key '{key}' not found or inactive.")
        if validation_errors:
            raise HTTPException(status_code=422,
                                detail=f"Validator ID {validation_errors} is not part of the cycle {data.cycle_id} or is inactive.")

        # Vérifie s'il existe déjà une configuration pour le cycle + flag
        result = await db.execute(select(ValidatorConfig).where(ValidatorConfig.cycle_id == data.cycle_id,
                                                                ValidatorConfig.flag == data.flag,
                                                                ValidatorConfig.is_active == True))
        existing = result.scalars().first()

        if existing:
            # Mise à jour
            for k, v in data.model_dump(exclude_unset=True).items():
                setattr(existing, k, v)
            existing.configured_by = configured_by
            existing.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing)
            return existing

        # Création
        new_config = ValidatorConfig(configured_by=configured_by, **data.model_dump())
        db.add(new_config)
        await db.commit()
        await db.refresh(new_config)
        return new_config
    except IntegrityError as e:
        await db.rollback()
        if "validator_configs_flag_cycle_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A validator setting with flag '{data.flag}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def toggle_activation_validator_config(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(
            select(ValidatorConfig).where(ValidatorConfig.id == id,))
        validator_config = result.scalars().first()

        if not validator_config:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Validator config not found")

        validator_config.is_active = not validator_config.is_active
        await db.commit()
        state = "activated" if validator_config.is_active else "deactivated"
        return {"message": f"Validator config {state} successfully"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_validator_config(db: AsyncSession, page: int, size: int, base_url: str, cycle_id: UUID) -> \
        PaginatedResponse[ValidatorConfigResponseSchema]:
    try:
        query = select(ValidatorConfig).where(ValidatorConfig.is_active == True)
        # Add filters conditionally
        if cycle_id is not None:
            query = query.where(ValidatorConfig.cycle_id == cycle_id)

        return await paginate(db, query, ValidatorConfigResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_penalty_category(data: PenaltyCategoryCreateSchema, db: AsyncSession, token: str) -> PenaltyCategory:
    try:
        # Vérifie que le cycle existe
        result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found or already closed")
        # Création
        category = PenaltyCategory(configured_by=JWTBearer.decode_jwt(token).get("user_id"), **data.model_dump())
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
    except IntegrityError as e:
        await db.rollback()
        if "penalty_categories_title_cycle_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A penalty categiry with name '{data.title}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_penalty_category(data: PenaltyCategoryCreateSchema, db: AsyncSession, token: str,
                                  id: UUID) -> PenaltyCategory:
    try:
        # Vérifie que le cycle existe
        result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found or already closed")

        result_category = await db.execute(
            select(PenaltyCategory).where(PenaltyCategory.cycle_id == data.cycle_id, PenaltyCategory.id == id))
        category = result_category.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Penalty category not found")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(category, key, value)
        category.configured_by = JWTBearer.decode_jwt(token).get("user_id")
        category.updated_at = datetime.now(timezone.utc)
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
    except IntegrityError as e:
        await db.rollback()
        if "penalty_categories_title_cycle_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A penalty categiry with name '{data.title}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def delete_penalty_category(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(select(PenaltyCategory).where(PenaltyCategory.id == id))
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Penalty category not found")

        await db.execute(delete(PenaltyCategory).where(PenaltyCategory.id == id,))
        await db.commit()

        return {"detail": "Penalty category successfully deleted"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_penalty_category(db: AsyncSession, page: int, size: int, base_url: str, cycle_id: UUID) -> \
        PaginatedResponse[PenaltyCategoryResponseSchema]:
    try:
        query = select(PenaltyCategory)
        # Add filters conditionally
        if cycle_id is not None:
            query = query.where(PenaltyCategory.cycle_id == cycle_id)

        return await paginate(db, query, PenaltyCategoryResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_or_update_penalty_sanction_config(data: PenaltySanctionConfigCreateSchema, db: AsyncSession,
                                                   token: str) -> PenaltySanctionConfig:
    try:
        configured_by = JWTBearer.decode_jwt(token).get("user_id")

        # Vérifie que le cycle existe
        result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found or already closed")

        # Vérifie que la categorie existe
        if data.category_id is not None:
            result = await db.execute(select(PenaltyCategory).where(PenaltyCategory.id == data.category_id, PenaltyCategory.cycle_id == data.cycle_id))
            category = result.scalar_one_or_none()
            if not category:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Penalty category not found in this cycle")
            category_id = data.category_id
        else:
            result = await db.execute(select(PenaltyCategory).where(PenaltyCategory.default == True, PenaltyCategory.cycle_id == data.cycle_id))
            default_category = result.scalar_one_or_none()
            category_id = default_category.id

        # Vérifie s'il existe déjà une configuration pour le cycle + flag
        result = await db.execute(select(PenaltySanctionConfig).where(PenaltySanctionConfig.cycle_id == data.cycle_id,
                                                                      PenaltySanctionConfig.flag == data.flag,
                                                                      PenaltySanctionConfig.is_active == True))
        existing = result.scalars().first()
        if existing:
            # Mise à jour
            for k, v in data.model_dump(exclude_unset=True, exclude={"category_id"}).items():
                setattr(existing, k, v)
            existing.category_id = category_id
            existing.configured_by = configured_by
            existing.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing)
            return existing
        sanction = PenaltySanctionConfig(category_id=category_id, **data.model_dump(exclude={"category_id"}), configured_by=configured_by)
        db.add(sanction)
        await db.commit()
        await db.refresh(sanction)
        return sanction
    except IntegrityError as e:
        await db.rollback()
        if "penalty_sanction_configs_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A penalty with name '{data.name}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_penalty_sanction_config(data: PenaltySanctionConfigUpdateSchema, db: AsyncSession,
                                                   token: str, id: UUID) -> PenaltySanctionConfig:
    try:
        # Vérifie s'il existe déjà une configuration pour le cycle + flag
        result = await db.execute(select(PenaltySanctionConfig).where(PenaltySanctionConfig.id == id,PenaltySanctionConfig.cycle_id == data.cycle_id,
                                                                      PenaltySanctionConfig.flag == data.flag, PenaltySanctionConfig.is_active == True))
        existing = result.scalars().first()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Penalty with flag {data.flag} not found in this cycle")

        # Vérifie que le cycle existe
        result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found or already closed")

        if existing:
            # Mise à jour
            for k, v in data.model_dump(exclude_unset=True, exclude={"flag"}).items():
                setattr(existing, k, v)
            existing.configured_by = JWTBearer.decode_jwt(token).get("user_id")
            existing.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing)
            return existing
    except IntegrityError as e:
        await db.rollback()
        if "penalty_sanction_configs_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A penalty with name '{data.name}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_manual_penalty_sanction(data: PenaltySanctionConfigCreateBase, db: AsyncSession,
                                                   token: str) -> PenaltySanctionConfig:
    try:
        # Vérifie que le cycle existe
        result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found or already closed")

        # Vérifie que la categorie existe
        if data.category_id is not None:
            result = await db.execute(select(PenaltyCategory).where(PenaltyCategory.id == data.category_id, PenaltyCategory.cycle_id == data.cycle_id))
            category = result.scalar_one_or_none()
            if not category:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Penalty category not found in this cycle")
            category_id = data.category_id
        else:
            result = await db.execute(select(PenaltyCategory).where(PenaltyCategory.default == True,
                                                                    PenaltyCategory.cycle_id == data.cycle_id))
            default_category = result.scalar_one_or_none()
            category_id = default_category.id

        sanction = PenaltySanctionConfig(category_id=category_id, **data.model_dump(exclude={"category_id"}), configured_by=JWTBearer.decode_jwt(token).get("user_id"))
        db.add(sanction)
        await db.commit()
        await db.refresh(sanction)
        return sanction
    except IntegrityError as e:
        await db.rollback()
        if "penalty_sanction_configs_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A penalty with name '{data.name}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                        "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def update_manual_penalty_sanction(data: PenaltySanctionConfigCreateBase, db: AsyncSession,
                                         token: str, id: UUID) -> PenaltySanctionConfig:
    try:
        result = await db.execute(select(PenaltySanctionConfig).where(PenaltySanctionConfig.id == id, PenaltySanctionConfig.cycle_id == data.cycle_id,
                                                           PenaltySanctionConfig.is_active == True))
        penalty = result.scalar_one_or_none()
        if not penalty:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Manual penalty not found in this cycle")

        # # Vérifie que le cycle existe
        # result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
        # cycle = result.scalar_one_or_none()
        # if not cycle:
        #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found or already closed")

        # Vérifie que la categorie existe
        if data.category_id is not None:
            result = await db.execute(select(PenaltyCategory).where(PenaltyCategory.id == data.category_id, ))
            category = result.scalar_one_or_none()
            if not category:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Penalty category not found")
            category_id = data.category_id
        else:
            result = await db.execute(select(PenaltyCategory).where(PenaltyCategory.default == True,
                                                                    PenaltyCategory.cycle_id == data.cycle_id))
            default_category = result.scalar_one_or_none()
            category_id = default_category.id

        for key, value in data.model_dump(exclude_unset=True, exclude={"category_id"}).items():
            setattr(penalty, key, value)
        penalty.category_id = category_id
        penalty.configured_by = JWTBearer.decode_jwt(token).get("user_id")
        penalty.updated_at = datetime.now(timezone.utc)
        db.add(penalty)
        await db.commit()
        await db.refresh(penalty)
        return penalty
    except IntegrityError as e:
        await db.rollback()
        if "penalty_sanction_configs_name_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A penalty with name '{data.name}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def toggle_activation_manual_penalty(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(select(PenaltySanctionConfig).where(PenaltySanctionConfig.id == id, PenaltySanctionConfig.flag.is_(None)))
        penalty = result.scalars().first()

        if not penalty:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Manual Penalty not found")

        penalty.is_active = not penalty.is_active
        await db.commit()
        state = "activated" if penalty.is_active else "deactivated"
        return {"message": f"Penalty {state} successfully"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_penalty(db: AsyncSession, page: int, size: int, base_url: str, cycle_id: UUID, manual: bool) -> \
        PaginatedResponse[PenaltySanctionConfigResponseSchema]:
    try:
        query = select(PenaltySanctionConfig).where(PenaltySanctionConfig.is_active == True)
        # Add filters conditionally
        if cycle_id is not None:
            query = query.where(PenaltySanctionConfig.cycle_id == cycle_id)
        if manual is not None:
            if manual is True:
                query = query.where(PenaltySanctionConfig.flag.is_(None))
            else:
                query = query.where(PenaltySanctionConfig.flag.is_not(None))

        return await paginate(db, query, PenaltySanctionConfigResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_loan_config(data: LoanConfigCreateSchema, db: AsyncSession, token: str) -> LoanConfig:
    try:
        # Vérifie si le cycle existe
        result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state == CycleState.not_open))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cycle not found or already active")

        cycle_duration = (cycle.end_date - cycle.start_date).days
        if data.duration_in_day > cycle_duration:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"loan duration must be less than cycle duration ({cycle_duration})")

        is_paid_once = True if data.payment_tranche == 1 else False

        result = await db.execute(select(LoanConfig).where(LoanConfig.duration_in_day == data.duration_in_day,
                                                           LoanConfig.payment_tranche == data.payment_tranche,
                                                           LoanConfig.interest_percentage == data.interest_percentage,
                                                           LoanConfig.is_active == True))
        existing_config = result.scalar_one_or_none()
        if existing_config:
            # Mise à jour
            existing_config.is_active = False
            existing_config.configured_by = JWTBearer.decode_jwt(token).get("user_id")
            existing_config.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing_config)
        new_config = LoanConfig(is_paid_once=is_paid_once, configured_by=JWTBearer.decode_jwt(token).get("user_id"),
                                **data.model_dump())
        db.add(new_config)
        await db.commit()
        await db.refresh(new_config)
        return new_config
    except IntegrityError as e:
        await db.rollback()
        # if "loan_configs_duration_interest_tranche_key" in str(e):
        #     raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
        #                         f"A loan with duration '{data.duration_in_day}', interest '{data.interest_percentage}' and payment tranche '{data.payment_tranche}' already exist.")
        # else:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# async def update_loan_config(data: LoanConfigCreateSchema, db: AsyncSession, token: str, id: UUID) -> LoanConfig:
#     try:
#         # Vérifie si le cycle existe
#         result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state == CycleState.not_open))
#         cycle = result.scalar_one_or_none()
#         if not cycle:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cycle not found or already active")
#
#         result = await db.execute(select(LoanConfig).where(LoanConfig.id == id, LoanConfig.cycle_id == data.cycle_id,
#                                                            LoanConfig.is_active == True))
#         loan_config = result.scalar_one_or_none()
#         if not loan_config:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Loan config not found in this cycle")
#
#         # result = await db.execute(select(LoanConfig).where(LoanConfig.duration_in_day == data.duration_in_day,
#         #                                                    LoanConfig.payment_tranche == data.payment_tranche,
#         #                                                    LoanConfig.interest_percentage == data.interest_percentage,
#         #                                                    LoanConfig.id != id))
#         # existing_config = result.scalar_one_or_none()
#         # if existing_config:
#         #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
#         #                         detail="A loan setting with the same duration, payment tranche and percentage interest already exist")
#         is_paid_once = True if data.payment_tranche == 1 else False
#         for key, value in data.model_dump(exclude_unset=True).items():
#             setattr(loan_config, key, value)
#         loan_config.is_paid_once = is_paid_once
#         loan_config.configured_by = JWTBearer.decode_jwt(token).get("user_id")
#         loan_config.updated_at = datetime.now(timezone.utc)
#         db.add(loan_config)
#         await db.commit()
#         await db.refresh(loan_config)
#         return loan_config
#     except IntegrityError as e:
#         await db.rollback()
#         if "loan_configs_duration_interest_tranche_key" in str(e):
#             raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
#                                 f"A loan with duration '{data.duration_in_day}', interest '{data.interest_percentage}' and payment tranche '{data.payment_tranche}' already exist.")
#         else:
#             raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                                 "Database integrity error occured.")
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# async def toggle_activation_loan_config(db: AsyncSession, id: UUID) -> dict:
#     try:
#         result = await db.execute(select(LoanConfig).where(LoanConfig.id == id))
#         loan_config = result.scalars().first()
#
#         if not loan_config:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Loan config not found")
#
#         loan_config.is_active = not loan_config.is_active
#         await db.commit()
#
#         state = "activated" if loan_config.is_active else "deactivated"
#         return {"message": f"Loan config {state} successfully"}
#     except IntegrityError as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
#                             "Database integrity error occured.")
#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_loan_config(db: AsyncSession, page: int, size: int, base_url: str, cycle_id: UUID) -> \
        PaginatedResponse[LoanConfigResponseSchema]:
    try:
        query = select(LoanConfig).where(LoanConfig.is_active == True)
        # Add filters conditionally
        if cycle_id is not None:
            query = query.where(LoanConfig.cycle_id == cycle_id)

        return await paginate(db, query, LoanConfigResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def create_guarantee(data: GuaranteeCreateSchema, db: AsyncSession, token: str) -> Guarantee:
    try:
        # Vérifie si le cycle existe
        result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cycle not found or already closed")

        new_guarantee = Guarantee(configured_by=JWTBearer.decode_jwt(token).get("user_id"), **data.model_dump())
        db.add(new_guarantee)
        await db.commit()
        await db.refresh(new_guarantee)
        return new_guarantee
    except IntegrityError as e:
        await db.rollback()
        if "guarantees_name_cycle_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A Guarantee type with name '{data.name}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERER_ERROR, str(e))


async def update_guarantee(data: GuaranteeCreateSchema, db: AsyncSession, token: str, id: UUID) -> Guarantee:
    try:
        configured_by = JWTBearer.decode_jwt(token).get("member_nui")
        if not configured_by:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Invalid token payload: member_nui missing")

        # Vérifie si le cycle existe
        result = await db.execute(select(Cycle).where(Cycle.id == data.cycle_id, Cycle.state != CycleState.closed))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cycle not found")

        result = await db.execute(select(Guarantee).where(Guarantee.id == id, Guarantee.cycle_id == data.cycle_id))
        type_operator = result.scalar_one_or_none()
        if not type_operator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guarantee not found in this cycle")

        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(type_operator, key, value)
        type_operator.configured_by = JWTBearer.decode_jwt(token).get("user_id")
        type_operator.updated_at = datetime.now(timezone.utc)
        db.add(type_operator)
        await db.commit()
        await db.refresh(type_operator)
        return type_operator
    except IntegrityError as e:
        await db.rollback()
        if "guarantees_name_cycle_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A Guarantee with name '{data.name}' already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def delete_guarantee(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(select(Guarantee).where(Guarantee.id == id))
        type_op = result.scalars().first()

        if not type_op:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Guarantee not found")

        await db.execute(delete(Guarantee).where(Guarantee.id == id,))
        await db.commit()

        return {"message": "Guarantee deleted successfully"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_guarantee(db: AsyncSession, page: int, size: int, base_url: str, cycle_id: UUID) -> \
        PaginatedResponse[GuaranteeResponseSchema]:
    try:
        query = select(Guarantee)
        # Add filters conditionally
        if cycle_id is not None:
            query = query.where(Guarantee.cycle_id == cycle_id)

        return await paginate(db, query, GuaranteeResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def open_inactive_cycle(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(
            select(Cycle).filter(Cycle.id == id, Cycle.state == CycleState.not_open))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found or Cycle already active")

        cycle.state = CycleState.open
        cycle.updated_at = datetime.now(timezone.utc)

        return {"message": "Cycle open"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def close_active_cycle(db: AsyncSession, id: UUID) -> dict:
    try:
        result = await db.execute(
            select(Cycle).filter(Cycle.id == id, Cycle.state == CycleState.open))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found or Cycle already closed")

        cycle.state = CycleState.closed
        cycle.updated_at = datetime.now(timezone.utc)

        return {"message": "Cycle closed"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
