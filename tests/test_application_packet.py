from application_packet import REVIEW_WARNING, generate_application_packet


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
            "title": "Full-Stack Developer",
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
    assert "Draft only" not in cover_letter
    assert "verify" not in cover_letter.lower()
    assert "tailor my resume" not in cover_letter.lower()
    assert "Remote / Remote" not in cover_letter


def test_maybe_cover_letter_is_polished_but_cautious() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, and documentation.",
    )
    cover_letter = packet["cover_letter_draft"]

    assert "I would welcome the chance to learn more" in cover_letter
    assert "technical support background could be useful" in cover_letter
    assert "Maybe" not in cover_letter


def test_cover_letter_does_not_claim_missing_keywords_as_experience() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, and documentation.",
    )
    cover_letter = packet["cover_letter_draft"].lower()

    for missing_keyword in ["python", "api", "automation", "dashboard", "data", "linux"]:
        assert missing_keyword not in cover_letter


def test_safety_reminders_stay_outside_cover_letter() -> None:
    packet = generate_application_packet(_fei_score_result())

    assert REVIEW_WARNING in packet["risk_notes"]
    assert any("only where your resume/profile supports them" in item for item in packet["application_checklist"])
    assert REVIEW_WARNING not in packet["cover_letter_draft"]
