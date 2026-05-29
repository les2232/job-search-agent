"""Load local candidate profiles without mixing private application data."""

from pathlib import Path
import json
import re


DEFAULT_PROFILE_ID = "default"


def safe_profile_id(name: object) -> str:
    """Return a safe profile id for folders and CLI use."""
    if not isinstance(name, str):
        return DEFAULT_PROFILE_ID

    text = name.strip().lower()
    if not text:
        return DEFAULT_PROFILE_ID

    profile_id = re.sub(r"[^a-z0-9]+", "-", text)
    profile_id = re.sub(r"-+", "-", profile_id).strip("-")
    return profile_id or DEFAULT_PROFILE_ID


def list_profiles(
    profile_root: str | Path = "profiles",
    local_profile_root: str | Path = "local_profiles",
) -> list[dict[str, object]]:
    """List committed demo profiles and ignored local profiles."""
    profiles_by_id: dict[str, dict[str, object]] = {}

    for root, is_local in (
        (Path(profile_root), False),
        (Path(local_profile_root), True),
    ):
        if not root.exists():
            continue
        for profile_dir in sorted(path for path in root.iterdir() if path.is_dir()):
            profile = _load_profile_dir(profile_dir, is_local)
            if profile is None:
                continue
            profiles_by_id[str(profile["profile_id"])] = profile

    return sorted(
        profiles_by_id.values(),
        key=lambda profile: (
            str(profile["profile_id"]) != DEFAULT_PROFILE_ID,
            str(profile["display_name"]).lower(),
        ),
    )


def load_profile(
    profile_id: str = DEFAULT_PROFILE_ID,
    profile_root: str | Path = "profiles",
    local_profile_root: str | Path = "local_profiles",
) -> dict[str, object]:
    """Load one profile, preferring ignored local profiles over committed profiles."""
    normalized_id = safe_profile_id(profile_id)

    for root, is_local in (
        (Path(local_profile_root), True),
        (Path(profile_root), False),
    ):
        profile_dir = root / normalized_id
        profile = _load_profile_dir(profile_dir, is_local)
        if profile is not None:
            return profile

    raise FileNotFoundError(
        f"Profile '{profile_id}' was not found. Create local_profiles/{normalized_id}/ "
        "or use --profile default."
    )


def get_default_profile(
    profile_root: str | Path = "profiles",
    local_profile_root: str | Path = "local_profiles",
) -> dict[str, object]:
    """Load the default profile."""
    return load_profile(DEFAULT_PROFILE_ID, profile_root, local_profile_root)


def profile_applications_dir(
    applications_root: str | Path,
    profile: dict[str, object],
) -> Path:
    """Return the application packet root for a profile."""
    return Path(applications_root) / safe_profile_id(profile.get("profile_id"))


def _load_profile_dir(
    profile_dir: Path,
    is_local: bool,
) -> dict[str, object] | None:
    metadata_path = profile_dir / "profile.json"
    if not metadata_path.exists():
        return None

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(metadata, dict):
        return None

    profile_id = safe_profile_id(metadata.get("profile_id") or profile_dir.name)
    display_name = _safe_text(metadata.get("display_name"), profile_id)
    resume_path = profile_dir / "resume_base.md"
    resume_text = _read_optional_text(resume_path)

    target_roles = metadata.get("target_roles")
    if not isinstance(target_roles, list):
        target_roles = []

    return {
        "profile_id": profile_id,
        "display_name": display_name,
        "target_roles": [str(role) for role in target_roles if str(role).strip()],
        "notes": _safe_text(metadata.get("notes"), ""),
        "profile_path": profile_dir,
        "resume_path": resume_path,
        "resume_text": resume_text,
        "is_default": profile_id == DEFAULT_PROFILE_ID,
        "is_local": is_local,
        "source": "local" if is_local else "committed",
    }


def _safe_text(value: object, fallback: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    return value.strip()


def _read_optional_text(path: Path) -> str | None:
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None
    return text
