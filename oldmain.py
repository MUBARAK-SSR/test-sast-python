import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from app.common.exception_handler import http_exception_handler, validation_exception_handler
from mangum import Mangum

app = FastAPI()

import asyncio
from app.config.database import Database


@app.on_event("startup")
async def on_startup():
    await Database.init_database()


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def form_validation_exception_handler(request, exc):
    return await validation_exception_handler(request, exc)



if os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None:
    handler = Mangum(app)
else:
    load_dotenv()
