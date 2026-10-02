import pytest

from app.core.errors import ValidationError
from app.utils.skill_normalizer import normalize_skill


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("C++", "c++"),
        (" cpp ", "c++"),
        ("CPP", "c++"),
        ("c plus plus", "c++"),
        ("C#", "c#"),
        (" c# ", "c#"),
        ("C Sharp", "c#"),
        ("c sharp", "c#"),
        (".NET", ".net"),
        ("dotnet", ".net"),
        ("dot net", ".net"),
        (" .net ", ".net"),
        ("Node.js", "node.js"),
        ("nodejs", "node.js"),
        ("Node JS", "node.js"),
        (" node.js ", "node.js"),
        ("Java", "java"),
        (" java ", "java"),
        ("JAVA", "java"),
        ("JavaScript", "javascript"),
        ("javascript", "javascript"),
        ("JS", "javascript"),
        ("java script", "javascript"),
        ("ReactJS", "react"),
        (" Postgres ", "postgresql"),
    ],
)
def test_explicit_aliases_normalize_deterministically(
    value: str,
    expected: str,
) -> None:
    assert normalize_skill(value).normalized == expected


def test_java_and_javascript_remain_distinct() -> None:
    assert normalize_skill("Java").normalized == "java"
    assert normalize_skill("JavaScript").normalized == "javascript"
    assert normalize_skill("JavaScript").normalized != normalize_skill("Java").normalized


def test_original_input_is_preserved_exactly() -> None:
    result = normalize_skill("  NodeJS  ")

    assert result.original == "  NodeJS  "
    assert result.normalized == "node.js"


def test_unknown_skill_only_gets_case_and_whitespace_normalization() -> None:
    result = normalize_skill("  Rust   Systems  ")

    assert result.original == "  Rust   Systems  "
    assert result.normalized == "rust systems"


def test_typo_is_not_fuzzy_matched() -> None:
    assert normalize_skill("Javva").normalized == "javva"


@pytest.mark.parametrize("value", ["", " ", "\t\n"])
def test_empty_skill_raises_structured_validation_error(value: str) -> None:
    with pytest.raises(ValidationError) as error:
        normalize_skill(value)

    assert error.value.code == "INVALID_SKILL"
    assert error.value.status_code == 422
