from datetime import datetime, timezone
from uuid import UUID, uuid4
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette import status
from app.common.auth import JWTBearer
from app.common.models.AccountMovement import AccountMovement
from app.common.models.Contribution import Contribution
from app.common.models.CyclePaymentAccount import CyclePaymentAccount
from app.common.models.FinancialAccount import FinancialAccount
from app.common.models.Operator import Operator
from app.common.models.PaymentAccount import PaymentAccount
from app.common.models.PaymentReference import PaymentReference
from app.common.models.Ticket import Ticket
from app.common.models.TicketLog import TicketLog
from app.common.models.User import User
from app.common.models.UserCycle import UserCycle
from app.common.models.ValidatorConfig import ValidatorConfig
from app.common.pagination import PaginatedResponse, paginate
from app.common.s3 import upload_file_to_s3
from app.services.contributions.schemas import ContributionPaymentSchema, ValidateContributionPaymentSchema, \
    ContributionPaymentOutSchema
from app.services.cycle_configurations.constants import ValidatorFlag, PaymentMode, SourceTable, \
    ValidationState, ContributionStep, PaymentType


async def process_contribution_payment(data: ContributionPaymentSchema, db: AsyncSession, token: str):
    try:
        user_id = JWTBearer.decode_jwt(token).get("user_id")
        result = await db.execute(select(UserCycle).options(selectinload(UserCycle.user)).where(UserCycle.user_id == user_id, UserCycle.cycle_id == data.cycle_id))
        membership = result.scalar_one_or_none()
        if not membership:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not member of this cycle")

        # Vérifie que le moyen de paiement (operator) existe
        result = await db.execute(select(Operator).where(Operator.id == data.operator_id))
        operator = result.scalar_one_or_none()
        if not operator:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")

        # 4. Créer un ticket
        ticket = Ticket(
            source_table=SourceTable.contributions,
            step=ContributionStep.opening,
            initiator_id=user_id,
            # users_validator=validator_config.validators_id, # no users validator when auto
            state=ValidationState.pending,
        )
        db.add(ticket)
        await db.flush()
        await db.refresh(ticket)

        db.add(TicketLog(ticket_id=ticket.id, user_id=user_id, infos=f"contribution opening by {membership.user.name}"))
        await db.flush()

        if data.payment_mode == PaymentMode.cash:
            if operator.type_operator != PaymentType.cash:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator must be of type cash")

            # Création de la contribution
            contribution = Contribution(ticket_id=ticket.id, cycle_id=data.cycle_id, user_id=user_id, amount=data.amount, operator_id=data.operator_id, payment_mode=data.payment_mode, payment_date=data.payment_date, state=ValidationState.pending)
            db.add(contribution)
            await db.commit()
        elif data.payment_mode == PaymentMode.manual:
            if operator.type_operator == PaymentType.cash:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator must not be of type cash")
            if operator.type_operator == PaymentType.bank:
                if data.attachment is None:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                        detail="attachment must be provided when type_operator is 'bank'.")

            result = await db.execute(select(CyclePaymentAccount)
              .options(selectinload(CyclePaymentAccount.payment_account))
              .join(PaymentAccount, CyclePaymentAccount.payment_account_id == PaymentAccount.id)
              .where(
                    CyclePaymentAccount.payment_account_id == data.credit_account,
                    CyclePaymentAccount.cycle_id == data.cycle_id,
                    PaymentAccount.operator_id == data.operator_id,
            ))
            credit_account = result.scalar_one_or_none()
            if not credit_account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cycle credit account with operator_id {data.operator_id} not found")

            result = await db.execute(select(PaymentAccount).where(PaymentAccount.id == data.debit_account,
                                        PaymentAccount.user_id == user_id, PaymentAccount.operator_id == data.operator_id, PaymentAccount.is_active == True))
            debit_account = result.scalar_one_or_none()
            if not debit_account:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User's debit account with operator_id {data.operator_id} not found")

            uploaded_files_url = None
            uploaded_files_name = None
            if data.attachment:
                if data.attachment.content_type not in ("image/png", "image/jpeg", "application/pdf"):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type de fichier non supporté.")
                s3_url, key = await upload_file_to_s3(data.attachment, "contribution_attachments", f"contribution_{str(uuid4())}")
                if s3_url:
                    uploaded_files_url = s3_url
                    uploaded_files_name = key

            # Création de la contribution
            contribution = Contribution(ticket_id=ticket.id, cycle_id=data.cycle_id,user_id=user_id, amount=data.amount,operator_id=data.operator_id, payment_mode=data.payment_mode, payment_date=data.payment_date,
            attachment_file_name = uploaded_files_name if uploaded_files_name else None,
            attachment_file_url = uploaded_files_url if uploaded_files_url else None, state=ValidationState.pending
            )
            db.add(contribution)
            await db.flush()  # Récupérer l'ID de la contribution
            # Enregistrement de la référence de paiement
            reference = PaymentReference(source_table=SourceTable.contributions,source_id=contribution.id,financial_reference=data.financial_reference,
                debit_account=data.debit_account,credit_account=data.credit_account,)
            db.add(reference)
            await db.commit()
        elif data.payment_mode == PaymentMode.auto:
            # operator_id where has_api = 1 et # de cash
            # save contrib
            # call api
            # get ref adnd save in paymentref
            # validate by putting state == 1
            return {"message": "Not yet implemented"}

        return {"message": "Contribution registered successfully", "ticket_id": str(ticket.id)}
    except HTTPException as e:
        raise e
    except IntegrityError as e:
        await db.rollback()
        if "payment_references_financial_reference_key" in str(e):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"This financial reference already exist.")
        else:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database integrity error occured.")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def list_contributions(db: AsyncSession, page: int, size: int, base_url: str, state: ValidationState, id: UUID, payment_mode: PaymentMode) -> \
        PaginatedResponse[ContributionPaymentOutSchema]:
    try:
        query = select(Ticket).options(selectinload(Ticket.contribution))
        # Add filters conditionally
        if state is not None:
            query = query.where(Ticket.state == state)
        if payment_mode is not None:
            query = query.join(Contribution, Ticket.id == Contribution.ticket_id).where(Contribution.payment_mode == payment_mode)
        if id is not None:
            query = query.where(Ticket.id == id)

        return await paginate(db, query, ContributionPaymentOutSchema, page, size, base_url, mapper=lambda ticket: ContributionPaymentOutSchema(
        id=ticket.id,
        initiator_id=ticket.initiator_id,
        state=ticket.state,
        open_at=ticket.open_at,
        payment_mode=ticket.contribution.payment_mode,
        cycle_id=ticket.contribution.cycle_id,
        operator_id=ticket.contribution.operator_id,
        amount=ticket.contribution.amount,

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


async def validate_contribution_payment(ticket_id: UUID, data: ValidateContributionPaymentSchema, db: AsyncSession, token: str):
    try:

        # 1. Vérifie l'existence de la contribution
        result = await db.execute(select(Ticket).where(Ticket.id == ticket_id, Ticket.source_table == SourceTable.contributions))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution ticket not found")

        if ticket.state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contribution ticket already validated")

        if ticket.step != ContributionStep.opening:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The opening step of contribution is not done")

        result = await db.execute(
            select(Contribution).where(Contribution.ticket_id == ticket_id))
        contribution = result.scalar_one_or_none()
        if not contribution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")

        if contribution.amount != data.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid amount")

        # # 3. Récupérer la configuration du validateur
        # validator_result = await db.execute(
        #     select(ValidatorConfig).where(ValidatorConfig.cycle_id == contribution.cycle_id,
        #                                   ValidatorConfig.flag == ValidatorFlag.collection_contribution))
        # validator_config = validator_result.scalar_one_or_none()
        #
        # if not validator_config:
        #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No validation configuration found for this operation.")
        #
        # validator_id = JWTBearer.decode_jwt(token).get("user_id")
        # if validator_id != validator_config.validators_id.get("0"):
        #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not authorized to process this ticket")

        # validation_errors = []
        if contribution.payment_mode == PaymentMode.cash:
            if data.financial_reference is not None:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="financial_reference must not be provided when contribution payment_mode is 'cash'.")
                # validation_errors.append("financial_reference must not be provided when contribution payment_mode is 'cash'.")
            # if data.amount is None or data.amount is "":
            #     validation_errors.append(f"amount is required when contribution payment_mode is 'cash'.")
            # if validation_errors:
            #     raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(validation_errors))

        if contribution.payment_mode == PaymentMode.manual:
            # if data.amount is not None:
            #     validation_errors.append(f"amount must not be provided when contribution payment_mode is 'manual'.")
            if data.financial_reference is None or data.financial_reference is "":
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                    detail="financial_reference is required when contribution payment_mode is 'manual'.")
                # validation_errors.append("financial_reference is required when contribution payment_mode is 'manual'.")
            # if validation_errors:
            #     raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(validation_errors))

            # 2. Vérifie la référence financière
            result = await db.execute(select(PaymentReference).where(PaymentReference.source_table == SourceTable.contributions,
                PaymentReference.source_id == contribution.id,
            ))
            payment_ref = result.scalar_one_or_none()
            if payment_ref.financial_reference != data.financial_reference:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid financial reference")
            if payment_ref.state == ValidationState.accepted:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail="Financial reference already validated for another ticket")
            payment_ref.state == ValidationState.accepted
            payment_ref.updated_at = datetime.now(timezone.utc)
            db.add(payment_ref)

        if contribution.payment_mode == PaymentMode.auto:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="contribution tickets paid via api does not undergo validation")

        # 3. Marquer la contribution comme validée
        contribution.state = ValidationState.accepted
        contribution.updated_at = datetime.now(timezone.utc)

        ticket.state = ValidationState.accepted
        ticket.step = ContributionStep.validation
        ticket.close_at = datetime.now(timezone.utc)
        ticket.updated_at = datetime.now(timezone.utc)

        # 4. Créditer le compte du souscripteur et enregistrer les mouvements
        result = await db.execute(select(FinancialAccount).where(
            FinancialAccount.user_id == contribution.user_id,
            FinancialAccount.cycle_id == contribution.cycle_id
        ))
        subscriber_account = result.scalar_one_or_none()
        if not subscriber_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscriber's financial account not found")

        old_balance = subscriber_account.balance
        subscriber_account.balance += contribution.amount
        subscriber_account.updated_at = datetime.now(timezone.utc)
        db.add(AccountMovement(
            financial_account_id=subscriber_account.id,
            source_table=SourceTable.contributions,
            source_id=contribution.id,
            old_balance=old_balance,
            new_balance=subscriber_account.balance,
            balance=subscriber_account.balance - old_balance
        ))

        # 5. Créditer le compte du cycle et enregistrer les mouvements
        result = await db.execute(select(FinancialAccount).where(FinancialAccount.cycle_id == contribution.cycle_id,
                                                                 FinancialAccount.user_id.is_(None)
                                                                 ))
        cycle_account = result.scalar_one_or_none()
        if not cycle_account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial account of the cycle not found")

        old_cycle_balance = cycle_account.balance
        cycle_account.balance += contribution.amount
        cycle_account.updated_at = datetime.now(timezone.utc)
        db.add(AccountMovement(
            financial_account_id=cycle_account.id,
            source_table=SourceTable.contributions,
            source_id=contribution.id,
            old_balance=old_cycle_balance,
            new_balance=cycle_account.balance,
            balance = cycle_account.balance - old_balance
        ))
        user_id = JWTBearer.decode_jwt(token).get("user_id")
        result = await db.execute(select(User.name).where(User.id == user_id))
        validator_name = result.scalar_one_or_none()
        if not validator_name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        db.add(TicketLog(ticket_id=ticket.id, user_id=user_id, infos=f"contribution validation by {validator_name}"))
        await db.flush()
        await db.commit()
        return {"message": "contribution validated and accounts updated successfully."}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def reject_contribution_payment(ticket_id: UUID,  db: AsyncSession, token: str):
    try:

        # 1. Vérifie l'existence de la contribution
        result = await db.execute(
            select(Ticket).where(Ticket.id == ticket_id, Ticket.source_table == SourceTable.contributions))
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution ticket not found")

        if ticket.state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contribution ticket already validated")

        if ticket.step != ContributionStep.opening:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="The previous step of contribution is not done")

        result = await db.execute(
            select(Contribution).where(Contribution.ticket_id == ticket_id))
        contribution = result.scalar_one_or_none()
        if not contribution:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contribution not found")

        if contribution.payment_mode == PaymentMode.auto:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="contribution tickets paid via api does not undergo validation")

        # 3. Marquer la contribution comme validée
        contribution.state = ValidationState.rejected
        contribution.updated_at = datetime.now(timezone.utc)

        ticket.state = ValidationState.rejected
        ticket.step = ContributionStep.validation
        ticket.close_at = datetime.now(timezone.utc)
        ticket.updated_at = datetime.now(timezone.utc)

        user_id = JWTBearer.decode_jwt(token).get("user_id")
        result = await db.execute(select(User.name).where(User.id == user_id))
        validator_name = result.scalar_one_or_none()
        if not validator_name:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        db.add(TicketLog(ticket_id=ticket.id, user_id=user_id, infos=f"contribution rejection by {validator_name}"))
        await db.flush()
        await db.commit()
        return {"message": "contribution rejected successfully."}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))