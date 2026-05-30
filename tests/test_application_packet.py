from application_packet import REVIEW_WARNING, generate_application_packet
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


def _score_result(
    score: int,
    recommendation: str,
    title: str = "Junior Python Support Analyst",
    company: str = "Example Studio",
    location: str = "Remote",
) -> dict[str, object]:
    return {
        "job_metadata": {
            "title": title,
            "company": company,
            "location": location,
            "work_mode": "Remote" if location != "Unknown" else "Unknown",
        },
        "score": score,
        "recommendation": recommendation,
        "matched_keywords": ["python", "documentation", "troubleshooting"],
        "missing_keywords": ["sql", "linux"],
        "concerns": [],
        "explanation": {
            "fit_summary": "Example explanation.",
            "strengths": ["Matched fit keywords: python, documentation"],
            "gaps": ["Potential gaps to review: sql, linux."],
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
        "missing_keywords": [
            "python",
            "api",
            "apis",
            "automation",
            "dashboard",
            "dashboards",
            "data",
            "linux",
        ],
        "concerns": [],
        "explanation": {
            "fit_summary": "Possible fit with gaps to review.",
            "strengths": ["Matched fit keywords: sql, git, remote"],
            "gaps": ["Potential gaps to review: python, api, linux."],
            "concerns": ["No concern keywords or metadata issues were found."],
            "tailoring_suggestions": ["Review gaps before applying."],
        },
        "job_requirements": extract_job_requirements(FEI_JOB_TEXT),
        "raw_text": FEI_JOB_TEXT,
    }


def test_generate_application_packet_high_score() -> None:
    packet = generate_application_packet(
        _score_result(85, "Apply"),
        "Fake profile with IT support, Python, Flask, and documentation projects.",
    )

    assert "strong target" in packet["positioning_summary"]
    assert packet["apply_recommendation"].startswith("Apply")
    assert "python" in packet["keywords_to_include_honestly"]
    assert len(packet["resume_bullet_suggestions"]) >= 3


def test_generate_application_packet_medium_score() -> None:
    packet = generate_application_packet(_score_result(65, "Maybe"))

    assert packet["apply_recommendation"].startswith("Maybe")
    assert "honestly address" in packet["apply_recommendation"]
    assert "sql" in packet["keywords_to_avoid_or_verify"]


def test_generate_application_packet_low_score() -> None:
    packet = generate_application_packet(_score_result(45, "Skip"))

    assert "lower priority" in packet["positioning_summary"]
    assert packet["apply_recommendation"].startswith("Lower priority")


def test_generate_application_packet_uses_fallback_wording_for_unknown_metadata() -> None:
    packet = generate_application_packet(
        _score_result(
            60,
            "Maybe",
            title="Unknown",
            company="Unknown",
            location="Unknown",
        )
    )

    assert "this role" in packet["positioning_summary"]
    assert "the organization" in packet["positioning_summary"]
    assert "Unknown" not in packet["cover_letter_draft"]
    assert "Unknown" not in packet["recruiter_message"]


def test_generate_application_packet_does_not_include_raw_job_description() -> None:
    score_result = _score_result(85, "Apply")
    score_result["raw_text"] = "Python role with private details " * 50

    packet_text = str(generate_application_packet(score_result))

    assert "private details" not in packet_text
    assert str(score_result["raw_text"]) not in packet_text


def test_generate_application_packet_does_not_invent_metrics_or_certifications() -> None:
    packet_text = str(generate_application_packet(_score_result(85, "Apply")))

    assert "%" not in packet_text
    assert "Certified" not in packet_text
    assert "certified" not in packet_text
    assert "Led a team" not in packet_text
    assert "Expert in" not in packet_text


def test_generate_application_packet_bullets_are_editable_suggestions() -> None:
    packet = generate_application_packet(_score_result(85, "Apply"))

    bullets = packet["resume_bullet_suggestions"]

    assert len(bullets) >= 3
    assert all(str(bullet).startswith("Suggested bullet:") for bullet in bullets)
    assert REVIEW_WARNING in packet["risk_notes"]


def test_cover_letter_draft_is_employer_facing_without_internal_warnings() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        (
            "Local IT support, user communication, troubleshooting, documentation, "
            "and classroom AV troubleshooting."
        ),
    )
    cover_letter = packet["cover_letter_draft"]

    assert "FEI Systems" in cover_letter
    assert "Full-Stack Developer" in cover_letter
    assert "Full-Stack Developer Who Shares Our Commitment" not in cover_letter
    assert "Draft only" not in cover_letter
    assert "Review carefully" not in cover_letter
    assert "verify" not in cover_letter.lower()
    assert "claims you cannot" not in cover_letter.lower()
    assert "tailor my resume" not in cover_letter.lower()
    assert "appears relevant" not in cover_letter.lower()
    assert "posting appears" not in cover_letter.lower()
    assert "Remote / Remote" not in cover_letter
    assert "sql, git, and remote" not in cover_letter.lower()


def test_maybe_cover_letter_is_polished_but_cautious() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, and documentation.",
    )
    cover_letter = packet["cover_letter_draft"]

    assert "I am interested in learning more" in cover_letter
    assert "where my background could be most useful" in cover_letter
    assert "Maybe" not in cover_letter


def test_cover_letter_does_not_claim_missing_keywords_as_experience() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, and documentation.",
    )
    cover_letter = packet["cover_letter_draft"].lower()

    for missing_keyword in [
        "python",
        "api",
        "automation",
        "dashboard",
        "linux",
        "c#",
        ".net",
        "angular",
        "aws",
        "domain driven",
        "test driven",
    ]:
        assert missing_keyword not in cover_letter


def test_safety_reminders_stay_outside_cover_letter() -> None:
    packet = generate_application_packet(_fei_score_result())

    assert REVIEW_WARNING in packet["risk_notes"]
    assert any("only where your resume/profile supports them" in item for item in packet["application_checklist"])
    assert REVIEW_WARNING not in packet["cover_letter_draft"]


def test_cover_letter_includes_company_mission_reason_when_available() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, and documentation.",
    )
    cover_letter = packet["cover_letter_draft"]

    assert "health and human services" in cover_letter
    assert "support people who depend on those services" in cover_letter
    assert "database-backed systems" in cover_letter
    assert "version control" in cover_letter
    assert "remote collaboration" in cover_letter


def test_packet_highlights_fei_hard_requirements_to_verify() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, documentation, git, and SQL.",
    )
    focus_text = " ".join(packet["resume_focus_areas"])
    risk_text = " ".join(packet["risk_notes"])

    assert "Strong / supported overlap" in focus_text
    assert "Git/version control" in focus_text
    assert "SQL/database work" in focus_text
    assert "Major requirements to verify" in focus_text
    assert "C# / .NET 5+" in focus_text
    assert "Angular 16+" in focus_text
    assert "TypeScript" in focus_text
    assert "AWS serverless" in risk_text
    assert "Domain Driven Design" in risk_text
    assert "Service Oriented Architecture" in risk_text
    assert "Unit testing" in risk_text
    assert "Test Driven Development" in risk_text


def test_packet_does_not_list_unrelated_config_keywords_as_fei_gaps() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, documentation, git, and SQL.",
    )
    gap_text = " ".join(packet["keywords_to_avoid_or_verify"]).lower()

    assert "python" not in gap_text
    assert "dashboard" not in gap_text
    assert "linux" not in gap_text


def test_packet_marks_fei_role_as_stretch_when_hard_requirements_are_unsupported() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, documentation, git, and SQL.",
    )
    packet_text = " ".join(packet["resume_focus_areas"] + packet["risk_notes"])

    assert "stretch full-stack developer role" in packet_text
    assert "C#/.NET" in packet_text
    assert "Angular/TypeScript" in packet_text
    assert "cloud/serverless" in packet_text
    assert "testing" in packet_text
    assert "architecture" in packet_text
