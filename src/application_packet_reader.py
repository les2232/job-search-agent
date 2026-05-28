"""Read saved application packets from local packet folders."""

import json
from pathlib import Path
import re


RAW_TEXT_KEYS = {
    "raw_text",
    "job_text",
    "raw_job_text",
    "raw_job_description",
    "job_description",
}


def list_saved_application_packets(
    output_root: str | Path = "applications",
) -> list[dict[str, object]]:
    """Return summaries for saved application packets."""
    root = Path(output_root)
    if not root.exists():
        return []

    summaries = []
    for folder_path in sorted(path for path in root.iterdir() if path.is_dir()):
        packet = load_saved_application_packet(folder_path)
        if packet:
            summaries.append(packet["summary"])
    return summaries


def load_saved_application_packet(packet_folder: str | Path) -> dict[str, object] | None:
    """Load one saved packet, returning None if it is missing or broken."""
    folder_path = Path(packet_folder)
    packet_path = folder_path / "packet.json"
    if not packet_path.exists():
        return None

    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    payload = _sanitize_packet_value(payload)
    summary = _build_summary(folder_path, payload)
    return {
        "folder_path": folder_path,
        "summary": summary,
        "job_metadata": _dict_value(payload.get("job_metadata")),
        "score_summary": _dict_value(payload.get("score_summary")),
        "application_packet": _dict_value(payload.get("application_packet")),
    }


def _build_summary(
    folder_path: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    metadata = _dict_value(payload.get("job_metadata"))
    score_summary = _dict_value(payload.get("score_summary"))
    application_packet = _dict_value(payload.get("application_packet"))
    matched_keywords = _list_value(score_summary.get("matched_keywords"))
    concerns = _list_value(score_summary.get("concerns"))

    return {
        "folder_path": folder_path,
        "saved_date": _safe_text(
            payload.get("created_date"),
            _date_from_folder_name(folder_path.name),
        ),
        "title": _safe_text(metadata.get("title"), "Unknown"),
        "company": _safe_text(metadata.get("company"), "Unknown"),
        "location": _safe_text(metadata.get("location"), "Unknown"),
        "work_mode": _safe_text(metadata.get("work_mode"), "Unknown"),
        "score": score_summary.get("score", "Unknown"),
        "recommendation": _safe_text(score_summary.get("recommendation"), "Unknown"),
        "apply_recommendation": _safe_text(
            application_packet.get("apply_recommendation"),
            "Unknown",
        ),
        "matched_keywords_count": len(matched_keywords),
        "concern_count": len(concerns),
    }


def _date_from_folder_name(folder_name: str) -> str:
    if re.match(r"^\d{4}-\d{2}-\d{2}_", folder_name):
        return folder_name[:10]
    return "Unknown"


def _dict_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return value


def _list_value(value: object) -> list[object]:
    if not isinstance(value, list):
        return []
    return value


def _safe_text(value: object, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    return value.strip()


def _sanitize_packet_value(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_packet_value(item)
            for key, item in value.items()
            if str(key) not in RAW_TEXT_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_packet_value(item) for item in value]
    return value
