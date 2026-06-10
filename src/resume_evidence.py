"""Normalize profile and proof data into resume tailoring evidence items."""

from pathlib import Path
import re

from profile_manager import parse_proof_blocks


WRAPPER_KEYS = ["evidence", "items", "proof", "proof_blocks", "projects", "experience"]
SKILL_KEYS = ["skills", "skill", "tags", "tools", "target_role_tags"]
SECTION_KEYS = ["sections", "section"]
EVIDENCE_KEYS = ["evidence", "description", "summary", "name"]
BULLET_KEYS = ["resume_bullet", "resumeBullet", "bullet"]
SOURCE_KEYS = ["source", "category", "type"]
DEFAULT_SOURCE = "profile"


def normalize_evidence_item(raw_item: object) -> dict[str, object]:
    """Return one normalized evidence item, or an empty dict if unusable."""
    if not isinstance(raw_item, dict):
        return {}

    skills = _first_string_list(raw_item, SKILL_KEYS)
    sections = _first_string_list(raw_item, SECTION_KEYS)
    evidence = _first_text(raw_item, EVIDENCE_KEYS)
    resume_bullet = _first_text(raw_item, BULLET_KEYS)
    source = _first_text(raw_item, SOURCE_KEYS) or _source_from_shape(raw_item)
    evidence_id = _first_text(raw_item, ["id", "evidence_id", "evidenceId"])

    if not resume_bullet:
        resume_bullet = _first_bullet(raw_item.get("bullets"))
    if not evidence:
        evidence = resume_bullet
    if not skills:
        skills = _first_string_list(raw_item, ["tools"])
    if not sections:
        sections = _default_sections(source)
    if not evidence and not resume_bullet and not skills:
        return {}

    stable_text = evidence_id or evidence or resume_bullet or " ".join(skills)
    return {
        "id": evidence_id or _safe_id(stable_text),
        "skills": skills,
        "sections": sections,
        "evidence": evidence,
        "resume_bullet": resume_bullet,
        "source": source or DEFAULT_SOURCE,
    }


def build_profile_evidence(profile_data: object) -> list[dict[str, object]]:
    """Build normalized evidence items from profile dictionaries or item lists."""
    raw_items = _profile_items(profile_data)
    normalized_items = []
    seen_ids = set()
    for raw_item in raw_items:
        item = normalize_evidence_item(raw_item)
        if not item:
            continue
        item_id = str(item["id"])
        if item_id in seen_ids:
            item = {**item, "id": _unique_id(item_id, seen_ids)}
        seen_ids.add(str(item["id"]))
        normalized_items.append(item)
    return normalized_items


def extract_resume_bullets_from_text(resume_text: object) -> list[dict[str, object]]:
    """Extract simple bullet evidence from resume text without inventing skills."""
    if not isinstance(resume_text, str) or not resume_text.strip():
        return []
    items = []
    current_section = ""
    for line in resume_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            current_section = stripped.lstrip("#").strip()
            continue
        if not stripped.startswith(("- ", "* ")):
            continue
        bullet = stripped[2:].strip()
        if not bullet:
            continue
        items.append(
            normalize_evidence_item(
                {
                    "id": _safe_id(bullet),
                    "sections": [current_section] if current_section else ["Resume"],
                    "evidence": bullet,
                    "resume_bullet": bullet,
                    "source": "resume_bullet",
                }
            )
        )
    return [item for item in items if item]


def load_profile_evidence_from_path(profile_path: str | Path) -> list[dict[str, object]]:
    """Load evidence from an existing profile directory or resume markdown file."""
    path = Path(profile_path)
    resume_path = path / "resume_base.md" if path.is_dir() else path
    if not resume_path.exists():
        return []
    resume_text = resume_path.read_text(encoding="utf-8")
    proof_items = build_profile_evidence({"proof_blocks": parse_proof_blocks(resume_text)})
    bullet_items = extract_resume_bullets_from_text(resume_text)
    return proof_items + [
        item for item in bullet_items if str(item.get("id")) not in {str(proof.get("id")) for proof in proof_items}
    ]


def _profile_items(profile_data: object) -> list[object]:
    if isinstance(profile_data, list):
        return profile_data
    if not isinstance(profile_data, dict):
        return []

    items = []
    for key in WRAPPER_KEYS:
        value = profile_data.get(key)
        if isinstance(value, list):
            items.extend(value)
        elif isinstance(value, dict):
            items.append(value)
    skills = profile_data.get("skills")
    if isinstance(skills, list):
        items.append(
            {
                "id": "profile_skills",
                "skills": skills,
                "sections": ["Technical Skills"],
                "evidence": "Profile skills list.",
                "source": "skills",
            }
        )
    resume_text = profile_data.get("resume_text")
    if isinstance(resume_text, str):
        items.extend(extract_resume_bullets_from_text(resume_text))
    return items


def _first_text(raw_item: dict[str, object], keys: list[str]) -> str:
    for key in keys:
        value = raw_item.get(key)
        if isinstance(value, str) and value.strip():
            return " ".join(value.split())
    return ""


def _first_string_list(raw_item: dict[str, object], keys: list[str]) -> list[str]:
    for key in keys:
        value = raw_item.get(key)
        values = _string_list(value)
        if values:
            return values
    return []


def _string_list(value: object) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _first_bullet(value: object) -> str:
    values = _string_list(value)
    return values[0] if values else ""


def _source_from_shape(raw_item: dict[str, object]) -> str:
    if "bullets" in raw_item or "tools" in raw_item:
        return "project"
    return DEFAULT_SOURCE


def _default_sections(source: str) -> list[str]:
    if source == "project":
        return ["Projects"]
    if source == "skills":
        return ["Technical Skills"]
    return ["Resume"]


def _safe_id(value: object) -> str:
    text = str(value or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80] or "evidence"


def _unique_id(base_id: str, seen_ids: set[str]) -> str:
    counter = 2
    while f"{base_id}-{counter}" in seen_ids:
        counter += 1
    return f"{base_id}-{counter}"
