import json
from datetime import date
from pathlib import Path

from application_packet_reader import (
    count_saved_applications_by_status,
    filter_saved_application_packets,
    get_next_action,
    get_next_action_state,
    get_today_application_queue,
    list_saved_application_packets,
    load_saved_application_packet,
    sort_saved_application_packets,
    update_application_status,
    update_application_tracking,
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
            "next_action_date": None,
            "next_action_note": "",
        },
    }


def _summary(
    title: str = "Junior Python Analyst",
    company: str = "Example Analytics Studio",
    status: str = "Interested",
    score: int = 85,
    saved_date: str = "2026-05-28",
) -> dict[str, object]:
    return {
        "folder_path": Path("applications/example"),
        "saved_date": saved_date,
        "title": title,
        "company": company,
        "location": "Remote",
        "work_mode": "Remote",
        "score": score,
        "recommendation": "Apply",
        "apply_recommendation": "Apply after tailoring.",
        "status": status,
        "status_updated_at": "",
        "applied_date": None,
        "notes": "",
        "next_action": get_next_action(status),
        "next_action_date": None,
        "next_action_note": "",
        "days_until_next_action": None,
        "is_overdue": False,
        "needs_attention": False,
        "attention_reason": "",
        "matched_keywords_count": 2,
        "concern_count": 0,
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
    assert packets[0]["next_action_date"] is None
    assert packets[0]["next_action_note"] == ""
    assert packets[0]["next_action"] == "Finish resume/cover letter edits."


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
    assert packets[0]["next_action_date"] is None
    assert packets[0]["next_action_note"] == ""


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
    assert packets[0]["next_action_date"] is None
    assert packets[0]["next_action_note"] == ""


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


def test_update_application_tracking_saves_next_action_fields(tmp_path: Path) -> None:
    folder_path = _write_packet(
        tmp_path,
        "2026-05-28_example-analytics-studio_junior-python-analyst",
        _packet_payload(),
    )

    update_application_tracking(
        folder_path,
        status="Tailoring",
        next_action_date="2026-06-04",
        next_action_note="Finish resume tailoring.",
    )
    packet = load_saved_application_packet(folder_path)

    assert packet["application_tracking"]["next_action_date"] == "2026-06-04"
    assert packet["application_tracking"]["next_action_note"] == "Finish resume tailoring."


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


def test_get_next_action_state_marks_overdue() -> None:
    state = get_next_action_state(
        {"status": "Tailoring", "next_action_date": "2026-05-27"},
        today=date(2026, 5, 28),
    )

    assert state["is_overdue"] is True
    assert state["needs_attention"] is True
    assert state["days_until_next_action"] == -1


def test_get_next_action_state_marks_due_soon() -> None:
    state = get_next_action_state(
        {"status": "Tailoring", "next_action_date": "2026-05-31"},
        today=date(2026, 5, 28),
    )

    assert state["is_overdue"] is False
    assert state["needs_attention"] is True
    assert state["days_until_next_action"] == 3


def test_get_next_action_state_marks_ready_to_apply_without_date() -> None:
    state = get_next_action_state(
        {"status": "Ready to Apply"},
        today=date(2026, 5, 28),
    )

    assert state["needs_attention"] is True
    assert state["attention_reason"] == "Ready to apply"


def test_get_next_action_state_marks_applied_without_date() -> None:
    state = get_next_action_state(
        {"status": "Applied"},
        today=date(2026, 5, 28),
    )

    assert state["needs_attention"] is True
    assert state["attention_reason"] == "Add a follow-up date"


def test_get_next_action_state_archived_needs_no_attention() -> None:
    state = get_next_action_state(
        {"status": "Archived", "next_action_date": "2026-05-27"},
        today=date(2026, 5, 28),
    )

    assert state["is_overdue"] is False
    assert state["needs_attention"] is False


def test_count_saved_applications_by_status() -> None:
    packets = [
        _summary(status="Interested"),
        _summary(status="Tailoring"),
        _summary(status="Tailoring"),
        _summary(status="Applied"),
    ]

    counts = count_saved_applications_by_status(packets)

    assert counts["Interested"] == 1
    assert counts["Tailoring"] == 2
    assert counts["Applied"] == 1
    assert counts["Archived"] == 0


def test_filter_saved_application_packets_by_status() -> None:
    packets = [
        _summary(status="Interested"),
        _summary(status="Tailoring"),
    ]

    filtered = filter_saved_application_packets(packets, status="tailoring")

    assert len(filtered) == 1
    assert filtered[0]["status"] == "Tailoring"


def test_filter_saved_application_packets_by_min_score() -> None:
    packets = [
        _summary(score=55),
        _summary(score=90),
    ]

    filtered = filter_saved_application_packets(packets, min_score=70)

    assert len(filtered) == 1
    assert filtered[0]["score"] == 90


def test_filter_saved_application_packets_by_company_and_title_search() -> None:
    packets = [
        _summary(title="Junior Python Analyst", company="Example Analytics Studio"),
        _summary(title="Desktop Support Specialist", company="Campus IT"),
    ]

    company_filtered = filter_saved_application_packets(
        packets,
        company_search="analytics",
    )
    text_filtered = filter_saved_application_packets(
        packets,
        text_search="desktop",
    )

    assert company_filtered[0]["company"] == "Example Analytics Studio"
    assert text_filtered[0]["title"] == "Desktop Support Specialist"


def test_filter_saved_application_packets_by_attention_flags() -> None:
    packets = [
        {**_summary(title="Calm"), "needs_attention": False, "is_overdue": False},
        {
            **_summary(title="Due"),
            "needs_attention": True,
            "is_overdue": False,
            "days_until_next_action": 3,
        },
        {
            **_summary(title="Late"),
            "needs_attention": True,
            "is_overdue": True,
            "days_until_next_action": -1,
        },
    ]

    attention = filter_saved_application_packets(packets, needs_attention=True)
    overdue = filter_saved_application_packets(packets, overdue=True)
    due_soon = filter_saved_application_packets(packets, due_within_days=7)

    assert [packet["title"] for packet in attention] == ["Due", "Late"]
    assert [packet["title"] for packet in overdue] == ["Late"]
    assert [packet["title"] for packet in due_soon] == ["Due"]


def test_get_next_action_returns_status_guidance() -> None:
    assert get_next_action("Interested") == "Review score and decide whether to tailor."
    assert get_next_action("Ready to Apply") == "Submit application."
    assert get_next_action("Archived") == "No action needed."


def test_sort_saved_application_packets_by_score_and_saved_date() -> None:
    packets = [
        _summary(title="Low", score=50, saved_date="2026-05-27"),
        _summary(title="High", score=95, saved_date="2026-05-28"),
    ]

    by_score = sort_saved_application_packets(packets, "Highest score first")
    by_oldest = sort_saved_application_packets(packets, "Oldest saved first")

    assert by_score[0]["title"] == "High"
    assert by_oldest[0]["title"] == "Low"


def test_dashboard_helpers_handle_missing_fields_without_crashing() -> None:
    packets = [{"title": "Unknown"}]

    counts = count_saved_applications_by_status(packets)
    filtered = filter_saved_application_packets(packets, min_score=1)
    sorted_packets = sort_saved_application_packets(packets, "Company")

    assert counts["Interested"] == 1
    assert filtered == []
    assert sorted_packets == packets


def test_filtered_summaries_do_not_return_raw_job_text() -> None:
    packets = [
        {
            **_summary(),
            "raw_text": "Private raw text",
            "raw_job_description": "Private raw text",
        }
    ]

    filtered = filter_saved_application_packets(packets, status="Interested")

    assert "Private raw text" in str(packets)
    assert "Private raw text" not in str(filtered)
    assert "raw_text" not in str(filtered)
    assert "raw_job_description" not in str(filtered)


def test_today_queue_groups_overdue_items() -> None:
    applications = [
        {
            **_summary(title="Late"),
            "needs_attention": True,
            "is_overdue": True,
            "days_until_next_action": -1,
            "attention_reason": "Overdue",
        }
    ]

    queue = get_today_application_queue(applications)

    assert queue["overdue"][0]["title"] == "Late"


def test_today_queue_groups_due_today_items() -> None:
    applications = [
        {
            **_summary(title="Today"),
            "needs_attention": True,
            "is_overdue": False,
            "days_until_next_action": 0,
            "attention_reason": "Due soon",
        }
    ]

    queue = get_today_application_queue(applications)

    assert queue["due_today"][0]["title"] == "Today"


def test_today_queue_groups_due_soon_items() -> None:
    applications = [
        {
            **_summary(title="Soon"),
            "needs_attention": True,
            "is_overdue": False,
            "days_until_next_action": 2,
            "attention_reason": "Due soon",
        }
    ]

    queue = get_today_application_queue(applications)

    assert queue["due_soon"][0]["title"] == "Soon"


def test_today_queue_groups_ready_to_apply_without_date() -> None:
    applications = [
        {
            **_summary(title="Ready", status="Ready to Apply"),
            "needs_attention": True,
            "attention_reason": "Ready to apply",
        }
    ]

    queue = get_today_application_queue(applications)

    assert queue["ready_to_apply_without_date"][0]["title"] == "Ready"


def test_today_queue_groups_applied_without_follow_up() -> None:
    applications = [
        {
            **_summary(title="Applied", status="Applied"),
            "needs_attention": True,
            "attention_reason": "Add a follow-up date",
        }
    ]

    queue = get_today_application_queue(applications)

    assert queue["applied_without_follow_up"][0]["title"] == "Applied"


def test_today_queue_excludes_archived_applications() -> None:
    applications = [
        {
            **_summary(title="Archived", status="Archived"),
            "needs_attention": True,
            "is_overdue": True,
            "attention_reason": "Overdue",
        }
    ]

    queue = get_today_application_queue(applications)

    assert all(not group for group in queue.values())


def test_today_queue_handles_missing_dates() -> None:
    applications = [
        {
            **_summary(title="Missing Date"),
            "needs_attention": False,
            "days_until_next_action": None,
        }
    ]

    queue = get_today_application_queue(applications)

    assert all(not group for group in queue.values())


def test_today_queue_does_not_return_raw_job_text() -> None:
    applications = [
        {
            **_summary(title="Private"),
            "needs_attention": True,
            "is_overdue": True,
            "attention_reason": "Overdue",
            "raw_text": "Private raw text",
            "raw_job_description": "Private raw text",
        }
    ]

    queue = get_today_application_queue(applications)

    assert "Private raw text" not in str(queue)
    assert "raw_text" not in str(queue)
    assert "raw_job_description" not in str(queue)
