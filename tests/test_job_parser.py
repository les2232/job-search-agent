from job_parser import parse_job_text


def test_parse_job_text_extracts_labeled_fields() -> None:
    job = parse_job_text(
        """Title: Junior Python Analyst
Company: Example Studio
Location: Remote

Use Python and SQL to support dashboards.
"""
    )

    assert job["title"] == "Junior Python Analyst"
    assert job["company"] == "Example Studio"
    assert job["location"] == "Remote"
    assert job["work_mode"] == "Remote"
    assert "Python and SQL" in job["raw_text"]


def test_parse_job_text_returns_unknown_for_missing_labels() -> None:
    job = parse_job_text("Use Python to automate reporting workflows.")

    assert job["title"] == "Unknown"
    assert job["company"] == "Unknown"
    assert job["location"] == "Unknown"


def test_parse_job_text_extracts_common_labeled_fields() -> None:
    job = parse_job_text(
        """Job Title: Technical Support Specialist
Organization: Example Helpdesk Team
Work Location: Aurora, CO

Support users with Microsoft 365 and classroom AV systems.
"""
    )

    assert job["title"] == "Technical Support Specialist"
    assert job["company"] == "Example Helpdesk Team"
    assert job["location"] == "Aurora, CO"
    assert job["parser_debug"]["fallback_path"] == "explicit fields"


def test_parse_job_text_infers_metadata_from_raw_post_top_lines() -> None:
    job = parse_job_text(
        """Product Support Specialist
Example Software Studio
Denver, CO (Hybrid)

We are looking for a support specialist to troubleshoot customer issues,
document workflows, and coordinate escalations.
"""
    )

    assert job["title"] == "Product Support Specialist"
    assert job["company"] == "Example Software Studio"
    assert job["location"] == "Denver, CO (Hybrid)"
    assert job["work_mode"] == "Hybrid"
    assert job["parser_debug"]["fallback_path"] == "top-line inference"


def test_parse_job_text_uses_separate_fields_before_raw_text() -> None:
    job = parse_job_text(
        "A raw posting with unclear metadata.",
        title="IT Support Analyst",
        company="Example College",
        location="Aurora, CO",
    )

    assert job["title"] == "IT Support Analyst"
    assert job["company"] == "Example College"
    assert job["location"] == "Aurora, CO"
