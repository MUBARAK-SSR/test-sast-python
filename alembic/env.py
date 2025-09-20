import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from alembic import context

# Charger les variables d'environnement
load_dotenv()

# Importer les modèles SQLAlchemy
from app.config.database import Base
from app.common.models import (
    model_permission , Client, SubClient, PenaltyCategory, PenaltySanctionConfig, Activity, User, SubClientUser, SubClientActivity,
    Cycle, Operator, Role, UserCycle, UserCycleRole, ValidatorConfig, RequestToJoin, CycleConfig, LoanConfig, Guarantee,
    Ticket, TicketLog, LoanRequest, Debt, DebtHistory, Refund, Withdrawal, Contribution, PaymentAccount, FinancialAccount, AccountMovement, PaymentReference,
    Log, CyclePaymentAccount,
)

# Alembic config object
config = context.config

# Logging (facultatif)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Construire l'URL de la base **en dehors du bloc conditionnel**
db_url = f"{os.getenv('DB_DRIVER')}://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

if not db_url or 'None' in db_url:
    raise ValueError(f"[Alembic] sqlalchemy.url is invalid: {db_url}")

# Injecter dynamiquement l’URL dans la config Alembic
config.set_main_option("sqlalchemy.url", db_url)

# Cible pour autogenerate
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
