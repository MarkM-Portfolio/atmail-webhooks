from fastapi import APIRouter
from ..endpoints import management


router = APIRouter()
router.include_router(management.router, prefix="/management", tags=[ "Management" ])
