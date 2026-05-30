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
    display_role_label = _cover_role_label(role_label)
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
    display_requirements_to_verify = _display_requirements(requirements_to_verify)
    gaps_to_review = _gaps_to_review(
        missing_keywords,
        concerns,
        display_requirements_to_verify,
    )
    stretch_warning = _build_stretch_warning(display_requirements_to_verify)
    resume_strategy_sections = _build_resume_strategy_sections(
        display_role_label,
        company_label,
        recommendation,
        supported_overlap,
        display_requirements_to_verify,
        profile_themes,
        stretch_warning,
    )

    return {
        "positioning_summary": _build_positioning_summary(
            score,
            recommendation,
            display_role_label,
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
            display_requirements_to_verify,
            stretch_warning,
        ),
        "resume_strategy_sections": resume_strategy_sections,
        "resume_bullet_suggestions": _build_resume_bullet_suggestions(
            strongest_matches,
            profile_themes,
            supported_overlap,
            display_requirements_to_verify,
        ),
        "keywords_to_include_honestly": _build_keywords_to_include_honestly(
            matched_keywords,
            profile_themes,
        ),
        "keywords_to_avoid_or_verify": gaps_to_review[:8],
        "cover_letter_draft": _build_cover_letter_draft(
            display_role_label,
            company_label,
            metadata,
            matched_keywords,
            profile_themes,
            recommendation,
            source_text,
        ),
        "recruiter_message": _build_recruiter_message(
            display_role_label,
            company_label,
            strongest_matches,
        ),
        "application_checklist": _build_application_checklist(recommendation),
        "risk_notes": _build_risk_notes(
            metadata,
            gaps_to_review,
            explanation_concerns,
            display_requirements_to_verify,
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
            "Fit Verdict: Stretch Role\n\n"
            f"{role_label} at {company_label} is likely a stretch unless the "
            "candidate has direct evidence for the main hard requirements."
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
    if profile_themes:
        focus_areas.append(
            _build_transferable_theme_note(profile_themes)
        )
    focus_areas.extend(_build_apply_skip_guidance(requirements_to_verify))
    if not focus_areas:
        focus_areas.append(
            "Use only resume/profile details you can verify, and keep the summary broad."
        )
    return focus_areas


def _build_resume_strategy_sections(
    role_label: str,
    company_label: str,
    recommendation: str,
    supported_overlap: list[str],
    requirements_to_verify: list[str],
    profile_themes: list[str],
    stretch_warning: str,
) -> dict[str, object]:
    fit_verdict = "Stretch Role" if stretch_warning else "Review Fit"
    if recommendation == "Apply" and not stretch_warning:
        fit_verdict = "Strong Target"
    elif recommendation == "Skip" and not stretch_warning:
        fit_verdict = "Lower Priority"

    fit_summary = (
        f"{role_label} at {company_label} is likely a stretch unless the candidate "
        "has direct evidence for the main hard requirements."
        if stretch_warning
        else f"{role_label} at {company_label} should be reviewed against verified resume evidence before applying."
    )

    return {
        "fit_verdict": fit_verdict,
        "fit_summary": fit_summary,
        "apply_recommendation": _build_apply_recommendation(
            recommendation,
            requirements_to_verify,
        ),
        "supported_overlap": _build_supported_overlap_items(supported_overlap),
        "major_requirements_to_verify": requirements_to_verify,
        "transferable_support_evidence": _build_transferable_support_items(profile_themes),
        "apply_only_if": _build_apply_only_if_items(requirements_to_verify),
        "consider_skipping_if": _build_consider_skipping_items(requirements_to_verify),
    }


def _build_supported_overlap_items(supported_overlap: list[str]) -> list[str]:
    if not supported_overlap:
        return ["Use only profile details and project examples the candidate can verify."]

    items = []
    for value in supported_overlap:
        mapped = {
            "Git/version control, if supported by the candidate's profile or projects": (
                "Git/version control, if supported by coursework, scripts, or software projects."
            ),
            "SQL/database work, if supported by database, query, reporting, or data-backed troubleshooting examples": (
                "SQL/database work, if supported by database queries, reports, or data-backed troubleshooting."
            ),
            "Python scripting/development, if supported by coursework, scripts, or software projects": (
                "Python, if supported by coursework, scripts, or software projects."
            ),
            "APIs/integrations, if supported by projects or technical work": (
                "APIs / integrations, if supported by projects or technical work."
            ),
            "automation or workflow improvement, if supported by real examples": (
                "Automation or workflow improvement, if supported by real examples."
            ),
            "data-backed troubleshooting": "Data-backed troubleshooting and documentation.",
            "remote collaboration": "Remote collaboration and clear communication.",
            "documentation": "Technical documentation.",
            "user-facing technical troubleshooting": "User-facing technical troubleshooting and documentation.",
            "follow-through in support workflows": "Follow-through in systems used by real users.",
            "user-facing technical support translated as understanding user needs and supporting reliable systems": (
                "User-facing technical support translated as evidence of understanding user needs and supporting reliable systems."
            ),
        }.get(value, value)
        if not mapped.endswith("."):
            mapped += "."
        items.append(mapped)
    return _dedupe(items)


def _build_transferable_support_items(profile_themes: list[str]) -> list[str]:
    if "classroom/AV troubleshooting" in profile_themes:
        return [
            (
                "Frame support work as user-facing technical troubleshooting, "
                "documentation, clear communication, and support for systems used by real users."
            ),
            (
                "Do not present support, classroom, or AV troubleshooting as software "
                "development experience."
            ),
        ]
    if profile_themes:
        return [
            (
                "Use concrete examples from verified profile themes such as "
                + _format_inline_list(profile_themes[:5], "profile themes")
                + "."
            )
        ]
    return ["Keep transferable evidence broad unless the resume supports a more specific claim."]


def _build_apply_only_if_items(requirements_to_verify: list[str]) -> list[str]:
    if not requirements_to_verify:
        return ["The candidate can support the main role requirements with real examples."]
    if _has_ai_automation_requirements(requirements_to_verify):
        return [
            (
                "The candidate can point to real Python, API, automation, SQL, "
                "AI assistant, or agent-building examples."
            ),
            (
                "The candidate can explain at least one project or workflow where "
                "they improved, automated, or integrated a technical process."
            ),
            (
                "The candidate can honestly connect their profile to the role "
                "without pretending to have production AI engineering experience."
            ),
        ]
    return [
        (
            "The candidate can show direct evidence of .NET/C#, Angular/TypeScript, "
            "or comparable full-stack development work."
        ),
        "The candidate can explain SQL/database work clearly.",
        (
            "The candidate has projects, coursework, or professional examples "
            "involving testing, architecture, APIs, or cloud services."
        ),
        "The candidate is comfortable positioning this as a stretch role.",
    ]


def _build_consider_skipping_items(requirements_to_verify: list[str]) -> list[str]:
    if not requirements_to_verify:
        return ["The role is not worth the tailoring time or does not support the candidate's goals."]
    if _has_ai_automation_requirements(requirements_to_verify):
        return [
            "The candidate has no Python, automation, API, SQL, or AI/project evidence.",
            "The candidate would rely almost entirely on interest rather than demonstrable work.",
            (
                "The posting expects production-level AI/agent experience that "
                "the candidate cannot support."
            ),
        ]
    return [
        "The candidate's experience is mostly IT support with little software development evidence.",
        "The candidate cannot support the required years of full-stack development.",
        "The candidate would be relying almost entirely on transferable skills.",
    ]


def _build_resume_bullet_suggestions(
    strongest_matches: list[str],
    profile_themes: list[str],
    supported_overlap: list[str],
    requirements_to_verify: list[str],
) -> list[str]:
    if _has_ai_automation_requirements(requirements_to_verify):
        bullets = [
            (
                "Use only if true: Built or adapted Python scripts, support tools, "
                "or automation workflows to reduce manual technical work."
            ),
            (
                "Use only if true: Worked with APIs or integrations in projects, "
                "coursework, scripts, or technical troubleshooting."
            ),
            (
                "Use only if true: Used SQL, reports, queries, or data-backed "
                "troubleshooting to understand and improve a process."
            ),
            (
                "Use only if true: Documented technical workflows so users or team "
                "members could resolve recurring issues more consistently."
            ),
            (
                "Do not claim production AI agent, LLM framework, or professional "
                "AI engineering experience unless the profile or resume supports it."
            ),
        ]
        return bullets

    bullets = [
        (
            "Use only if true: Used Git/version control in coursework, scripts, "
            "or software projects to track changes and manage technical work."
        ),
        (
            "Use only if true: Worked with SQL, reports, database queries, or "
            "data-backed troubleshooting to support technical decisions."
        ),
        (
            "Use only if true: Documented technical workflows so users or team "
            "members could resolve recurring issues more consistently."
        ),
        (
            "Use only if true: Troubleshot technical systems used by real users "
            "and communicated resolution steps clearly to stakeholders."
        ),
    ]

    if requirements_to_verify:
        bullets.append(
            "Do not present support, classroom, or AV troubleshooting as software "
            "development experience. Use it only as evidence of user-centered "
            "technical support, troubleshooting, documentation, and follow-through."
        )
    return bullets[:5]


def _build_keywords_to_include_honestly(
    matched_keywords: list[str],
    profile_themes: list[str],
) -> list[str]:
    normalized_keywords = {keyword.lower() for keyword in matched_keywords}
    labels = []
    if "sql" in normalized_keywords or "database" in normalized_keywords:
        labels.append("SQL / database-backed troubleshooting, only if supported.")
    if "git" in normalized_keywords or "github" in normalized_keywords:
        labels.append("Git / version control, only if supported.")
    if "remote" in normalized_keywords:
        labels.append("Remote collaboration.")
    if "apis" in normalized_keywords or "api" in normalized_keywords:
        labels.append("APIs / integrations, only if supported.")
    if "automation" in normalized_keywords:
        labels.append("Automation or workflow improvement, only if supported.")
    if "data" in normalized_keywords:
        labels.append("Data-backed technical work, only if supported.")
    if "documentation" in normalized_keywords or "documentation" in profile_themes:
        labels.append("Technical documentation.")
    if any(theme in profile_themes for theme in ["frontline IT support", "classroom/AV troubleshooting"]):
        labels.append("User-facing troubleshooting.")
    if profile_themes or "remote" in normalized_keywords:
        labels.append("Clear communication and follow-through.")
    for keyword in matched_keywords:
        if keyword.lower() not in {"sql", "database", "git", "github", "remote", "apis", "api", "automation", "data", "documentation"}:
            label = f"{keyword.title()}, only if supported."
            if label not in labels:
                labels.append(label)
    return labels[:8]


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
    if "ai agent" in normalized or "agentic workflow" in normalized:
        return "building useful AI and automation workflows"
    if "workflow automation" in normalized:
        return "improving technical workflows through automation"
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
        + _format_inline_list(needs[:4], "dependable technical work")
        + "."
    )


def _human_role_needs(matched_keywords: list[str]) -> list[str]:
    keyword_map = {
        "python": "Python scripting",
        "sql": "database-backed systems and data-backed problem solving",
        "git": "version control",
        "apis": "API integrations",
        "api": "API integrations",
        "automation": "automation and workflow improvement",
        "data": "data-backed problem solving",
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
        risk_notes.append(
            "Stretch-role risk: direct evidence is needed for "
            + _format_inline_list(
                _stretch_gap_labels(requirements_to_verify),
                "the main hard-skill gaps",
            )
            + "."
        )
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
    if any(keyword.lower() == "python" for keyword in matched_keywords):
        overlap.append("Python scripting/development, if supported by coursework, scripts, or software projects")
    if any(keyword.lower() in {"api", "apis"} for keyword in matched_keywords):
        overlap.append("APIs/integrations, if supported by projects or technical work")
    if any(keyword.lower() == "automation" for keyword in matched_keywords):
        overlap.append("automation or workflow improvement, if supported by real examples")
    if any(keyword.lower() in {"git", "github"} for keyword in matched_keywords):
        overlap.append("Git/version control, if supported by the candidate's profile or projects")
    if any(keyword.lower() in {"sql", "database", "data"} for keyword in matched_keywords):
        overlap.append("SQL/database work, if supported by database, query, reporting, or data-backed troubleshooting examples")
    if any(keyword.lower() == "data" for keyword in matched_keywords):
        overlap.append("data-backed troubleshooting")
    if any(keyword.lower() == "remote" for keyword in matched_keywords):
        overlap.append("remote collaboration")
    for theme, label in [
        ("frontline IT support", "user-facing technical support translated as understanding user needs and supporting reliable systems"),
        ("documentation", "documentation"),
        ("classroom/AV troubleshooting", "user-facing technical troubleshooting"),
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
        "SQL / data workflows": ["sql", "data", "database"],
        "Git / Azure DevOps / CI/CD": ["git", "azure devops", "ci/cd"],
        "Python scripting/development": ["python", "python scripting", "python development"],
        "API integration": ["api", "apis", "api integration", "integrations"],
        "Automation workflows": ["automation", "workflow automation", "automated"],
        "Data pipelines / ETL": ["data pipeline", "etl"],
        "Cloud tools / deployment": ["cloud", "deployment", "deploy"],
        "Workflow orchestration": ["orchestration", "workflow tools"],
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
    if value.startswith("Python scripting/development"):
        return "Python scripting/development" in hard_requirements
    if value.startswith("APIs/integrations"):
        return "API integration" in hard_requirements
    if value.startswith("automation or workflow improvement"):
        return "Automation workflows" in hard_requirements
    if value == "data-backed troubleshooting":
        return "SQL / data workflows" in hard_requirements
    if value == "Git/version control":
        return "Git / Azure DevOps / CI/CD" in hard_requirements
    if value in {"SQL/database work", "SQL Server / relational database"}:
        return "SQL Server / relational database" in hard_requirements
    return True


def _build_stretch_warning(requirements_to_verify: list[str]) -> str:
    stack_gaps = _stretch_gap_labels(requirements_to_verify)
    if len(stack_gaps) < 3:
        return ""
    return (
        "This role is likely a stretch unless the candidate "
        "has direct evidence for the required "
        + _format_inline_list(stack_gaps, "hard-skill")
        + " experience."
    )


def _stretch_gap_labels(requirements_to_verify: list[str]) -> list[str]:
    hard_gap_text = " ".join(requirements_to_verify).lower()
    return [
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


def _display_requirements(requirements: list[str]) -> list[str]:
    display_values = []
    for requirement in requirements:
        mapped = {
            "C# / .NET 5+": "C# / .NET 5+ professional experience",
            "Angular 16+": "Angular 16+ and TypeScript",
            "TypeScript": "Angular 16+ and TypeScript",
            "SQL Server / relational database": "SQL Server or comparable relational database experience",
            "AWS serverless": "AWS serverless or similar cloud services",
            "Domain Driven Design": "Domain Driven Design and Service Oriented Architecture",
            "Service Oriented Architecture": "Domain Driven Design and Service Oriented Architecture",
            "Unit testing": "Unit testing and Test Driven Development",
            "Test Driven Development": "Unit testing and Test Driven Development",
            "AI agent / agentic workflows": "AI agent or automation workflow experience",
            "LLM / large language model workflows": "LLM or large language model workflow experience",
            "Prompt engineering": "Prompt engineering or prompting experience",
            "RAG / retrieval augmented generation": "RAG / retrieval augmented generation experience",
            "Embeddings / vector database": "Embeddings or vector database experience",
            "Agent-building tools or LLM platforms": "Agent-building tools or LLM platform experience",
            "Python scripting/development": "Python scripting/development",
            "API integration": "API integration experience",
            "Automation workflows": "Automation workflow experience",
            "SQL / data workflows": "SQL/data workflow experience",
            "Data pipelines / ETL": "Data pipelines / ETL experience",
            "Cloud tools / deployment": "Cloud tools or deployment experience",
            "Workflow orchestration": "Workflow orchestration experience",
        }.get(requirement, requirement)
        if "years" in mapped.lower():
            mapped = "Required years of full-stack software development experience"
        display_values.append(mapped)
    return _dedupe(display_values)


def _build_transferable_theme_note(profile_themes: list[str]) -> str:
    if "classroom/AV troubleshooting" in profile_themes:
        return (
            "Transferable support evidence: frame learning-space technical support as "
            "user-facing technical troubleshooting, documentation, support for "
            "systems used by real users, clear communication, and follow-through. "
            "Do not present it as software development experience."
        )
    return (
        "Use concrete examples from profile themes such as: "
        + _format_inline_list(profile_themes[:5], "your profile themes")
        + "."
    )


def _build_apply_skip_guidance(requirements_to_verify: list[str]) -> list[str]:
    if not requirements_to_verify:
        return []
    if _has_ai_automation_requirements(requirements_to_verify):
        return [
            (
                "Apply only if: you can point to real Python, API, automation, "
                "SQL, AI assistant, or agent-building examples; you can explain "
                "a project or workflow where you improved, automated, or integrated "
                "a technical process; and you can avoid overstating production AI "
                "engineering experience."
            ),
            (
                "Consider skipping or deprioritizing if: you have no Python, "
                "automation, API, SQL, or AI/project evidence; you would rely "
                "mostly on interest; or the posting expects production-level "
                "AI/agent experience you cannot support."
            ),
        ]
    return [
        (
            "Apply only if: you can show direct evidence of .NET/C#, "
            "Angular/TypeScript, or comparable full-stack development work; you "
            "can explain SQL/database work clearly; you have projects, coursework, "
            "or professional examples involving testing, architecture, APIs, or "
            "cloud services; and you are comfortable positioning this as a stretch role."
        ),
        (
            "Consider skipping or deprioritizing if: your experience is mostly IT "
            "support with little software development evidence; you cannot support "
            "the required years of full-stack development; or you would be relying "
            "almost entirely on transferable skills."
        ),
    ]


def _requirement_values(job_requirements: dict[str, object], key: str) -> list[str]:
    values = job_requirements.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value).strip()]


def _has_ai_automation_requirements(requirements: list[str]) -> bool:
    text = " ".join(requirements).lower()
    return any(
        marker in text
        for marker in [
            "ai agent",
            "agentic",
            "llm",
            "large language",
            "prompt",
            "rag",
            "retrieval",
            "embeddings",
            "vector database",
            "python scripting",
            "api integration",
            "automation workflow",
            "sql/data",
            "data pipelines",
            "workflow orchestration",
        ]
    )


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
