"""Run the local job search agent."""

from pathlib import Path
import sys

from job_parser import parse_job_text
from job_scorer import score_job
from tracker import save_job_result


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_JOB_PATH = PROJECT_ROOT / "data" / "sample_job.txt"
JOBS_CSV_PATH = PROJECT_ROOT / "data" / "jobs.csv"


def main(argv: list[str] | None = None, jobs_csv_path: Path = JOBS_CSV_PATH) -> int:
    args = sys.argv[1:] if argv is None else argv
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

    print("Job Search Agent - Milestone 4")
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
