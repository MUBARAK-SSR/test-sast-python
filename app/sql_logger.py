import logging
import sys
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine

# Configuration du logger
logger = logging.getLogger("sqlalchemy_logger")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Handler vers fichier
file_handler = logging.FileHandler("sql_queries.log", mode='a', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Fonction à appeler explicitement après la création du moteur async
def setup_sql_logging(async_engine: AsyncEngine):
    @event.listens_for(async_engine.sync_engine, "before_cursor_execute")
    def log_sql_statements(conn, cursor, statement, parameters, context, executemany):
        logger.info("SQL Statement: %s", statement)
