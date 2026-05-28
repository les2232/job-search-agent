"""Read saved application packets from local packet folders."""

from datetime import date, datetime
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

APPLICATION_STATUSES = [
    "Interested",
    "Tailoring",
    "Ready to Apply",
    "Applied",
    "Interview",
    "Offer",
    "Rejected",
    "Archived",
]
DEFAULT_APPLICATION_STATUS = "Interested"
NEXT_ACTIONS = {
    "Interested": "Review score and decide whether to tailor.",
    "Tailoring": "Finish resume/cover letter edits.",
    "Ready to Apply": "Submit application.",
    "Applied": "Track response or follow up later.",
    "Interview": "Prepare interview notes.",
    "Offer": "Review offer details.",
    "Rejected": "Archive or review lessons learned.",
    "Archived": "No action needed.",
}
SORT_OPTIONS = [
    "Newest saved first",
    "Oldest saved first",
    "Highest score first",
    "Lowest score first",
    "Status",
    "Company",
    "Title",
]


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


def count_saved_applications_by_status(
    packets: list[dict[str, object]],
) -> dict[str, int]:
    """Return status counts for saved applications."""
    counts = {status: 0 for status in APPLICATION_STATUSES}
    for packet in packets:
        status = _safe_text(packet.get("status"), DEFAULT_APPLICATION_STATUS)
        if status not in counts:
            status = DEFAULT_APPLICATION_STATUS
        counts[status] += 1
    return counts


def filter_saved_application_packets(
    packets: list[dict[str, object]],
    status: str | None = None,
    recommendation: str | None = None,
    apply_recommendation: str | None = None,
    work_mode: str | None = None,
    min_score: int | None = None,
    company_search: str | None = None,
    text_search: str | None = None,
    needs_attention: bool = False,
    overdue: bool = False,
    due_within_days: int | None = None,
) -> list[dict[str, object]]:
    """Filter saved application summaries without exposing raw packet data."""
    filtered_packets = []
    for packet in packets:
        if status and not _matches_text(packet.get("status"), status):
            continue
        if recommendation and not _matches_text(
            packet.get("recommendation"),
            recommendation,
        ):
            continue
        if apply_recommendation and not _contains_text(
            packet.get("apply_recommendation"),
            apply_recommendation,
        ):
            continue
        if work_mode and not _matches_text(packet.get("work_mode"), work_mode):
            continue
        if min_score is not None and _score_value(packet.get("score")) < min_score:
            continue
        if company_search and not _contains_text(
            packet.get("company"),
            company_search,
        ):
            continue
        if text_search and not (
            _contains_text(packet.get("title"), text_search)
            or _contains_text(packet.get("company"), text_search)
        ):
            continue
        if needs_attention and not bool(packet.get("needs_attention")):
            continue
        if overdue and not bool(packet.get("is_overdue")):
            continue
        if due_within_days is not None and not _is_due_within(
            packet.get("days_until_next_action"),
            due_within_days,
        ):
            continue
        filtered_packets.append(_sanitize_summary(packet))
    return filtered_packets


def sort_saved_application_packets(
    packets: list[dict[str, object]],
    sort_by: str,
) -> list[dict[str, object]]:
    """Sort saved application summaries for dashboard display."""
    if sort_by == "Oldest saved first":
        return sorted(packets, key=lambda packet: _date_sort_key(packet.get("saved_date")))
    if sort_by == "Highest score first":
        return sorted(packets, key=lambda packet: _score_value(packet.get("score")), reverse=True)
    if sort_by == "Lowest score first":
        return sorted(packets, key=lambda packet: _score_value(packet.get("score")))
    if sort_by == "Status":
        return sorted(
            packets,
            key=lambda packet: (
                APPLICATION_STATUSES.index(str(packet.get("status")))
                if packet.get("status") in APPLICATION_STATUSES
                else 0,
                str(packet.get("company", "")).lower(),
            ),
        )
    if sort_by == "Company":
        return sorted(packets, key=lambda packet: str(packet.get("company", "")).lower())
    if sort_by == "Title":
        return sorted(packets, key=lambda packet: str(packet.get("title", "")).lower())
    return sorted(
        packets,
        key=lambda packet: _date_sort_key(packet.get("saved_date")),
        reverse=True,
    )


def get_next_action(status: object) -> str:
    """Return a simple next action for an application status."""
    status_text = _safe_text(status, DEFAULT_APPLICATION_STATUS)
    return NEXT_ACTIONS.get(status_text, NEXT_ACTIONS[DEFAULT_APPLICATION_STATUS])


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
        "application_tracking": _tracking_value(payload.get("application_tracking")),
        "job_metadata": _dict_value(payload.get("job_metadata")),
        "score_summary": _dict_value(payload.get("score_summary")),
        "application_packet": _dict_value(payload.get("application_packet")),
    }


def update_application_status(
    packet_folder: str | Path,
    status: str,
    notes: str | None = None,
    applied_date: str | None = None,
) -> dict[str, object]:
    """Update application tracking fields in packet.json."""
    return update_application_tracking(
        packet_folder,
        status=status,
        notes=notes,
        applied_date=applied_date,
    )


def update_application_tracking(
    packet_folder: str | Path,
    status: str | None = None,
    notes: str | None = None,
    applied_date: str | None = None,
    next_action_date: str | None = None,
    next_action_note: str | None = None,
) -> dict[str, object]:
    """Update application tracking fields in packet.json."""
    if status is not None and status not in APPLICATION_STATUSES:
        return {
            "updated": False,
            "message": f"Invalid status: {status}",
        }

    folder_path = Path(packet_folder)
    packet_path = folder_path / "packet.json"
    if not packet_path.exists():
        return {
            "updated": False,
            "message": f"Could not find packet.json in: {folder_path}",
        }

    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "updated": False,
            "message": f"Could not read packet.json in: {folder_path}",
        }

    if not isinstance(payload, dict):
        return {
            "updated": False,
            "message": f"Invalid packet format in: {folder_path}",
        }

    payload = _sanitize_packet_value(payload)
    tracking = _tracking_value(payload.get("application_tracking"))
    if status is not None:
        tracking["status"] = status
    tracking["status_updated_at"] = _current_timestamp()
    if notes is not None:
        tracking["notes"] = notes
    if applied_date is not None:
        tracking["applied_date"] = applied_date or None
    if next_action_date is not None:
        tracking["next_action_date"] = next_action_date or None
    if next_action_note is not None:
        tracking["next_action_note"] = next_action_note
    payload["application_tracking"] = tracking

    packet_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "updated": True,
        "message": f"Updated application tracking for {tracking['status']}.",
        "folder_path": folder_path,
        "application_tracking": tracking,
    }


def _build_summary(
    folder_path: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    metadata = _dict_value(payload.get("job_metadata"))
    score_summary = _dict_value(payload.get("score_summary"))
    application_packet = _dict_value(payload.get("application_packet"))
    application_tracking = _tracking_value(payload.get("application_tracking"))
    next_action_state = get_next_action_state(application_tracking)
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
        "status": application_tracking["status"],
        "status_updated_at": application_tracking["status_updated_at"],
        "applied_date": application_tracking["applied_date"],
        "notes": application_tracking["notes"],
        "next_action": get_next_action(application_tracking["status"]),
        "next_action_date": application_tracking["next_action_date"],
        "next_action_note": application_tracking["next_action_note"],
        "days_until_next_action": next_action_state["days_until_next_action"],
        "is_overdue": next_action_state["is_overdue"],
        "needs_attention": next_action_state["needs_attention"],
        "attention_reason": next_action_state["attention_reason"],
        "matched_keywords_count": len(matched_keywords),
        "concern_count": len(concerns),
    }


def _tracking_value(value: object) -> dict[str, object]:
    tracking = _dict_value(value)
    status = _safe_text(tracking.get("status"), DEFAULT_APPLICATION_STATUS)
    if status not in APPLICATION_STATUSES:
        status = DEFAULT_APPLICATION_STATUS

    return {
        "status": status,
        "status_updated_at": _safe_text(tracking.get("status_updated_at"), ""),
        "applied_date": _optional_text(tracking.get("applied_date")),
        "notes": _safe_text(tracking.get("notes"), ""),
        "next_action_date": _optional_text(tracking.get("next_action_date")),
        "next_action_note": _safe_text(tracking.get("next_action_note"), ""),
    }


def get_next_action_state(
    tracking: dict[str, object],
    today: date | None = None,
) -> dict[str, object]:
    """Return due/attention state for saved application tracking."""
    today = date.today() if today is None else today
    status = _safe_text(tracking.get("status"), DEFAULT_APPLICATION_STATUS)
    next_action_date_text = _optional_text(tracking.get("next_action_date"))

    if status == "Archived":
        return _attention_state(None, False, False, "")

    if next_action_date_text:
        action_date = _parse_date(next_action_date_text)
        if action_date is not None:
            days_until = (action_date - today).days
            if days_until < 0:
                return _attention_state(days_until, True, True, "Overdue")
            if days_until <= 3:
                return _attention_state(days_until, False, True, "Due soon")
            return _attention_state(days_until, False, False, "")

    if status == "Ready to Apply":
        return _attention_state(None, False, True, "Ready to apply")
    if status == "Applied":
        return _attention_state(None, False, True, "Add a follow-up date")
    return _attention_state(None, False, False, "")


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


def _matches_text(value: object, expected: str) -> bool:
    return str(value).strip().lower() == expected.strip().lower()


def _contains_text(value: object, expected: str) -> bool:
    return expected.strip().lower() in str(value).lower()


def _score_value(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _date_sort_key(value: object) -> str:
    text = _safe_text(value, "0000-00-00")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text
    return "0000-00-00"


def _is_due_within(value: object, days: int) -> bool:
    if not isinstance(value, int):
        return False
    return 0 <= value <= days


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _attention_state(
    days_until_next_action: int | None,
    is_overdue: bool,
    needs_attention: bool,
    attention_reason: str,
) -> dict[str, object]:
    return {
        "days_until_next_action": days_until_next_action,
        "is_overdue": is_overdue,
        "needs_attention": needs_attention,
        "attention_reason": attention_reason,
    }


def _optional_text(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _current_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


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


def _sanitize_summary(packet: dict[str, object]) -> dict[str, object]:
    return {
        str(key): value
        for key, value in packet.items()
        if str(key) not in RAW_TEXT_KEYS
    }
