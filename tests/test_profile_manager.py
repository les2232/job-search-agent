import json
from pathlib import Path

import pytest

from application_packet import generate_application_packet
from profile_manager import (
    get_default_profile,
    list_profiles,
    load_profile,
    profile_applications_dir,
    safe_profile_id,
)


def _write_profile(
    root: Path,
    profile_id: str,
    display_name: str,
    resume_text: str = "Profile has Python support documentation.",
) -> Path:
    profile_dir = root / profile_id
    profile_dir.mkdir(parents=True)
    (profile_dir / "profile.json").write_text(
        json.dumps(
            {
                "profile_id": profile_id,
                "display_name": display_name,
                "target_roles": ["IT Support"],
                "notes": "Test profile.",
            }
        ),
        encoding="utf-8",
    )
    (profile_dir / "resume_base.md").write_text(resume_text, encoding="utf-8")
    return profile_dir


def _score_result() -> dict[str, object]:
    return {
        "job_metadata": {
            "title": "Junior Support Analyst",
            "company": "Example Studio",
            "location": "Remote",
            "work_mode": "Remote",
        },
        "score": 85,
        "recommendation": "Apply",
        "matched_keywords": ["python", "documentation"],
        "missing_keywords": [],
        "concerns": [],
        "explanation": {
            "fit_summary": "Strong match.",
            "strengths": [],
            "gaps": [],
            "concerns": [],
            "tailoring_suggestions": [],
        },
    }


def test_safe_profile_id_slugifies_names() -> None:
    assert safe_profile_id("Leslie Cordova!") == "leslie-cordova"
    assert safe_profile_id("!!!") == "default"
    assert safe_profile_id(None) == "default"


def test_profiles_can_be_listed(tmp_path: Path) -> None:
    profile_root = tmp_path / "profiles"
    local_root = tmp_path / "local_profiles"
    _write_profile(profile_root, "default", "Default Profile")
    _write_profile(local_root, "leslie", "Leslie Local Profile")

    profiles = list_profiles(profile_root, local_root)

    assert [profile["profile_id"] for profile in profiles] == ["default", "leslie"]
    assert profiles[1]["is_local"] is True


def test_default_profile_loads(tmp_path: Path) -> None:
    profile_root = tmp_path / "profiles"
    local_root = tmp_path / "local_profiles"
    _write_profile(profile_root, "default", "Default Profile")

    profile = get_default_profile(profile_root, local_root)

    assert profile["profile_id"] == "default"
    assert profile["display_name"] == "Default Profile"
    assert "Python support documentation" in str(profile["resume_text"])


def test_missing_profile_is_handled_clearly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Profile 'missing' was not found"):
        load_profile("missing", tmp_path / "profiles", tmp_path / "local_profiles")


def test_malformed_profile_is_skipped_safely(tmp_path: Path) -> None:
    profile_root = tmp_path / "profiles"
    broken_profile = profile_root / "broken"
    broken_profile.mkdir(parents=True)
    (broken_profile / "profile.json").write_text("{not json", encoding="utf-8")

    assert list_profiles(profile_root, tmp_path / "local_profiles") == []


def test_local_profile_overrides_committed_profile(tmp_path: Path) -> None:
    profile_root = tmp_path / "profiles"
    local_root = tmp_path / "local_profiles"
    _write_profile(profile_root, "default", "Committed Default")
    _write_profile(local_root, "default", "Local Default")

    profile = load_profile("default", profile_root, local_root)

    assert profile["display_name"] == "Local Default"
    assert profile["is_local"] is True


def test_profile_text_can_feed_packet_generation(tmp_path: Path) -> None:
    profile_root = tmp_path / "profiles"
    local_root = tmp_path / "local_profiles"
    _write_profile(
        profile_root,
        "default",
        "Default Profile",
        resume_text="Profile includes IT support, Python, Flask, and documentation.",
    )
    profile = load_profile("default", profile_root, local_root)

    packet = generate_application_packet(_score_result(), profile["resume_text"])

    assert "python" in packet["keywords_to_include_honestly"]
    assert len(packet["resume_bullet_suggestions"]) >= 3


def test_profile_applications_dir_uses_profile_id(tmp_path: Path) -> None:
    profile = {"profile_id": "Leslie Profile"}

    path = profile_applications_dir(tmp_path / "applications", profile)

    assert path == tmp_path / "applications" / "leslie-profile"
