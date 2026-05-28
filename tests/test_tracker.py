import csv
from datetime import date
from pathlib import Path

from tracker import CSV_FIELDS, save_job_result


def _sample_job() -> dict[str, str]:
    return {
        "title": "Junior Python Analyst",
        "company": "Example Studio",
        "location": "Remote",
        "raw_text": "Python analyst role",
    }


def _sample_score() -> dict[str, object]:
    return {
        "score": 85,
        "recommendation": "Apply",
        "matched_keywords": ["python"],
        "concerns": [],
    }


def test_save_job_result_creates_header(tmp_path: Path) -> None:
    csv_path = tmp_path / "jobs.csv"

    save_job_result(csv_path, _sample_job(), _sample_score())

    first_line = csv_path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == ",".join(CSV_FIELDS)


def test_save_job_result_appends_new_job_with_defaults(tmp_path: Path) -> None:
    csv_path = tmp_path / "jobs.csv"

    result = save_job_result(csv_path, _sample_job(), _sample_score())

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert result["saved"] is True
    assert len(rows) == 1
    assert rows[0]["title"] == "Junior Python Analyst"
    assert rows[0]["company"] == "Example Studio"
    assert rows[0]["status"] == "New"
    assert rows[0]["notes"] == ""
    assert rows[0]["source_url"] == ""
    assert rows[0]["date_found"] == date.today().isoformat()
    assert rows[0]["follow_up_date"] == ""


def test_save_job_result_skips_duplicate_title_and_company(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "jobs.csv"
    job = _sample_job()
    score = _sample_score()

    first_result = save_job_result(csv_path, job, score)
    second_result = save_job_result(csv_path, job, score)

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert first_result["saved"] is True
    assert second_result["saved"] is False
    assert "Already tracked" in str(second_result["message"])
    assert len(rows) == 1
