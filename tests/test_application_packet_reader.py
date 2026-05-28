import json
from pathlib import Path

from application_packet_reader import (
    list_saved_application_packets,
    load_saved_application_packet,
    update_application_status,
)


def _packet_payload() -> dict[str, object]:
    return {
        "created_date": "2026-05-28",
        "job_metadata": {
            "title": "Junior Python Analyst",
            "company": "Example Analytics Studio",
            "location": "Remote",
            "work_mode": "Remote",
        },
        "score_summary": {
            "score": 85,
            "recommendation": "Apply",
            "matched_keywords": ["python", "documentation"],
            "concerns": ["on-call"],
            "raw_text": "Private raw job text should not appear.",
        },
        "application_packet": {
            "positioning_summary": "Strong target.",
            "apply_recommendation": "Apply after tailoring.",
            "resume_focus_areas": ["Support experience."],
            "resume_bullet_suggestions": ["Suggested bullet: Use verified scope."],
            "keywords_to_include_honestly": ["python"],
            "keywords_to_avoid_or_verify": ["linux"],
            "cover_letter_draft": "Draft only.",
            "recruiter_message": "Hi.",
            "application_checklist": ["Review."],
            "risk_notes": ["Verify claims."],
            "raw_job_description": "Private raw job text should not appear.",
        },
        "application_tracking": {
            "status": "Tailoring",
            "status_updated_at": "2026-05-28T10:00:00",
            "applied_date": None,
            "notes": "Need to tailor resume summary.",
        },
    }


def _write_packet(root: Path, folder_name: str, payload: dict[str, object]) -> Path:
    folder_path = root / folder_name
    folder_path.mkdir(parents=True)
    (folder_path / "packet.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    return folder_path


def test_list_saved_application_packets_missing_folder_returns_empty(
    tmp_path: Path,
) -> None:
    assert list_saved_application_packets(tmp_path / "missing") == []


def test_list_saved_application_packets_lists_valid_packet(tmp_path: Path) -> None:
    _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        _packet_payload(),
    )

    packets = list_saved_application_packets(tmp_path)

    assert len(packets) == 1
    assert packets[0]["title"] == "Junior Python Analyst"
    assert packets[0]["company"] == "Example Analytics Studio"
    assert packets[0]["matched_keywords_count"] == 2
    assert packets[0]["concern_count"] == 1
    assert packets[0]["status"] == "Tailoring"
    assert packets[0]["status_updated_at"] == "2026-05-28T10:00:00"
    assert packets[0]["applied_date"] is None


def test_list_saved_application_packets_skips_broken_folder(tmp_path: Path) -> None:
    broken_folder = tmp_path / "broken"
    broken_folder.mkdir()
    (broken_folder / "packet.json").write_text("{not json", encoding="utf-8")
    _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        _packet_payload(),
    )

    packets = list_saved_application_packets(tmp_path)

    assert len(packets) == 1
    assert packets[0]["company"] == "Example Analytics Studio"


def test_load_saved_application_packet_reads_packet_json(tmp_path: Path) -> None:
    folder_path = _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        _packet_payload(),
    )

    packet = load_saved_application_packet(folder_path)

    assert packet is not None
    assert packet["summary"]["score"] == 85
    assert packet["application_tracking"]["status"] == "Tailoring"
    assert packet["application_packet"]["apply_recommendation"] == "Apply after tailoring."


def test_saved_application_summaries_do_not_include_raw_job_text(tmp_path: Path) -> None:
    _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        _packet_payload(),
    )

    packets = list_saved_application_packets(tmp_path)
    packet = load_saved_application_packet(packets[0]["folder_path"])

    assert "Private raw job text" not in str(packets)
    assert "Private raw job text" not in str(packet)
    assert "raw_text" not in str(packet)
    assert "raw_job_description" not in str(packet)


def test_saved_application_uses_safe_fallback_text(tmp_path: Path) -> None:
    payload = {
        "score_summary": {},
        "application_packet": {},
    }
    _write_packet(tmp_path, "2026-05-28_unknown-company_unknown-role", payload)

    packets = list_saved_application_packets(tmp_path)

    assert packets[0]["saved_date"] == "2026-05-28"
    assert packets[0]["title"] == "Unknown"
    assert packets[0]["company"] == "Unknown"
    assert packets[0]["location"] == "Unknown"
    assert packets[0]["work_mode"] == "Unknown"
    assert packets[0]["recommendation"] == "Unknown"
    assert packets[0]["apply_recommendation"] == "Unknown"
    assert packets[0]["status"] == "Interested"
    assert packets[0]["status_updated_at"] == ""
    assert packets[0]["applied_date"] is None


def test_old_packet_without_tracking_loads_as_interested(tmp_path: Path) -> None:
    payload = _packet_payload()
    payload.pop("application_tracking")
    _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        payload,
    )

    packets = list_saved_application_packets(tmp_path)

    assert packets[0]["status"] == "Interested"
    assert packets[0]["status_updated_at"] == ""
    assert packets[0]["applied_date"] is None
    assert packets[0]["notes"] == ""


def test_update_application_status_writes_valid_status(tmp_path: Path) -> None:
    folder_path = _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        _packet_payload(),
    )

    result = update_application_status(folder_path, "Applied")
    packet = load_saved_application_packet(folder_path)

    assert result["updated"] is True
    assert packet["application_tracking"]["status"] == "Applied"
    assert packet["application_tracking"]["status_updated_at"]


def test_update_application_status_rejects_invalid_status(tmp_path: Path) -> None:
    folder_path = _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        _packet_payload(),
    )

    result = update_application_status(folder_path, "Thinking About It")
    packet = load_saved_application_packet(folder_path)

    assert result["updated"] is False
    assert packet["application_tracking"]["status"] == "Tailoring"


def test_update_application_status_saves_notes(tmp_path: Path) -> None:
    folder_path = _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        _packet_payload(),
    )

    update_application_status(
        folder_path,
        "Ready to Apply",
        notes="Need final cover letter review.",
    )
    packet = load_saved_application_packet(folder_path)

    assert packet["application_tracking"]["notes"] == "Need final cover letter review."


def test_update_application_status_saves_applied_date(tmp_path: Path) -> None:
    folder_path = _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        _packet_payload(),
    )

    update_application_status(folder_path, "Applied", applied_date="2026-05-28")
    packet = load_saved_application_packet(folder_path)

    assert packet["application_tracking"]["applied_date"] == "2026-05-28"


def test_update_application_status_does_not_add_raw_job_description(
    tmp_path: Path,
) -> None:
    payload = _packet_payload()
    folder_path = _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        payload,
    )

    update_application_status(folder_path, "Applied", notes="Safe note.")
    packet_text = (folder_path / "packet.json").read_text(encoding="utf-8")

    assert "Private raw job text" not in packet_text
    assert "raw_text" not in packet_text
    assert "raw_job_description" not in packet_text
