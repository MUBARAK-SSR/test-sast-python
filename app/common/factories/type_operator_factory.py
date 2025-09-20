import uuid
from datetime import datetime, timezone
import factory
from app.common.models.TypeOperator import TypeOperator
from app.services.cycle_configurations.constants import PaymentType


class TypeOperatorFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = TypeOperator
        sqlalchemy_session_persistence = "flush"

    id = factory.LazyFunction(uuid.uuid4)
    # name = factory.Iterator([PaymentType.bank, PaymentType.mopay, PaymentType.cash])
    name = factory.Iterator(["bank", "mopay", "cash"])
    description = factory.Faker("sentence")
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = None
    deleted_at = None
