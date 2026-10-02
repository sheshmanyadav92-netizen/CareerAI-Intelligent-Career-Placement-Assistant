from collections.abc import Sequence


class ApplicationError(Exception):
    def __init__(
        self,
        *,
        code: str,
        status_code: int,
        message: str,
        details: Sequence[dict[str, str]] = (),
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details = list(details)


class BadRequestError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="BAD_REQUEST",
            status_code=400,
            message="The request could not be understood.",
        )


class ValidationError(ApplicationError):
    def __init__(
        self,
        details: Sequence[dict[str, str]] = (),
        *,
        code: str = "VALIDATION_ERROR",
        status_code: int = 422,
        message: str = "The request contains invalid data.",
    ) -> None:
        super().__init__(
            code=code,
            status_code=status_code,
            message=message,
            details=details,
        )


class AuthenticationError(ApplicationError):
    def __init__(
        self,
        *,
        code: str = "AUTHENTICATION_REQUIRED",
        message: str = "Authentication is required.",
    ) -> None:
        super().__init__(code=code, status_code=401, message=message)


class InvalidCredentialsError(AuthenticationError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password.",
        )


class AuthorizationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="FORBIDDEN",
            status_code=403,
            message="You do not have permission to perform this action.",
        )


class NotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            status_code=404,
            message="The requested resource was not found.",
        )


class ConflictError(ApplicationError):
    def __init__(
        self,
        *,
        code: str = "CONFLICT",
        message: str = "The request conflicts with an existing resource.",
    ) -> None:
        super().__init__(code=code, status_code=409, message=message)


class EmailAlreadyExistsError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            code="EMAIL_ALREADY_EXISTS",
            message="An account with these details already exists.",
        )


class RateLimitError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            message="Too many requests. Please try again later.",
        )


class AIConfigurationError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="AI_CONFIGURATION_ERROR",
            status_code=503,
            message="AI analysis is not configured.",
        )


class AIProviderError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="AI_PROVIDER_ERROR",
            status_code=503,
            message="AI analysis is temporarily unavailable. Please try again later.",
        )


class AIProviderTimeoutError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="AI_PROVIDER_TIMEOUT",
            status_code=504,
            message="AI analysis took too long. Please try again.",
        )


class AIInvalidOutputError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            code="AI_INVALID_OUTPUT",
            status_code=502,
            message="We couldn't complete the AI analysis. Please try again.",
        )