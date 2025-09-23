from fastapi import APIRouter
from .services import mail_service, billing


router = APIRouter()
router.include_router(mail_service.router, prefix="/mail-service", tags=[ "Mail Service" ])
router.include_router(billing.router, prefix="/billing", tags=[ "Billing" ])
