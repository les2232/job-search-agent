"""Score a job posting with rules tailored to the user's job-search goals."""

import re


TECH_KEYWORDS = [
    "python",
    "sql",
    "api",
    "apis",
    "automation",
    "dashboard",
    "dashboards",
    "data",
    "git",
    "linux",
    "documentation",
    "troubleshooting",
    "testing",
    "quality assurance",
    "qa",
]

WORK_STYLE_KEYWORDS = [
    "remote",
    "hybrid",
    "flexible",
    "asynchronous",
    "async",
    "independent",
    "documentation",
]

GROWTH_KEYWORDS = [
    "junior",
    "entry-level",
    "entry level",
    "associate",
    "mentor",
    "mentoring",
    "training",
    "growth",
]

CONCERN_KEYWORDS = [
    "senior",
    "principal",
    "lead engineer",
    "8+ years",
    "10+ years",
    "sales",
    "commission",
    "on-call",
    "on call",
    "heavy phones",
    "travel required",
    "customer-facing",
    "customer facing",
]

PRIORITY_KEYWORDS = [
    "python",
    "sql",
    "remote",
    "automation",
    "data",
    "documentation",
]


def score_job(job: dict[str, str]) -> dict[str, object]:
    """Return score details for a parsed job."""
    text = job["raw_text"]

    tech_matches = _find_keywords(text, TECH_KEYWORDS)
    work_style_matches = _find_keywords(text, WORK_STYLE_KEYWORDS)
    growth_matches = _find_keywords(text, GROWTH_KEYWORDS)
    concerns = _find_keywords(text, CONCERN_KEYWORDS)
    missing_keywords = _missing_keywords(text, PRIORITY_KEYWORDS)

    breakdown = {
        "base": 35,
        "skills_match": min(35, len(tech_matches) * 4),
        "work_style_fit": min(15, len(work_style_matches) * 5),
        "growth_fit": min(15, len(growth_matches) * 5),
        "concern_penalty": min(35, len(concerns) * 8),
    }

    score = (
        breakdown["base"]
        + breakdown["skills_match"]
        + breakdown["work_style_fit"]
        + breakdown["growth_fit"]
        - breakdown["concern_penalty"]
    )
    score = max(0, min(100, score))

    matched_keywords = _unique_preserve_order(
        tech_matches + work_style_matches + growth_matches
    )

    return {
        "score": score,
        "recommendation": get_recommendation(score, concerns),
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "concerns": concerns,
        "breakdown": breakdown,
    }


def get_recommendation(score: int, concerns: list[str] | None = None) -> str:
    concerns = concerns or []

    if score >= 75 and len(concerns) <= 2:
        return "Apply"
    if score >= 60:
        return "Maybe"
    return "Skip"


def _find_keywords(text: str, keywords: list[str]) -> list[str]:
    found = []

    for keyword in keywords:
        if _contains_keyword(text, keyword):
            found.append(keyword)

    return found


def _missing_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if not _contains_keyword(text, keyword)]


def _contains_keyword(text: str, keyword: str) -> bool:
    escaped_keyword = re.escape(keyword)
    pattern = rf"(?<![A-Za-z0-9]){escaped_keyword}(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    unique_values = []

    for value in values:
        if value not in seen:
            unique_values.append(value)
            seen.add(value)

    return unique_values
