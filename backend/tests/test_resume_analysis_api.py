from collections.abc import Iterator
from typing import Any

import pytest
from app.api.v1 import resume_analysis as resume_analysis_api
from app.core.config import Settings
from app.schemas.resume_analysis import (
    ExtractedResumeFacts,
    ResumeAIAnalysis,
    ResumeAnalysisResult,
)
from fastapi import FastAPI
from main import create_app
from starlette.testclient import TestClient


class FakePdfPage:
    def __init__(self, text: str) -> None:
        self.text = text

    def extract_text(self) -> str:
        return self.text


class FakePdfReader:
    def __init__(self, *_: Any, **__: Any) -> None:
        self.is_encrypted = False
        self.pages = [FakePdfPage("Built a React application with TypeScript.")]


class FakeAnalysisService:
    def __init__(self) -> None:
        self.analyzed_text: str | None = None

    async def analyze(self, resume_text: str) -> ResumeAnalysisResult:
        self.analyzed_text = resume_text
        return ResumeAnalysisResult(
            extracted_facts=ExtractedResumeFacts(
                skills=["React", "TypeScript"],
                experience=["Built a React application with TypeScript."],
            ),
            ai_observations=ResumeAIAnalysis(
                summary="Frontend application development experience.",
                summary_evidence=["Built a React application with TypeScript."],
                strengths=[],
                improvement_areas=[],
                skills_observations=[],
                experience_observations=[],
                education_observations=[],
                recommended_next_steps=[],
            ),
        )


@pytest.fixture
def analysis_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, FakeAnalysisService]]:
    fake_service = FakeAnalysisService()
    app: FastAPI = create_app(prewarm_local_model=False)
    app.dependency_overrides[resume_analysis_api.get_settings] = lambda: Settings(_env_file=None)
    app.dependency_overrides[resume_analysis_api.get_resume_analysis_service] = (
        lambda: fake_service
    )
    monkeypatch.setattr(
        resume_analysis_api,
        "PdfReader",
        FakePdfReader,
    )
    from app.services import resume_validation

    monkeypatch.setattr(resume_validation, "PdfReader", FakePdfReader)
    with TestClient(app) as client:
        yield client, fake_service
    app.dependency_overrides.clear()


def test_upload_endpoint_returns_validated_ai_result(
    analysis_client: tuple[TestClient, FakeAnalysisService],
) -> None:
    client, fake_service = analysis_client

    response = client.post(
        "/api/v1/resume-analysis/analyze",
        files={"file": ("resume.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "resume.pdf"
    assert response.json()["page_count"] == 1
    assert response.json()["result"]["extracted_facts"]["skills"] == [
        "React",
        "TypeScript",
    ]
    assert response.json()["result"]["ai_observations"]["summary"] == (
        "Frontend application development experience."
    )
    assert fake_service.analyzed_text == "Built a React application with TypeScript."


def test_upload_endpoint_rejects_scanned_pdfs_without_sending_them_to_ai(
    analysis_client: tuple[TestClient, FakeAnalysisService],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, fake_service = analysis_client

    class ScannedPdfReader(FakePdfReader):
        def __init__(self, *_: Any, **__: Any) -> None:
            self.is_encrypted = False
            self.pages = [FakePdfPage("")]

    monkeypatch.setattr(resume_analysis_api, "PdfReader", ScannedPdfReader)
    from app.services import resume_validation

    monkeypatch.setattr(resume_validation, "PdfReader", ScannedPdfReader)

    response = client.post(
        "/api/v1/resume-analysis/analyze",
        files={"file": ("scanned.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_RESUME_TEXT"
    assert fake_service.analyzed_text is None


def test_upload_endpoint_is_disabled_in_production(
    analysis_client: tuple[TestClient, FakeAnalysisService],
) -> None:
    client, fake_service = analysis_client
    client.app.dependency_overrides[resume_analysis_api.get_settings] = (
        lambda: Settings(_env_file=None, environment="production", secret_key="configured")
    )

    response = client.post(
        "/api/v1/resume-analysis/analyze",
        files={"file": ("resume.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert fake_service.analyzed_text is None


def test_upload_endpoint_returns_configuration_error_when_ai_is_disabled(
    analysis_client: tuple[TestClient, FakeAnalysisService],
) -> None:
    client, fake_service = analysis_client
    client.app.dependency_overrides.pop(
        resume_analysis_api.get_resume_analysis_service
    )

    response = client.post(
        "/api/v1/resume-analysis/analyze",
        files={"file": ("resume.pdf", b"%PDF-1.4 test", "application/pdf")},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "AI_CONFIGURATION_ERROR"
    assert fake_service.analyzed_text is None
