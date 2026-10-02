from typing import Literal

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)
    request_id: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


class DatabaseHealthResponse(BaseModel):
    status: Literal["ok", "error"]
    detail: str | None = None