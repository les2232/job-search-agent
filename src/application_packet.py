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

    profile_themes = _find_profile_themes(profile_text)
    role_label = _role_label(metadata)
    company_label = _company_label(metadata)
    strongest_matches = _strongest_matches(matched_keywords, profile_themes)
    gaps_to_review = _gaps_to_review(missing_keywords, concerns)

    return {
        "positioning_summary": _build_positioning_summary(
            score,
            recommendation,
            role_label,
            company_label,
            strongest_matches,
        ),
        "apply_recommendation": _build_apply_recommendation(
            recommendation,
            gaps_to_review,
        ),
        "resume_focus_areas": _build_resume_focus_areas(
            strongest_matches,
            gaps_to_review,
            profile_themes,
        ),
        "resume_bullet_suggestions": _build_resume_bullet_suggestions(
            strongest_matches,
            profile_themes,
        ),
        "keywords_to_include_honestly": matched_keywords[:8],
        "keywords_to_avoid_or_verify": gaps_to_review[:8],
        "cover_letter_draft": _build_cover_letter_draft(
            role_label,
            company_label,
            metadata,
            strongest_matches,
            recommendation,
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
) -> list[str]:
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
) -> str:
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
) -> list[str]:
    focus_areas = []
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
    strongest_matches: list[str],
    recommendation: str,
) -> str:
    match_text = _format_inline_list(strongest_matches[:3], "support and documentation")
    location_note = _build_location_note(metadata)
    priority_note = ""
    if recommendation != "Apply":
        priority_note = (
            " I would review the role requirements carefully and keep the final letter "
            "focused only on experience I can verify."
        )

    return "\n".join(
        [
            REVIEW_WARNING,
            "",
            "Dear Hiring Team,",
            "",
            (
                f"I am interested in {role_label} at {company_label}."
                f"{location_note}"
            ),
            "",
            (
                "My background includes local IT support, user communication, "
                f"troubleshooting, and documentation work that appears relevant to {match_text}. "
                "I would tailor my resume around the examples that are most directly supported "
                "by my experience and project notes."
            ),
            "",
            (
                "This role seems aligned with practical support work, clear documentation, "
                "and steady follow-through."
                f"{priority_note}"
            ),
            "",
            "Thank you for your consideration.",
        ]
    )


def _build_location_note(metadata: dict[str, str]) -> str:
    parts = []
    if _is_known(metadata["location"]):
        parts.append(metadata["location"])
    if _is_known(metadata["work_mode"]):
        parts.append(metadata["work_mode"])
    if not parts:
        return ""
    return " The posting appears to be connected to " + " / ".join(parts) + "."


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
    if gaps_to_review:
        risk_notes.append(
            "Only include these areas if you can support them: "
            + _format_inline_list(gaps_to_review[:6], "potential gaps")
            + "."
        )
    for concern in explanation_concerns:
        if "No concern" not in concern and concern not in risk_notes:
            risk_notes.append(concern)
    if len(risk_notes) == 1:
        risk_notes.append("No major packet risks were detected from the score data.")
    return risk_notes


def _format_inline_list(values: list[str], fallback: str) -> str:
    if not values:
        return fallback
    if len(values) == 1:
        return values[0]
    return ", ".join(values[:-1]) + f", and {values[-1]}"
