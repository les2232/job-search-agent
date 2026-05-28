"""Score a job posting with simple keyword rules."""

import re
from typing import Any

from config_loader import BUILT_IN_SCORING_CONFIG, load_scoring_config


POSITIVE_KEYWORDS = BUILT_IN_SCORING_CONFIG["positive_keywords"]
NEGATIVE_KEYWORDS = BUILT_IN_SCORING_CONFIG["concern_keywords"]


def score_job(
    job: dict[str, str],
    scoring_config: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Return score details for a parsed job."""
    config = load_scoring_config() if scoring_config is None else scoring_config
    text = job["raw_text"]
    matched_keywords = _find_keywords(text, config["positive_keywords"])
    concerns = _find_keywords(text, config["concern_keywords"])

    score = (
        config["starting_score"]
        + (len(matched_keywords) * config["positive_keyword_points"])
        - (len(concerns) * config["concern_keyword_penalty"])
    )
    score = max(0, min(100, score))

    return {
        "score": score,
        "recommendation": get_recommendation(score, config),
        "matched_keywords": matched_keywords,
        "concerns": concerns,
    }


def get_recommendation(
    score: int,
    scoring_config: dict[str, Any] | None = None,
) -> str:
    config = load_scoring_config() if scoring_config is None else scoring_config

    if score >= config["apply_threshold"]:
        return "Apply"
    if score >= config["maybe_threshold"]:
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
