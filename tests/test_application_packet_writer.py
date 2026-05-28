from datetime import date
import json
from pathlib import Path

from application_packet_writer import (
    build_packet_folder_name,
    safe_slug,
    save_application_packet,
)


def _packet() -> dict[str, object]:
    return {
        "positioning_summary": "Strong target based on verified support overlap.",
        "apply_recommendation": "Apply after tailoring.",
        "resume_focus_areas": ["Lead with verified IT support experience."],
        "resume_bullet_suggestions": [
            "Suggested bullet: Supported users through verified troubleshooting examples."
        ],
        "keywords_to_include_honestly": ["python", "documentation"],
        "keywords_to_avoid_or_verify": ["linux"],
        "cover_letter_draft": "Draft only. Review carefully before using.",
        "recruiter_message": "Hi, I am interested in the role.",
        "application_checklist": ["Confirm metadata.", "Apply after review."],
        "risk_notes": ["Do not include claims you cannot verify."],
    }


def _score_result(
    title: str = "Junior Python Analyst",
    company: str = "Example Analytics Studio",
) -> dict[str, object]:
    return {
        "job_metadata": {
            "title": title,
            "company": company,
            "location": "Remote",
            "work_mode": "Remote",
        },
        "score": 85,
        "recommendation": "Apply",
        "matched_keywords": ["python", "documentation"],
        "missing_keywords": ["linux"],
        "concerns": [],
        "raw_text": "Private full job description should not be saved.",
        "explanation": {
            "fit_summary": "This job scored well.",
            "strengths": ["Matched fit keywords: python"],
            "gaps": ["Potential gaps to review: linux."],
            "concerns": ["No concern keywords or metadata issues were found."],
            "tailoring_suggestions": ["Emphasize verified experience."],
        },
    }


def test_safe_slug_removes_unsafe_characters() -> None:
    assert safe_slug("Example: Analytics / Studio!", "fallback") == "example-analytics-studio"
    assert safe_slug("Unknown", "unknown-company") == "unknown-company"
    assert safe_slug("!!!", "unknown-role") == "unknown-role"


def test_build_packet_folder_name_uses_date_company_and_title() -> None:
    folder_name = build_packet_folder_name(
        {
            "company": "Example Analytics Studio",
            "title": "Junior Python Analyst",
        },
        date(2026, 5, 28),
    )

    assert folder_name == "2026-05-28_example-analytics-studio_junior-python-analyst"


def test_save_application_packet_writes_expected_files(tmp_path: Path) -> None:
    result = save_application_packet(
        _packet(),
        _score_result(),
        tmp_path,
        packet_date=date(2026, 5, 28),
    )

    folder_path = result["folder_path"]
    output_paths = result["output_paths"]

    assert folder_path.exists()
    assert folder_path.name == "2026-05-28_example-analytics-studio_junior-python-analyst"
    assert output_paths["job_summary"].exists()
    assert output_paths["score_explanation"].exists()
    assert output_paths["resume_tailoring_notes"].exists()
    assert output_paths["cover_letter_draft"].exists()
    assert output_paths["recruiter_message"].exists()
    assert output_paths["application_checklist"].exists()
    assert output_paths["packet_json"].exists()


def test_save_application_packet_uses_unknown_fallbacks(tmp_path: Path) -> None:
    result = save_application_packet(
        _packet(),
        _score_result(title="Unknown", company="Unknown"),
        tmp_path,
        packet_date=date(2026, 5, 28),
    )

    assert result["folder_path"].name == "2026-05-28_unknown-company_unknown-role"


def test_save_application_packet_does_not_write_raw_job_description(tmp_path: Path) -> None:
    packet = _packet()
    packet["raw_text"] = "Private full job description should not be saved."
    result = save_application_packet(
        packet,
        _score_result(),
        tmp_path,
        packet_date=date(2026, 5, 28),
    )

    for output_path in result["output_paths"].values():
        assert "Private full job description" not in output_path.read_text(encoding="utf-8")


def test_save_application_packet_does_not_overwrite_existing_folder(tmp_path: Path) -> None:
    first = save_application_packet(
        _packet(),
        _score_result(),
        tmp_path,
        packet_date=date(2026, 5, 28),
    )
    second = save_application_packet(
        _packet(),
        _score_result(),
        tmp_path,
        packet_date=date(2026, 5, 28),
    )

    assert first["folder_path"] != second["folder_path"]
    assert second["folder_path"].name.endswith("-2")


def test_save_application_packet_json_is_valid(tmp_path: Path) -> None:
    result = save_application_packet(
        _packet(),
        _score_result(),
        tmp_path,
        packet_date=date(2026, 5, 28),
    )

    payload = json.loads(
        result["output_paths"]["packet_json"].read_text(encoding="utf-8")
    )

    assert payload["created_date"] == "2026-05-28"
    assert payload["job_metadata"]["company"] == "Example Analytics Studio"
    assert payload["score_summary"]["score"] == 85
    assert "raw_text" not in payload["score_summary"]
    assert "raw_text" not in payload["application_packet"]
