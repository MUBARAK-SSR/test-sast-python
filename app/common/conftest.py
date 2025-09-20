import os
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config.database import Base
from app.config.database import get_db_instance

from main import app

# DB en mémoire partagée entre toutes les connexions
DATABASE_URL = f"{os.getenv('DB_DRIVER_ASYNC')}://{os.getenv('DB_TEST_USER')}:{os.getenv('DB_TEST_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_TEST_NAME')}"

# Engine de test avec NullPool
async_engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

# Session async liée à l'engine de test
TestingSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Création/destruction de la base entre chaque test
@pytest.fixture(scope="function", autouse=True)
async def prepare_database():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Override de la dépendance get_db_instance
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


# Plug le remplacement
app.dependency_overrides[get_db_instance] = override_get_db


# Client HTTP async pour tester FastAPI
@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="function")
async def async_session() -> AsyncSession:
    async with async_engine.connect() as connection:
        yield TestingSessionLocal(bind=connection)