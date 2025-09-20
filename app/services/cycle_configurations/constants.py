import enum


# from http.client import HTTPException
# from fastapi import Depends
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
# from starlette import status
# from app.common.models.TypeOperator import TypeOperator
# from app.config.database import get_db_instance


class Currency(str, enum.Enum):
    XAF = "XAF"


class WeekDay(str, enum.Enum):
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"
    sunday = "sunday"


class FrequencyWeek(str, enum.Enum):
    first = "first"
    second = "second"
    third = "third"
    fourth = "fourth"
    last = "last"


class FrequencyCycle(str, enum.Enum):
    weekly = "weekly"
    monthly = "monthly"


class FinancialAccountType(enum.IntEnum):
    saving = 1
    placement = 2


class PaymentMode(enum.IntEnum):
    auto = 1
    manual = 2
    cash = 3


# async def get_type_operator_id(name: str, db: AsyncSession) -> str:
#     try:
#         type_op_result = await db.execute(select(TypeOperator).where(TypeOperator.name == name,
#                                                                      TypeOperator.deleted_at.is_(None)))
#         type_op = type_op_result.scalar_one_or_none()
#         return type_op.id
#     except Exception as e:
#         raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


class PaymentType(enum.IntEnum):
    bank = 1  # get_type_operator_id("bank", Depends(get_db_instance))
    mopay = 2
    cash = 3


class PaymentAccountType(enum.IntEnum):
    sim_mere = 1
    sim_fille = 2
    sub_client = 3
    user = 4


class OperatorEnum(enum.IntEnum):
    afriland = 1
    orange = 2
    mtn = 3


class ValidatorFlag(enum.IntEnum):
    membership_cycle = 1
    collection_contribution = 2
    validation_disbursement_loan = 3
    collection_reimbursement = 4
    validation_disbursement_withdrawal = 5

    @property
    def description(self):
        return {
            ValidatorFlag.membership_cycle: "Validation for joining a cycle",
            ValidatorFlag.collection_contribution: "Validation for contribution collection",
            ValidatorFlag.validation_disbursement_loan: "Validation for loan disbursement",
            ValidatorFlag.collection_reimbursement: "Validation for reimbursement collection",
            ValidatorFlag.validation_disbursement_withdrawal: "Validation for withdrawal disbursement",
        }[self]


class PenalityFlag(enum.IntEnum):
    mandatory_contribution_failure = 1
    early_withdrawal = 2
    delay_reimbursement = 3

    @property
    def description(self) -> str:
        return {
            PenalityFlag.mandatory_contribution_failure: "Penalty applied when a member fails to make a mandatory contribution",
            PenalityFlag.early_withdrawal: "Penalty applied when funds are withdrawn before the allowed period",
            PenalityFlag.delay_reimbursement: "Penalty applied when a loan reimbursement is delayed beyond its due date",
        }[self]

class PriorityEnum(enum.IntEnum):
    low = 1
    average = 2
    high = 3


class ValidationState(enum.IntEnum):
    accepted = 1
    pending = 0
    rejected = -1


class ValidationOpinion(enum.IntEnum):
    accepted = 1
    rejected = -1


class CycleState(enum.IntEnum):
    not_open = 1
    open = 2
    closed = 3

class SourceTable(enum.IntEnum):
    request_to_joins = 1
    contributions = 2
    loan_requests = 3
    refunds = 4
    withdrawals = 5


class RequestToJoinsStep(enum.IntEnum):
    opening = 1
    validation = 2


class ContributionStep(enum.IntEnum):
    opening = 1
    validation = 2


class WithdrawalStep(enum.IntEnum):
    opening = 1
    validation = 2
    disbursement = 3
    confirmation = 4
    deny_confirmation = 5
    re_disbursement = 6
    send_for_confirmation = 7
