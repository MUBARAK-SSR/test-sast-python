import abc
from typing import List

# La classe abstraite (le contrat)
class PermProvider(abc.ABC):
    @abc.abstractmethod
    def get_permissions(self, user_id: str) -> List[str]:
        pass
    
    @abc.abstractmethod
    def check_permission(self, user_id: str, permission: str, resource_type: str, resource_id: str) -> bool:
        pass