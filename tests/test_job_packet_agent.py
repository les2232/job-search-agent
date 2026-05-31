from pathlib import Path

import pytest

from job_packet_agent import AGENT_NAME
from job_packet_agent import run_job_packet_agent


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
ARRIVIA_JOB_TEXT = (FIXTURE_ROOT / "jobs" / "arrivia_ai_agent_builder.txt").read_text(
    encoding="utf-8",
)
PROFILE_TEXT = (
    FIXTURE_ROOT / "profiles" / "test_profile" / "resume_base.md"
).read_text(encoding="utf-8")


def test_job_packet_agent_rejects_empty_job_text() -> None:
    with pytest.raises(ValueError, match="job_text is required"):
        run_job_packet_agent("   ")


def test_job_packet_agent_warns_when_job_text_is_short() -> None:
    result = run_job_packet_agent("Title: Analyst\nCompany: Example\nPython role.")

    warnings = result["warnings"]

    assert any("looks short" in warning for warning in warnings)
    assert any("Review all generated materials" in warning for warning in warnings)


def test_job_packet_agent_returns_structured_review_for_normal_posting() -> None:
    result = run_job_packet_agent(
        ARRIVIA_JOB_TEXT,
        {"resume_text": PROFILE_TEXT},
    )

    assert result["agent_name"] == AGENT_NAME
    assert set(result) == {
        "agent_name",
        "role_summary",
        "extracted_requirements",
        "score_summary",
        "resume_focus_recommendations",
        "packet_outputs",
        "next_actions",
        "warnings",
    }

    role_summary = result["role_summary"]
    score_summary = result["score_summary"]
    requirements = result["extracted_requirements"]
    packet_outputs = result["packet_outputs"]

    assert role_summary["title"] == "AI Agent Builder"
    assert role_summary["company"] == "Arrivia, Inc."
    assert role_summary["work_mode"] == "Remote"
    assert score_summary["score"] >= 75
    assert score_summary["recommendation"] == "Apply"
    assert "python" in score_summary["matched_keywords"]
    assert "AI agent / agentic workflows" in requirements["hard_requirements"]
    assert "LLM / large language model workflows" in requirements["hard_requirements"]
    assert "cover_letter_draft" in packet_outputs
    assert "tailored_resume_draft" in packet_outputs
    assert result["next_actions"]
    assert any("does not submit applications" in warning for warning in result["warnings"])


def test_job_packet_agent_uses_profile_text_for_packet_generation() -> None:
    result = run_job_packet_agent(
        ARRIVIA_JOB_TEXT,
        {"resume_text": PROFILE_TEXT},
    )
    packet_outputs = result["packet_outputs"]
    cover_letter = str(packet_outputs["cover_letter_draft"])

    assert "local-first job application packet tool" in cover_letter
    assert "Flask-based IT support assistant" in cover_letter
