from pydantic import BaseModel, ConfigDict

from app.schemas.resume_analysis import ResumeAnalysisResult


class ResumeUploadAnalysisResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    filename: str
    page_count: int
    size_bytes: int
    result: ResumeAnalysisResult
