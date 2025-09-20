from typing import Optional
from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from sqlalchemy import select, and_, func, exists, asc, desc
from datetime import datetime, timedelta, timezone, date

from starlette import status

from app.common.models.Cycle import Cycle
from app.common.models.CycleConfig import CycleConfig
from app.common.models.DebtSlice import DebtSlice
from app.common.models.Operator import Operator
from app.common.models.TicketLog import TicketLog
from app.common.models.TypeOperator import TypeOperator
from app.common.models.UserCycle import UserCycle
from app.common.models.AccountMovement import AccountMovement
from app.common.models.FinancialAccount import FinancialAccount
from app.common.models.Guarantee import Guarantee
from app.common.models.LoanConfig import LoanConfig
from app.common.models.PaymentReference import PaymentReference
from app.common.models.Ticket import Ticket
from app.common.models.ValidatorConfig import ValidatorConfig
from app.services.cycle_configurations.constants import ValidationState, ValidationOpinion, ValidatorFlag, PaymentMode, \
    SourceTable
from app.services.loan_debts.constants import StepValidationLoan, FilterOrder

from app.services.loan_debts.schemas import LoanSimulationRequest, LoanRequestCreate, RejectLoanRequestSchema, \
    LoanDisbursementRequest, ReceiptPaymentRequest, ValidationGuarantorSchema, LoanAutorisationRequest, ListLoanSchema
from app.common.models.LoanRequest import LoanRequest
from app.common.models.Debt import Debt
from uuid import uuid4, UUID
from decimal import Decimal
from app.common.auth import JWTBearer
from app.common.models.User import User
from app.common.models.RequestToJoin import RequestToJoin


async def simulate_loan(db: AsyncSession, payload: LoanSimulationRequest, token: str):
    user_id = JWTBearer.decode_jwt(token).get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Token : user_id missing")

    result_maximum_loan = await db.execute(
        select(CycleConfig.maximum_loan).where(CycleConfig.cycle_id == payload.cycle_id)
    )
    maximum_loan = result_maximum_loan.scalar_one_or_none()
    if payload.amount_claimed > maximum_loan :
        raise HTTPException(
            status_code=400,
            detail=(
                f"The amount requested exceeds the margin authorized in the association."
            )
        )

    #Vérifier que l'identifiant du loan_config_id existe en BD
    result = await db.execute(
        select(LoanConfig).where(LoanConfig.id == payload.loan_config_id)
    )
    check_loan_config_id = result.scalars().first()
    if not check_loan_config_id:
        raise HTTPException(status_code=404, detail=f"LoanConfig with id {payload.loan_config_id} not found")

    # vérifier qu'en acceptant cette config la durée de rembourssement autorisé n'exède pas la date de fin de cycle
    result_date = await db.execute(
        select(Cycle.end_date).where(Cycle.id == payload.cycle_id)
    )
    end_date_cycle = result_date.scalar_one_or_none()
    date_today_utc = datetime.now(ZoneInfo("UTC")).date()
    print(f" valeur des dates : {end_date_cycle}, {date_today_utc}")

    # S'assurer que les date en cours n'exède pas la date de fin du cycle
    if end_date_cycle < date_today_utc:
        raise HTTPException(status_code=400, detail="Today's date cannot be later than the cycle end date")

    # Calcul du nombre de jours
    jours = (end_date_cycle - date_today_utc).days
    if payload.include_cycle_end_date:
        jours += 1
    print(f"nombre jours : {jours}")

    # Récupérer la configuration de prêt du cycle
    result = await db.execute(
        select(LoanConfig).where(LoanConfig.cycle_id == payload.cycle_id, LoanConfig.id == payload.loan_config_id)
    )
    config = result.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Loan configuration not found for this cycle")
    print(f"NOMBRE JOURS : {jours}")
    if jours < config.duration_in_day:
        raise HTTPException(status_code=404, detail=f"It is impossible to have a loan for a period of {config.duration_in_day} days because the end of cycle date will be exceeded in this case.")

    interest_percentage = Decimal(config.interest_percentage)
    tranche_count = config.payment_tranche
    capital = Decimal(payload.amount_claimed)

    total_interest = (capital * interest_percentage) / 100
    total_to_refund = capital + total_interest
    tranche_capital = capital / tranche_count

    deadlines = []
    current_date = datetime.now(timezone.utc)
    step_days = int(config.duration_in_day) // tranche_count

    for i in range(tranche_count):
        refund_deadline = current_date + timedelta(days=step_days * (i + 1))
        tranche_interest = total_interest / tranche_count
        deadlines.append({
            "refund_deadline": refund_deadline.strftime("%d/%m/%Y"),
            "capital": round(tranche_capital, 2),
            "interest": round(tranche_interest, 2),
            "total": round(tranche_capital + tranche_interest, 2)
        })

    return {
        "total_amount_to_refund": round(total_to_refund, 2),
        "deadlines": deadlines
    }


async def submit_loan_request(db: AsyncSession, payload: LoanRequestCreate, token: str):
    user_id = JWTBearer.decode_jwt(token).get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Token : member_nui or user_id missing")

    # Vérifie qu'un souscripteur existe avec ce member_nui et est bien rattaché au cycle
    result = await db.execute(
        select(UserCycle).where(
            UserCycle.cycle_id == payload.cycle_id, UserCycle.user_id == user_id))

    subscriber = result.scalar_one_or_none()

    if not subscriber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subscriber not found for this cycle")

    result_maximum_loan = await db.execute(
        select(CycleConfig.maximum_loan).where(CycleConfig.cycle_id == payload.cycle_id)
    )
    maximum_loan = result_maximum_loan.scalar_one_or_none()

    if payload.amount_claimed > maximum_loan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The amount requested exceeds the margin authorized in the association."
            )
        )
    # vérifier que l'utilisateur n'a pas déja une dette en cours
    result_debt = await db.execute(
        select(Debt)
        .join(LoanRequest, LoanRequest.id == Debt.loan_request_id)
        .filter(LoanRequest.user_id == user_id, LoanRequest.cycle_id == payload.cycle_id)
        .filter(Debt.state == False)
        .limit(1)
    )
    has_debt = result_debt.scalar_one_or_none()
    print(f"réponse true or false sur la dette: {has_debt}")
    if has_debt:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="the user already has an unpaid debt")

    # Vérifie si une demande en cours existe déjà pour cet utilisateur
    await check_existing_pending_request(db, user_id)

    # Vérifier que l'identifiant du loan_config_id existe en BD
    result_loan_config = await db.execute(
        select(LoanConfig).where(LoanConfig.id == payload.loan_config_id)
    )
    check_loan_config = result_loan_config.scalars().first()
    if not check_loan_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No configuration on loans associated with this identifier")

    # vérifier qu'en acceptant cette config la durée de rembourssement autorisé n'exède pas la date de fin de cycle
    result_date = await db.execute(
        select(Cycle.end_date).where(Cycle.id == payload.cycle_id)
    )
    end_date_cycle = result_date.scalar_one_or_none()
    date_today_utc = datetime.now(ZoneInfo("UTC")).date()
    print(f" valeur des dates : {end_date_cycle}, {date_today_utc}")

    # S'assurer que la date en cours n'exède pas la date de fin du cycle
    if end_date_cycle < date_today_utc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Today's date cannot be later than the cycle end date")

    # Calcul du nombre de jours
    jours = (end_date_cycle - date_today_utc).days
    if payload.include_cycle_end_date:
        jours += 1
    print(f"nombre jours : {jours}")

    # Calcul du total des soldes des comptes du cycle
    result = await db.execute(
        select(func.sum(FinancialAccount.balance)).where(
            FinancialAccount.cycle_id == payload.cycle_id, FinancialAccount.user_id == None
        )
    )
    print(result)
    total_cycle_balance = result.scalar() or Decimal("0.00")
    print(total_cycle_balance)

    # Calcul du total des prêts validés mais non remboursés ( il est possible que je ne fasse plus et que je récupère direct dans financial_account sur le champs amount_loaned_cycle
    loan_result = await db.execute(
        select(func.sum(LoanRequest.amount_claimed)).where(
            LoanRequest.cycle_id == payload.cycle_id,
            LoanRequest.state == ValidationState.accepted,
            LoanRequest.state_refund == False
        )
    )
    total_engaged = loan_result.scalar() or Decimal("0.00")
    print(total_engaged)

    # Evaluation du Solde réellement disponible dans le solde courant
    available_balance_cycle = Decimal(str(total_cycle_balance)) - Decimal(str(total_engaged))

    if payload.amount_claimed > available_balance_cycle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient funds in the cycle."
            )
        )

    exists_query = select(exists().where(
        and_(
            UserCycle.user_id == payload.guarantee.guarantor_id,
            UserCycle.cycle_id == payload.cycle_id
        )
    ))
    guarantor_exists = await db.scalar(exists_query)
    if not guarantor_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guarantor with ID {payload.guarantee.guarantor_id} in cycle {payload.cycle_id} not found."
        )

    if UUID(user_id) == payload.guarantee.guarantor_id:
        raise HTTPException(
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
            detail="you cannot be your guarantor"
        )
    print(f" valeur de user_id : {user_id}, garant: {payload.guarantee.guarantor_id}")

    exists_query = select(exists().where(
        and_(
            Guarantee.id == payload.guarantee.guarantee_id,
            Guarantee.cycle_id == payload.cycle_id
        )
    ))
    guarantee_exists = await db.scalar(exists_query)
    if not guarantee_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Guarantee with ID {payload.guarantee.guarantee_id} in cycle {payload.cycle_id} not found."
        )

    result_financial_guarantor = await db.execute(
        select(FinancialAccount).where(FinancialAccount.user_id == payload.guarantee.guarantor_id,
                                                                                        FinancialAccount.cycle_id == None)
    )
    guarantor_financial_balance = result_financial_guarantor.scalar_one_or_none()
    if not guarantor_financial_balance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=("No financial records found for this guarantor")
        )
    debt_amount_guarantor = guarantor_financial_balance.debt_amount
    amount_to_endorse_guarantor = guarantor_financial_balance.amount_to_endorse
    balance_guarantor = guarantor_financial_balance.balance

    print(f"valeur des montant : debt_amount_guarantor: {debt_amount_guarantor}")
    print(f"valeur des montant : amount_to_endorse_guarantor: {amount_to_endorse_guarantor}")
    print(f"valeur des montant : balance_guarantor: {balance_guarantor}")

    net_balance_guarantor = balance_guarantor - amount_to_endorse_guarantor - debt_amount_guarantor
    if payload.amount_claimed > net_balance_guarantor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The guarantor does not have sufficient funds to guarantee the loan."
            )
        )

    operator = await db.execute(
        select(Operator.id).where(Operator.id == payload.desired_payment_method)
    )
    operator_id = operator.scalar_one_or_none()
    if not operator_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"operator with ID {payload.desired_payment_method} not found."
        )

    # Récupérer les configurations sur la validation
    validator_result = await db.execute(select(ValidatorConfig).where(ValidatorConfig.cycle_id == payload.cycle_id,
                                                                      ValidatorConfig.flag == ValidatorFlag.validation_disbursement_loan))
    validator_config = validator_result.scalar_one_or_none()

    if not validator_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Aucune configuration de validation trouvée pour cette opération.")

    # Créer un ticket de validation (ticket de validation qui en 1er lieu chez le garant renseigné)
    ticket = Ticket(
        source_table=SourceTable.loan_requests,
        step=StepValidationLoan.opening_loan,
        initiator_id=payload.guarantee.guarantor_id,
        users_validator=validator_config.validators_id,
        users_validated={},
        all_users_validated={},
        state=ValidationState.pending,
    )
    db.add(ticket)
    await db.flush()

    # Enregistrement de la demande de prêt
    new_loan_request = LoanRequest(
        id=uuid4(),
        user_id=user_id,
        cycle_id=payload.cycle_id,
        ticket_id=ticket.id,
        amount_claimed=payload.amount_claimed,
        desired_payment_method=payload.desired_payment_method,
        loan_config_id=check_loan_config.id,
        loan_duration_day=check_loan_config.duration_in_day,
        interest_percentage=check_loan_config.interest_percentage,
        refund_at_end_of_cycle=check_loan_config.is_paid_once,
        cut_interest_before=payload.cut_interest_before,
        payment_tranche=check_loan_config.payment_tranche,
        guarantor_opinion=None,
        guarantor_id=str(payload.guarantee.guarantor_id),
        guarantee_id=payload.guarantee.guarantee_id,
        file_names=payload.guarantee.guarantee_file_names,
        state=ValidationState.pending
    )
    db.add(new_loan_request)
    await db.flush()

    await db.commit()

    return {
        "message": "Demande de prêt enregistrée avec succès. En attente de validation par le garant choisit.",
        "status": status.HTTP_200_OK
    }

async def check_existing_pending_request(db: AsyncSession, user_id: UUID):
    try:
        existing_request = (
            await db.execute(
                select(LoanRequest).where(
                    LoanRequest.user_id == user_id,
                    LoanRequest.state == None
                )
            )
        ).scalars().first()

        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The user already has a loan request being processed."
            )

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking pending requests: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error has occurred: {e}"
        )


async def validation_guarantor_loan(db: AsyncSession, loan_id: UUID, payload: ValidationGuarantorSchema, token: str):
    # Vérifie l'existence de la demande d'emprunt
    result_loan = await db.execute(
        select(LoanRequest).where(LoanRequest.id == loan_id, LoanRequest.cycle_id == payload.cycle_id))
    loan = result_loan.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found for this cycle")

    user_id = JWTBearer.decode_jwt(token).get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalid Token : missing member_id or user_id")

    # Récupérer le ticket à traiter par le ou les garants (pour le pluriel maj à venir)
    result = await db.execute(
        select(Ticket)
        .join(LoanRequest, LoanRequest.ticket_id == Ticket.id)
        .where(LoanRequest.id == loan_id)
    )

    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun ticket trouvé pour cette demande d'emprunt."
        )
    if ticket.step != StepValidationLoan.opening_loan or ticket.state != ValidationState.pending or ticket.close_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="This validation ticket is not pending at this validator")

    # Créer l'enregistrement de la validation du garant dans TicketLog
    ticketLog = TicketLog(
        ticket_id=ticket.id,
        user_id=user_id,
        opinion=payload.opinion,
        reason=payload.reason,
        infos="Avis du garant sur le ticket de demande d'emprunt dont il avalise",
    )
    db.add(ticketLog)
    await db.flush()

    # vérification de l'avis du garant
    if ticketLog.opinion == ValidationOpinion.rejected:
        ticket.state = ValidationState.rejected
        ticket.step = StepValidationLoan.authorization_guarantor
        ticket.rejection_comment = payload.reason
        ticket.add_validated(UUID(user_id))
        ticket.add_all_validated(UUID(user_id))
        ticket.updated_at = datetime.now(timezone.utc)
        ticket.close_at = datetime.now(timezone.utc)
        loan.state = ValidationState.rejected
        loan.guarantor_opinion = False
        loan.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return {
        "message": "Demande d'avalisation rejeté par le garant",
        "status": status.HTTP_200_OK,
        "comment":payload.reason
        }

    # Validation du garant
    ticket.add_validated(UUID(user_id))
    ticket.add_all_validated(UUID(user_id))

    # Créer le projet TicketLog pour la validation des autorisateur
    ticket.step = StepValidationLoan.authorization_guarantor
    ticket.updated_at = datetime.now(timezone.utc)
    loan.guarantor_opinion = True
    loan.updated_at = datetime.now(timezone.utc)

    db.add(ticket)
    await db.commit()
    return {
        "message": "Avalisation acceptée par le Garant.Demande de prêt en cours de traitement.",
        "status": status.HTTP_200_OK,
        "comment": payload.reason
    }


async def reject_loan_request(db: AsyncSession, loan_id: UUID, payload: RejectLoanRequestSchema, token: str):
    # Vérifie l'existence de la demande d'emprunt
    result_loan = await db.execute(
        select(LoanRequest).where(LoanRequest.id == loan_id, LoanRequest.cycle_id == payload.cycle_id))
    loan = result_loan.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found for this cycle")

    user_id = JWTBearer.decode_jwt(token).get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalid Token : missing member_id or user_id")
    print(f"identifiant de l'utilisateur :{user_id}")

    # Récupérer la configuration du validateur attendu
    result = await db.execute(
        select(ValidatorConfig).where(ValidatorConfig.cycle_id == payload.cycle_id,
                                      ValidatorConfig.flag == ValidatorFlag.validation_disbursement_loan))
    validation_config = result.scalar_one_or_none()
    print(f"valeur config : {validation_config}")

    if not validation_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No validation configuration found for this operation")

    # Récupérer le ticket à traiter par les autorisateurs
    result = await db.execute(
        select(Ticket)
        .join(LoanRequest, LoanRequest.ticket_id == Ticket.id)
        .where(LoanRequest.id == loan_id)
    )
    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun ticket trouvé pour cette demande d'emprunt."
        )
    if ticket.step != StepValidationLoan.authorization_guarantor or ticket.state != ValidationState.pending or ticket.close_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="This validation ticket is not pending at this validator")

    if not ticket.is_validator(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource."
        )

    # Créer  l'enregistrement de la validation du garant dans TicketLog
    ticketLog = TicketLog(
        ticket_id=ticket.id,
        user_id=user_id,
        opinion=ValidationOpinion.rejected,
        reason=payload.reason,
        infos="Rejet d'une demande d'emprunt",
    )
    db.add(ticketLog)
    await db.flush()

    # Mise à jour du ticket courant
    ticket.state = ValidationState.rejected
    ticket.step = StepValidationLoan.authorization_validators
    ticket.rejection_comment = payload.reason
    ticket.add_all_validated(UUID(user_id))
    ticket.mark_user_validated(UUID(user_id))
    ticket.updated_at = datetime.now(timezone.utc)
    ticket.close_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(ticket)
    loan.state = ValidationState.rejected
    loan.updated_at = datetime.now(timezone.utc)
    db.add(loan)
    await db.commit()

    return {
        "message": "Demande de prêt rejetée avec succès",
        "status": status.HTTP_200_OK,
    }



async def authorize_loan_request(
        db: AsyncSession,
        loan_id: UUID,
        payload: LoanAutorisationRequest,
        token: str
):
    validator_id = JWTBearer.decode_jwt(token).get("user_id")
    print(f"validator_id : {validator_id}")
    if not validator_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalid Token: missing user_id or member_id")

    # Vérifions l’existence du prêt
    loan = await db.get(LoanRequest, loan_id)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The loan request does not exist")

    # Récupérer le dernier ticket non traité pour cette demande

    result = await db.execute(
            select(Ticket)
            .join(LoanRequest, LoanRequest.ticket_id == Ticket.id)
            .where(LoanRequest.id == loan_id)
        )
    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun ticket trouvé pour cette demande d'emprunt."
        )
    if ticket.step != StepValidationLoan.authorization_guarantor or ticket.state != ValidationState.pending or ticket.close_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="This validation ticket is not pending at this validator")

    # vérifier que l'user connecté existe dans users_validator
    if not ticket.is_validator(validator_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource."
        )

    # Récupérer les configurations de validation
    result = await db.execute(
        select(ValidatorConfig).where(ValidatorConfig.cycle_id == payload.cycle_id,
                                      ValidatorConfig.flag == ValidatorFlag.validation_disbursement_loan))
    validation_config = result.scalar_one_or_none()

    if not validation_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No validation configuration found in this cycle for this operation.")

    # Créer l'enregistrement de la validation de l'autorisateur  connecté
    ticketLog = TicketLog(
        ticket_id=ticket.id,
        user_id=validator_id,
        opinion=ValidationOpinion.accepted,
        reason=payload.reason,
        infos="Validation de la demande d'emprunt",
    )
    db.add(ticketLog)
    await db.flush()

    # Mise à jour du ticket associé
    ticket.state = ValidationState.pending
    ticket.opinion = ValidationOpinion.accepted
    ticket.reason = payload.reason
    ticket.updated_at = datetime.now(timezone.utc)
    ticket.add_all_validated(UUID(validator_id))
    ticket.mark_user_validated(UUID(validator_id))
    db.add(ticket)
    await db.commit()

    #vérifions s'il y'a encore des validateurs, si oui on n'incémente pas StepValidation
    if not ticket.is_fully_validated:
        return {
            "message": "Validation recorded. Waiting for the next validator.",
            "status": status.HTTP_200_OK,
            #"data": ticket
        }
    else:
        ticket.step = StepValidationLoan.authorization_validators
        ticket.update_at = datetime.now(timezone.utc)
    await db.commit()
    return {
        "message": "Le décaissement pour cette demande d'emprunt a été autorisé par tous les validateurs",
        "status": status.HTTP_200_OK,
        #"data": ticket
    }



async def disburse_loan_amount(
        db: AsyncSession,
        loan_id: UUID,
        payload: LoanDisbursementRequest,
        token: str
):
    # Extraire les données du payload
    payment_method_code = payload.payment_method_code
    payment_mode_code = payload.payment_mode_code
    financial_reference = payload.financial_reference
    debit_account = payload.debit_account
    credit_account = payload.credit_account
    attachment_url = payload.attachment_url

    validator_id = JWTBearer.decode_jwt(token).get("user_id")
    print(f"validator_id : {validator_id}")
    if not validator_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalid Token: missing user_id or member_id")

    # Vérifions l’existence du prêt
    loan = await db.get(LoanRequest, loan_id)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The loan request does not exist")

    # Récupérer le ticket à traiter par le trésorier
    result = await db.execute(
        select(Ticket)
        .join(LoanRequest, LoanRequest.ticket_id == Ticket.id)
        .where(LoanRequest.id == loan_id)
    )
    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun ticket trouvé pour cette demande d'emprunt."
        )
    if ticket.step != StepValidationLoan.authorization_validators or ticket.state != ValidationState.pending or ticket.close_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="This validation ticket is not pending at this validator")

    # Récupérer les configurations de validation (PAS NECESSAIRE)
    result = await db.execute(
        select(ValidatorConfig).where(ValidatorConfig.cycle_id == payload.cycle_id,
                                      ValidatorConfig.flag == ValidatorFlag.validation_disbursement_loan))
    validation_config = result.scalar_one_or_none()

    if not validation_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No validation configuration found in this cycle for this operation.")

    # récupération du garant de la dette
    result_guarantor = await db.execute(
        select(LoanRequest.guarantor_id).where(LoanRequest.id == loan_id))
    guarantor_id = result_guarantor.scalar_one_or_none()

    # initiateur de la demande d'emprunt
    result_initiator = await db.execute(
        select(LoanRequest.user_id).where(LoanRequest.id == loan_id))
    loan_initiator = result_initiator.scalar_one_or_none()
    print(f"valeur de loan_initiator: {loan_initiator}")

    # Récupérer les configurations du prêt
    result = await db.execute(select(LoanConfig).where(LoanConfig.cycle_id == payload.cycle_id))
    loan_parameter = result.scalars().first()
    if not loan_parameter:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This Loan Configuration does not exist.")

    interest_rate = Decimal(str(loan_parameter.interest_percentage))
    tranche_count = loan_parameter.payment_tranche
    capital = Decimal(str(loan.amount_claimed))
    total_interest = (capital * interest_rate) / 100

    # Evaluer le montant à verser en fonction du choix de rembourssement des intérêts
    cut_interest_before = loan.cut_interest_before
    if cut_interest_before:
        amount_given = Decimal(str(loan.amount_claimed)) - Decimal(str(total_interest))
        capital = amount_given
        total_to_refund = capital
        total_interest = 0

    else:
        amount_given = Decimal(str(loan.amount_claimed))
        capital = amount_given
        total_to_refund = Decimal(str(capital)) + Decimal(str(total_interest))

    # Obetenir la date de rembourssement prévu
    current_date = datetime.now(timezone.utc)
    duration_in_day = loan_parameter.duration_in_day
    refund_preview_day = current_date + timedelta(days=duration_in_day)

    if not payment_mode_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payment '{payment_mode_code}' method.")

    # Vérifier que pour l'opérateur choisit, sa valeur type_operator renseigné existe bien
    operator = await db.get(Operator, payload.operator_id)
    print(f"identifiant :{operator.type_operator}")
    if not operator.type_operator == payment_method_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Please check the type of operator entered."
        )

    # Validation conditionnelle des champs pour le mode MANUEL
    if payment_mode_code == PaymentMode.manual:
        if not financial_reference or not debit_account or not credit_account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Références, comptes débit et crédit sont obligatoires pour un paiement manuel."
            )
        if not attachment_url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Une pièce jointe est requise pour le mode de paiement manuel.")

    elif payment_mode_code == PaymentMode.auto:
         # Prochaine MAJ à faire
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MAJ à faire")
    elif payment_mode_code == PaymentMode.cash:
        # Paiement direct, on ne doit pas avoir  de référence
        debit_account = "CAISSE"
        credit_account = "SUBSCRIBER_ACCOUNT"

    # Créer l'enregistrement du versement
    payment = PaymentReference(
        id=uuid4(),
        source_table=SourceTable.loan_requests,
        #source_table="loan_requests",
        source_id=loan_id,
        financial_reference=payload.financial_reference,
        debit_account=payload.debit_account,
        credit_account=payload.credit_account,
    )
    db.add(payment)
    await db.flush()

    # Créer les dettes par tranche
    tranche_capital = capital / tranche_count
    tranche_interest = total_interest / tranche_count

    print(f"valeur  tranche_count :{tranche_count}")

    debt = Debt(
        id=uuid4(),
        loan_request_id=loan_id,
        operator_id=payload.operator_id,
        amount_given=capital,
        refund_amount=round(capital, 2),
        refund_interest=round(total_interest, 2),
        total_refund_amount=round(total_to_refund, 2),
        tranche_number=loan_parameter.payment_tranche,
        type=SourceTable.loan_requests,
        refund_preview_day=refund_preview_day,
        date_he_repaid=None,
        state=False
        )
    db.add(debt)
    await db.flush()

    for i in range(tranche_count):
        debt_slice = DebtSlice(
            id=uuid4(),
            debts_id=debt.id,
            refund_amount=round(tranche_capital, 2),
            refund_interest=round(tranche_interest, 2),
            total_refund_amount=round(Decimal(str(tranche_capital)) + Decimal(str(tranche_interest)), 2),
            tranche_number=i + 1,
            state=False
        )
        db.add(debt_slice)
        await db.commit()

    # Mouvements des comptes (trésorier,emprunteur et garant)
    await financial_movement_process(db, loan_initiator, guarantor_id, payload.cycle_id, capital, loan_id)

    # Créer l'enregistrement du décaissement effectué
    ticketLog = TicketLog(
        ticket_id=ticket.id,
        user_id=validator_id,
        opinion=ValidationOpinion.accepted,
        reason=payload.reason,
        infos="Décaissement des fonds pour un emprunt autorisé",
    )
    db.add(ticketLog)
    await db.flush()

    # Mise à jour du ticket associé à la demande d'emprunt,
    ticket.update = datetime.now(timezone.utc)
    ticket.add_all_validated(UUID(validator_id))
    ticket.step = StepValidationLoan.disbursement_completed
    db.add(ticket)
    await db.commit()

    # Mise à jour de la demande d'emprunt, identifiant dans loan_request
    loan.state = ValidationState.accepted
    loan.updated_at = datetime.now(timezone.utc)
    db.add(loan)
    await db.commit()


    return {
        "message": f"Versement de {capital} FCFA effectué avec succès.",
        "status": status.HTTP_200_OK,
        "total_to_refund": total_to_refund,
    }

async def financial_movement_process(
    db: AsyncSession,
    loan_initiator: UUID,
    guarantor_id: UUID,
    cycle_id: UUID,
    capital: Decimal,
    loan_id: UUID
):
    # Trouver le compte financier de l'emprunteur
    account_subscriber = await db.execute(
        select(FinancialAccount).where(
            FinancialAccount.user_id == loan_initiator,
            FinancialAccount.cycle_id == None
        )
    )
    subscriber_account = account_subscriber.scalars().first()

    if not subscriber_account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The financial account of the member requesting the loan cannot be found")

    # Trouver le compte financier de l'organisation
    account_cycle = await db.execute(
        select(FinancialAccount).where(
            FinancialAccount.user_id == None,
            FinancialAccount.cycle_id == cycle_id
        )
    )
    cycle_account = account_cycle.scalars().first()
    if not cycle_account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The organization's financial account does not exist.")

    # Trouver le compte financier du garant
    account_guarantor = await db.execute(
        select(FinancialAccount).where(
            FinancialAccount.user_id == guarantor_id,
            FinancialAccount.cycle_id == None
        )
    )
    guarantor_account = account_guarantor.scalars().first()
    if not guarantor_account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="The financial account of the guarantor selected to guarantee the loan cannot be found")

    # MAJ des comptes du cycle
    if cycle_account.balance < capital:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient funds in the organization's financial account.")

    # MAJ de l'état des comptes financier du garant : montant de la demande endossé
    old_amount_to_endorse = guarantor_account.amount_to_endorse
    new_amount_to_endorse = Decimal(old_amount_to_endorse) + capital
    guarantor_account.amount_to_endorse = new_amount_to_endorse
    guarantor_account.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(guarantor_account)

    table_name = LoanRequest.__tablename__

    # Création de l'enregistrement de mouvement financier pour le garant du prêt
    movement_fond_guarantor = AccountMovement(
        id=uuid4(),
        financial_account_id=guarantor_account.id,
        source_table=table_name,
        source_id=loan_id,
        old_balance=old_amount_to_endorse,
        new_balance=new_amount_to_endorse,
        amount_to_endorse=capital
    )
    db.add(movement_fond_guarantor)

    # MAJ du montant emprunté par l'organisation : montant de la dette
    old_amount_loaned_by_cycle = cycle_account.amount_loaned_by_cycle
    new_amount_loaned_by_cycle = Decimal(old_amount_loaned_by_cycle) + capital
    cycle_account.amount_loaned_by_cycle = new_amount_loaned_by_cycle
    cycle_account.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(cycle_account)

    # Création de l'enregistrement de mouvement pour le compte du cycle
    movement_fond_cycle = AccountMovement(
        id=uuid4(),
        financial_account_id=cycle_account.id,
        source_table=table_name,
        source_id=loan_id,
        old_balance=old_amount_loaned_by_cycle,
        new_balance=new_amount_loaned_by_cycle,
        amount_loaned_by_cycle=capital
    )
    db.add(movement_fond_cycle)

    # MAJ de l'état des comptes financier du membre : montant de la demande d'emprunt
    old_debt_amount = subscriber_account.debt_amount
    new_debt_amount = Decimal(old_debt_amount) + capital
    subscriber_account.debt_amount = new_debt_amount
    subscriber_account.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(subscriber_account)

    # Création de l'enregistrement de mouvement pour l'initiateur de la demande du prêt
    movement_fond_member = AccountMovement(
        id=uuid4(),
        financial_account_id=subscriber_account.id,
        source_table=table_name,
        source_id=loan_id,
        old_balance=old_debt_amount,
        new_balance=new_debt_amount,
        debt_amount=capital
    )
    db.add(movement_fond_member)
    await db.flush()


async def validation_receipt_payment(
        db: AsyncSession,
        loan_id: UUID,
        payload: ReceiptPaymentRequest,
        token: str
):
    try:
        table_name = LoanRequest.__tablename__

        validator_id = JWTBearer.decode_jwt(token).get("user_id")
        print(f"validator_id : {validator_id}")
        if not validator_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Invalid Token: missing user_id or member_id")

        # Vérifions l’existence du prêt
        loan = await db.get(LoanRequest, loan_id)
        if not loan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The loan request does not exist")

        # initiateur de la demande d'emprunt
        result_initiator = await db.execute(
            select(LoanRequest.user_id).where(LoanRequest.id == loan_id))
        loan_initiator = result_initiator.scalar_one_or_none()

        if UUID(validator_id) != loan_initiator:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not the initiator of this loan request")

        # Récupérer le ticket à traiter par le trésorier
        result = await db.execute(
            select(Ticket)
            .join(LoanRequest, LoanRequest.ticket_id == Ticket.id)
            .where(LoanRequest.id == loan_id)
        )
        ticket = result.scalars().first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Aucun ticket trouvé pour cette demande d'emprunt."
            )
        if ticket.step != StepValidationLoan.disbursement_completed or ticket.state != ValidationState.pending or ticket.close_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="This validation ticket is not pending at this validator")

        # Créer l'enregistrement du réquérant pour valider ou invalider la reception des fonds

        ticketLog = TicketLog(
            ticket_id=ticket.id,
            user_id=validator_id,
            opinion=ValidationOpinion.accepted,
            infos="Traitement de l'emprunteur pour valider ou rejeter la reception des fonds",
        )
        db.add(ticketLog)
        await db.flush()

        # Mise à jour du champ
        if payload.payment_received:
            ticket.state = ValidationState.accepted
        else:
            ticket.state = ValidationState.rejected
        print(f"validator_id brut: {validator_id}")
        ticket.updated_at = datetime.now(timezone.utc)
        ticket.add_all_validated(UUID(validator_id))
        ticket.step = StepValidationLoan.confirm_receipt_money
        ticket.close_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(ticket)
        return {
            "message": "Ticket status successfully updated by requester",
            "status": status.HTTP_200_OK,
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne: {str(e)}"
        )

STATE_MAPPING = {
    "valide": True,
    "rejete": False,
    "encours": None
}

async def get_loans_by_state(
    db: AsyncSession,
    payload: ListLoanSchema
):
    try:
        query = select(LoanRequest)

        # Filtrage par état sécurisé
        if payload.state is not None:
           query = query.where(LoanRequest.state == payload.state)

        # Tri
        if payload.order.lower() == FilterOrder.croissant:
            query = query.order_by(asc(LoanRequest.created_at))
        else:
            query = query.order_by(desc(LoanRequest.created_at))

        # Pagination
        result = await db.execute(query.limit(payload.limit).offset(payload.offset))
        items = result.scalars().all()

        return {"message": "demand success", "status": status.HTTP_200_OK, "items": items}

    except Exception as e:
        print(f"[ERROR] get_loans_by_state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne: {str(e)}"
        )


async def get_loans_by_user(
    db: AsyncSession,
    payload: ListLoanSchema,
):
    try:
        query = select(LoanRequest).where(LoanRequest.user_id == payload.user_id)

        # Filtrage par état sécurisé
        if payload.state is not None:
            query = query.where(LoanRequest.state == payload.state)

        # Tri
        if payload.order.lower() == FilterOrder.croissant:
            query = query.order_by(asc(LoanRequest.created_at))
        else:
            query = query.order_by(desc(LoanRequest.created_at))

        # Pagination
        result = await db.execute(query.limit(payload.limit).offset(payload.offset))
        items = result.scalars().all()

        return {"message": "demand success", "status": status.HTTP_200_OK, "items": items}

    except Exception as e:
        print(f"[ERROR] get_loans_by_state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne: {str(e)}"
        )


async def get_debts_by_loan_request(
    db: AsyncSession,
    payload: ListLoanSchema,
    #loan_request_id: UUID,
    #refunded: Optional[bool] = None,
    #offset: int = 0,
    #limit: int = 10,
    #sort_by: str = "created_at",
    #order: str = "desc"
):
    try:
        # Vérifier que le champ de tri existe dans le modèle
        if not hasattr(Debt, payload.sort_by):
            raise HTTPException(status_code=400, detail=f"Champ de tri invalide: {payload.sort_by}")

        # Construire la requête
        query = select(Debt).where(Debt.loan_request_id == payload.loan_request_id)

        # Filtre refunded
        if payload.refunded is not None:
            query = query.where(Debt.refunded == payload.refunded)

        # Tri
        column = getattr(Debt, payload.sort_by)
        if payload.order.lower() == "asc":
            query = query.order_by(asc(column))
        else:
            query = query.order_by(desc(column))

        # Comptage total
        count_query = query.with_only_columns(func.count()).order_by(None)
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()
        result = await db.execute(query.offset(payload.offset).limit(payload.limit))
        debts = result.scalars().all()

        return {
            "message": "demand success",
            "status": status.HTTP_200_OK,
            "total": total,
            "items": debts
        }

    except Exception as e:
        print(f"[ERROR] get_loans_by_state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne: {str(e)}"
        )



async def get_user_debt_info(
    db: AsyncSession,
    user_id: UUID,
    cycle_id: UUID,
):
    try:
        stmt = (
            select(func.sum(Debt.total_refund_amount))
            .join(LoanRequest, LoanRequest.id == Debt.loan_request_id)
            .filter(LoanRequest.user_id == user_id, LoanRequest.cycle_id == cycle_id)
        )

        result = await db.execute(stmt)
        total_amount = result.scalar()
        has_debt = False
        if total_amount and total_amount > 0:
            has_debt = True
        return {
            "error": None,
            "has_debt": has_debt,
            "total_debt_amount": float(total_amount) if total_amount else 0
        }

    except Exception as e:
        return {
            "error": str(e),
            "has_debt": False,
            "total_debt_amount": 0
        }


"""
    Fonction old qui ont modifié en attente de rejet total;
"""

async def financial_movement_process_old(
    db: AsyncSession,
    subscriber_id: UUID,
    cycle_id: UUID,
    capital: Decimal,
    loan_id: UUID
):
    # Trouver le compte financier du membre
    account_subscriber = await db.execute(
        select(FinancialAccount).where(
            FinancialAccount.user_id == subscriber_id,
            FinancialAccount.cycle_id == None
        )
    )
    subscriber_account = account_subscriber.scalars().first()

    if not subscriber_account:
        raise HTTPException(status_code=404, detail="The financial account of the member requesting the loan cannot be found")

    # Trouver le compte financier de l'organisation
    account_cycle = await db.execute(
        select(FinancialAccount).where(
            FinancialAccount.user_id == None,
            FinancialAccount.cycle_id == cycle_id
        )
    )
    cycle_account = account_cycle.scalars().first()
    if not cycle_account:
        raise HTTPException(status_code=404, detail="Compte de trésorerie de l'organisation introuvable")

    # Débiter le compte du cycle
    if cycle_account.balance < capital:
        raise HTTPException(status_code=400, detail="Fonds insuffisants sur le compte de l'organisation.")

    # Débit du compte de l'organisation
    old_cycle_balance = cycle_account.balance
    new_cycle_balance = Decimal(old_cycle_balance) - capital
    cycle_account.balance = new_cycle_balance
    db.add(cycle_account)
    table_name = LoanRequest.__tablename__

    # Création de l'enregistrement de mouvement pour le débit du cycle
    movement_debit_cycle = AccountMovement(
        id=uuid4(),
        financial_account_id=cycle_account.id,
        source_table=table_name,
        source_id=loan_id,
        #date_mouvement=datetime.now(timezone.utc),
        old_balance=old_cycle_balance,
        new_balance=new_cycle_balance
    )
    db.add(movement_debit_cycle)

    # 2. Déditer le compte du membre
    old_subcriber_balance = subscriber_account.balance
    new_subcriber_balance = Decimal(old_subcriber_balance) - capital
    subscriber_account.balance = new_subcriber_balance
    db.add(subscriber_account)

    # Création de l'enregistrement de mouvement pour le débit du cycle
    movement_debit_member = AccountMovement(
        id=uuid4(),
        financial_account_id=subscriber_account.id,
        source_table=table_name,
        source_id=loan_id,
        #date_mouvement=datetime.now(timezone.utc),
        old_balance=old_subcriber_balance,
        new_balance=new_subcriber_balance
    )
    db.add(movement_debit_member)
    await db.flush()



async def disburse_loan_amount_old(db: AsyncSession, loan_id: UUID, data: RejectLoanRequestSchema,
                                   token: str):
    # Vérifie l'existence de la demande d'emprunt
    result = await db.execute(
        select(LoanRequest).where(LoanRequest.id == loan_id, LoanRequest.cycle_id == data.cycle_id))
    loan = result.scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found for this cycle")

    validator_id = JWTBearer.decode_jwt(token).get("user_id")
    if not validator_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Invalid Token : user_id or member_id missing")

    # Récupérer la configuration de validation
    result = await db.execute(
        select(ValidatorConfig).where(ValidatorConfig.cycle_id == data.cycle_id,
                                      ValidatorConfig.flag == ValidatorFlag.validation_disbursement_loan))
    validation_config = result.scalar_one_or_none()

    if not validation_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No validation configuration found for this operation.")

    if not validator_id == validation_config.validators_id.get("0"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You do not have the rights to validate loan")

        # Récupérer le dernier ticket non traité pour cette demande
    result = await db.execute(select(Ticket).where(
        Ticket.source_table == "loan_requests", Ticket.source_id == loan_id,
        Ticket.state == ValidationState.pending, Ticket.validator_id == UUID(validator_id),
        Ticket.opinion is None
    ))
    ticket = result.scalar_one_or_none()

    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No pending validation ticket for this validator")

    # Vérification d’ordre de validation
    expected_index = None
    for k, v in ticket.users_validator.items():
        if v == validator_id:
            expected_index = int(k)
            break

    # Mise à jour du ticket courant
    ticket.opinion = data.opinion
    ticket.reason = data.reason
    ticket.users_validated[str(expected_index)] = validator_id
    ticket.users_validator.pop(str(expected_index), None)
    ticket.updated_at = datetime.now(timezone.utc)
    await db.flush()

    """if data.opinion == ValidationState.rejected:
        # Rejet du ticket
        ticket.state = ValidationState.rejected
        loan.state = ValidationState.rejected
        loan.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return {"message": "Request to join rejected. Process completed.", "data": ticket}"""

    # Si tous ont validé (plus personne dans users_validator) // ici tu vas faire cette action (maj state après avoir terminer le versement)
    if not ticket.users_validator:
        ticket.state = ValidationState.accepted
        loan.state = ValidationState.accepted
        loan.subscription_date = datetime.now(timezone.utc)

        # Sinon, créer le prochain ticket
        next_index = expected_index + 1
        next_validator_id = ticket.users_validator.get(str(next_index))
        if not next_validator_id:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error: following validator not defined")

        new_ticket = Ticket(
            source_table="loan_requests",
            source_id=loan_id,
            validator_id=UUID(next_validator_id),
            users_validator=ticket.users_validator.copy(),
            users_validated=ticket.users_validated.copy(),
            state=ValidationState.pending,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_ticket)
        await db.commit()
        return {"message": "Validation recorded. Waiting for the next validator.", "data": ticket}
