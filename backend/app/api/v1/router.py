from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.resume_analysis import router as resume_analysis_router

router = APIRouter()
router.include_router(health_router)
router.include_router(resume_analysis_router)