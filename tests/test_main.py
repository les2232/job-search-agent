from pathlib import Path

from main import main


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
