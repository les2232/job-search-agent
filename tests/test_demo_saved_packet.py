from pathlib import Path
from zipfile import ZipFile

from application_packet_export import build_saved_packet_zip
from application_packet_validator import validate_saved_packet_folder


DEMO_PACKET_PATH = Path("docs/demo_saved_packet")


def test_demo_saved_packet_validates_successfully() -> None:
    result = validate_saved_packet_folder(DEMO_PACKET_PATH)

    assert result["is_valid"] is True
    assert result["missing_required_files"] == []
    assert result["present_files"] == [
        "packet_index.md",
        "tailored_resume.md",
        "packet.json",
        "application_checklist.md",
        "job_summary.md",
    ]


def test_demo_saved_packet_exports_known_files_only(tmp_path) -> None:
    zip_path = tmp_path / "demo_saved_packet.zip"
    zip_path.write_bytes(build_saved_packet_zip(DEMO_PACKET_PATH))

    with ZipFile(zip_path) as archive:
        assert archive.namelist() == [
            "packet_index.md",
            "tailored_resume.md",
            "packet.json",
            "application_checklist.md",
            "job_summary.md",
        ]
