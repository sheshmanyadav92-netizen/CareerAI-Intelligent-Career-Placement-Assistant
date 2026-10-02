from collections.abc import Iterator

import pytest
from app.core.errors import (
    AuthorizationError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    RateLimitError,
)
from fastapi import APIRouter, FastAPI
from main import create_app
from pydantic import BaseModel
from starlette.testclient import TestClient


class ValidationPayload(BaseModel):
    age: int


@pytest.fixture
def app() -> FastAPI:
    application = create_app(prewarm_local_model=False)
    test_router = APIRouter()

    @test_router.post("/validation")
    def validation(payload: ValidationPayload) -> dict[str, int]:
        return {"age": payload.age}

    @test_router.get("/authentication")
    def authentication() -> None:
        raise InvalidCredentialsError()

    @test_router.get("/forbidden")
    def forbidden() -> None:
        raise AuthorizationError()

    @test_router.get("/conflict")
    def conflict() -> None:
        raise EmailAlreadyExistsError()

    @test_router.get("/rate-limit")
    def rate_limit() -> None:
        raise RateLimitError()

    @test_router.get("/unexpected")
    def unexpected() -> None:
        raise RuntimeError("internal diagnostic marker")

    application.include_router(test_router, prefix="/api/v1/__test__")
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client