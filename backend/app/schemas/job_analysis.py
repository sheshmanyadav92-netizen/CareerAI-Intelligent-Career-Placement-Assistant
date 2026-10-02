from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

EvidenceText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


class ExplicitSkill(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    original_text: EvidenceText
    evidence_quote: EvidenceText


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    original_text: EvidenceText
    evidence_quote: EvidenceText
    status: Literal["required", "preferred", "unspecified"]


class Responsibility(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    original_text: EvidenceText
    evidence_quote: EvidenceText


class JobAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    required_skills: list[ExplicitSkill] = Field(max_length=40)
    preferred_skills: list[ExplicitSkill] = Field(max_length=40)
    unspecified_skills: list[ExplicitSkill] = Field(max_length=40)
    programming_languages: list[Requirement] = Field(max_length=30)
    frameworks: list[Requirement] = Field(max_length=30)
    tools: list[Requirement] = Field(max_length=40)
    experience_requirements: list[Requirement] = Field(
        max_length=20,
    )
    education_requirements: list[Requirement] = Field(
        max_length=20,
    )
    role_responsibilities: list[Responsibility] = Field(
        max_length=40,
    )
