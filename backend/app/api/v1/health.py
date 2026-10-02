from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import DatabaseHealthResponse, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/db", response_model=DatabaseHealthResponse)
def database_health(db: Annotated[Session, Depends(get_db)]) -> DatabaseHealthResponse:
    try:
        db.execute(text("SELECT 1"))
        return DatabaseHealthResponse(status="ok")
    except (SQLAlchemyError, TypeError):
        return DatabaseHealthResponse(status="error", detail="database unavailable")