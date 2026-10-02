import logging
from uuid import UUID, uuid4

from httpx import Response
from starlette.testclient import TestClient


def assert_error_contract(response: Response) -> dict[str, object]:
    body = response.json()
    assert set(body) == {"code", "message", "details", "request_id"}
    assert isinstance(body["code"], str)
    assert isinstance(body["message"], str)
    assert isinstance(body["details"], list)
    UUID(body["request_id"])
    assert response.headers["X-Request-ID"] == body["request_id"]
    return body


def test_validation_error_is_sanitized_and_uses_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/__test__/validation",
        json={"age": "private-password-value"},
    )

    assert response.status_code == 422
    body = assert_error_contract(response)
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"] == [
        {"field": "age", "message": "Enter a value of the correct type."}
    ]
    assert "private-password-value" not in response.text


def test_successful_request_has_generated_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    UUID(response.headers["X-Request-ID"])


def test_malformed_json_uses_400(client: TestClient) -> None:
    response = client.post(
        "/api/v1/__test__/validation",
        content="{",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    body = assert_error_contract(response)
    assert body["code"] == "MALFORMED_REQUEST"


def test_authentication_error_uses_safe_message(client: TestClient) -> None:
    response = client.get("/api/v1/__test__/authentication")

    assert response.status_code == 401
    body = assert_error_contract(response)
    assert body["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Invalid email or password."


def test_forbidden_error_uses_403(client: TestClient) -> None:
    response = client.get("/api/v1/__test__/forbidden")

    assert response.status_code == 403
    assert assert_error_contract(response)["code"] == "FORBIDDEN"


def test_unknown_route_uses_not_found_contract(client: TestClient) -> None:
    response = client.get("/api/v1/not-a-real-resource")

    assert response.status_code == 404
    assert assert_error_contract(response)["code"] == "RESOURCE_NOT_FOUND"


def test_conflict_error_uses_409(client: TestClient) -> None:
    response = client.get("/api/v1/__test__/conflict")

    assert response.status_code == 409
    assert assert_error_contract(response)["code"] == "EMAIL_ALREADY_EXISTS"


def test_rate_limit_error_uses_429(client: TestClient) -> None:
    response = client.get("/api/v1/__test__/rate-limit")

    assert response.status_code == 429
    assert assert_error_contract(response)["code"] == "RATE_LIMIT_EXCEEDED"


def test_unexpected_error_is_hidden_and_request_id_is_traceable(
    client: TestClient,
    caplog,
) -> None:
    request_id = str(uuid4())
    with caplog.at_level(logging.INFO, logger="main"):
        response = client.get(
            "/api/v1/__test__/unexpected",
            headers={"X-Request-ID": request_id},
        )

    assert response.status_code == 500
    body = assert_error_contract(response)
    assert body["code"] == "INTERNAL_SERVER_ERROR"
    assert body["message"] == "Something went wrong. Please try again later."
    assert "internal diagnostic marker" not in response.text
    assert "Traceback" not in response.text
    assert body["request_id"] == request_id
    assert request_id in caplog.text
    assert "RuntimeError" in caplog.text
    assert "Traceback" in caplog.text
    assert "internal diagnostic marker" not in caplog.text


def test_invalid_client_request_id_is_replaced(client: TestClient) -> None:
    response = client.get(
        "/api/v1/not-a-real-resource",
        headers={"X-Request-ID": "not-a-valid-request-id"},
    )

    body = assert_error_contract(response)
    assert body["request_id"] != "not-a-valid-request-id"