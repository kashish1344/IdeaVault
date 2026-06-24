from fastapi import APIRouter

from .endpoints.auth import router as auth_router
from .endpoints.generate import router as generate_router
from .endpoints.jobs import router as jobs_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(generate_router)
api_router.include_router(jobs_router)
