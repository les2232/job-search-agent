from job_scorer import NEGATIVE_KEYWORDS, POSITIVE_KEYWORDS, score_job


def test_score_job_clamps_to_100() -> None:
    job = {"raw_text": " ".join(POSITIVE_KEYWORDS)}

    assert score_job(job)["score"] == 100


def test_score_job_clamps_to_0() -> None:
    job = {"raw_text": " ".join(NEGATIVE_KEYWORDS)}

    assert score_job(job)["score"] == 0


def test_score_job_uses_custom_scoring_config() -> None:
    config = {
        "starting_score": 40,
        "positive_keyword_points": 20,
        "concern_keyword_penalty": 15,
        "apply_threshold": 70,
        "maybe_threshold": 50,
        "positive_keywords": ["python", "remote"],
        "concern_keywords": ["senior"],
    }
    job = {"raw_text": "Remote Python role with senior ownership."}

    score_details = score_job(job, config)

    assert score_details["score"] == 65
    assert score_details["recommendation"] == "Maybe"
    assert score_details["matched_keywords"] == ["python", "remote"]
    assert score_details["concerns"] == ["senior"]


def test_score_job_includes_high_score_explanation() -> None:
    job = {
        "title": "Junior Python Analyst",
        "company": "Example Studio",
        "location": "Remote",
        "work_mode": "Remote",
        "raw_text": " ".join(POSITIVE_KEYWORDS),
    }

    score_details = score_job(job)
    explanation = score_details["explanation"]

    assert score_details["recommendation"] == "Apply"
    assert "100/100" in explanation["fit_summary"]
    assert any("Matched fit keywords" in item for item in explanation["strengths"])
    assert any("Generate an application packet" in item for item in explanation["tailoring_suggestions"])


def test_score_job_includes_medium_score_explanation() -> None:
    config = {
        "starting_score": 50,
        "positive_keyword_points": 5,
        "concern_keyword_penalty": 8,
        "apply_threshold": 75,
        "maybe_threshold": 60,
        "positive_keywords": ["python", "sql", "remote"],
        "concern_keywords": ["senior"],
    }
    job = {
        "title": "Support Analyst",
        "company": "Example Studio",
        "location": "Remote",
        "work_mode": "Remote",
        "raw_text": "Python SQL support role.",
    }

    score_details = score_job(job, config)
    explanation = score_details["explanation"]

    assert score_details["score"] == 60
    assert score_details["recommendation"] == "Maybe"
    assert "gaps should be reviewed before applying" in explanation["fit_summary"]
    assert "remote" in score_details["missing_keywords"]


def test_score_job_includes_low_score_explanation() -> None:
    job = {
        "title": "Senior Sales Lead",
        "company": "Example Studio",
        "location": "Unknown",
        "work_mode": "Unknown",
        "raw_text": "Senior sales commission role with on-call expectations.",
    }

    score_details = score_job(job)
    explanation = score_details["explanation"]

    assert score_details["recommendation"] == "Skip"
    assert "may require skills or experience" in explanation["fit_summary"]
    assert any("Concern keywords found" in item for item in explanation["concerns"])


def test_score_job_explanation_mentions_unknown_metadata() -> None:
    job = {"raw_text": "Python documentation support role."}

    score_details = score_job(job)
    explanation = score_details["explanation"]

    assert any(
        "Job metadata did not parse cleanly" in item
        for item in explanation["concerns"]
    )
    assert any(
        "Work mode was not clearly detected" in item
        for item in explanation["concerns"]
    )


def test_score_job_explanation_does_not_include_full_raw_text() -> None:
    raw_text = "Python support role. " + ("private details " * 100)
    job = {
        "title": "Support Analyst",
        "company": "Example Studio",
        "location": "Remote",
        "work_mode": "Remote",
        "raw_text": raw_text,
    }

    explanation_text = str(score_job(job)["explanation"])

    assert raw_text not in explanation_text
    assert "private details" not in explanation_text
