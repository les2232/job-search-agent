from datetime import date

from application_packet_validator import (
    OPTIONAL_PACKET_FILES,
    REQUIRED_PACKET_FILES,
    validate_saved_packet_folder,
)
from application_packet_writer import save_application_packet


def _packet() -> dict[str, object]:
    return {
        "positioning_summary": "Strong target.",
        "apply_recommendation": "Apply after tailoring.",
        "resume_focus_areas": ["Use verified support evidence."],
        "resume_bullet_suggestions": ["Use only if true: Built local tools."],
        "keywords_to_include_honestly": ["python"],
        "keywords_to_avoid_or_verify": ["linux"],
        "cover_letter_draft": "Dear Hiring Team,",
        "tailored_resume_draft": "# Tailored Resume Draft\n\nReviewable draft.",
        "recruiter_message": "Hi, I am interested in the role.",
        "application_checklist": ["Review every claim."],
        "risk_notes": ["Do not include unsupported claims."],
    }


def _score_result() -> dict[str, object]:
    return {
        "job_metadata": {
            "title": "Junior Python Analyst",
            "company": "Example Analytics Studio",
            "location": "Remote",
            "work_mode": "Remote",
        },
        "score": 85,
        "recommendation": "Apply",
        "matched_keywords": ["python"],
        "missing_keywords": [],
        "concerns": [],
        "explanation": {"fit_summary": "Good fit."},
    }


def test_complete_saved_packet_folder_validates_successfully(tmp_path) -> None:
    save_result = save_application_packet(
        _packet(),
        _score_result(),
        tmp_path,
        packet_date=date(2026, 6, 13),
    )

    result = validate_saved_packet_folder(save_result["folder_path"])

    assert result["is_valid"] is True
    assert result["missing_required_files"] == []
    assert result["missing_optional_files"] == []
    assert result["present_files"] == REQUIRED_PACKET_FILES + OPTIONAL_PACKET_FILES
    assert result["warnings"] == []


def test_missing_packet_json_is_reported_as_required(tmp_path) -> None:
    packet_folder = tmp_path / "packet"
    packet_folder.mkdir()
    (packet_folder / "packet_index.md").write_text("# Index", encoding="utf-8")
    (packet_folder / "tailored_resume.md").write_text("# Resume", encoding="utf-8")

    result = validate_saved_packet_folder(packet_folder)

    assert result["is_valid"] is False
    assert result["missing_required_files"] == ["packet.json"]
    assert "packet.json" in result["warnings"][0]


def test_missing_packet_index_is_reported_as_required(tmp_path) -> None:
    packet_folder = tmp_path / "packet"
    packet_folder.mkdir()
    (packet_folder / "tailored_resume.md").write_text("# Resume", encoding="utf-8")
    (packet_folder / "packet.json").write_text("{}", encoding="utf-8")

    result = validate_saved_packet_folder(packet_folder)

    assert result["is_valid"] is False
    assert result["missing_required_files"] == ["packet_index.md"]


def test_missing_tailored_resume_is_reported_as_required(tmp_path) -> None:
    packet_folder = tmp_path / "packet"
    packet_folder.mkdir()
    (packet_folder / "packet_index.md").write_text("# Index", encoding="utf-8")
    (packet_folder / "packet.json").write_text("{}", encoding="utf-8")

    result = validate_saved_packet_folder(packet_folder)

    assert result["is_valid"] is False
    assert result["missing_required_files"] == ["tailored_resume.md"]


def test_optional_files_are_reported_separately_and_in_order(tmp_path) -> None:
    packet_folder = tmp_path / "packet"
    packet_folder.mkdir()
    for filename in REQUIRED_PACKET_FILES:
        (packet_folder / filename).write_text("present", encoding="utf-8")
    (packet_folder / "cover_letter_draft.md").write_text("present", encoding="utf-8")
    (packet_folder / "job_summary.md").write_text("present", encoding="utf-8")

    result = validate_saved_packet_folder(packet_folder)

    assert result["is_valid"] is True
    assert result["missing_required_files"] == []
    assert result["missing_optional_files"] == [
        "resume_tailoring_notes.md",
        "recruiter_message.txt",
        "application_checklist.md",
        "score_explanation.md",
    ]
    assert result["present_files"] == [
        "packet_index.md",
        "tailored_resume.md",
        "packet.json",
        "cover_letter_draft.md",
        "job_summary.md",
    ]


def test_nonexistent_folder_is_handled_safely(tmp_path) -> None:
    packet_folder = tmp_path / "missing"

    result = validate_saved_packet_folder(packet_folder)

    assert result["is_valid"] is False
    assert result["packet_path"] == packet_folder
    assert result["present_files"] == []
    assert result["missing_required_files"] == REQUIRED_PACKET_FILES
    assert result["missing_optional_files"] == OPTIONAL_PACKET_FILES
    assert "does not exist" in result["warnings"][0]
