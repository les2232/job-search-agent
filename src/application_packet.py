"""Build deterministic application packet guidance from a scored job."""


REVIEW_WARNING = (
    "Draft only. Review carefully before using. "
    "Do not include claims you cannot verify."
)

PROFILE_THEMES = {
    "frontline IT support": ["it support", "frontline", "technical support"],
    "classroom/AV troubleshooting": ["classroom", "av"],
    "endpoint/device support": ["endpoint", "device", "deployment"],
    "account/access support": ["account", "access", "active directory"],
    "ticket workflows": ["ticket", "workflow", "wrike"],
    "documentation": ["documentation", "documenting", "knowledge base"],
    "Python/Flask support tools": ["python", "flask"],
    "knowledge base design": ["knowledge base"],
    "training/onboarding tools": ["training", "onboarding", "assessment"],
}


def generate_application_packet(
    score_result: dict[str, object],
    profile_text: str | None = None,
) -> dict[str, object]:
    """Return reviewable, deterministic application guidance for a scored job."""
    metadata = _get_metadata(score_result)
    score = int(score_result.get("score", 0))
    recommendation = str(score_result.get("recommendation", "Skip"))
    matched_keywords = _as_string_list(score_result.get("matched_keywords"))
    missing_keywords = _as_string_list(score_result.get("missing_keywords"))
    concerns = _as_string_list(score_result.get("concerns"))
    explanation = score_result.get("explanation")
    explanation_concerns = _explanation_list(explanation, "concerns")
    source_text = _source_text(score_result)
    job_requirements = _job_requirements(score_result)

    profile_themes = _find_profile_themes(profile_text)
    role_label = _role_label(metadata)
    cover_role_label = _cover_role_label(role_label)
    company_label = _company_label(metadata)
    strongest_matches = _strongest_matches(matched_keywords, profile_themes)
    supported_overlap = _supported_overlap(
        matched_keywords,
        profile_themes,
        job_requirements,
        profile_text,
    )
    requirements_to_verify = _requirements_to_verify(
        job_requirements,
        matched_keywords,
        profile_text,
    )
    gaps_to_review = _gaps_to_review(
        missing_keywords,
        concerns,
        requirements_to_verify,
    )
    stretch_warning = _build_stretch_warning(requirements_to_verify)

    return {
        "positioning_summary": _build_positioning_summary(
            score,
            recommendation,
            role_label,
            company_label,
            strongest_matches,
            stretch_warning,
        ),
        "apply_recommendation": _build_apply_recommendation(
            recommendation,
            gaps_to_review,
        ),
        "resume_focus_areas": _build_resume_focus_areas(
            strongest_matches,
            gaps_to_review,
            profile_themes,
            supported_overlap,
            requirements_to_verify,
            stretch_warning,
        ),
        "resume_bullet_suggestions": _build_resume_bullet_suggestions(
            strongest_matches,
            profile_themes,
        ),
        "keywords_to_include_honestly": matched_keywords[:8],
        "keywords_to_avoid_or_verify": gaps_to_review[:8],
        "cover_letter_draft": _build_cover_letter_draft(
            cover_role_label,
            company_label,
            metadata,
            matched_keywords,
            profile_themes,
            recommendation,
            source_text,
        ),
        "recruiter_message": _build_recruiter_message(
            role_label,
            company_label,
            strongest_matches,
        ),
        "application_checklist": _build_application_checklist(recommendation),
        "risk_notes": _build_risk_notes(
            metadata,
            gaps_to_review,
            explanation_concerns,
            requirements_to_verify,
            stretch_warning,
        ),
    }


def _get_metadata(score_result: dict[str, object]) -> dict[str, str]:
    metadata = score_result.get("job_metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "title": _safe_metadata_value(metadata.get("title")),
        "company": _safe_metadata_value(metadata.get("company")),
        "location": _safe_metadata_value(metadata.get("location")),
        "work_mode": _safe_metadata_value(metadata.get("work_mode")),
    }


def _safe_metadata_value(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        return "Unknown"
    return value.strip()


def _role_label(metadata: dict[str, str]) -> str:
    if _is_known(metadata["title"]):
        return metadata["title"]
    return "this role"


def _company_label(metadata: dict[str, str]) -> str:
    if _is_known(metadata["company"]):
        return metadata["company"]
    return "the organization"


def _is_known(value: str) -> bool:
    return value.strip().lower() != "unknown"


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _source_text(score_result: dict[str, object]) -> str:
    for key in ["raw_text", "job_text", "job_description"]:
        value = score_result.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _job_requirements(score_result: dict[str, object]) -> dict[str, object]:
    value = score_result.get("job_requirements")
    if not isinstance(value, dict):
        return {}
    return value


def _explanation_list(explanation: object, key: str) -> list[str]:
    if not isinstance(explanation, dict):
        return []
    return _as_string_list(explanation.get(key))


def _find_profile_themes(profile_text: str | None) -> list[str]:
    if not profile_text:
        return []

    normalized = profile_text.lower()
    themes = []
    for theme, markers in PROFILE_THEMES.items():
        if any(marker in normalized for marker in markers):
            themes.append(theme)
    return themes


def _strongest_matches(
    matched_keywords: list[str],
    profile_themes: list[str],
) -> list[str]:
    matches = []
    for value in matched_keywords + profile_themes:
        if value not in matches:
            matches.append(value)
    return matches[:6]


def _gaps_to_review(
    missing_keywords: list[str],
    concerns: list[str],
    requirements_to_verify: list[str],
) -> list[str]:
    if requirements_to_verify:
        return requirements_to_verify

    gaps = []
    for value in missing_keywords + concerns:
        if value not in gaps:
            gaps.append(value)
    return gaps


def _build_positioning_summary(
    score: int,
    recommendation: str,
    role_label: str,
    company_label: str,
    strongest_matches: list[str],
    stretch_warning: str,
) -> str:
    if stretch_warning:
        return (
            f"{role_label} at {company_label} should be treated as a stretch "
            f"role. {stretch_warning}"
        )
    match_text = _format_inline_list(strongest_matches[:4], "the configured fit areas")
    if recommendation == "Apply":
        return (
            f"{role_label} at {company_label} looks like a strong target. "
            f"The score is supported by overlap with {match_text}; tailor the resume "
            "around verified examples before applying."
        )
    if recommendation == "Maybe":
        return (
            f"{role_label} at {company_label} may be worth applying to if you can "
            f"honestly support the main requirements. The clearest overlap is {match_text}."
        )
    return (
        f"{role_label} at {company_label} should be treated as lower priority unless "
        f"there is a strategic reason to pursue it. The current score shows limited "
        f"overlap with {match_text}."
    )


def _build_apply_recommendation(
    recommendation: str,
    gaps_to_review: list[str],
) -> str:
    if recommendation == "Apply":
        return "Apply after tailoring the resume and reviewing the packet for accuracy."
    if recommendation == "Maybe":
        return (
            "Maybe. Apply only if you can honestly address the gaps with real "
            "examples from your resume, projects, or work history."
        )
    if gaps_to_review:
        return (
            "Lower priority. Consider skipping unless the role is important enough "
            "to justify tailoring around the gaps."
        )
    return "Lower priority based on the current score."


def _build_resume_focus_areas(
    strongest_matches: list[str],
    gaps_to_review: list[str],
    profile_themes: list[str],
    supported_overlap: list[str],
    requirements_to_verify: list[str],
    stretch_warning: str,
) -> list[str]:
    focus_areas = []
    if supported_overlap:
        focus_areas.append(
            "Strong / supported overlap: "
            + _format_inline_list(supported_overlap[:8], "supported overlap")
            + "."
        )
    if requirements_to_verify:
        focus_areas.append(
            "Major requirements to verify: "
            + _format_inline_list(requirements_to_verify[:10], "role requirements")
            + "."
        )
    if stretch_warning:
        focus_areas.append("Stretch warning: " + stretch_warning)
    if strongest_matches:
        focus_areas.append(
            "Lead with verified experience related to: "
            + _format_inline_list(strongest_matches[:5], "your strongest matches")
            + "."
        )
    if profile_themes:
        focus_areas.append(
            "Use concrete examples from profile themes such as: "
            + _format_inline_list(profile_themes[:5], "your profile themes")
            + "."
        )
    if gaps_to_review:
        focus_areas.append(
            "Review before adding: "
            + _format_inline_list(gaps_to_review[:5], "potential gaps")
            + "."
        )
    if not focus_areas:
        focus_areas.append(
            "Use only resume/profile details you can verify, and keep the summary broad."
        )
    return focus_areas


def _build_resume_bullet_suggestions(
    strongest_matches: list[str],
    profile_themes: list[str],
) -> list[str]:
    matches = _format_inline_list(strongest_matches[:3], "the role requirements")
    bullets = [
        (
            "Suggested bullet: Supported users through frontline technical support, "
            "clear communication, and documented troubleshooting steps; replace with "
            "your exact verified scope."
        ),
        (
            "Suggested bullet: Troubleshot classroom, AV, endpoint, account/access, "
            "or workflow issues using examples that are already supported by your resume."
        ),
        (
            f"Suggested bullet: Tailored documentation or support workflows around "
            f"{matches}; keep only the keywords you can explain with real examples."
        ),
    ]

    if any("Python" in theme or "knowledge base" in theme for theme in profile_themes):
        bullets.append(
            "Suggested bullet: Built or organized Python/Flask support tools, "
            "knowledge base content, or guided support flows as a project or prototype."
        )
    if any("training" in theme for theme in profile_themes):
        bullets.append(
            "Suggested bullet: Created training, onboarding, checklist, or assessment "
            "materials to help users or new team members follow support workflows."
        )

    return bullets[:5]


def _build_cover_letter_draft(
    role_label: str,
    company_label: str,
    metadata: dict[str, str],
    matched_keywords: list[str],
    profile_themes: list[str],
    recommendation: str,
    source_text: str,
) -> str:
    company_reason = _build_company_reason(company_label, source_text)
    role_needs = _build_role_needs_sentence(matched_keywords)
    profile_strengths = _build_profile_strengths_sentence(profile_themes)
    maybe_note = _build_maybe_cover_letter_note(recommendation, role_label)

    return "\n".join(
        [
            "Dear Hiring Team,",
            "",
            (
                f"I am interested in the {role_label} role at {company_label}."
                f" {company_reason}"
            ),
            "",
            (
                f"My background includes {profile_strengths}. In those settings, "
                "I have worked to understand user needs, communicate clearly, and "
                "support technical workflows with careful follow-through. "
                f"{role_needs}"
            ),
            "",
            (
                "I would bring a service-minded technical perspective, strong "
                "documentation habits, and a practical approach to solving problems "
                "for users and teams."
                f"{maybe_note}"
            ),
            "",
            (
                "Thank you for your time and consideration. I would welcome the "
                f"opportunity to discuss how my technical background and interest "
                f"in this work could support {company_label}."
            ),
        ]
    )


def _build_maybe_cover_letter_note(recommendation: str, role_label: str) -> str:
    if recommendation != "Maybe":
        return ""
    return (
        f" I am interested in learning more about how {role_label} supports "
        "the team and where my background could be most useful."
    )


def _cover_role_label(role_label: str) -> str:
    if role_label == "this role":
        return role_label
    for separator in [" Who ", " who ", " With ", " with "]:
        if separator in role_label:
            return role_label.split(separator, 1)[0].strip()
    return role_label


def _build_company_reason(company_label: str, source_text: str) -> str:
    mission = _mission_context(source_text)
    if mission:
        return (
            f"I am drawn to {_possessive(company_label)} focus on {mission}, where reliable "
            "systems, clear communication, and thoughtful problem solving can "
            "support people who depend on those services."
        )
    return (
        "I am drawn to technical work where reliable systems, clear communication, "
        "and thoughtful problem solving help teams serve users well."
    )


def _mission_context(source_text: str) -> str:
    normalized = source_text.lower()
    if "health and human services" in normalized:
        return "building technology for health and human services"
    if "access to care" in normalized or "support" in normalized and "care" in normalized:
        return "improving access to care and support"
    if "case management" in normalized:
        return "case management software for public services"
    if "public" in normalized and ("service" in normalized or "impact" in normalized):
        return "mission-driven public-impact technology"
    return ""


def _possessive(value: str) -> str:
    if value.endswith("s"):
        return f"{value}'"
    return f"{value}'s"


def _build_role_needs_sentence(matched_keywords: list[str]) -> str:
    needs = _human_role_needs(matched_keywords)
    if not needs:
        return (
            "That experience connects with roles that require dependable technical "
            "work, collaboration, and clear documentation."
        )
    return (
        "That experience connects with the role's emphasis on "
        + _format_inline_list(needs[:3], "dependable technical work")
        + "."
    )


def _human_role_needs(matched_keywords: list[str]) -> list[str]:
    keyword_map = {
        "sql": "database-backed systems",
        "git": "version control",
        "remote": "remote collaboration",
        "documentation": "clear documentation",
        "troubleshooting": "practical troubleshooting",
        "support": "user support",
        "ticket": "structured support workflows",
    }
    needs = []
    for keyword in matched_keywords:
        need = keyword_map.get(keyword.lower())
        if need and need not in needs:
            needs.append(need)
    return needs


def _build_profile_strengths_sentence(profile_themes: list[str]) -> str:
    strengths = []
    for theme in [
        "frontline IT support",
        "user communication",
        "troubleshooting",
        "documentation",
        "classroom/AV troubleshooting",
        "ticket workflows",
    ]:
        if theme in profile_themes or theme in {"user communication", "troubleshooting"}:
            strengths.append(theme)
    if not strengths:
        return "technical support, user communication, troubleshooting, and documentation"
    return _format_inline_list(strengths[:4], "technical support")


def _build_recruiter_message(
    role_label: str,
    company_label: str,
    strongest_matches: list[str],
) -> str:
    match_text = _format_inline_list(strongest_matches[:2], "technical support")
    return (
        f"Hi, I am interested in {role_label} at {company_label}. My background "
        f"includes IT support, troubleshooting, documentation, and overlap with "
        f"{match_text}. I would appreciate the chance to learn more about the role."
    )


def _build_application_checklist(recommendation: str) -> list[str]:
    final_step = "Apply after review." if recommendation == "Apply" else "Decide whether to apply or skip."
    return [
        "Confirm the title, company, location, and work mode.",
        "Review gaps and concern keywords before tailoring.",
        "Tailor the resume summary around verified matched keywords.",
        "Add matched keywords only where your resume/profile supports them.",
        "Adjust project bullets if they are relevant and accurate.",
        "Write or revise the final cover letter in your own voice.",
        "Save the job posting and packet locally.",
        final_step,
    ]


def _build_risk_notes(
    metadata: dict[str, str],
    gaps_to_review: list[str],
    explanation_concerns: list[str],
    requirements_to_verify: list[str],
    stretch_warning: str,
) -> list[str]:
    risk_notes = [REVIEW_WARNING]
    unknown_fields = [
        label
        for label in ["title", "company", "location"]
        if not _is_known(metadata[label])
    ]
    if unknown_fields:
        risk_notes.append(
            "Confirm job metadata before applying: " + ", ".join(unknown_fields) + "."
        )
    if requirements_to_verify:
        risk_notes.append(
            "Major role requirements to verify before applying: "
            + _format_inline_list(requirements_to_verify[:12], "role requirements")
            + "."
        )
    elif gaps_to_review:
        risk_notes.append(
            "Only include these areas if you can support them: "
            + _format_inline_list(gaps_to_review[:6], "potential gaps")
            + "."
        )
    if stretch_warning:
        risk_notes.append(stretch_warning)
    for concern in explanation_concerns:
        if "No concern" not in concern and concern not in risk_notes:
            risk_notes.append(concern)
    if len(risk_notes) == 1:
        risk_notes.append("No major packet risks were detected from the score data.")
    return risk_notes


def _supported_overlap(
    matched_keywords: list[str],
    profile_themes: list[str],
    job_requirements: dict[str, object],
    profile_text: str | None,
) -> list[str]:
    overlap = []
    hard_requirements = _requirement_values(job_requirements, "hard_requirements")
    if any(keyword.lower() in {"git", "github"} for keyword in matched_keywords):
        overlap.append("Git/version control")
    if any(keyword.lower() in {"sql", "database", "data"} for keyword in matched_keywords):
        overlap.append("SQL/database work")
    if any(keyword.lower() == "remote" for keyword in matched_keywords):
        overlap.append("remote collaboration")
    for theme, label in [
        ("frontline IT support", "communication and user support"),
        ("documentation", "documentation"),
        ("classroom/AV troubleshooting", "troubleshooting"),
        ("ticket workflows", "follow-through in support workflows"),
    ]:
        if theme in profile_themes:
            overlap.append(label)
    if _profile_supports(profile_text, ["sql server", "relational database"]):
        overlap.append("SQL Server / relational database")
    return _dedupe([item for item in overlap if _is_overlap_relevant(item, hard_requirements)])


def _requirements_to_verify(
    job_requirements: dict[str, object],
    matched_keywords: list[str],
    profile_text: str | None,
) -> list[str]:
    requirements = []
    for requirement in _requirement_values(job_requirements, "hard_requirements"):
        if not _requirement_supported(requirement, matched_keywords, profile_text):
            requirements.append(requirement)
    requirements.extend(_requirement_values(job_requirements, "experience_requirements"))
    return _dedupe(requirements)


def _requirement_supported(
    requirement: str,
    matched_keywords: list[str],
    profile_text: str | None,
) -> bool:
    normalized_matches = {keyword.lower() for keyword in matched_keywords}
    support_markers = {
        "SQL Server / relational database": ["sql", "database", "relational database"],
        "Git / Azure DevOps / CI/CD": ["git", "azure devops", "ci/cd"],
    }
    markers = support_markers.get(requirement, [requirement.lower()])
    if any(marker in normalized_matches for marker in markers):
        return True
    return _profile_supports(profile_text, markers)


def _profile_supports(profile_text: str | None, markers: list[str]) -> bool:
    if not profile_text:
        return False
    normalized = profile_text.lower()
    return any(marker.lower() in normalized for marker in markers)


def _is_overlap_relevant(value: str, hard_requirements: list[str]) -> bool:
    if value in {"communication and user support", "documentation", "troubleshooting", "follow-through in support workflows", "remote collaboration"}:
        return True
    if value == "Git/version control":
        return "Git / Azure DevOps / CI/CD" in hard_requirements
    if value in {"SQL/database work", "SQL Server / relational database"}:
        return "SQL Server / relational database" in hard_requirements
    return True


def _build_stretch_warning(requirements_to_verify: list[str]) -> str:
    hard_gap_text = " ".join(requirements_to_verify).lower()
    stack_gaps = [
        label
        for label, markers in [
            ("C#/.NET", ["c# / .net", ".net"]),
            ("Angular/TypeScript", ["angular", "typescript"]),
            ("cloud/serverless", ["aws", "serverless"]),
            ("testing", ["unit testing", "test driven"]),
            ("architecture", ["domain driven", "service oriented", "object-oriented"]),
        ]
        if any(marker in hard_gap_text for marker in markers)
    ]
    if len(stack_gaps) < 3:
        return ""
    return (
        "This appears to be a stretch full-stack developer role unless the candidate "
        "has direct evidence for the required "
        + _format_inline_list(stack_gaps, "hard-skill")
        + " experience."
    )


def _requirement_values(job_requirements: dict[str, object], key: str) -> list[str]:
    values = job_requirements.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value).strip()]


def _dedupe(values: list[str]) -> list[str]:
    deduped = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _format_inline_list(values: list[str], fallback: str) -> str:
    if not values:
        return fallback
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + f", and {values[-1]}"
