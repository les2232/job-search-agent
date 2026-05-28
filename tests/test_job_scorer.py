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
