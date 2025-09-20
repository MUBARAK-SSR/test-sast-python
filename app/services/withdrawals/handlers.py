from fastapi import HTTPException
from sqlalchemy import select
from uuid import UUID, uuid4
from datetime import datetime, timezone, date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from app.common.auth import JWTBearer
from app.common.models.AccountMovement import AccountMovement
from app.common.models.CycleConfig import CycleConfig
from app.common.models.CyclePaymentAccount import CyclePaymentAccount
from app.common.models.FinancialAccount import FinancialAccount
from app.common.models.Operator import Operator
from app.common.models.PaymentAccount import PaymentAccount
from app.common.models.PaymentReference import PaymentReference
from app.common.models.PenaltySanctionConfig import PenaltySanctionConfig
from app.common.models.RequestToJoin import RequestToJoin
from app.common.models.SubClientUser import SubClientUser
from app.common.models.TicketLog import TicketLog
from app.common.models.User import User
from app.common.models.Ticket import Ticket
from app.common.models.UserCycle import UserCycle
from app.common.models.ValidatorConfig import ValidatorConfig
from app.common.models.Withdrawal import Withdrawal
from app.common.models.model_permission import UserPermission, Permission, UserRelation
from app.common.pagination import PaginatedResponse, paginate
from app.common.s3 import upload_file_to_s3
from app.services.cycle_configurations.constants import ValidationState, ValidatorFlag, FinancialAccountType, \
    SourceTable, WithdrawalStep, PenalityFlag, PaymentMode, PaymentType
from app.services.memberships.schemas import ValidateJoinRequestSchema
from app.services.permissions.constants import SourceTypeConstant
from app.services.withdrawals.schemas import WithdrawalRequestSchema, RejectWithdrawalSchema, WithdrawalPaymentSchema, \
     WithdrawalOutSchema, ConfirmWithdrawal


async def percentage(part: float, whole: float) -> float:
    if whole == 0:
        return 0
    return (part / whole) * 100


async def request_withdrawal(data: WithdrawalRequestSchema, db: AsyncSession, token: str):
    try:
        user_id = JWTBearer.decode_jwt(token).get("user_id")
        result = await db.execute(
            select(UserCycle).options(selectinload(UserCycle.user)).where(UserCycle.user_id == user_id, UserCycle.cycle_id == data.cycle_id))
        membership = result.scalar_one_or_none()
        # is cycle active
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not member of this cycle")

        # Vérifier l'existence du compte de paiement
        result = await db.execute(select(PaymentAccount).where(PaymentAccount.id == data.desired_payment_account,
                                        PaymentAccount.user_id == user_id, PaymentAccount.is_active == True))
        payment_account = result.scalar_one_or_none()
        if not payment_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User's payment account not found")

        # Vérifie que le solde du souscripteur est suffisant
        fa_result = await db.execute(select(FinancialAccount).where(
            FinancialAccount.user_id == user_id,FinancialAccount.cycle_id == data.cycle_id
        ))
        subscriber_account = fa_result.scalar_one_or_none()
        if not subscriber_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscriber's financial account not found")

        if data.amount_claimed > subscriber_account.balance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient balance to make this withdrawal")

        result = await db.execute(select(CycleConfig).where(CycleConfig.cycle_id == data.cycle_id, CycleConfig.is_active == True))
        cycle_config = result.scalar_one_or_none()
        if not cycle_config:
            return {"message": "No active cycle config found."}

        if data.withdrawal_request_date < date.today():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="The withdrawal date cannot be earlier than today.")
        if cycle_config.can_user_provide_withdrawal_date is True:
            # # Vérifier is le retrait est anticicpé
            # result = await db.execute(
            #     select(UserCycle).where(RequestToJoin.user_id == user_id, RequestToJoin.cycle_id == data.cycle_id,
            #                             RequestToJoin.state == ValidationState.accepted))
            # request_to_join = result.scalar_one_or_none()
            # if not request_to_join:
            #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            #                         detail="Request to join of the user not found")
            # if data.withdrawal_request_date < request_to_join.withdrawal_date:
            #     # 3. Récupérer la configuration de la penalité
            #     penality_result = await db.execute(
            #         select(PenaltySanctionConfig).where(PenaltySanctionConfig.cycle_id == data.cycle_id,
            #                                             PenaltySanctionConfig.flag == PenalityFlag.early_withdrawal))
            #     penality_config = penality_result.scalar_one_or_none()
            #
            #     if not penality_config:
            #         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
            #                             detail="No penality configuration found for early withdrawals.")
            #     if penality_config.percentage_levy is None:
            #         value = penality_config.value
            #     elif penality_config.value is None:
            #         value = percentage(penality_config.percentage_levy, data.amount_cliamed)
            #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
            #                         detail=f"The withdrawal request date is earlier than the withdrawal date mentionned during membership (anticicpated) and will cost you {value} as penality.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not yet implemented")
        else:
            # # withdrawal date must not be provided
            # if data.withdrawal_request_date is not None:
            #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal date must not be provided")

            # Normalize withdrawal_dates to list of date objects
            withdrawal_dates = [d if isinstance(d, date) else datetime.fromisoformat(d).date()
                                for d in cycle_config.withdrawal_dates or []]
            if data.withdrawal_request_date not in withdrawal_dates:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"We are not on any withdrawal date. allowed are {cycle_config.withdrawal_dates}.")

        # Vérifier s'il à dautre penalité et debt non payé


        # 3. Récupérer la configuration du validateur
        validator_result = await db.execute(select(ValidatorConfig).where(ValidatorConfig.cycle_id == data.cycle_id,
                                                                          ValidatorConfig.flag == ValidatorFlag.validation_disbursement_withdrawal))
        validator_config = validator_result.scalar_one_or_none()

        # if not validator_config:
        #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        #                         detail="No validation configuration found for this operation.")
        # validator_id = validator_config.validators_id.get("0")
        # if not validator_id:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
        #                         detail="No principal validator configured for this operation.")

        stmt = (select(User)
                .join(SubClientUser, User.id == SubClientUser.user_id)
                .join(UserPermission, UserPermission.customer_user_id == SubClientUser.id)
                .join(Permission, Permission.id == UserPermission.source_id)
                .filter(Permission.code == "DCS"))
        result = await db.execute(stmt)
        # users = result.scalars().all()
        user = result.scalars().first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="No user found with disbursement permission")

        if not validator_config or not validator_config.validators_id.get("0"):
            next_user = user.id
        else:
            next_user = validator_config.validators_id.get("0")

        ticket = Ticket(source_table=SourceTable.withdrawals,step=WithdrawalStep.opening,
            initiator_id=user_id,
            next_user=next_user,
            users_validator=validator_config.validators_id, # no users validator when auto
            users_validated={},
            all_users_validated={},
            state=ValidationState.pending,
        )
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)

        db.add(TicketLog(ticket_id=ticket.id, user_id=user_id, infos=f"withdrawal opening by {membership.user.name}"))
        await db.flush()

        # Créer la demande de retrait
        withdrawal = Withdrawal(**data.model_dump(),user_id=user_id, ticket_id=ticket.id, state=ValidationState.pending)
        db.add(withdrawal)
        await db.flush()
        await db.commit()
        return {"message": f"Withdrawal request submitted successfully. Awaiting validation. Ticket id {ticket.id}"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def list_withdrawals(db: AsyncSession, page: int, size: int, base_url: str, state: ValidationState, id: UUID, payment_mode: PaymentMode) -> \
        PaginatedResponse[WithdrawalOutSchema]:
    try:
        query = select(Ticket).join(Withdrawal).options(selectinload(Ticket.withdrawal))
        # Add filters conditionally
        if state is not None:
            query = query.where(Ticket.state == state)
        if payment_mode is not None:
            query = query.join(Withdrawal, Ticket.id == Withdrawal.ticket_id).where(Withdrawal.payment_mode == payment_mode)
        if id is not None:
            query = query.where(Ticket.id == id)

        return await paginate(db, query, WithdrawalOutSchema, page, size, base_url, mapper=lambda ticket: WithdrawalOutSchema(
            id=ticket.id,
            initiator_id=ticket.initiator_id,
            state=ticket.state,
            open_at=ticket.open_at,
            cycle_id=ticket.withdrawal.cycle_id if ticket.withdrawal else None,
            desired_payment_mode=ticket.withdrawal.desired_payment_mode if ticket.withdrawal else None,
            payment_mode=ticket.withdrawal.payment_mode if ticket.withdrawal else None,
            desired_payment_account=ticket.withdrawal.desired_payment_account if ticket.withdrawal else None,
            payment_account_id=ticket.withdrawal.payment_account_id if ticket.withdrawal else None,
            amount_claimed=ticket.withdrawal.amount_claimed if ticket.withdrawal else None,
            amount_withdraw=ticket.withdrawal.amount_withdraw if ticket.withdrawal else None,
            withdrawal_request_date=ticket.withdrawal.withdrawal_request_date if ticket.withdrawal else None,
            payment_date=ticket.withdrawal.payment_date if ticket.withdrawal else None,

            # financial_reference=(
            #     ticket.contribution.payment_reference.financial_reference
            #     if ticket.contribution.payment_reference else None
            # ),
            # credit_account=(
            #     ticket.contribution.payment_reference.credit_account
            #     if ticket.contribution.payment_reference else None
            # ),
            # debit_account=(
            #     ticket.contribution.payment_reference.debit_account
            #     if ticket.contribution.payment_reference else None
            # ),
        ))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def reject_withdrawal(ticket_id: UUID, data: RejectWithdrawalSchema, db: AsyncSession, token: str) -> dict:
    try:
        validator_id = JWTBearer.decode_jwt(token).get("user_id")

        # # Récupérer la configuration du validateur
        # validator_result = await db.execute(select(ValidatorConfig).where(ValidatorConfig.cycle_id == data.cycle_id,
        #                                                                   ValidatorConfig.flag == ValidatorFlag.validation_disbursement_withdrawal
        #                                                                   ))
        # validator_config = validator_result.scalar_one_or_none()
        #
        # if not validator_config or not validator_config.validators_id.get("0"):
        #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No validation configuration found for this operation")

        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id, Ticket.source_table == SourceTable.withdrawals))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal ticket not found")
        # if ticket.state:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Withdrawal ticket already validated")
        if UUID(validator_id) != ticket.next_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not authorized to process this ticket")
        # if ticket.step != WithdrawalStep.opening:
        #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        #                         detail="The previous step of withdrawal is not done")
        result = await db.execute(
            select(Withdrawal).where(Withdrawal.ticket_id == ticket_id))
        withdrawal = result.scalar_one_or_none()
        if not withdrawal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal not found")

        # if withdrawal.payment_mode == PaymentMode.auto:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
        #                         detail="contribution tickets paid via api does not undergo validation")

        result = await db.execute(
            select(CycleConfig).where(CycleConfig.cycle_id == withdrawal.cycle_id, CycleConfig.is_active == True))
        cycle_config = result.scalar_one_or_none()
        if not cycle_config:
            return {"message": "No active cycle config found."}

        # Normalize withdrawal_dates to list of date objects
        withdrawal_dates = [d if isinstance(d, date) else datetime.fromisoformat(d).date()
            for d in cycle_config.withdrawal_dates or []]

        if cycle_config.can_user_provide_withdrawal_date is False and date.today() not in withdrawal_dates:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"We are not on any withdrawal date. allowed are {cycle_config.withdrawal_dates}.")

        users_validated = ticket.users_validated or {}
        next_index = str(len(users_validated))
        users_validated[next_index] = str(validator_id)
        ticket.users_validated = users_validated

        # Remove validator by value and reindex users_validator
        users_validator = ticket.users_validator or {}
        users_validator = {k: v for k, v in users_validator.items() if str(v) != str(validator_id)}
        ticket.users_validator = {str(i): v for i, v in enumerate(users_validator.values())}

        withdrawal.state = ValidationState.rejected
        withdrawal.updated_at = datetime.now(timezone.utc)

        ticket.state = ValidationState.rejected
        ticket.rejection_comment = data.reason
        ticket.step = WithdrawalStep.validation
        ticket.close_at = datetime.now(timezone.utc)
        ticket.updated_at = datetime.now(timezone.utc)

        result = await db.execute(select(User.name).where(User.id == validator_id))
        validator_name = result.scalar_one_or_none()
        if not validator_name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Créer le ticket de validation
        db.add(TicketLog(ticket_id=ticket.id,user_id=validator_id, opinion=ValidationState.rejected, reason=data.reason, infos=f"withdrawal rejection by {validator_name}"))
        await db.flush()
        await db.commit()
        return {"message": "Withdraw request successfully rejected"}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,"Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def validate_withdrawal(ticket_id: UUID, db: AsyncSession, token: str) -> dict:
    try:
        validator_id = JWTBearer.decode_jwt(token).get("user_id")

        # # Récupérer la configuration du validateur
        # validator_result = await db.execute(select(ValidatorConfig).where(ValidatorConfig.cycle_id == withdrawal.cycle_id,
        #                                                                   ValidatorConfig.flag == ValidatorFlag.validation_disbursement_withdrawal
        #                                                                   ))
        # validator_config = validator_result.scalar_one_or_none()
        #
        # if not validator_config or not validator_config.validators_id.get("0"):
        #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        #                         detail="No validation configuration found for this operation")


        result = await db.execute(
            select(Ticket).where(Ticket.id == ticket_id, Ticket.source_table == SourceTable.withdrawals))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal ticket not found")
        # if ticket.state:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Withdrawal ticket already validated")
        if UUID(validator_id) != ticket.next_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not authorized to process this ticket")
        if ticket.step != WithdrawalStep.opening:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="The previous step of withdrawal is not done")
        result = await db.execute(
            select(Withdrawal).where(Withdrawal.ticket_id == ticket_id))
        withdrawal = result.scalar_one_or_none()
        if not withdrawal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal not found")

        # if withdrawal.payment_mode == PaymentMode.auto:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
        #                         detail="withdrawal tickets paid via api does not undergo validation")

        result = await db.execute(
            select(CycleConfig).where(CycleConfig.cycle_id == withdrawal.cycle_id, CycleConfig.is_active == True))
        cycle_config = result.scalar_one_or_none()
        if not cycle_config:
            return {"message": "No active cycle config found."}

        # Normalize withdrawal_dates to list of date objects
        withdrawal_dates = [d if isinstance(d, date) else datetime.fromisoformat(d).date()
                            for d in cycle_config.withdrawal_dates or []]

        if cycle_config.can_user_provide_withdrawal_date is False and date.today() not in withdrawal_dates:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"We are not on any withdrawal date. allowed are {cycle_config.withdrawal_dates}.")

        # # 2. Vérification d’ordre de validation
        # expected_index = None
        # for k, v in ticket.users_validator.items():
        #     if str(v) == str(validator_id):
        #         expected_index = int(k)
        #         break

        result = await db.execute(select(User.name).where(User.id == validator_id))
        validator_name = result.scalar_one_or_none()
        if not validator_name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Créer le ticket de validation
        db.add(TicketLog(ticket_id=ticket.id, user_id=validator_id, opinion=ValidationState.accepted, infos=f"withdrawal validation by {validator_name}"))
        await db.flush()

        users_validated = ticket.users_validated or {}
        next_index = str(len(users_validated))
        users_validated[next_index] = str(validator_id)
        ticket.users_validated = users_validated

        # Remove validator by value and reindex users_validator
        users_validator = ticket.users_validator or {}
        users_validator = {k: v for k, v in users_validator.items() if str(v) != str(validator_id)}
        ticket.users_validator = {str(i): v for i, v in enumerate(users_validator.values())}

        ticket.updated_at = datetime.now(timezone.utc)
        await db.flush()

        # Si tous ont validé (plus personne dans users_validator)
        if not ticket.users_validator:
            stmt = (select(User)
                    .join(SubClientUser, User.id == SubClientUser.user_id)
                    .join(UserPermission, UserPermission.customer_user_id == SubClientUser.id)
                    .join(Permission, Permission.id == UserPermission.source_id)
                    .filter(Permission.code == "DCS"))
            result = await db.execute(stmt)
            # users = result.scalars().all()
            user = result.scalars().first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No user found with disbursement permission")

            # withdrawal.state = ValidationState.accepted
            # withdrawal.updated_at = datetime.now(timezone.utc)
            # ticket.state = ValidationState.accepted
            # ticket.close_at = datetime.now(timezone.utc)
            ticket.step = WithdrawalStep.validation
            ticket.next_user = user.id
            ticket.updated_at = datetime.now(timezone.utc)
            await db.commit()
            return {"message": "Validation completed successfully."}

        ticket.next_user = UUID(ticket.users_validator.get("0"))
        await db.commit()
        return {"message": "Validation recorded. Waiting for the next validator."}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def process_withdrawal(ticket_id: UUID, data: WithdrawalPaymentSchema, db: AsyncSession, token: str) -> dict:
    try:
        user_id = JWTBearer.decode_jwt(token).get("user_id")
        validator_result = await db.execute(select(ValidatorConfig).where(ValidatorConfig.cycle_id == data.cycle_id,
                                                                          ValidatorConfig.flag == ValidatorFlag.validation_disbursement_withdrawal))
        validator_config = validator_result.scalar_one_or_none()

        result = await db.execute(
            select(Ticket).where(Ticket.id == ticket_id, Ticket.source_table == SourceTable.withdrawals))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal ticket not found")
        if UUID(user_id) != ticket.next_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not authorized to process this ticket")
        if ticket.step != WithdrawalStep.validation and not (ticket.step == WithdrawalStep.opening and (
                not validator_config or not validator_config.validators_id.get(
                "0"))) and ticket.step != WithdrawalStep.deny_confirmation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="The previous step of withdrawal is not done")
        result = await db.execute(select(Withdrawal).where(Withdrawal.ticket_id == ticket_id))
        withdrawal = result.scalar_one_or_none()
        if not withdrawal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal not found")

        result = await db.execute(
            select(CycleConfig).where(CycleConfig.cycle_id == data.cycle_id, CycleConfig.is_active == True))
        cycle_config = result.scalar_one_or_none()
        if not cycle_config:
            return {"message": "No active cycle config found."}
        if cycle_config.can_user_provide_withdrawal_date is True:
            penalty_amount = 0
            # calculate penalty ot cut
        # get his other penalty, sum it and add it to the previous
        # Couper la pénalité configuré pr les retraits anticipé si le retrait est anticipé et mettre dans le compte du cycle et partage benef

        # Normalize withdrawal_dates to list of date objects
        withdrawal_dates = [d if isinstance(d, date) else datetime.fromisoformat(d).date()
                            for d in cycle_config.withdrawal_dates or []]

        if date.today() not in withdrawal_dates:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"We are not on any withdrawal date. allowed are {cycle_config.withdrawal_dates}.")
        if withdrawal.withdrawal_request_date != date.today():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"We are not on the requested withdrawal date of the initiated ticket.")

        if data.amount_withdraw > withdrawal.amount_claimed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="the given amount can't be greater than the requested amount")
        if data.amount_withdraw < withdrawal.amount_claimed and data.reason is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="when the given amount is less than the requested amount, a reason should be given")
        if data.amount_withdraw == withdrawal.amount_claimed and data.reason is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="when the given amount is equal to the requested amount, a reason should not be given")

        if data.payment_mode == PaymentMode.cash or data.payment_mode == PaymentMode.manual:
            if data.payment_date < ticket.open_at.date():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment date can't be less than than the ticket open date")
            if data.payment_date > date.today():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="payment date can't be greater than today")

        # Vérifie que le moyen de paiement (operator) existe
        result = await db.execute(select(Operator).where(Operator.id == data.operator_id))
        operator = result.scalar_one_or_none()
        if not operator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")

        credit_account = None
        uploaded_files_url = None
        uploaded_files_name = None
        if data.payment_mode == PaymentMode.cash:
            if operator.type_operator != PaymentType.cash:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator must be of type cash")
        elif data.payment_mode == PaymentMode.manual:
            if operator.type_operator == PaymentType.cash:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator must not be of type cash")
            if operator.type_operator == PaymentType.bank:
                if data.attachment is None:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail="attachment must be provided when type_operator is 'bank'.")

            # verify credit and debit account
            result = await db.execute(select(PaymentAccount).where(PaymentAccount.id == data.credit_account,
                                                                  PaymentAccount.user_id == ticket.initiator_id,
                                                                  PaymentAccount.operator_id == data.operator_id,
                                                                  PaymentAccount.is_active == True))
            credit_account = result.scalar_one_or_none()
            if not credit_account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"User's credit account with operator_id {data.operator_id} not found")

            result = await db.execute(select(CyclePaymentAccount)
            .options(selectinload(CyclePaymentAccount.payment_account))
            .join(PaymentAccount, CyclePaymentAccount.payment_account_id == PaymentAccount.id)
            .where(
                CyclePaymentAccount.payment_account_id == data.debit_account,
                CyclePaymentAccount.cycle_id == data.cycle_id,
                PaymentAccount.operator_id == data.operator_id,
            ))
            debit_account = result.scalar_one_or_none()
            if not debit_account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Cycle debit account with operator_id {data.operator_id} not found")
            if data.attachment:
                if data.attachment.content_type not in ("image/png", "image/jpeg", "application/pdf"):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type de fichier non supporté.")
                s3_url, key = await upload_file_to_s3(data.attachment, "withdrawal_attachments",
                                                      f"withdrawal_{str(uuid4())}")
                if s3_url:
                    uploaded_files_url = s3_url
                    uploaded_files_name = key

            # Enregistrement de la référence de paiement
            reference = PaymentReference(source_table=SourceTable.withdrawals, source_id=withdrawal.id,
                                         financial_reference=data.financial_reference,
                                         debit_account=data.debit_account, credit_account=data.credit_account, )
            db.add(reference)
        elif data.payment_mode == PaymentMode.auto:
            # operator_id where has_api = 1 et # de cash
            # call api
            # get ref adnd save in paymentref
            # validate by putting state == 1
            return {"message": "Not yet implemented"}

        withdrawal.reason = data.reason if data.reason else None
        withdrawal.payment_account_id = credit_account.id if credit_account else None
        withdrawal.payment_mode = data.payment_mode
        withdrawal.amount_withdraw = data.amount_withdraw
        withdrawal.payment_date = data.payment_date if data.payment_date else None
        # withdrawal.penalty_amount = penalty_amount
        withdrawal.attachment_file_name = uploaded_files_name if uploaded_files_name else None
        withdrawal.attachment_file_url = uploaded_files_url if uploaded_files_url else None
        withdrawal.updated_at = datetime.now(timezone.utc)

        result = await db.execute(select(User.name).where(User.id == user_id))
        validator_name = result.scalar_one_or_none()
        if not validator_name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if ticket.step == WithdrawalStep.validation or (ticket.step == WithdrawalStep.opening and (not validator_config or not validator_config.validators_id.get("0"))):
            db.add(TicketLog(ticket_id=ticket.id, user_id=user_id, infos=f"withdrawal disbursement by {validator_name}"))
            await db.flush()
        elif ticket.step == WithdrawalStep.deny_confirmation:
            db.add(TicketLog(ticket_id=ticket.id, user_id=user_id, infos=f"withdrawal re_disbursement {validator_name}"))
            await db.flush()

        ticket.next_user = withdrawal.user_id
        ticket.step = WithdrawalStep.re_disbursement if ticket.step == WithdrawalStep.deny_confirmation else WithdrawalStep.disbursement
        ticket.updated_at = datetime.now(timezone.utc)

        await db.commit()
        return {"message": "Withdrawal completed successfully",}
    except IntegrityError as e:
        await db.rollback()
        if "payment_references_financial_reference_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"This financial reference '{data.financial_reference}' already exist.")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,"Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def confirm_withdrawal(ticket_id: UUID, data: ConfirmWithdrawal, db: AsyncSession, token: str) -> dict:
    try:
        user_id = JWTBearer.decode_jwt(token).get("user_id")

        result = await db.execute(
            select(Ticket).where(Ticket.id == ticket_id, Ticket.source_table == SourceTable.withdrawals))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal ticket not found")
        if ticket.initiator_id != UUID(user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="You are not the initiator of this ticket")
        if ticket.step != WithdrawalStep.disbursement and ticket.step != WithdrawalStep.re_disbursement and ticket.step != WithdrawalStep.send_for_confirmation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="The previous step of withdrawal is not done")

        result = await db.execute(select(Withdrawal).where(Withdrawal.ticket_id == ticket_id))
        withdrawal = result.scalar_one_or_none()
        if not withdrawal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal not found")
        if data.financial_reference is not None and withdrawal.payment_mode == PaymentMode.cash:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="financial_reference must not be provided when payment_mode is 'cash'")

        if data.status == True:
            if data.financial_reference is None and withdrawal.payment_mode == PaymentMode.manual:
                raise HTTPException(422, "financial_reference is required when status is True and payment_mode is manual.")
            if withdrawal.amount_withdraw != data.amount:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid amount")
            if withdrawal.payment_mode == PaymentMode.manual:
                # recuperer la référence de paiement
                result = await db.execute(select(PaymentReference).where(PaymentReference.source_table == SourceTable.withdrawals,
                    PaymentReference.source_id == withdrawal.id,PaymentReference.financial_reference == data.financial_reference
                ))
                ref = result.scalar_one_or_none()
                if not ref:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid financial reference")
                if ref.state == ValidationState.accepted:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="Financial reference already validated for another ticket")
                ref.state = ValidationState.accepted
                ref.updated_at = datetime.now(timezone.utc)

            # 4. Débiter le compte du souscripteur et enregistrer les mouvements
            result = await db.execute(select(FinancialAccount).where(
                FinancialAccount.user_id == user_id,FinancialAccount.cycle_id == withdrawal.cycle_id
            ))
            subscriber_account = result.scalar_one_or_none()
            if not subscriber_account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Subscriber's financial account not found")

            old_balance = subscriber_account.balance
            subscriber_account.balance -= withdrawal.amount_withdraw
            subscriber_account.updated_at = datetime.now(timezone.utc)
            db.add(AccountMovement(
                financial_account_id=subscriber_account.id,
                source_table=SourceTable.withdrawals,
                source_id=withdrawal.id,
                old_balance=old_balance,
                new_balance=subscriber_account.balance
            ))

            # 5. Débiter le compte du cycle et enregistrer les mouvements
            result = await db.execute(select(FinancialAccount).where(FinancialAccount.cycle_id == withdrawal.cycle_id,
                                                                     FinancialAccount.user_id.is_(None)))
            cycle_account = result.scalar_one_or_none()
            if not cycle_account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Financial account of the cycle not found")

            old_cycle_balance = cycle_account.balance
            cycle_account.balance -= withdrawal.amount_withdraw
            cycle_account.updated_at = datetime.now(timezone.utc)
            db.add(AccountMovement(
                financial_account_id=cycle_account.id,
                source_table=SourceTable.withdrawals,
                source_id=withdrawal.id,
                old_balance=old_cycle_balance,
                new_balance=cycle_account.balance
            ))

            ticket.state = ValidationState.accepted
            ticket.step = WithdrawalStep.confirmation
            ticket.close_at = datetime.now(timezone.utc)
            ticket.updated_at = datetime.now(timezone.utc)

            withdrawal.state = ValidationState.accepted
            withdrawal.updated_at = datetime.now(timezone.utc)

            result = await db.execute(select(User.name).where(User.id == user_id))
            validator_name = result.scalar_one_or_none()
            if not validator_name:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            db.add(TicketLog(ticket_id=ticket.id, user_id=user_id, infos=f"withdrawal confirmation by {validator_name}"))
            await db.flush()
        else:
            # renvoie du ticket au decaisseur avec step=deny
            stmt = (select(User)
                    .join(SubClientUser, User.id == SubClientUser.user_id)
                    .join(UserPermission, UserPermission.customer_user_id == SubClientUser.id)
                    .join(Permission, Permission.id == UserPermission.source_id)
                    .filter(Permission.code == "DCS"))
            result = await db.execute(stmt)
            user = result.scalars().first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="No user found with disbursement permission")
            ticket.next_user = user.id
            ticket.step = WithdrawalStep.deny_confirmation
            ticket.updated_at = datetime.now(timezone.utc)

            result = await db.execute(select(User.name).where(User.id == user_id))
            validator_name = result.scalar_one_or_none()
            if not validator_name:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
            db.add(TicketLog(ticket_id=ticket.id, user_id=user_id, infos=f"withdrawal denial by {validator_name}"))
            await db.flush()
        await db.commit()
        return {"message": "Confimation done",}
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,"Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


async def return_ticket_to_initiator(ticket_id: UUID, db: AsyncSession, token: str) -> dict:
    try:
        result = await db.execute(
            select(Ticket).where(Ticket.id == ticket_id, Ticket.source_table == SourceTable.withdrawals))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Withdrawal ticket not found")
        if ticket.step != WithdrawalStep.deny_confirmation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="The previous step of withdrawal is not done")
        ticket.next_user = ticket.initiator_id
        ticket.step = WithdrawalStep.send_for_confirmation
        ticket.updated_at = datetime.now(timezone.utc)

        user_id = JWTBearer.decode_jwt(token).get("user_id")
        result = await db.execute(select(User.name).where(User.id == user_id))
        validator_name = result.scalar_one_or_none()
        if not validator_name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        db.add(TicketLog(ticket_id=ticket.id, user_id=user_id, infos=f"withdrawal ticket returned to initiator {validator_name}"))
        await db.flush()
        await db.commit()
        return {"message": "Withdrawal Ticket returned to initiator successfully", }
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database integrity error occured.")
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


