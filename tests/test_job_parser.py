from job_parser import parse_job_text
from pathlib import Path


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "jobs"


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


def test_parse_job_text_extracts_clean_labeled_position_and_work_mode() -> None:
    job = parse_job_text(
        """Position: AI Developer
Company: Example Automation Lab
Location: Denver, CO
Work Arrangement: Remote with travel

Responsibilities:
- Build deterministic automation tools.
- Document repeatable workflows.
"""
    )

    assert job["title"] == "AI Developer"
    assert job["company"] == "Example Automation Lab"
    assert job["location"] == "Denver, CO"
    assert job["work_mode"] == "Remote"


def test_parse_job_text_reports_verified_confidence_for_labeled_fields() -> None:
    job = parse_job_text(
        """Job Title: IT Support Specialist
Company: Example Organization
Location: Remote
Work Mode: Remote

Responsibilities:
- Support users with Microsoft 365.
"""
    )

    assert job["field_sources"] == {
        "title": "label",
        "company": "label",
        "location": "label",
        "work_mode": "label",
    }
    assert job["field_confidence"] == {
        "title": "verified",
        "company": "verified",
        "location": "verified",
        "work_mode": "verified",
    }


def test_parse_job_text_reports_unverified_confidence_for_heuristic_fields() -> None:
    job = parse_job_text(
        """Product Support Specialist
Example Software Studio
Denver, CO (Hybrid)

We are looking for a support specialist to troubleshoot customer issues.
"""
    )

    assert job["title"] == "Product Support Specialist"
    assert job["company"] == "Example Software Studio"
    assert job["location"] == "Denver, CO (Hybrid)"
    assert job["work_mode"] == "Hybrid"
    assert job["field_sources"] == {
        "title": "heuristic",
        "company": "heuristic",
        "location": "heuristic",
        "work_mode": "heuristic",
    }
    assert job["field_confidence"] == {
        "title": "unverified",
        "company": "unverified",
        "location": "unverified",
        "work_mode": "unverified",
    }


def test_parse_job_text_rejects_page_chrome_as_heuristic_title_or_company() -> None:
    job = parse_job_text(
        """Start of main content
Clarvida logo
Responsibilities:
Build local workflow automation tools for support teams.
Qualifications:
Python scripting and documentation habits.
"""
    )

    assert job["title"] == "Unknown"
    assert job["company"] == "Unknown"
    assert job["field_sources"]["title"] == "none"
    assert job["field_sources"]["company"] == "none"
    assert job["field_confidence"]["title"] == "none"
    assert job["field_confidence"]["company"] == "none"


def test_parse_job_text_keeps_valid_unlabeled_heuristic_title() -> None:
    job = parse_job_text(
        """AI Automation Specialist
Example Automation Studio
Remote

Responsibilities:
Build local workflow automation tools for support teams.
Qualifications:
Python scripting and documentation habits.
"""
    )

    assert job["title"] == "AI Automation Specialist"
    assert job["company"] == "Example Automation Studio"
    assert job["field_sources"]["title"] == "heuristic"
    assert job["field_confidence"]["title"] == "unverified"


def test_parse_job_text_returns_unknown_for_missing_labels() -> None:
    job = parse_job_text("Use Python to automate reporting workflows.")

    assert job["title"] == "Unknown"
    assert job["company"] == "Unknown"
    assert job["location"] == "Unknown"


def test_parse_job_text_extracts_narrative_bridge_partners_shape() -> None:
    job = parse_job_text((FIXTURE_DIR / "bridge_partners_ai_developer.txt").read_text())

    assert job["title"] == "AI Developer"
    assert job["company"] == "Bridge Partners"
    assert job["location"] == "Unknown"
    assert job["work_mode"] == "Remote"


def test_parse_job_text_ignores_generic_section_headings_without_guessing() -> None:
    job = parse_job_text(
        """About the job
About the Company
How you'll contribute
Your skills and approach
Compensation
Work Eligibility
Benefits

We build useful software and value clear documentation.
This role is remote.
"""
    )

    assert job["title"] == "Unknown"
    assert job["company"] == "Unknown"
    assert job["work_mode"] == "Remote"


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


def test_parse_job_text_handles_noisy_copied_posting_with_heading_title() -> None:
    job = parse_job_text(
        """Home
Search jobs
Apply now
Save job

The role: Platform Support Analyst
Example Cloud Studio
Remote with travel

About the job
This role is remote, with preferred hubs in Denver, CO and Austin, TX.

Your skills and approach
- Troubleshooting SaaS integrations
- SQL
- Customer documentation

Share job
Similar jobs
"""
    )

    assert job["title"] == "Platform Support Analyst"
    assert job["company"] == "Example Cloud Studio"
    assert job["location"] == "Remote with travel"
    assert job["work_mode"] == "Remote"


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


def test_parse_job_text_uses_clean_header_fields_before_boilerplate() -> None:
    job = parse_job_text(
        """Job details
Job type

Job Title: Full-Stack Developer
Company: FEI Systems
Location: Remote
Work Mode: Remote

Full Job Description

At FEI Systems...
We're looking for a full-stack developer to support internal tools.
"""
    )

    assert job["title"] == "Full-Stack Developer"
    assert job["company"] == "FEI Systems"
    assert job["location"] == "Remote"
    assert job["work_mode"] == "Remote"


def test_parse_job_text_ignores_job_board_boilerplate_from_copied_posting() -> None:
    job = parse_job_text(
        """Job details
Here's how the job details align with your profile.
Job type

Full job description

At FEI Systems...
We're looking for a full-stack developer to build and maintain web applications.

Required Skills/Experience
- Python
- JavaScript

Location: Remote
"""
    )

    assert job["title"] == "Full-Stack Developer"
    assert job["company"] == "FEI Systems"
    assert job["location"] == "Remote"
    assert job["work_mode"] == "Remote"


def test_parse_job_text_ignores_html_entities_from_copied_posting() -> None:
    job = parse_job_text(
        """Job details
&nbsp;
&
 
Job type

Full job description

At FEI Systems...
We're looking for a full-stack developer to build and maintain web applications.

Required Skills/Experience
- Python
- JavaScript

Location: Remote
"""
    )

    assert job["title"] == "Full-Stack Developer"
    assert job["company"] == "FEI Systems"
    assert job["location"] == "Remote"
    assert job["work_mode"] == "Remote"
