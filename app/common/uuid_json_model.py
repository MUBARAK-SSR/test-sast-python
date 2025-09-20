import uuid
from typing import List, Union, Dict, Any
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UUIDJsonModel:
    """
    Mixin pour convertir proprement les champs JSONB <-> UUID
    en utilisant une structure Dict[int, UUID].
    """

    @staticmethod
    def _to_str_dict(values: Union[Dict[int, uuid.UUID], Dict[str, str], None]) -> Dict[int, str]:
        if not values:
            return {}
        result = {}
        for k, v in values.items():
            key = int(k)  # assure que la clé est un entier
            val = str(v) if isinstance(v, uuid.UUID) else v
            result[key] = val
        return result

    @staticmethod
    def _to_uuid_dict(values: Union[Dict[int, str], Dict[str, str], None]) -> Dict[int, uuid.UUID]:
        if not values:
            return {}
        result = {}
        for k, v in values.items():
            key = int(k)
            val = v if isinstance(v, uuid.UUID) else uuid.UUID(v)
            result[key] = val
        return result

    @classmethod
    def jsonb_uuid_property(cls, field_name: str):
        """
        Expose un champ JSONB comme Dict[int, UUID] plutôt que Dict[int, str].
        """
        def getter(self) -> Dict[int, uuid.UUID]:
            return cls._to_uuid_dict(getattr(self, field_name))

        def setter(self, values: Dict[int, uuid.UUID]):
            setattr(self, field_name, cls._to_str_dict(values))

        return property(getter, setter)