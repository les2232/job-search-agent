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
        "proof_blocks": parse_proof_blocks(resume_text),
        "is_default": profile_id == DEFAULT_PROFILE_ID,
        "is_local": is_local,
        "source": "local" if is_local else "committed",
    }


def parse_proof_blocks(resume_text: str | None) -> list[dict[str, object]]:
    """Parse simple Markdown proof blocks from resume_base.md text."""
    if not resume_text:
        return []

    section = _proof_library_section(resume_text)
    if not section:
        return []

    blocks = []
    current_name = ""
    current_lines: list[str] = []
    for line in section.splitlines():
        if line.startswith("### "):
            if current_name:
                blocks.append(_parse_proof_block(current_name, current_lines))
            current_name = line.replace("### ", "", 1).strip()
            current_lines = []
        elif current_name:
            current_lines.append(line)
    if current_name:
        blocks.append(_parse_proof_block(current_name, current_lines))

    return [block for block in blocks if str(block["name"]).strip()]


def append_proof_block(
    resume_path: str | Path,
    name: str,
    tools: str | list[str],
    bullets: str | list[str],
    use_carefully_notes: str = "",
    target_role_tags: str = "",
) -> None:
    """Append a Markdown proof block to a private resume_base.md file."""
    path = Path(resume_path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    proof_block = format_proof_block(
        name,
        tools,
        bullets,
        use_carefully_notes=use_carefully_notes,
        target_role_tags=target_role_tags,
    )
    if "## Project Evidence / Proof Library" not in text:
        section_intro = "\n".join(
            [
                "## Project Evidence / Proof Library",
                "",
                (
                    "Use these proof blocks as evidence anchors for tailored resumes "
                    "and cover letters. Do not include every project in every resume. "
                    "Select only the projects that match the target job and only use "
                    "claims that can be explained in an interview."
                ),
                "",
            ]
        )
        new_text = _join_markdown(text, section_intro + proof_block)
    else:
        new_text = _join_markdown(text, proof_block)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")


def format_proof_block(
    name: str,
    tools: str | list[str],
    bullets: str | list[str],
    use_carefully_notes: str = "",
    target_role_tags: str = "",
) -> str:
    """Return a Markdown proof block."""
    clean_name = _safe_text(name, "Untitled Proof Block")
    tool_text = _format_inline_values(tools)
    bullet_values = _normalize_bullets(bullets)
    lines = [
        f"### {clean_name}",
        "",
        f"**Tools / Skills:** {tool_text}",
        "",
    ]
    if target_role_tags.strip():
        lines.extend([f"**Target Role Tags:** {target_role_tags.strip()}", ""])
    if use_carefully_notes.strip():
        lines.extend([f"**Use Carefully:** {use_carefully_notes.strip()}", ""])
    lines.extend([f"* {bullet}" for bullet in bullet_values])
    return "\n".join(lines).strip() + "\n"


def _proof_library_section(resume_text: str) -> str:
    lines = resume_text.splitlines()
    start_index = None
    for index, line in enumerate(lines):
        if line.strip() == "## Project Evidence / Proof Library":
            start_index = index + 1
            break
    if start_index is None:
        return ""

    section_lines = []
    for line in lines[start_index:]:
        if line.startswith("## ") and line.strip() != "## Project Evidence / Proof Library":
            break
        section_lines.append(line)
    return "\n".join(section_lines)


def _parse_proof_block(name: str, lines: list[str]) -> dict[str, object]:
    tools: list[str] = []
    bullets: list[str] = []
    use_carefully_notes = ""
    target_role_tags: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**Tools / Skills:**"):
            tools = _split_inline_values(stripped.replace("**Tools / Skills:**", "", 1))
        elif stripped.startswith("**Use Carefully:**"):
            use_carefully_notes = stripped.replace("**Use Carefully:**", "", 1).strip()
        elif stripped.startswith("**Target Role Tags:**"):
            target_role_tags = _split_inline_values(stripped.replace("**Target Role Tags:**", "", 1))
        elif stripped.startswith(("* ", "- ")):
            bullets.append(stripped[2:].strip())

    raw_lines = [f"### {name}", *lines]
    return {
        "name": name,
        "tools": tools,
        "bullets": bullets,
        "use_carefully_notes": use_carefully_notes,
        "target_role_tags": target_role_tags,
        "raw_text": "\n".join(raw_lines).strip(),
    }


def _split_inline_values(value: str) -> list[str]:
    return [item.strip().rstrip(".") for item in value.split(",") if item.strip()]


def _format_inline_values(values: str | list[str]) -> str:
    if isinstance(values, list):
        return ", ".join(str(value).strip() for value in values if str(value).strip())
    return values.strip()


def _normalize_bullets(values: str | list[str]) -> list[str]:
    if isinstance(values, list):
        bullets = [str(value).strip().lstrip("*- ").strip() for value in values]
    else:
        bullets = [
            line.strip().lstrip("*- ").strip()
            for line in values.splitlines()
        ]
    return [bullet for bullet in bullets if bullet]


def _join_markdown(existing_text: str, addition: str) -> str:
    existing = existing_text.rstrip()
    if not existing:
        return addition.strip() + "\n"
    return existing + "\n\n" + addition.strip() + "\n"


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
