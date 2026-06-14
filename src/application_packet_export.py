"""Export saved application packet folders without regenerating content."""

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile
from zipfile import ZipInfo

from application_packet_validator import OPTIONAL_PACKET_FILES
from application_packet_validator import REQUIRED_PACKET_FILES
from application_packet_validator import validate_saved_packet_folder


ZIP_PACKET_FILES = REQUIRED_PACKET_FILES + OPTIONAL_PACKET_FILES
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def build_saved_packet_zip(packet_folder_path: str | Path) -> bytes:
    """Return a deterministic ZIP containing known saved packet files."""
    packet_path = Path(packet_folder_path)
    validation = validate_saved_packet_folder(packet_path)

    if not packet_path.exists():
        raise ValueError(
            f"Cannot export saved packet ZIP: packet folder does not exist: {packet_path}"
        )
    if not packet_path.is_dir():
        raise ValueError(
            f"Cannot export saved packet ZIP: packet path is not a folder: {packet_path}"
        )

    missing_required = validation.get("missing_required_files")
    if isinstance(missing_required, list) and missing_required:
        missing_text = ", ".join(str(filename) for filename in missing_required)
        raise ValueError(
            f"Cannot export saved packet ZIP: missing required files: {missing_text}"
        )

    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for filename in ZIP_PACKET_FILES:
            file_path = packet_path / filename
            if not file_path.is_file():
                continue
            info = ZipInfo(filename=filename, date_time=ZIP_TIMESTAMP)
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, file_path.read_bytes())

    return buffer.getvalue()
