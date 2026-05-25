"""Save and read scored jobs from a local CSV tracker."""

import csv
from pathlib import Path


CSV_FIELDS = [
    "title",
    "company",
    "location",
    "score",
    "recommendation",
    "status",
    "skills_match",
    "work_style_fit",
    "growth_fit",
    "concern_penalty",
    "matched_keywords",
    "missing_keywords",
    "concerns",
]


def save_job_result(
    csv_path: Path,
    job: dict[str, str],
    score_details: dict[str, object],
    status: str = "saved",
) -> None:
    """Append a scored job result to the tracker CSV."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    should_write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    breakdown = score_details["breakdown"]

    row = {
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "score": score_details["score"],
        "recommendation": score_details["recommendation"],
        "status": status,
        "skills_match": breakdown["skills_match"],
        "work_style_fit": breakdown["work_style_fit"],
        "growth_fit": breakdown["growth_fit"],
        "concern_penalty": breakdown["concern_penalty"],
        "matched_keywords": _join_list(score_details["matched_keywords"]),
        "missing_keywords": _join_list(score_details["missing_keywords"]),
        "concerns": _join_list(score_details["concerns"]),
    }

    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        if should_write_header:
            writer.writeheader()
        writer.writerow(row)


def load_job_results(
    csv_path: Path,
    recommendation: str | None = None,
) -> list[dict[str, str]]:
    """Load saved job results from the tracker CSV."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return []

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    if recommendation is None:
        return rows

    return [row for row in rows if row.get("recommendation") == recommendation]


def _join_list(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
