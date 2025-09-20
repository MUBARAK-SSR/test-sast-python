from datetime import timezone, datetime, date
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.common.auth import JWTBearer
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from uuid import UUID
from app.common.models.Cycle import Cycle
from app.common.models.Debt import Debt
from app.common.models.FinancialAccount import FinancialAccount
from app.common.models.PenaltySanctionConfig import PenaltySanctionConfig
from app.common.models.RequestToJoin import RequestToJoin
from app.common.models.SubClientActivity import SubClientActivity
from app.common.models.Ticket import Ticket
from app.common.models.TicketLog import TicketLog
from app.common.models.User import User
from app.common.models.UserCycle import UserCycle
from app.common.models.ValidatorConfig import ValidatorConfig
from app.common.pagination import PaginatedResponse, paginate
from app.services.cycle_configurations.constants import ValidatorFlag, ValidationState, \
    FinancialAccountType, CycleState, RequestToJoinsStep, SourceTable
from app.services.memberships.schemas import JoinCycleRequestSchema, ValidateJoinRequestSchema, \
    JoinCycleResponseSchema, DirectJoinSchema, SanctionUsersSchema


async def request_to_join(data: JoinCycleRequestSchema, db: AsyncSession, token: str) -> RequestToJoin:
    try:
        payload = JWTBearer.decode_jwt(token)
        association_id = payload.get("a_key")
        user_id = payload.get("user_id")

        result = await db.execute(select(Cycle).options(
            selectinload(Cycle.sub_client_activity).selectinload(SubClientActivity.sub_client)
        ).filter(Cycle.id == data.cycle_id, Cycle.state == CycleState.not_open))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found or active or closed")

        if UUID(association_id) != cycle.sub_client_activity.activity.sub_client.common_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You can't join a cycle not part of your association")
        print(cycle.start_date, data.withdrawal_date, cycle.end_date, cycle.created_at)
        if cycle.start_date >= data.withdrawal_date > cycle.end_date:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Withdrawal date must be during the cycle period {cycle.start_date} and {cycle.end_date}.")

        if data.withdrawal_date <= date.today():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Withdrawal date must be after the actual date.")

        # 3. Récupérer la configuration du validateur
        validator_result = await db.execute(select(ValidatorConfig).where(ValidatorConfig.cycle_id == data.cycle_id,
                                                                          ValidatorConfig.flag == ValidatorFlag.membership_cycle))
        validator_config = validator_result.scalar_one_or_none()

        if not validator_config:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No validation configuration found for this operation.")

        validator_id = validator_config.validators_id.get("0")
        if not validator_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="No principal validator configured for this operation.")

        # 4. Créer un ticket
        ticket = Ticket(
            source_table=SourceTable.request_to_joins,
            step=RequestToJoinsStep.opening,
            initiator_id=user_id,
            users_validator=validator_config.validators_id,
            state=ValidationState.pending,
        )
        await db.flush()

        # 2. Créer la demande d’adhésion
        join_request = RequestToJoin(**data.model_dump(), user_id=user_id, ticket_id=ticket.id,
                                     state=ValidationState.pending)
        db.add(join_request)
        await db.commit()
        await db.refresh(join_request)
        return join_request
    except IntegrityError as e:
        await db.rollback()
        if "request_to_joins_user_id_cycle_id_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"A request to join with this member_id '{data.member_id}' already exist for this cycle.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def list_request_to_joins(db: AsyncSession, page: int, size: int, base_url: str, state: ValidationState,
                                id: UUID) -> \
        PaginatedResponse[JoinCycleResponseSchema]:
    try:
        query = select(RequestToJoin).where(RequestToJoin.deleted_at.is_(None))
        # Add filters conditionally
        if state is not None:
            query = query.where(RequestToJoin.state == state)
        if id is not None:
            query = query.where(RequestToJoin.id == id)

        return await paginate(db, query, JoinCycleResponseSchema, page, size, base_url)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def validate_join_request(ticket_id: UUID, data: ValidateJoinRequestSchema, db: AsyncSession, token: str) -> dict:
    try:
        validator_id = UUID(JWTBearer.decode_jwt(token).get("user_id"))

        # 1. Récupérer le dernier ticket non traité pour cette demande
        result = await db.execute(select(Ticket).where(
            Ticket.source_table == "request_to_joins", Ticket.id == ticket_id,
            Ticket.state == ValidationState.pending))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request to join ticket not found")

        if ticket.step != RequestToJoinsStep.opening:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The previous step of join request is not done")

        if not ticket.users_validator or not ticket.users_validator.get("0") or validator_id != ticket.users_validator.get("0"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Not authorized to process this ticket")

        result = await db.execute(select(RequestToJoin).where(RequestToJoin.ticket_id == ticket_id))
        join_request = result.scalar_one_or_none()
        if not join_request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request to join not found")

        # 2. Vérification d’ordre de validation
        expected_index = None
        for k, v in ticket.users_validator.items():
            if str(v) == str(validator_id):
                expected_index = int(k)
                break

        # 3. Mise à jour du ticket courant
        TicketLog(ticket_id=ticket.id,user_id=validator_id,opinion=data.opinion,
            reason=data.reason,infos="request to join validation",)
        await db.flush()

        ticket.step = RequestToJoinsStep.validation
        # ticket.users_validated[str(len(ticket.users_validated))] = str(validator_id)
        users_validated = ticket.users_validated or {}
        users_validated[str(len(users_validated))] = str(validator_id)
        ticket.users_validated = users_validated

        # Remove and reindex users_validator
        ticket.users_validator.pop(str(expected_index), None)
        ticket.users_validator = {
            str(i): v for i, v in enumerate(ticket.users_validator.values())
        }
        ticket.updated_at = datetime.now(timezone.utc)
        await db.flush()

        if data.opinion == ValidationState.rejected:
            # Rejet du ticket
            ticket.state = ValidationState.rejected
            join_request.state = ValidationState.rejected
            join_request.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return {"message": "Request to join rejected. Process completed.", "data": ticket}

        # Si tous ont validé (plus personne dans users_validator)
        if not ticket.users_validator:
            ticket.state = ValidationState.accepted
            join_request.state = ValidationState.accepted
            join_request.subscription_date = datetime.now(timezone.utc)

            # Créer l'adhésion
            await db.execute(insert(UserCycle).values(user_id=join_request.user_id, cycle_id=join_request.cycle_id))
            await db.flush()

            # Créer le compte courant du souscripteur
            result = await db.execute(
                select(Cycle).where(Cycle.id == join_request.cycle_id).options(
                    selectinload(Cycle.sub_client_activity).selectinload(SubClientActivity.activity)
                ))
            cycle = result.scalar_one_or_none()
            if not cycle:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")
            account_type = FinancialAccountType.saving if cycle.sub_client_activity.activity.title == FinancialAccountType.saving else FinancialAccountType.placement
            current_account = FinancialAccount(account_type=account_type, cycle_id=join_request.cycle_id,
                                               user_id=join_request.user_id)
            db.add(current_account)

            await db.commit()
            return {"message": "Validation completed successfully. User registered.", "data": ticket}

        # # Sinon, créer le prochain ticket
        # next_index = expected_index + 1
        # next_validator_id = ticket.users_validator.get(str(next_index))
        # if not next_validator_id:
        #     raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error: following validator not defined")
        #
        # # Convert UUIDs to strings in users_validated and users_validator
        # # users_validated = {k: str(v) for k, v in ticket.users_validated.copy().items()}
        # # users_validator = {k: str(v) for k, v in ticket.users_validator.copy().items()}
        # new_ticket = Ticket(
        #     source_table="request_to_joins",
        #     source_id=join_id,
        #     validator_id=UUID(next_validator_id),
        #     users_validator=ticket.users_validator.copy(),
        #     users_validated=ticket.users_validated.copy(),
        #     state=ValidationState.pending,
        #     created_at=datetime.now(timezone.utc)
        # )
        # db.add(new_ticket)
        await db.commit()
        return {"message": "Validation recorded. Waiting for the next validator.", "data": ticket}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def direct_join(data: DirectJoinSchema, db: AsyncSession) -> dict:
    try:
        result = await db.execute(select(Cycle).options(
            selectinload(Cycle.sub_client_activity).selectinload(SubClientActivity.activity)
        ).where(Cycle.id == data.cycle_id, Cycle.state == CycleState.not_open))
        cycle = result.scalar_one_or_none()
        if cycle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Cycle not found or active or closed.")

        results = await db.execute(select(User).where(User.id.in_(data.user_ids), User.is_active == True))
        existing_users = {str(user.id) for user in results.scalars().all()}

        # Vérifier s'ils sont déjà dans le cycle
        existing_in_cycle = await db.execute(
            select(UserCycle.user_id)
            .where(UserCycle.cycle_id == data.cycle_id, UserCycle.user_id.in_(data.user_ids))
        )
        already_members = {str(row[0]) for row in existing_in_cycle.all()}

        errors = {"not_found_or_inactive": [], "already_in_cycle": []}
        registered = []

        # Vérifier s'il y a un user_id invalide
        for user_id in data.user_ids:
            if str(user_id) not in existing_users:
                errors["not_found_or_inactive"].append(str(user_id))
                continue

            if str(user_id) in already_members:
                errors["already_in_cycle"].append(str(user_id))
                continue
                # raise HTTPException(status.HTTP_404_NOT_FOUND,detail=f"User with id '{user_id}' not found or inactive")

            # for user_id in data.user_ids:
            #     if str(user_id) in already_members:
            #         raise HTTPException(status.HTTP_400_BAD_REQUEST,detail=f"User with id '{user_id}' is already part of the cycle")

            await db.execute(insert(UserCycle).values(user_id=user_id, cycle_id=data.cycle_id))
            account_type = FinancialAccountType.saving if cycle.sub_client_activity.activity.title == FinancialAccountType.saving else FinancialAccountType.placement
            current_account = FinancialAccount(account_type=account_type, cycle_id=data.cycle_id, user_id=user_id)
            db.add(current_account)
            registered.append(str(user_id))
        await db.commit()
        return {"message": "User registered in cycle.", "registered": registered,
                "errors": {k: v for k, v in errors.items() if v}}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def sanction_subscribers(data: SanctionUsersSchema, db: AsyncSession) -> dict:
    try:
        result = await db.execute(select(PenaltySanctionConfig).where(PenaltySanctionConfig.id == data.penalty_id))
        penalty = result.scalar_one_or_none()
        if not penalty:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Penalty not found")

        result = await db.execute(
            select(Cycle).where(Cycle.id == data.cycle_id).options(
                selectinload(Cycle.sub_client_activity).selectinload(SubClientActivity.activity)
            ))
        cycle = result.scalar_one_or_none()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

        for user_id in data.user_ids:
            debt = Debt(cycle_id=data.cycle_id, user_id=user_id, penalty_id=data.penalty_id,
                        amount_given=penalty.value, )
            db.add(debt)

        await db.commit()
        return {"message": "Users sanctioned."}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
