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
    assert "Python and SQL" in job["raw_text"]


def test_parse_job_text_returns_unknown_for_missing_labels() -> None:
    job = parse_job_text("Use Python to automate reporting workflows.")

    assert job["title"] == "Unknown"
    assert job["company"] == "Unknown"
    assert job["location"] == "Unknown"
