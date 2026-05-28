import csv
from datetime import date
from pathlib import Path

from tracker import CSV_FIELDS
from tracker import filter_tracked_jobs
from tracker import read_tracked_jobs
from tracker import repair_tracker
from tracker import save_job_result
from tracker import update_job_status
from tracker import write_tracker_rows


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


def test_read_tracked_jobs_returns_empty_list_for_missing_file(
    tmp_path: Path,
) -> None:
    assert read_tracked_jobs(tmp_path / "missing_jobs.csv") == []


def test_read_tracked_jobs_returns_saved_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "jobs.csv"
    save_job_result(csv_path, _sample_job(), _sample_score())

    rows = read_tracked_jobs(csv_path)

    assert len(rows) == 1
    assert rows[0]["title"] == "Junior Python Analyst"
    assert rows[0]["company"] == "Example Studio"
    assert set(rows[0]) == set(CSV_FIELDS)


def test_filter_tracked_jobs_by_status_case_insensitive() -> None:
    rows = [
        {"status": "New", "recommendation": "Apply"},
        {"status": "Applied", "recommendation": "Apply"},
    ]

    filtered_rows = filter_tracked_jobs(rows, status="new")

    assert filtered_rows == [{"status": "New", "recommendation": "Apply"}]


def test_filter_tracked_jobs_by_recommendation_case_insensitive() -> None:
    rows = [
        {"status": "New", "recommendation": "Apply"},
        {"status": "New", "recommendation": "Maybe"},
    ]

    filtered_rows = filter_tracked_jobs(rows, recommendation="apply")

    assert filtered_rows == [{"status": "New", "recommendation": "Apply"}]


def test_update_job_status_updates_matching_job(tmp_path: Path) -> None:
    csv_path = tmp_path / "jobs.csv"
    save_job_result(csv_path, _sample_job(), _sample_score())

    result = update_job_status(
        csv_path,
        "junior python analyst",
        "example studio",
        "Applied",
    )
    rows = read_tracked_jobs(csv_path)

    assert result["updated"] is True
    assert rows[0]["status"] == "Applied"
    assert rows[0]["title"] == "Junior Python Analyst"


def test_update_job_status_returns_no_match(tmp_path: Path) -> None:
    csv_path = tmp_path / "jobs.csv"
    save_job_result(csv_path, _sample_job(), _sample_score())

    result = update_job_status(csv_path, "Other Role", "Other Company", "Applied")
    rows = read_tracked_jobs(csv_path)

    assert result["updated"] is False
    assert "No tracked job matched" in str(result["message"])
    assert rows[0]["status"] == "New"


def test_repair_tracker_removes_duplicate_header_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "jobs.csv"
    rows = [_sample_tracker_row(), dict(zip(CSV_FIELDS, CSV_FIELDS))]
    write_tracker_rows(csv_path, rows)

    result = repair_tracker(csv_path)
    repaired_rows = read_tracked_jobs(csv_path)

    assert result["duplicate_header_rows_removed"] == 1
    assert result["rows_written"] == 1
    assert repaired_rows == [_sample_tracker_row()]
    assert Path(str(result["backup_path"])).exists()


def test_repair_tracker_dedupes_repeated_title_and_company(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "jobs.csv"
    first_row = _sample_tracker_row(status="New")
    duplicate_row = _sample_tracker_row(status="Applied")
    write_tracker_rows(csv_path, [first_row, duplicate_row])

    result = repair_tracker(csv_path)
    repaired_rows = read_tracked_jobs(csv_path)

    assert result["duplicate_jobs_removed"] == 1
    assert result["rows_written"] == 1
    assert repaired_rows[0]["status"] == "New"


def _sample_tracker_row(status: str = "New") -> dict[str, str]:
    return {
        "title": "Junior Python Analyst",
        "company": "Example Studio",
        "location": "Remote",
        "score": "85",
        "recommendation": "Apply",
        "status": status,
        "notes": "",
        "source_url": "",
        "date_found": date.today().isoformat(),
        "follow_up_date": "",
    }
