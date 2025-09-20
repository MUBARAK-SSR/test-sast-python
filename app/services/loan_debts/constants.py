# Placeholder content for constants.py
import enum


class StepValidationLoan(enum.IntEnum):
    opening_loan = 1
    authorization_guarantor = 2
    authorization_validators = 3
    disbursement_completed = 4
    confirm_receipt_money = 5


class FilterOrder(str, enum.Enum):
    croissant = "asc"
    decroissant = "desc"
