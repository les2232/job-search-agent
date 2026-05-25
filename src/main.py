"""Run the local job search agent."""

import argparse
from pathlib import Path

from job_parser import parse_job_text
from job_scorer import score_job
from tracker import load_job_results, save_job_result


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_JOB_PATH = PROJECT_ROOT / "data" / "sample_job.txt"
JOBS_CSV_PATH = PROJECT_ROOT / "data" / "jobs.csv"
APPLICATION_STATUSES = ["saved", "applied", "interview", "rejected", "follow_up"]


def main() -> None:
    args = parse_args()

    if args.command == "list":
        jobs = load_job_results(JOBS_CSV_PATH, recommendation=args.recommendation)
        print_saved_jobs(jobs)
        return

    job_path = Path(args.job_file)
    job_text = read_job_file(job_path)
    job = parse_job_text(job_text)
    score_details = score_job(job)

    print_summary(job, score_details)
    save_job_result(JOBS_CSV_PATH, job, score_details, status=args.status)
    print(f"\nSaved result to: {JOBS_CSV_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score job postings and track promising opportunities."
    )
    subparsers = parser.add_subparsers(dest="command")

    score_parser = subparsers.add_parser("score", help="Score a job posting file.")
    score_parser.add_argument(
        "--job-file",
        default=str(SAMPLE_JOB_PATH),
        help="Path to a plain-text job posting. Defaults to data/sample_job.txt.",
    )
    score_parser.add_argument(
        "--status",
        choices=APPLICATION_STATUSES,
        default="saved",
        help="Initial tracker status for this job.",
    )

    list_parser = subparsers.add_parser("list", help="List saved job results.")
    list_parser.add_argument(
        "--recommendation",
        choices=["Apply", "Maybe", "Skip"],
        help="Only show jobs with this recommendation.",
    )

    args = parser.parse_args()
    if args.command is None:
        args.command = "score"
        args.job_file = str(SAMPLE_JOB_PATH)
        args.status = "saved"

    return args


def read_job_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Could not find job file: {path}")
    return path.read_text(encoding="utf-8")


def print_summary(job: dict[str, str], score_details: dict[str, object]) -> None:
    matched_keywords = _format_list(score_details["matched_keywords"])
    missing_keywords = _format_list(score_details["missing_keywords"])
    concerns = _format_list(score_details["concerns"])
    breakdown = score_details["breakdown"]

    print("Job Search Agent - Milestone 2")
    print("=" * 30)
    print(f"Title: {job['title']}")
    print(f"Company: {job['company']}")
    print(f"Location: {job['location']}")
    print()
    print(f"Score: {score_details['score']}/100")
    print(f"Recommendation: {score_details['recommendation']}")
    print()
    print("Score breakdown")
    print(f"- Skills match: {breakdown['skills_match']}")
    print(f"- Work-style fit: {breakdown['work_style_fit']}")
    print(f"- Growth fit: {breakdown['growth_fit']}")
    print(f"- Concern penalty: -{breakdown['concern_penalty']}")
    print()
    print(f"Matched keywords: {matched_keywords}")
    print(f"Missing priority keywords: {missing_keywords}")
    print(f"Concerns: {concerns}")


def print_saved_jobs(jobs: list[dict[str, str]]) -> None:
    print("Saved Jobs")
    print("=" * 30)

    if not jobs:
        print("No saved jobs found yet.")
        return

    for index, job in enumerate(jobs, start=1):
        print(f"{index}. {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        print(f"   Location: {job.get('location', 'Unknown')}")
        print(
            "   "
            f"Score: {job.get('score', 'N/A')} | "
            f"Recommendation: {job.get('recommendation', 'N/A')} | "
            f"Status: {job.get('status', 'saved')}"
        )


def _format_list(value: object) -> str:
    if isinstance(value, list) and value:
        return ", ".join(str(item) for item in value)
    return "None"


if __name__ == "__main__":
    main()
