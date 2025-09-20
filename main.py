import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from mangum import Mangum
from contextlib import asynccontextmanager
from app.config.database import Database
from app.common.exception_handler import http_exception_handler, validation_exception_handler

from app.services.authentications import router as authentications_routes
from app.services.initial_configurations import router as initial_configurations_routes
from app.services.cycle_configurations import router as cycle_configurations_routes
from app.services.memberships import router as memberships_routes
from app.services.contributions import router as contributions_routes
from app.services.loan_debts import router as loan_debts_routes
from app.services.refunds import router as refunds_routes
from app.services.benefit_distributions import router as benefit_distributions_routes
from app.services.withdrawals import router as withdrawals_routes
from app.services.permissions import router as permission_routes
'''
 import relatif à la cache
'''
from redis import asyncio as aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.coder import JsonCoder

'''
 import relatif à la cache
'''


# Chargement des variables d'environnement si ce n’est pas en Lambda
if os.getenv('AWS_LAMBDA_FUNCTION_NAME') is None:
    load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code exécuté au démarrage de l'application
    await Database.init_database()

    redis_client = aioredis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)
    FastAPICache.init(
        RedisBackend(redis_client),
        prefix="fastapi-cache",
        coder=JsonCoder()
    )

    yield

    await redis_client.close()
    # Code exécuté à la fermeture de l'application (si besoin tu peux ajouter du cleanup ici)

app = FastAPI(lifespan=lifespan)

# Gestionnaires d'exceptions personnalisés
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return await http_exception_handler(request, exc)

@app.exception_handler(RequestValidationError)
async def form_validation_exception_handler(request: Request, exc: RequestValidationError):
    return await validation_exception_handler(request, exc)

# Inclusion des routes
app.include_router(authentications_routes.router)
app.include_router(initial_configurations_routes.router)
app.include_router(cycle_configurations_routes.router)
app.include_router(memberships_routes.router)
app.include_router(contributions_routes.router)
app.include_router(loan_debts_routes.router)
app.include_router(refunds_routes.router)
app.include_router(benefit_distributions_routes.router)
app.include_router(withdrawals_routes.router)
app.include_router(permission_routes.router)


# Pour AWS Lambda (Mangum adapter)
handler = Mangum(app) if os.getenv('AWS_LAMBDA_FUNCTION_NAME') else None
