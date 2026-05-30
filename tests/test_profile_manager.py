import json
from pathlib import Path

import pytest

from application_packet import generate_application_packet
from profile_manager import (
    append_proof_block,
    format_proof_block,
    get_default_profile,
    list_profiles,
    load_profile,
    parse_proof_blocks,
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

    assert any("Python" in item for item in packet["keywords_to_include_honestly"])
    assert len(packet["resume_bullet_suggestions"]) >= 3


def test_profile_applications_dir_uses_profile_id(tmp_path: Path) -> None:
    profile = {"profile_id": "Leslie Profile"}

    path = profile_applications_dir(tmp_path / "applications", profile)

    assert path == tmp_path / "applications" / "leslie-profile"


def test_parse_proof_blocks_reads_project_names_tools_and_bullets() -> None:
    resume_text = """
# Profile

## Project Evidence / Proof Library

### Job Search Automation Tool

**Tools / Skills:** Python, Streamlit, JSON, pytest

* Built a local-first packet generator.
* Added smoke tests and validation checks.

### IT Support Assistant

**Tools / Skills:** Python, Flask, SQLite, OpenAI API
**Use Carefully:** Do not claim production AI engineering.
**Target Role Tags:** AI automation, support engineering

* Developed support assistant workflows.

## Skills To Use Carefully
"""

    blocks = parse_proof_blocks(resume_text)

    assert [block["name"] for block in blocks] == [
        "Job Search Automation Tool",
        "IT Support Assistant",
    ]
    assert blocks[0]["tools"] == ["Python", "Streamlit", "JSON", "pytest"]
    assert blocks[0]["bullets"] == [
        "Built a local-first packet generator.",
        "Added smoke tests and validation checks.",
    ]
    assert blocks[1]["use_carefully_notes"] == "Do not claim production AI engineering."
    assert blocks[1]["target_role_tags"] == ["AI automation", "support engineering"]


def test_parse_proof_blocks_handles_missing_section_gracefully() -> None:
    assert parse_proof_blocks("# Profile\n\nNo proof library yet.") == []


def test_append_proof_block_preserves_existing_profile_text(tmp_path: Path) -> None:
    resume_path = tmp_path / "resume_base.md"
    resume_path.write_text("# Profile\n\nExisting notes.", encoding="utf-8")

    append_proof_block(
        resume_path,
        "Job Search Automation Tool",
        "Python, Streamlit, pytest",
        ["Built a local-first packet generator."],
        use_carefully_notes="Do not overstate production experience.",
        target_role_tags="automation, tooling",
    )
    text = resume_path.read_text(encoding="utf-8")
    blocks = parse_proof_blocks(text)

    assert "Existing notes." in text
    assert "## Project Evidence / Proof Library" in text
    assert blocks[0]["name"] == "Job Search Automation Tool"
    assert blocks[0]["tools"] == ["Python", "Streamlit", "pytest"]
    assert blocks[0]["bullets"] == ["Built a local-first packet generator."]


def test_format_proof_block_normalizes_text_fields() -> None:
    block = format_proof_block(
        "TradeOS / Dashboard Project",
        ["Python", "Streamlit", "Pandas"],
        "* Built dashboard tooling.\n- Added reporting.",
    )

    assert "### TradeOS / Dashboard Project" in block
    assert "**Tools / Skills:** Python, Streamlit, Pandas" in block
    assert "* Built dashboard tooling." in block
    assert "* Added reporting." in block
