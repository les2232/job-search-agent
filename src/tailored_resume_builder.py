"""Build deterministic Markdown resume drafts from tailoring plans."""


OUTPUT_KEYS = [
    "markdown",
    "included_sections",
    "selected_bullet_count",
    "warnings",
    "gaps",
    "metadata",
]


def build_tailored_resume_draft(
    tailoring_plan: object,
    base_resume: object = None,
    profile: object = None,
) -> dict[str, object]:
    """Return a portable Markdown resume draft from verified tailoring output."""
    plan = tailoring_plan if isinstance(tailoring_plan, dict) else {}
    skills = _string_list(plan.get("skills_to_emphasize"))
    sections = _string_list(plan.get("sections_to_prioritize"))
    bullets = _selected_bullets(plan.get("selected_bullets"))
    matched_requirements = _match_requirement_lines(plan.get("matched_evidence"))
    weak_matches = _match_requirement_lines(plan.get("weak_matches"))
    warnings = _string_list(plan.get("review_warnings"))
    gaps = _string_list(plan.get("gaps"))
    summary = _safe_text(plan.get("tailoring_summary"))
    profile_name = _profile_name(profile)
    emphasis = _suggested_emphasis(skills, sections)

    included_sections = [
        "Tailored Resume Draft",
        "Candidate Summary",
        "Target Role Alignment",
        "Matched Requirements",
        "Strong Evidence Bullets",
        "Gaps or Weak Matches",
        "Suggested Resume Emphasis",
        "Review Warnings",
        "Human Review Checklist",
    ]

    markdown = "\n".join(
        [
            "# Tailored Resume Draft",
            "",
            (
                f"Candidate: {profile_name}"
                if profile_name
                else "Candidate: Add your name during human review."
            ),
            "",
            (
                "Human review required: verify every selected bullet against your "
                "real experience before applying."
            ),
            "",
            "## Candidate Summary",
            "",
            (
                f"{profile_name}: review and adapt this draft using only verified evidence."
                if profile_name
                else "Add a candidate summary during human review using only verified evidence."
            ),
            "",
            "## Target Role Alignment",
            "",
            summary or "No tailoring summary was provided.",
            "",
            "## Matched Requirements",
            "",
            _markdown_bullets(matched_requirements, "No matched requirements were found."),
            "",
            "## Strong Evidence Bullets",
            "",
            _markdown_bullets(bullets, "No verified resume bullets were selected."),
            "",
            "## Gaps or Weak Matches",
            "",
            _markdown_bullets(
                weak_matches + gaps,
                "No weak matches or evidence gaps were reported.",
            ),
            "",
            "## Suggested Resume Emphasis",
            "",
            _markdown_bullets(emphasis, "No resume emphasis areas were selected."),
            "",
            "## Review Warnings",
            "",
            _markdown_bullets(warnings, "No review warnings were provided."),
            "",
            "## Human Review Checklist",
            "",
            "\n".join(
                [
                    "- Confirm each bullet is true, specific, and interview-ready.",
                    "- Remove any bullet that is not backed by verified evidence.",
                    "- Add metrics only if you can substantiate them.",
                    "- Confirm the final resume matches the target role without overstating experience.",
                ]
            ),
            "",
        ]
    )

    return {
        "markdown": markdown,
        "included_sections": included_sections,
        "selected_bullet_count": len(bullets),
        "warnings": warnings,
        "gaps": gaps,
        "metadata": {
            "builder": "tailored_resume_builder_v1",
            "base_resume_supplied": bool(_safe_text(base_resume)),
            "profile_supplied": isinstance(profile, dict),
            "skills_to_emphasize_count": len(skills),
            "matched_requirement_count": len(matched_requirements),
            "weak_match_count": len(weak_matches),
        },
    }


def _selected_bullets(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    bullets = []
    for item in value:
        bullet = ""
        if isinstance(item, str):
            bullet = item
        elif isinstance(item, dict):
            bullet = _safe_text(item.get("bullet")) or _safe_text(item.get("resume_bullet"))
        bullet = " ".join(bullet.split())
        if bullet and bullet not in bullets:
            bullets.append(bullet)
    return bullets


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    values = []
    for item in value:
        text = _safe_text(item)
        if text and text not in values:
            values.append(text)
    return values


def _match_requirement_lines(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    lines = []
    for item in value:
        if not isinstance(item, dict):
            continue
        requirement = _safe_text(item.get("requirement"))
        evidence = _safe_text(item.get("resume_bullet")) or _safe_text(item.get("evidence"))
        if requirement and evidence:
            line = f"{requirement}: {evidence}"
        else:
            line = requirement or evidence
        if line and line not in lines:
            lines.append(line)
    return lines


def _suggested_emphasis(skills: list[str], sections: list[str]) -> list[str]:
    emphasis = []
    for skill in skills:
        emphasis.append(f"Emphasize {skill} only where existing evidence supports it.")
    for section in sections:
        emphasis.append(f"Review the {section} section for relevant supported examples.")
    return emphasis


def _safe_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _profile_name(profile: object) -> str:
    if not isinstance(profile, dict):
        return ""
    for key in ["display_name", "name", "candidate_name"]:
        value = _safe_text(profile.get(key))
        if value:
            return value
    return ""


def _markdown_bullets(values: list[str], fallback: str) -> str:
    if not values:
        return f"- {fallback}"
    return "\n".join(f"- {value}" for value in values)
