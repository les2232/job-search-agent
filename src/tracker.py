"""Save scored jobs to a local CSV tracker."""

import csv
from datetime import date
from pathlib import Path


CSV_FIELDS = [
    "title",
    "company",
    "location",
    "score",
    "recommendation",
    "status",
    "notes",
    "source_url",
    "date_found",
    "follow_up_date",
]


def save_job_result(
    csv_path: Path,
    job: dict[str, str],
    score_details: dict[str, object],
) -> dict[str, object]:
    """Append a scored job result to the tracker CSV."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_csv_header(csv_path)

    if _job_already_tracked(csv_path, job):
        return {
            "saved": False,
            "message": (
                f"Already tracked: {job['title']} at {job['company']}. "
                "Skipped duplicate."
            ),
        }

    should_write_header = not csv_path.exists() or csv_path.stat().st_size == 0

    row = {
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "score": score_details["score"],
        "recommendation": score_details["recommendation"],
        "status": "New",
        "notes": "",
        "source_url": "",
        "date_found": date.today().isoformat(),
        "follow_up_date": "",
    }

    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        if should_write_header:
            writer.writeheader()
        writer.writerow(row)

    return {
        "saved": True,
        "message": f"Saved result to: {csv_path}",
    }


def _job_already_tracked(csv_path: Path, job: dict[str, str]) -> bool:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return False

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            if _same_job(row, job):
                return True

    return False


def _same_job(row: dict[str, str], job: dict[str, str]) -> bool:
    return (
        _normalize(row.get("title", "")) == _normalize(job["title"])
        and _normalize(row.get("company", "")) == _normalize(job["company"])
    )


def _normalize(value: str) -> str:
    return value.strip().lower()


def _ensure_csv_header(csv_path: Path) -> None:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return

    first_line = csv_path.read_text(encoding="utf-8").splitlines()[0]
    expected_header = ",".join(CSV_FIELDS)
    if first_line == expected_header:
        return

    existing_text = csv_path.read_text(encoding="utf-8")
    csv_path.write_text(f"{expected_header}\n{existing_text}", encoding="utf-8")
