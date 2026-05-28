"""Run the local job search agent."""

from pathlib import Path
import sys

from application_generator import generate_application_materials
from job_parser import parse_job_text
from job_scorer import score_job
from tracker import filter_tracked_jobs
from tracker import read_tracked_jobs
from tracker import repair_tracker
from tracker import save_job_result
from tracker import update_job_status


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_JOB_PATH = PROJECT_ROOT / "data" / "sample_job.txt"
JOBS_CSV_PATH = PROJECT_ROOT / "data" / "jobs.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"


def main(argv: list[str] | None = None, jobs_csv_path: Path = JOBS_CSV_PATH) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "generate-application":
        return generate_application_command(args[1:])
    if args and args[0] == "list":
        return list_command(args[1:], jobs_csv_path)
    if args and args[0] == "update-status":
        return update_status_command(args[1:], jobs_csv_path)
    if args and args[0] == "repair-tracker":
        return repair_tracker_command(jobs_csv_path)

    job_path = _get_job_path(args)

    try:
        job_text = read_job_text(job_path)
    except FileNotFoundError:
        print(f"Error: Could not find job posting file: {job_path}")
        return 1
    except ValueError as error:
        print(f"Error: {error}")
        return 1

    job = parse_job_text(job_text)
    score_details = score_job(job)

    print_summary(job, score_details)
    save_result = save_job_result(jobs_csv_path, job, score_details)
    print(f"\n{save_result['message']}")
    return 0


def list_command(args: list[str], jobs_csv_path: Path) -> int:
    status = _get_option(args, "--status")
    recommendation = _get_option(args, "--recommendation")

    if _has_unknown_args(args, {"--status", "--recommendation"}):
        print("Error: Use python .\\src\\main.py list [--status New] [--recommendation Apply]")
        return 1

    rows = read_tracked_jobs(jobs_csv_path)
    if not rows:
        print(f"No tracked jobs found at: {jobs_csv_path}")
        return 0

    rows = filter_tracked_jobs(rows, status=status, recommendation=recommendation)
    if not rows:
        print("No tracked jobs matched those filters.")
        return 0

    print(f"Tracked Jobs ({len(rows)})")
    print("=" * 30)
    for index, row in enumerate(rows, start=1):
        print(f"{index}. {row['title']} at {row['company']}")
        print(f"   Location: {row['location']}")
        print(f"   Score: {row['score']}")
        print(f"   Recommendation: {row['recommendation']}")
        print(f"   Status: {row['status']}")
        print(f"   Date found: {row['date_found']}")
        print(f"   Follow up: {row['follow_up_date'] or 'None'}")

    return 0


def update_status_command(args: list[str], jobs_csv_path: Path) -> int:
    title = _get_option(args, "--title")
    company = _get_option(args, "--company")
    status = _get_option(args, "--status")

    if (
        title is None
        or company is None
        or status is None
        or _has_unknown_args(args, {"--title", "--company", "--status"})
    ):
        print(
            "Error: Use "
            "python .\\src\\main.py update-status --title \"Job Title\" "
            "--company \"Company\" --status Applied"
        )
        return 1

    result = update_job_status(jobs_csv_path, title, company, status)
    print(result["message"])
    return 0


def repair_tracker_command(jobs_csv_path: Path) -> int:
    result = repair_tracker(jobs_csv_path)

    print(result["message"])
    if not result["repaired"]:
        return 0

    print(f"Backup path: {result['backup_path']}")
    print(f"Rows read: {result['rows_read']}")
    print(
        "Duplicate header rows removed: "
        f"{result['duplicate_header_rows_removed']}"
    )
    print(f"Duplicate jobs removed: {result['duplicate_jobs_removed']}")
    print(f"Rows written: {result['rows_written']}")
    return 0


def generate_application_command(args: list[str]) -> int:
    if len(args) != 3 or args[1] != "--resume":
        print(
            "Error: Use "
            "python .\\src\\main.py generate-application "
            ".\\path\\to\\job.txt --resume .\\data\\profile\\resume_base.md"
        )
        return 1

    job_path = Path(args[0])
    resume_path = Path(args[2])

    try:
        result = generate_application_materials(job_path, resume_path, OUTPUT_DIR)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}")
        return 1

    output_paths = result["output_paths"]
    matching_keywords = result["matching_keywords"]

    print("Generated application drafts")
    print("=" * 30)
    print(f"Matching keywords: {_format_list(matching_keywords)}")
    print(f"Output folder: {result['output_dir']}")
    print(f"Resume draft: {output_paths['resume']}")
    print(f"Cover letter draft: {output_paths['cover_letter']}")
    print(f"Match notes: {output_paths['match_notes']}")
    print(f"Job posting copy: {output_paths['job_posting']}")
    print()
    print(
        "Draft only. Review carefully before using. "
        "Do not include claims you cannot verify."
    )
    return 0


def _get_option(args: list[str], name: str) -> str | None:
    if name not in args:
        return None

    index = args.index(name)
    if index + 1 >= len(args):
        return None

    value = args[index + 1]
    if value.startswith("--"):
        return None

    return value


def _has_unknown_args(args: list[str], allowed_options: set[str]) -> bool:
    index = 0
    while index < len(args):
        option = args[index]
        if option not in allowed_options:
            return True
        if index + 1 >= len(args) or args[index + 1].startswith("--"):
            return True
        index += 2
    return False


def _get_job_path(args: list[str]) -> Path:
    if not args:
        return SAMPLE_JOB_PATH
    return Path(args[0])


def read_sample_job(path: Path) -> str:
    return read_job_text(path)


def read_job_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Could not find job posting file: {path}")

    job_text = path.read_text(encoding="utf-8")
    if not job_text.strip():
        raise ValueError(f"Job posting file is empty: {path}")

    return job_text


def print_summary(job: dict[str, str], score_details: dict[str, object]) -> None:
    matched_keywords = _format_list(score_details["matched_keywords"])
    concerns = _format_list(score_details["concerns"])

    print("Job Search Agent")
    print("=" * 30)
    print(f"Title: {job['title']}")
    print(f"Company: {job['company']}")
    print(f"Location: {job['location']}")
    print()
    print(f"Score: {score_details['score']}/100")
    print(f"Recommendation: {score_details['recommendation']}")
    print(f"Matched keywords: {matched_keywords}")
    print(f"Concerns: {concerns}")


def _format_list(value: object) -> str:
    if isinstance(value, list) and value:
        return ", ".join(str(item) for item in value)
    return "None"


if __name__ == "__main__":
    raise SystemExit(main())
