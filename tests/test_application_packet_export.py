from io import BytesIO
from zipfile import ZipFile

import pytest

from application_packet_export import build_saved_packet_zip
from application_packet_validator import OPTIONAL_PACKET_FILES
from application_packet_validator import REQUIRED_PACKET_FILES


def _write_packet_file(packet_folder, filename: str, content: str = "present") -> None:
    (packet_folder / filename).write_text(content, encoding="utf-8")


def _zip_names(zip_bytes: bytes) -> list[str]:
    with ZipFile(BytesIO(zip_bytes)) as archive:
        return archive.namelist()


def test_saved_packet_zip_includes_known_files_in_deterministic_order(tmp_path) -> None:
    packet_folder = tmp_path / "packet"
    packet_folder.mkdir()
    for filename in REQUIRED_PACKET_FILES + OPTIONAL_PACKET_FILES:
        _write_packet_file(packet_folder, filename, filename)

    first_zip = build_saved_packet_zip(packet_folder)
    second_zip = build_saved_packet_zip(packet_folder)

    assert first_zip == second_zip
    assert _zip_names(first_zip) == REQUIRED_PACKET_FILES + OPTIONAL_PACKET_FILES


def test_saved_packet_zip_uses_relative_filenames_only(tmp_path) -> None:
    packet_folder = tmp_path / "packet"
    packet_folder.mkdir()
    for filename in REQUIRED_PACKET_FILES:
        _write_packet_file(packet_folder, filename)

    zip_bytes = build_saved_packet_zip(packet_folder)

    with ZipFile(BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            assert name in REQUIRED_PACKET_FILES
            assert "/" not in name
            assert "\\" not in name
            assert str(tmp_path) not in name


def test_saved_packet_zip_skips_missing_optional_files(tmp_path) -> None:
    packet_folder = tmp_path / "packet"
    packet_folder.mkdir()
    for filename in REQUIRED_PACKET_FILES:
        _write_packet_file(packet_folder, filename)
    _write_packet_file(packet_folder, "cover_letter_draft.md")

    zip_bytes = build_saved_packet_zip(packet_folder)

    assert _zip_names(zip_bytes) == REQUIRED_PACKET_FILES + ["cover_letter_draft.md"]


def test_saved_packet_zip_excludes_unknown_private_and_hidden_files(tmp_path) -> None:
    packet_folder = tmp_path / "packet"
    packet_folder.mkdir()
    for filename in REQUIRED_PACKET_FILES:
        _write_packet_file(packet_folder, filename)
    _write_packet_file(packet_folder, "notes.md", "private notes")
    _write_packet_file(packet_folder, ".env", "SECRET=value")
    (packet_folder / "local_profiles").mkdir()
    _write_packet_file(packet_folder / "local_profiles", "profile.md", "private")

    zip_bytes = build_saved_packet_zip(packet_folder)

    assert _zip_names(zip_bytes) == REQUIRED_PACKET_FILES


def test_saved_packet_zip_reports_nonexistent_folder(tmp_path) -> None:
    with pytest.raises(ValueError, match="packet folder does not exist"):
        build_saved_packet_zip(tmp_path / "missing")


def test_saved_packet_zip_reports_missing_required_files(tmp_path) -> None:
    packet_folder = tmp_path / "packet"
    packet_folder.mkdir()
    _write_packet_file(packet_folder, "packet_index.md")
    _write_packet_file(packet_folder, "packet.json")

    with pytest.raises(ValueError, match="missing required files: tailored_resume.md"):
        build_saved_packet_zip(packet_folder)
