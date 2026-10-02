from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MAX_RESUME_ANALYSIS_ITEMS = 50

ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
SummaryText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]


class ResumeObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    observation: ShortText
    evidence: list[ShortText] = Field(min_length=1, max_length=3)


class ResumeAIAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    summary: SummaryText | None
    summary_evidence: list[ShortText] = Field(default_factory=list, max_length=3)
    strengths: list[ResumeObservation] = Field(default_factory=list, max_length=50)
    improvement_areas: list[ResumeObservation] = Field(default_factory=list, max_length=50)
    skills_observations: list[ResumeObservation] = Field(default_factory=list, max_length=50)
    experience_observations: list[ResumeObservation] = Field(default_factory=list, max_length=50)
    education_observations: list[ResumeObservation] = Field(default_factory=list, max_length=50)
    recommended_next_steps: list[ResumeObservation] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_summary_evidence(self) -> "ResumeAIAnalysis":
        if self.summary and not self.summary_evidence:
            raise ValueError("A summary requires supporting evidence.")
        if self.summary is None and self.summary_evidence:
            raise ValueError("Evidence cannot be supplied without a summary.")

        for field_name in (
            "summary_evidence",
            "strengths",
            "improvement_areas",
            "skills_observations",
            "experience_observations",
            "education_observations",
            "recommended_next_steps",
        ):
            items = getattr(self, field_name)
            if len(items) > MAX_RESUME_ANALYSIS_ITEMS:
                raise ValueError(
                    f"{field_name} exceeds the {MAX_RESUME_ANALYSIS_ITEMS}-item limit."
                )
        return self


class ExtractedResumeFacts(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    skills: list[ShortText] = Field(default_factory=list, max_length=50)
    education: list[ShortText] = Field(default_factory=list, max_length=50)
    experience: list[ShortText] = Field(default_factory=list, max_length=50)
    projects: list[ShortText] = Field(default_factory=list, max_length=50)
    certifications: list[ShortText] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_total_item_count(self) -> "ExtractedResumeFacts":
        for field_name in (
            "skills",
            "education",
            "experience",
            "projects",
            "certifications",
        ):
            items = getattr(self, field_name)
            if len(items) > MAX_RESUME_ANALYSIS_ITEMS:
                raise ValueError(
                    f"{field_name} exceeds the {MAX_RESUME_ANALYSIS_ITEMS}-item limit."
                )
        return self


class ResumeAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    extracted_facts: ExtractedResumeFacts = Field(default_factory=ExtractedResumeFacts)
    ai_observations: ResumeAIAnalysis