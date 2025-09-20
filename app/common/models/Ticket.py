import uuid
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy import Column, String, TIMESTAMP, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import relationship

from app.common.uuid_json_model import UUIDJsonModel
from app.config.database import Base
from app.common.models import LoanRequest, Refund, Withdrawal, Contribution, RequestToJoin, TicketLog
from app.services.cycle_configurations.constants import ValidationState, ValidationOpinion


class Ticket(Base, UUIDJsonModel):
    __tablename__ = "tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # ticket_number = Column(String, nullable=False)
    source_table = Column(Integer, nullable=False)
    step = Column(Integer, nullable=False)
    initiator_id = Column(UUID(as_uuid=True), nullable=False)
    next_user = Column(UUID(as_uuid=True), nullable=True)
    users_validator = Column(MutableDict.as_mutable(JSONB), nullable=True, default=dict)
    users_validated = Column(MutableDict.as_mutable(JSONB), nullable=True, default=dict)
    all_users_validated = Column(MutableDict.as_mutable(JSONB), nullable=True, default=dict)
    rejection_comment = Column(String, nullable=True)
    state = Column(Integer, nullable=False)

    open_at = Column(TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    close_at = Column(TIMESTAMP(timezone=True), nullable=True)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)


    refund = relationship("Refund", back_populates="ticket")
    withdrawal = relationship("Withdrawal", back_populates="ticket", uselist=False)
    contribution = relationship("Contribution", back_populates="ticket", uselist=False)
    request_to_join = relationship("RequestToJoin", back_populates="ticket")
    logs = relationship("TicketLog", back_populates="ticket")
    loan_request = relationship("LoanRequest", back_populates="ticket")


    # Propriétés UUID
    validators = UUIDJsonModel.jsonb_uuid_property("users_validator")
    validated = UUIDJsonModel.jsonb_uuid_property("users_validated")

    # Helpers internes
    @staticmethod
    def _to_uuid_dict(values: dict) -> Dict[int, uuid.UUID]:
        if not values:
            return {}
        return {int(k): (v if isinstance(v, uuid.UUID) else uuid.UUID(v)) for k, v in values.items()}

    @staticmethod
    def _to_str_dict(values: dict) -> Dict[int, str]:
        if not values:
            return {}
        return {int(k): str(v) if isinstance(v, uuid.UUID) else v for k, v in values.items()}

    #  Propriétés exposées
    @property
    def validators(self) -> Dict[int, uuid.UUID]:
        return self._to_uuid_dict(self.users_validator)

    @validators.setter
    def validators(self, values: Dict[int, uuid.UUID]):
        self.users_validator = self._to_str_dict(values)

    @property
    def validated(self) -> Dict[int, uuid.UUID]:
        return self._to_uuid_dict(self.users_validated)

    @validated.setter
    def validated(self, values: Dict[int, uuid.UUID]):
        self.users_validated = self._to_str_dict(values)

 #  Méthodes métier
    def add_validator(self, user_id: uuid.UUID):
        """Ajoute un validateur dans users_validator."""
        validators = self.validators
        new_index = max(validators.keys(), default=-1) + 1
        validators[new_index] = user_id
        self.validators = validators

    # def add_validator(self, user_id: uuid.UUID):
    #     """Adds a validator to the users_validator JSONB field."""
    #     # Ensure the field is initialized as a dictionary if it's None
    #     if self.users_validator is None:
    #         self.users_validator = {}
    #
    #     # Get the current validators dictionary
    #     validators_dict = self.users_validator
    #
    #     # Find the next available integer key
    #     if validators_dict:
    #         new_index = max(int(k) for k in validators_dict.keys()) + 1
    #     else:
    #         new_index = 0
    #     # Add the new validator UUID to the dictionary with the new integer key
    #     validators_dict[str(new_index)] = user_id
    #     return self

    def remove_validator(self, user_id: uuid.UUID) -> bool:
        """Retire un utilisateur de users_validator. Retourne True si supprimé."""
        current = self.validators
        for k, v in list(current.items()):
            if v == user_id:
                del current[k]
                self.validators = current
                return True
        return False

    def add_validated(self, user_id: uuid.UUID):
        """Ajoute un utilisateur dans users_validated."""
        validated = self.validated
        new_index = max(validated.keys(), default=-1) + 1
        validated[new_index] = user_id
        self.validated = validated

    def mark_user_validated(self, user_id: uuid.UUID) -> bool:
        """
        Déplace un utilisateur de users_validator -> users_validated.
        Retourne True si l’utilisateur a bien été déplacé, False sinon.
        """
        if user_id not in self.validators.values():
            raise ValueError("This user is not in the validator list")

        if self.remove_validator(user_id):
            self.add_validated(user_id)
            return True
        return False
    def has_validated(self, user_id: uuid.UUID) -> bool:
        """Retourne True si un utilisateur a déjà validé."""
        return user_id in self.validated.values()

    def remaining_validators(self) -> List[uuid.UUID]:
        """
        Retourne la liste des validateurs qui n’ont pas encore validé.
        """
        return list(self.validators.values())

    def reset_validations(self):
        """
        Réinitialise la validation:
        - remet tous les validateurs dans users_validator
        - vide complètement users_validated
        """
        all_users = list(self.validators.values()) + list(self.validated.values())
        new_validators = {i: u for i, u in enumerate(all_users)}
        self.validators = new_validators
        self.validated = {}

    def all_validated(self) -> bool:
        """
        Retourne True si tous les validateurs initiaux
        ont été déplacés dans validated, sans perte.
        """
        initial_validators = set(self._to_uuid_dict(self.users_validator).values()) | set(
            self._to_uuid_dict(self.users_validated).values())
        current_validators = set(self.validators.values())
        current_validated = set(self.validated.values())
        # La validation est complète si : il ne reste aucun validateur et que
        # les validés contiennent bien tous ceux de l'état initial
        return len(current_validators) == 0 and current_validated == initial_validators

    @property
    def is_fully_validated(self) -> bool:
        """
        Retourne True si tous les validateurs initiaux
        ont été déplacés dans validated.
        """
        initial_validators = (
                set(self._to_uuid_dict(self.users_validator).values())
                | set(self._to_uuid_dict(self.users_validated).values())
        )
        current_validators = set(self.validators.values())
        current_validated = set(self.validated.values())
        return len(current_validators) == 0 and current_validated == initial_validators



    # def remove_validator(self, uuid_to_remove: uuid.UUID): #old
    #     """Supprime un validateur et recompacte les index."""
    #     vals = [v for v in self.validators.values() if v != uuid_to_remove]
    #     self.validators = {i: v for i, v in enumerate(vals)}


    # def validate_user(self, user_id: uuid.UUID) -> bool:  #old
    #     """
    #     Déplace un utilisateur de users_validator -> users_validated.
    #     Retourne True si l’utilisateur a bien été déplacé, False sinon.
    #     """
    #     current = self.validators
    #     for k, v in list(current.items()):
    #         if v == user_id:
    #             # retirer du dict source
    #             del current[k]
    #             self.validators = current
    #
    #             # ajouter dans validated
    #             validated = self.validated
    #             new_index = max(validated.keys(), default=-1) + 1
    #             validated[new_index] = user_id
    #             self.validated = validated
    #             return True
    #     return False


    #    def add_validator(self, new_uuid: uuid.UUID): #old
    #        """Ajoute un validateur à la fin."""
    #        vals = self.validators
    #        if not vals:
    #            vals = {0: new_uuid}
    #        else:
    #            max_index = max(vals.keys())
    #            vals[max_index + 1] = new_uuid
    #        self.validators = vals