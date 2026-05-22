"""Score a job posting with simple keyword rules."""

import re


POSITIVE_KEYWORDS = [
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
    "junior",
    "entry-level",
    "remote",
    "hybrid",
]

NEGATIVE_KEYWORDS = [
    "senior",
    "principal",
    "lead engineer",
    "8+ years",
    "10+ years",
    "sales",
    "commission",
    "on-call",
]


def score_job(job: dict[str, str]) -> dict[str, object]:
    """Return score details for a parsed job."""
    text = job["raw_text"]
    matched_keywords = _find_keywords(text, POSITIVE_KEYWORDS)
    concerns = _find_keywords(text, NEGATIVE_KEYWORDS)

    score = 50 + (len(matched_keywords) * 5) - (len(concerns) * 8)
    score = max(0, min(100, score))

    return {
        "score": score,
        "recommendation": get_recommendation(score),
        "matched_keywords": matched_keywords,
        "concerns": concerns,
    }


def get_recommendation(score: int) -> str:
    if score >= 75:
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


def _contains_keyword(text: str, keyword: str) -> bool:
    escaped_keyword = re.escape(keyword)
    pattern = rf"(?<![A-Za-z0-9]){escaped_keyword}(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None
