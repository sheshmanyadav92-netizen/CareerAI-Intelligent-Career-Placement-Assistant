import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import UUID, uuid4

from app.api.v1.router import router as v1_router
from app.core.config import Settings
from app.core.errors import ApplicationError
from app.schemas.common import ErrorDetail, ErrorResponse
from app.services.llm.base import LLMProviderError
from app.services.llm.ollama_provider import OllamaProvider
from app.services.llm.provider import create_llm_provider
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def _warm_local_model(settings: Settings) -> None:
    started_at = perf_counter()
    try:
        provider = create_llm_provider(settings)
        if isinstance(provider, OllamaProvider):
            await provider.warmup()
    except (LLMProviderError, ApplicationError) as error:
        logger.warning(
            "local_model_warmup_failed exception_type=%s duration_ms=%.2f",
            type(error).__name__,
            (perf_counter() - started_at) * 1000,
        )
    else:
        logger.info(
            "local_model_warmup_completed duration_ms=%.2f",
            (perf_counter() - started_at) * 1000,
        )


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return request_id or str(uuid4())


def _error_response(
    request: Request,
    *,
    code: str,
    status_code: int,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        code=code,
        message=message,
        details=details or [],
        request_id=_request_id(request),
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
        headers={"X-Request-ID": body.request_id},
    )


def _validation_field_path(location: tuple[str | int, ...]) -> str:
    parts: list[str] = []
    for part in location:
        if not parts and part in {"body", "query", "path", "header", "cookie"}:
            continue
        if isinstance(part, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{part}]"
            else:
                parts.append(f"[{part}]")
        elif isinstance(part, str):
            parts.append(part if part.isidentifier() else "field")
    return ".".join(parts) or "body"


def _validation_message(error_type: str) -> str:
    if error_type == "missing":
        return "This field is required."
    if error_type in {"int_parsing", "float_parsing", "bool_parsing", "string_type"}:
        return "Enter a value of the correct type."
    if error_type in {"string_too_short", "string_too_long", "string_pattern_mismatch"}:
        return "Enter a valid value."
    return "Invalid value."


def _validation_details(errors: list[dict[str, object]]) -> list[ErrorDetail]:
    details = []
    for error in errors:
        location = error.get("loc", ())
        if not isinstance(location, tuple):
            location = ()
        error_type = error.get("type", "")
        details.append(
            ErrorDetail(
                field=_validation_field_path(location),
                message=_validation_message(str(error_type)),
            )
        )
    return details


def create_app(*, prewarm_local_model: bool = True) -> FastAPI:
    settings = Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        warmup_task = None
        if prewarm_local_model and settings.llm_provider == "ollama":
            warmup_task = asyncio.create_task(_warm_local_model(settings))
        application.state.local_model_warmup_task = warmup_task
        try:
            yield
        finally:
            application.state.local_model_warmup_task = None
            if warmup_task is not None and not warmup_task.done():
                warmup_task.cancel()
                try:
                    await warmup_task
                except asyncio.CancelledError:
                    logger.info("local_model_warmup_cancelled")

    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @application.middleware("http")
    async def log_request(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if request_id:
            try:
                request_id = str(UUID(request_id))
            except ValueError:
                request_id = None
        request_id = request_id or str(uuid4())
        request.state.request_id = request_id

        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = (perf_counter() - started_at) * 1000
            logger.info(
                "request request_id=%s method=%s path=%s status_code=%d duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                status_code,
                duration_ms,
            )

    @application.exception_handler(ApplicationError)
    async def application_error_handler(
        request: Request,
        exception: ApplicationError,
    ) -> JSONResponse:
        return _error_response(
            request,
            code=exception.code,
            status_code=exception.status_code,
            message=exception.message,
            details=[ErrorDetail(**detail) for detail in exception.details],
        )

    @application.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        errors = exception.errors()
        if any(error.get("type") == "json_invalid" for error in errors):
            return _error_response(
                request,
                code="MALFORMED_REQUEST",
                status_code=400,
                message="The request body is malformed.",
                details=[
                    ErrorDetail(field="body", message="Provide valid JSON.")
                ],
            )
        return _error_response(
            request,
            code="VALIDATION_ERROR",
            status_code=422,
            message="The request contains invalid data.",
            details=_validation_details(errors),
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        request: Request,
        exception: StarletteHTTPException,
    ) -> JSONResponse:
        error_by_status = {
            400: ("BAD_REQUEST", "The request could not be understood."),
            401: ("AUTHENTICATION_REQUIRED", "Authentication is required."),
            403: ("FORBIDDEN", "You do not have permission to perform this action."),
            404: ("RESOURCE_NOT_FOUND", "The requested resource was not found."),
            405: ("METHOD_NOT_ALLOWED", "This method is not allowed for this resource."),
            409: ("CONFLICT", "The request conflicts with an existing resource."),
            422: ("VALIDATION_ERROR", "The request contains invalid data."),
            429: ("RATE_LIMIT_EXCEEDED", "Too many requests. Please try again later."),
        }
        code, message = error_by_status.get(
            exception.status_code,
            ("INTERNAL_SERVER_ERROR", "Something went wrong. Please try again later."),
        )
        status_code = exception.status_code
        if status_code >= 500 or status_code not in error_by_status:
            code = "INTERNAL_SERVER_ERROR"
            status_code = 500
            message = "Something went wrong. Please try again later."
        return _error_response(
            request,
            code=code,
            status_code=status_code,
            message=message,
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        exception: Exception,
    ) -> JSONResponse:
        stack_trace = "\n".join(
            f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}'
            for frame in traceback.extract_tb(exception.__traceback__)
        )
        logger.error(
            "unhandled_exception request_id=%s exception_type=%s\n"
            "Traceback (most recent call last):\n%s",
            _request_id(request),
            type(exception).__name__,
            stack_trace,
        )
        return _error_response(
            request,
            code="INTERNAL_SERVER_ERROR",
            status_code=500,
            message="Something went wrong. Please try again later.",
        )

    application.include_router(v1_router, prefix=settings.api_prefix)

    return application


app = create_app()
