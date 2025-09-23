from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, status
from webhooks.chargebee import chargebee
from .utils.auth import get_secrets
import sys


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.secrets = get_secrets()
    except (Exception) as e:
        sys.exit(1)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def read_root():
    return [ "Root" ]

@app.get("/health")
async def health_check(response: Response):
    response.status_code = status.HTTP_200_OK 
    return { "message": "Health Check", "status": "ok" }

app.include_router(chargebee.router, prefix="/webhooks/chargebee")
