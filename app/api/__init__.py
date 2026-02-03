"""API routes module."""
from fastapi import APIRouter
from app.api import auth, documents, shipments, contacts, statistics, exports, reference

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(shipments.router, prefix="/shipments", tags=["Shipments"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["Statistics"])
api_router.include_router(exports.router, prefix="/exports", tags=["Exports"])
api_router.include_router(reference.router, prefix="/reference", tags=["Reference Data"])

