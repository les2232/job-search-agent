from pathlib import Path

from application_packet_validator import OPTIONAL_PACKET_FILES
from application_packet_validator import REQUIRED_PACKET_FILES
from main import main
from tracker import save_job_result


def _write_packet_files(packet_folder: Path, filenames: list[str]) -> None:
    packet_folder.mkdir(parents=True)
    for filename in filenames:
        (packet_folder / filename).write_text("present", encoding="utf-8")


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


def test_main_profile_option_requires_value(tmp_path: Path, capsys) -> None:
    jobs_csv_path = tmp_path / "jobs.csv"

    exit_code = main(["--profile"], jobs_csv_path=jobs_csv_path)

    assert exit_code == 1
    assert "--profile requires a profile id" in capsys.readouterr().out
    assert not jobs_csv_path.exists()


def test_validate_packet_command_valid_folder_exits_zero(tmp_path: Path, capsys) -> None:
    packet_folder = tmp_path / "packet"
    _write_packet_files(packet_folder, REQUIRED_PACKET_FILES + OPTIONAL_PACKET_FILES)

    exit_code = main(["--validate-packet", str(packet_folder)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert f"Saved packet validation: {packet_folder}" in output
    assert "Status: valid" in output
    assert "- packet_index.md: present" in output
    assert "- tailored_resume.md: present" in output
    assert "- packet.json: present" in output
    assert "Missing required files:" not in output


def test_validate_packet_command_missing_required_exits_nonzero(
    tmp_path: Path,
    capsys,
) -> None:
    packet_folder = tmp_path / "packet"
    _write_packet_files(packet_folder, ["packet_index.md", "tailored_resume.md"])

    exit_code = main(["--validate-packet", str(packet_folder)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Status: invalid" in output
    assert "Required files:" in output
    assert "- packet.json: missing" in output
    assert "Missing required files:" in output
    assert "- packet.json" in output


def test_validate_packet_command_nonexistent_folder_exits_nonzero(
    tmp_path: Path,
    capsys,
) -> None:
    packet_folder = tmp_path / "missing"

    exit_code = main(["--validate-packet", str(packet_folder)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Status: invalid" in output
    assert "Packet folder does not exist" in output
    assert "- packet_index.md: missing" in output
    assert "- packet.json" in output


def test_validate_packet_command_reports_optional_files_in_order(
    tmp_path: Path,
    capsys,
) -> None:
    packet_folder = tmp_path / "packet"
    _write_packet_files(
        packet_folder,
        REQUIRED_PACKET_FILES + ["cover_letter_draft.md", "job_summary.md"],
    )

    exit_code = main(["--validate-packet", str(packet_folder)])
    output = capsys.readouterr().out
    optional_block = output.split("Optional files:", 1)[1].split(
        "Missing optional files:",
        1,
    )[0]
    optional_lines = [line for line in optional_block.splitlines() if line.startswith("- ")]

    assert exit_code == 0
    assert "Missing optional files:" in output
    assert optional_lines == [
        "- resume_tailoring_notes.md: missing",
        "- cover_letter_draft.md: present",
        "- recruiter_message.txt: missing",
        "- application_checklist.md: missing",
        "- job_summary.md: present",
        "- score_explanation.md: missing",
    ]
