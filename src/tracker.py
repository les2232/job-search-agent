"""Save scored jobs to a local CSV tracker."""

import csv
from pathlib import Path


CSV_FIELDS = [
    "title",
    "company",
    "location",
    "score",
    "recommendation",
    "matched_keywords",
    "concerns",
]


def save_job_result(
    csv_path: Path,
    job: dict[str, str],
    score_details: dict[str, object],
) -> None:
    """Append a scored job result to the tracker CSV."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_csv_header(csv_path)
    should_write_header = not csv_path.exists() or csv_path.stat().st_size == 0

    row = {
        "title": job["title"],
        "company": job["company"],
        "location": job["location"],
        "score": score_details["score"],
        "recommendation": score_details["recommendation"],
        "matched_keywords": _join_list(score_details["matched_keywords"]),
        "concerns": _join_list(score_details["concerns"]),
    }

    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        if should_write_header:
            writer.writeheader()
        writer.writerow(row)


def _ensure_csv_header(csv_path: Path) -> None:
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return

    first_line = csv_path.read_text(encoding="utf-8").splitlines()[0]
    expected_header = ",".join(CSV_FIELDS)
    if first_line == expected_header:
        return

    existing_text = csv_path.read_text(encoding="utf-8")
    csv_path.write_text(f"{expected_header}\n{existing_text}", encoding="utf-8")


def _join_list(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
