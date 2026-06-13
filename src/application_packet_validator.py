"""Validate saved application packet folders without modifying them."""

from pathlib import Path


REQUIRED_PACKET_FILES = [
    "packet_index.md",
    "tailored_resume.md",
    "packet.json",
]
OPTIONAL_PACKET_FILES = [
    "resume_tailoring_notes.md",
    "cover_letter_draft.md",
    "recruiter_message.txt",
    "application_checklist.md",
    "job_summary.md",
    "score_explanation.md",
]


def validate_saved_packet_folder(packet_folder: str | Path) -> dict[str, object]:
    """Return deterministic validation details for a saved packet folder."""
    packet_path = Path(packet_folder)
    warnings = []

    if not packet_path.exists():
        warnings.append(f"Packet folder does not exist: {packet_path}")
    elif not packet_path.is_dir():
        warnings.append(f"Packet path is not a folder: {packet_path}")

    present_files = _present_files(packet_path) if packet_path.is_dir() else []
    missing_required_files = [
        filename for filename in REQUIRED_PACKET_FILES if filename not in present_files
    ]
    missing_optional_files = [
        filename for filename in OPTIONAL_PACKET_FILES if filename not in present_files
    ]

    if missing_required_files:
        warnings.append(
            "Missing required packet file(s): " + ", ".join(missing_required_files)
        )
    if missing_optional_files:
        warnings.append(
            "Missing optional packet file(s): " + ", ".join(missing_optional_files)
        )

    return {
        "packet_path": packet_path,
        "present_files": present_files,
        "missing_required_files": missing_required_files,
        "missing_optional_files": missing_optional_files,
        "is_valid": not missing_required_files and packet_path.is_dir(),
        "warnings": warnings,
    }


def _present_files(packet_path: Path) -> list[str]:
    expected_files = REQUIRED_PACKET_FILES + OPTIONAL_PACKET_FILES
    return [filename for filename in expected_files if (packet_path / filename).is_file()]
