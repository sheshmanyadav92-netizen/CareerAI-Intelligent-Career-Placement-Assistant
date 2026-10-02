from dataclasses import dataclass

from app.core.errors import ValidationError

_ALIASES = {
    "c plus plus": "c++",
    "cpp": "c++",
    "c sharp": "c#",
    "dotnet": ".net",
    "dot net": ".net",
    "nodejs": "node.js",
    "node js": "node.js",
    "js": "javascript",
    "java script": "javascript",
    "reactjs": "react",
    "postgres": "postgresql",
}


@dataclass(frozen=True)
class NormalizedSkill:
    original: str
    normalized: str


def normalize_skill(skill: str) -> NormalizedSkill:
    """Return the unchanged input and its deterministic canonical skill name."""
    if not skill.strip():
        raise ValidationError(
            code="INVALID_SKILL",
            status_code=422,
            message="A skill name must not be empty.",
            details=[{"field": "skill", "message": "A skill name must not be empty."}],
        )

    normalized = " ".join(skill.casefold().split())
    normalized = _ALIASES.get(normalized, normalized)
    return NormalizedSkill(original=skill, normalized=normalized)
