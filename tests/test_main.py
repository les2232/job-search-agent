from pathlib import Path

from main import main
from tracker import save_job_result


def test_main_missing_file_exits_without_writing_csv(
    tmp_path: Path,
    capsys,
) -> None:
    missing_job_path = tmp_path / "missing_job.txt"
    jobs_csv_path = tmp_path / "jobs.csv"

    exit_code = main([str(missing_job_path)], jobs_csv_path=jobs_csv_path)

    assert exit_code == 1
    assert "Could not find job posting file" in capsys.readouterr().out
    assert not jobs_csv_path.exists()


def test_main_list_reports_no_tracker_file(tmp_path: Path, capsys) -> None:
    jobs_csv_path = tmp_path / "jobs.csv"

    exit_code = main(["list"], jobs_csv_path=jobs_csv_path)

    assert exit_code == 0
    assert "No tracked jobs found" in capsys.readouterr().out


def test_main_list_prints_tracked_jobs(tmp_path: Path, capsys) -> None:
    jobs_csv_path = tmp_path / "jobs.csv"
    save_job_result(
        jobs_csv_path,
        {
            "title": "Junior Python Analyst",
            "company": "Example Studio",
            "location": "Remote",
            "raw_text": "Python analyst role",
        },
        {
            "score": 85,
            "recommendation": "Apply",
            "matched_keywords": ["python"],
            "concerns": [],
        },
    )

    exit_code = main(["list"], jobs_csv_path=jobs_csv_path)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Junior Python Analyst at Example Studio" in output
    assert "Recommendation: Apply" in output
