from fastapi import APIRouter
from .v2 import api_v2


router = APIRouter()
router.include_router(api_v2.router, prefix="/v2", tags=[ "API Version 2" ])
