# database.py
import json
import urllib.request
import urllib.parse
from collections.abc import AsyncGenerator
from urllib.error import HTTPError, URLError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from app import sql_logger

Base = declarative_base()


class Database:
    engine = None
    SessionEngine = None

    @staticmethod
    async def _load_from_secret_manager() -> None:
        try:
            aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
            encoded_parameter_key = urllib.parse.quote(os.environ.get('PARAMETER_STORE_KEY'))
            req = urllib.request.Request(
                f'http://localhost:2773/systemsmanager/parameters/get?name={encoded_parameter_key}')
            req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
            data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
            config = json.loads(data['Parameter']['Value'])
            os.environ.update(config)
        except HTTPError as e:
            print("HTTPError:", e.code, e.reason)
        except URLError as e:
            print("URLError:", e.reason)
        except Exception as e:
            print("An error occurred:", e)

    @staticmethod
    async def init_database() -> None:
        if os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None:
            await Database._load_from_secret_manager()
        db_url = f"{os.getenv('DB_DRIVER_ASYNC')}://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        Database.engine = create_async_engine(db_url)
        sql_logger.setup_sql_logging(Database.engine)
    @staticmethod
    def get_session():
        if Database.SessionEngine is None:
            Database.SessionEngine = sessionmaker(bind=Database.engine, class_=AsyncSession, expire_on_commit=False)
        return Database.SessionEngine

    @staticmethod
    async def get_instance() -> AsyncGenerator[AsyncSession, None]:
        async_session_local = Database.get_session()
        async with async_session_local() as session:
            yield session

async def get_db_instance() -> AsyncGenerator[AsyncSession, None]:
    async for session in Database.get_instance():
        yield session
