# app/common/factories/activity_factory.py
import uuid
from datetime import datetime, timezone
import factory
from app.common.models.Activity import Activity
from app.services.cycle_configurations.constants import FinancialAccountType


class ActivityFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Activity
        sqlalchemy_session_persistence = "flush"  # ou "commit" si tu veux commit directement

    id = factory.LazyFunction(uuid.uuid4)
    title = factory.Iterator(["saving", "placement"])
    description = factory.Faker("sentence")
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = None
