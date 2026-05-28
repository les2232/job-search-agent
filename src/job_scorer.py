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
    missing_keywords = _find_missing_keywords(
        config["positive_keywords"],
        matched_keywords,
    )

    score = (
        config["starting_score"]
        + (len(matched_keywords) * config["positive_keyword_points"])
        - (len(concerns) * config["concern_keyword_penalty"])
    )
    score = max(0, min(100, score))
    recommendation = get_recommendation(score, config)

    return {
        "job_metadata": {
            "title": job.get("title", "Unknown"),
            "company": job.get("company", "Unknown"),
            "location": job.get("location", "Unknown"),
            "work_mode": job.get("work_mode", "Unknown"),
        },
        "score": score,
        "recommendation": recommendation,
        "matched_keywords": matched_keywords,
        "concerns": concerns,
        "missing_keywords": missing_keywords,
        "explanation": build_score_explanation(
            job,
            score,
            recommendation,
            matched_keywords,
            missing_keywords,
            concerns,
            config,
        ),
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


def build_score_explanation(
    job: dict[str, str],
    score: int,
    recommendation: str,
    matched_keywords: list[str],
    missing_keywords: list[str],
    concerns: list[str],
    scoring_config: dict[str, Any],
) -> dict[str, object]:
    """Explain the score using deterministic, user-facing rules."""
    strengths = _build_strengths(matched_keywords, job)
    gaps = _build_gaps(missing_keywords, scoring_config)
    explanation_concerns = _build_concerns(concerns, job)
    tailoring_suggestions = _build_tailoring_suggestions(
        matched_keywords,
        missing_keywords,
        concerns,
        recommendation,
    )

    return {
        "fit_summary": _build_fit_summary(
            score,
            recommendation,
            matched_keywords,
            concerns,
        ),
        "strengths": strengths,
        "gaps": gaps,
        "concerns": explanation_concerns,
        "tailoring_suggestions": tailoring_suggestions,
    }


def _build_fit_summary(
    score: int,
    recommendation: str,
    matched_keywords: list[str],
    concerns: list[str],
) -> str:
    if recommendation == "Apply":
        return (
            f"This job scored {score}/100 because it matches "
            f"{len(matched_keywords)} configured fit keyword(s)"
            f"{_concern_phrase(concerns)}."
        )
    if recommendation == "Maybe":
        return (
            f"This job scored {score}/100. It has relevant overlap, "
            "but the gaps should be reviewed before applying"
            f"{_concern_phrase(concerns)}."
        )
    return (
        f"This job scored {score}/100. The role may require skills or "
        "experience not strongly reflected by the current scoring rules"
        f"{_concern_phrase(concerns)}."
    )


def _build_strengths(matched_keywords: list[str], job: dict[str, str]) -> list[str]:
    strengths = []
    if matched_keywords:
        strengths.append(
            "Matched fit keywords: " + ", ".join(matched_keywords[:8])
        )
    else:
        strengths.append("No configured fit keywords were found in the posting.")

    work_mode = job.get("work_mode", "Unknown")
    if work_mode != "Unknown":
        strengths.append(f"Work mode detected: {work_mode}.")

    return strengths


def _build_gaps(
    missing_keywords: list[str],
    scoring_config: dict[str, Any],
) -> list[str]:
    if not missing_keywords:
        return ["No configured fit keywords were missing from this posting."]

    missing_preview = ", ".join(missing_keywords[:8])
    return [
        f"Potential gaps to review: {missing_preview}.",
        "If the role still looks interesting, apply only if you can honestly tailor your resume around these areas.",
    ]


def _build_concerns(concerns: list[str], job: dict[str, str]) -> list[str]:
    explanation_concerns = []
    if concerns:
        explanation_concerns.append(
            "Concern keywords found: " + ", ".join(concerns)
        )

    unknown_fields = [
        label
        for label in ["title", "company", "location"]
        if job.get(label, "Unknown") == "Unknown"
    ]
    if unknown_fields:
        explanation_concerns.append(
            "Job metadata did not parse cleanly for: " + ", ".join(unknown_fields)
        )

    if job.get("work_mode", "Unknown") == "Unknown":
        explanation_concerns.append("Work mode was not clearly detected.")

    if not explanation_concerns:
        explanation_concerns.append("No concern keywords or metadata issues were found.")

    return explanation_concerns


def _build_tailoring_suggestions(
    matched_keywords: list[str],
    missing_keywords: list[str],
    concerns: list[str],
    recommendation: str,
) -> list[str]:
    suggestions = []
    if matched_keywords:
        suggestions.append(
            "Emphasize verified experience related to: "
            + ", ".join(matched_keywords[:5])
            + "."
        )
    if missing_keywords:
        suggestions.append(
            "Review whether your resume can honestly address: "
            + ", ".join(missing_keywords[:5])
            + "."
        )
    if concerns:
        suggestions.append(
            "Check whether concern terms indicate a seniority, sales, commission, or availability mismatch."
        )
    if recommendation == "Apply":
        suggestions.append("Generate an application packet and tailor the resume before applying.")
    elif recommendation == "Maybe":
        suggestions.append("Compare the posting against your resume before deciding to apply.")
    else:
        suggestions.append("Consider skipping unless the role has other strong non-keyword reasons.")

    return suggestions


def _concern_phrase(concerns: list[str]) -> str:
    if not concerns:
        return " and no concern keywords"
    return f" and {len(concerns)} concern keyword(s)"


def _find_keywords(text: str, keywords: list[str]) -> list[str]:
    found = []

    for keyword in keywords:
        if _contains_keyword(text, keyword):
            found.append(keyword)

    return found


def _find_missing_keywords(
    keywords: list[str],
    matched_keywords: list[str],
) -> list[str]:
    missing_keywords = []
    matched_normalized = {keyword.lower() for keyword in matched_keywords}

    for keyword in keywords:
        normalized = keyword.lower()
        if normalized in matched_normalized:
            continue
        if normalized.endswith("s") and normalized[:-1] in matched_normalized:
            continue
        if f"{normalized}s" in matched_normalized:
            continue
        missing_keywords.append(keyword)

    return missing_keywords


def _contains_keyword(text: str, keyword: str) -> bool:
    escaped_keyword = re.escape(keyword)
    pattern = rf"(?<![A-Za-z0-9]){escaped_keyword}(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None
