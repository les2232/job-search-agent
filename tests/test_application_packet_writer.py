from datetime import date
import json
from pathlib import Path

from application_packet_writer import (
    build_packet_folder_name,
    safe_slug,
    save_application_packet,
)
from application_packet import generate_application_packet
from job_scorer import extract_job_requirements


FEI_JOB_TEXT = """
FEI Systems builds technology solutions for health and human services.
We are looking for a Full-Stack Developer to work on case management software.

Required Skills/Experience
- 4+ years C#/.NET software development experience
- 3+ years Angular 16+ and TypeScript development
- SQL Server or relational database experience
- Git, Azure DevOps, and CI/CD pipelines
- 1+ years AWS serverless or similar cloud services
- Object-oriented design patterns
- Domain Driven Design
- Service Oriented Architecture
- Unit testing
- Test Driven Development
"""

ARRIVIA_AI_JOB_TEXT = """
Arrivia, Inc. is hiring an AI Agent Builder to improve automation workflows for
travel operations. This remote role will build AI agents and API integrations
that connect internal systems, data workflows, and user-facing support tools.

Required Skills/Experience
- Python scripting or Python development
- SQL and data workflows
- APIs and API integration
- Automation and workflow automation
- AI agent or agentic workflow experience
- LLM workflows and prompt engineering
- Object-oriented design patterns
"""


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


def _fei_score_result() -> dict[str, object]:
    return {
        "job_metadata": {
            "title": "Full-Stack Developer Who Shares Our Commitment",
            "company": "FEI Systems",
            "location": "Remote",
            "work_mode": "Remote",
        },
        "score": 65,
        "recommendation": "Maybe",
        "matched_keywords": ["sql", "git", "remote"],
        "missing_keywords": ["python", "dashboard", "linux"],
        "concerns": [],
        "explanation": {
            "fit_summary": "Possible fit with gaps to review.",
            "strengths": ["Matched fit keywords: sql, git, remote"],
            "gaps": ["Potential gaps to review: python, dashboard, linux."],
            "concerns": ["No concern keywords or metadata issues were found."],
            "tailoring_suggestions": ["Review gaps before applying."],
        },
        "job_requirements": extract_job_requirements(FEI_JOB_TEXT),
        "raw_text": FEI_JOB_TEXT,
    }


def _arrivia_score_result() -> dict[str, object]:
    return {
        "job_metadata": {
            "title": "AI Agent Builder",
            "company": "Arrivia, Inc.",
            "location": "Austin, TX",
            "work_mode": "Remote",
        },
        "score": 80,
        "recommendation": "Apply",
        "matched_keywords": ["python", "sql", "apis", "automation", "data", "remote"],
        "missing_keywords": ["dashboard", "linux"],
        "concerns": [],
        "explanation": {
            "fit_summary": "Strong overlap with AI/automation requirements to verify.",
            "strengths": ["Matched fit keywords: python, sql, apis, automation, data, remote"],
            "gaps": ["Role-specific hard requirements to verify."],
            "concerns": ["No concern keywords or metadata issues were found."],
            "tailoring_suggestions": ["Review AI/automation evidence before applying."],
        },
        "job_requirements": extract_job_requirements(ARRIVIA_AI_JOB_TEXT),
        "raw_text": ARRIVIA_AI_JOB_TEXT,
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
    assert payload["application_tracking"]["status"] == "Interested"
    assert payload["application_tracking"]["applied_date"] is None
    assert payload["application_tracking"]["notes"] == ""
    assert payload["application_tracking"]["next_action_date"] is None
    assert payload["application_tracking"]["next_action_note"] == ""
    assert payload["application_tracking"]["status_updated_at"]
    assert "raw_text" not in payload["score_summary"]
    assert "raw_text" not in payload["application_packet"]


def test_save_application_packet_can_write_under_profile_folder(tmp_path: Path) -> None:
    profile_root = tmp_path / "applications" / "default"

    result = save_application_packet(
        _packet(),
        _score_result(),
        profile_root,
        packet_date=date(2026, 5, 28),
    )

    assert result["folder_path"].parent == profile_root
    assert result["folder_path"].exists()


def test_resume_tailoring_notes_are_scannable_strategy_packet(tmp_path: Path) -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        (
            "Local IT support, user communication, troubleshooting, documentation, "
            "classroom AV troubleshooting, git, and SQL."
        ),
    )
    result = save_application_packet(
        packet,
        _fei_score_result(),
        tmp_path,
        packet_date=date(2026, 5, 29),
    )

    notes = result["output_paths"]["resume_tailoring_notes"].read_text(encoding="utf-8")

    assert "## Fit Verdict" in notes
    assert "Stretch Role" in notes
    assert "Full-Stack Developer at FEI Systems" in notes
    assert "Full-Stack Developer Who Shares Our Commitment" not in notes
    assert "## Apply Recommendation" in notes
    assert "## Strong / Supported Overlap" in notes
    assert "- Git/version control, if supported by coursework, scripts, or software projects." in notes
    assert "- SQL/database work, if supported by database queries, reports, or data-backed troubleshooting." in notes
    assert "## Major Requirements To Verify Before Applying" in notes
    assert "- C# / .NET 5+ professional experience" in notes
    assert "- Angular 16+ and TypeScript" in notes
    assert "- AWS serverless or similar cloud services" in notes
    assert "- Domain Driven Design and Service Oriented Architecture" in notes
    assert "- Unit testing and Test Driven Development" in notes
    assert "- Required years of full-stack software development experience" in notes
    assert "## Transferable Support Evidence" in notes
    assert "Do not present support, classroom, or AV troubleshooting as software development experience." in notes
    assert "## Apply Only If" in notes
    assert "## Consider Skipping Or Deprioritizing If" in notes
    assert "## Suggested Resume Bullets" in notes
    assert "Use only if true:" in notes
    assert "## Keywords / Themes To Include Honestly" in notes
    assert "- SQL / database-backed troubleshooting, only if supported." in notes
    assert "- Git / version control, only if supported." in notes
    assert "## Keywords To Verify Or Avoid" in notes
    assert "Draft only. Review carefully before using." in notes
    assert "python" not in notes.lower()
    assert "dashboard" not in notes.lower()
    assert "linux" not in notes.lower()


def test_saved_ai_packet_uses_same_requirements_as_analysis(tmp_path: Path) -> None:
    score_result = _arrivia_score_result()
    packet = generate_application_packet(
        score_result,
        (
            "Profile includes Python scripts, SQL reports, API experiments, "
            "automation projects, documentation, data troubleshooting, and IT support."
        ),
    )
    result = save_application_packet(
        packet,
        score_result,
        tmp_path,
        packet_date=date(2026, 5, 30),
    )

    notes = result["output_paths"]["resume_tailoring_notes"].read_text(encoding="utf-8")
    payload = json.loads(
        result["output_paths"]["packet_json"].read_text(encoding="utf-8")
    )
    packet_text = str(payload)

    assert "AI agent or automation workflow experience" in notes
    assert "LLM or large language model workflow experience" in notes
    assert "Prompt engineering or prompting experience" in notes
    assert "API integration experience" in notes
    assert "Object-oriented design patterns" in notes
    assert "C# / .NET" not in notes
    assert "Angular 16+" not in notes
    assert "comparable full-stack development work" not in notes
    assert "AI agent / agentic workflows" in packet_text
    assert "LLM / large language model workflows" in packet_text
    assert "Prompt engineering" in packet_text
    assert "raw_text" not in packet_text
    assert "raw_text" not in payload["score_summary"]
