"""Run the first milestone of the local job search agent."""

from pathlib import Path

from job_parser import parse_job_text
from job_scorer import score_job
from tracker import save_job_result


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_JOB_PATH = PROJECT_ROOT / "data" / "sample_job.txt"
JOBS_CSV_PATH = PROJECT_ROOT / "data" / "jobs.csv"


def main() -> None:
    job_text = read_sample_job(SAMPLE_JOB_PATH)
    job = parse_job_text(job_text)
    score_details = score_job(job)

    print_summary(job, score_details)
    save_job_result(JOBS_CSV_PATH, job, score_details)
    print(f"\nSaved result to: {JOBS_CSV_PATH}")


def read_sample_job(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Could not find sample job file: {path}")
    return path.read_text(encoding="utf-8")


def print_summary(job: dict[str, str], score_details: dict[str, object]) -> None:
    matched_keywords = _format_list(score_details["matched_keywords"])
    concerns = _format_list(score_details["concerns"])

    print("Job Search Agent - Milestone 1")
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
    main()
