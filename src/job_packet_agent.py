"""Deterministic orchestration layer for reviewing a job packet workflow."""

from application_packet import generate_application_packet
from job_parser import parse_job_text
from job_scorer import score_job


AGENT_NAME = "Job Packet Agent"
MIN_RELIABLE_JOB_TEXT_CHARS = 120


def run_job_packet_agent(
    job_text: str,
    user_profile: dict | None = None,
) -> dict[str, object]:
    """Parse, score, and generate an in-memory packet review."""
    clean_text = job_text.strip()
    if not clean_text:
        raise ValueError("job_text is required")

    job = parse_job_text(clean_text)
    score_result = score_job(job)
    profile_text = _profile_text(user_profile)
    packet = generate_application_packet(score_result, profile_text)
    score_explanation = score_result.get("explanation")
    fit_summary = ""
    if isinstance(score_explanation, dict):
        fit_summary = str(score_explanation.get("fit_summary", ""))

    return {
        "agent_name": AGENT_NAME,
        "role_summary": _role_summary(score_result),
        "extracted_requirements": score_result.get("job_requirements", {}),
        "score_summary": {
            "score": score_result.get("score"),
            "recommendation": score_result.get("recommendation"),
            "matched_keywords": _as_string_list(score_result.get("matched_keywords")),
            "concerns": _as_string_list(score_result.get("concerns")),
            "fit_summary": fit_summary,
        },
        "resume_focus_recommendations": {
            "top_resume_focus_areas": _as_string_list(packet.get("resume_focus_areas"))[:5],
            "requirements_to_verify": _requirements_to_verify(packet),
            "keywords_to_include_honestly": _as_string_list(
                packet.get("keywords_to_include_honestly")
            )[:6],
        },
        "packet_outputs": packet,
        "next_actions": _next_actions(score_result, packet),
        "warnings": _warnings(clean_text, score_result),
    }


def _profile_text(user_profile: dict | None) -> str | None:
    if not isinstance(user_profile, dict):
        return None
    value = user_profile.get("resume_text")
    if isinstance(value, str) and value.strip():
        return value
    return None


def _role_summary(score_result: dict[str, object]) -> dict[str, str]:
    metadata = score_result.get("job_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "title": _safe_text(metadata.get("title"), "Unknown"),
        "company": _safe_text(metadata.get("company"), "Unknown"),
        "location": _safe_text(metadata.get("location"), "Unknown"),
        "work_mode": _safe_text(metadata.get("work_mode"), "Unknown"),
    }


def _requirements_to_verify(packet: dict[str, object]) -> list[str]:
    strategy = packet.get("resume_strategy_sections")
    if isinstance(strategy, dict):
        return _as_string_list(strategy.get("major_requirements_to_verify"))[:8]
    return _as_string_list(packet.get("keywords_to_avoid_or_verify"))[:8]


def _next_actions(
    score_result: dict[str, object],
    packet: dict[str, object],
) -> list[str]:
    recommendation = str(score_result.get("recommendation", "")).strip().lower()
    requirements_to_verify = _requirements_to_verify(packet)
    actions = []

    if recommendation == "apply":
        actions.append("Review the packet drafts and evidence before applying manually.")
    elif recommendation == "maybe":
        actions.append("Review gaps and decide whether this is worth tailoring.")
    else:
        actions.append("Consider skipping or saving only if there is a deliberate reason.")

    if requirements_to_verify:
        actions.append("Verify evidence for the major hard requirements before using resume claims.")
    actions.append("Do not auto-apply; submit only after human review.")
    return actions


def _warnings(clean_text: str, score_result: dict[str, object]) -> list[str]:
    warnings = []
    if len(clean_text) < MIN_RELIABLE_JOB_TEXT_CHARS:
        warnings.append(
            "Job text looks short; analysis may be unreliable unless this is the full posting."
        )

    metadata = score_result.get("job_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    for label, key in [
        ("title", "title"),
        ("company", "company"),
        ("location", "location"),
        ("work mode", "work_mode"),
    ]:
        if _safe_text(metadata.get(key), "Unknown") == "Unknown":
            warnings.append(f"Parsed {label} is unknown; review the job text or clean header fields.")

    warnings.append("Draft only. Review all generated materials before using.")
    warnings.append("This agent does not submit applications, send emails, or contact employers.")
    return warnings


def _safe_text(value: object, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    return value.strip()


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
