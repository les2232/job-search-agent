"""Save scored jobs to a local CSV tracker."""

import csv
from datetime import date
from datetime import datetime
from pathlib import Path
import shutil


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


def read_tracked_jobs(csv_path: Path) -> list[dict[str, str]]:
    """Return tracked jobs from the local CSV, or an empty list."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return []

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = []
        for row in reader:
            rows.append({field: row.get(field, "") for field in CSV_FIELDS})

    return rows


def filter_tracked_jobs(
    rows: list[dict[str, str]],
    status: str | None = None,
    recommendation: str | None = None,
) -> list[dict[str, str]]:
    """Filter tracked jobs by status and/or recommendation."""
    filtered_rows = rows

    if status is not None:
        filtered_rows = [
            row
            for row in filtered_rows
            if _normalize(row.get("status", "")) == _normalize(status)
        ]

    if recommendation is not None:
        filtered_rows = [
            row
            for row in filtered_rows
            if _normalize(row.get("recommendation", ""))
            == _normalize(recommendation)
        ]

    return filtered_rows


def update_job_status(
    csv_path: Path,
    title: str,
    company: str,
    status: str,
) -> dict[str, object]:
    """Update the status for a tracked job matched by title and company."""
    rows = read_tracked_jobs(csv_path)
    if not rows:
        return {
            "updated": False,
            "message": f"No tracked jobs found at: {csv_path}",
        }

    updated = False
    for row in rows:
        if _same_title_and_company(row, title, company):
            row["status"] = status
            updated = True
            break

    if not updated:
        return {
            "updated": False,
            "message": f"No tracked job matched: {title} at {company}",
        }

    write_tracker_rows(csv_path, rows)
    return {
        "updated": True,
        "message": f"Updated status for {title} at {company} to {status}.",
    }


def repair_tracker(csv_path: Path) -> dict[str, object]:
    """Repair the local tracker CSV and create a backup first."""
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return {
            "repaired": False,
            "message": f"No tracker found at: {csv_path}",
            "backup_path": "",
            "rows_read": 0,
            "duplicate_header_rows_removed": 0,
            "duplicate_jobs_removed": 0,
            "rows_written": 0,
        }

    backup_path = _backup_tracker(csv_path)
    raw_rows = _read_raw_tracker_rows(csv_path)
    repaired_rows = []
    seen_jobs = set()
    duplicate_header_rows_removed = 0
    duplicate_jobs_removed = 0

    for raw_row in raw_rows:
        row = _normalize_tracker_row(raw_row)

        if _is_duplicate_header_row(row):
            duplicate_header_rows_removed += 1
            continue

        job_key = _job_key(row)
        if job_key in seen_jobs:
            duplicate_jobs_removed += 1
            continue

        seen_jobs.add(job_key)
        repaired_rows.append(row)

    write_tracker_rows(csv_path, repaired_rows)

    return {
        "repaired": True,
        "message": f"Repaired tracker: {csv_path}",
        "backup_path": str(backup_path),
        "rows_read": len(raw_rows),
        "duplicate_header_rows_removed": duplicate_header_rows_removed,
        "duplicate_jobs_removed": duplicate_jobs_removed,
        "rows_written": len(repaired_rows),
    }


def write_tracker_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
    """Write normalized tracker rows using the current CSV schema."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(_normalize_tracker_row(row))


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
    return _same_title_and_company(row, job["title"], job["company"])


def _same_title_and_company(row: dict[str, str], title: str, company: str) -> bool:
    return (
        _normalize(row.get("title", "")) == _normalize(title)
        and _normalize(row.get("company", "")) == _normalize(company)
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


def _backup_tracker(csv_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = csv_path.with_name(f"{csv_path.stem}_backup_{timestamp}.csv")
    shutil.copy2(csv_path, backup_path)
    return backup_path


def _read_raw_tracker_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _normalize_tracker_row(row: dict[str, str]) -> dict[str, str]:
    return {field: row.get(field, "") for field in CSV_FIELDS}


def _is_duplicate_header_row(row: dict[str, str]) -> bool:
    return all(row.get(field, "") == field for field in CSV_FIELDS)


def _job_key(row: dict[str, str]) -> tuple[str, str]:
    return (_normalize(row.get("title", "")), _normalize(row.get("company", "")))
