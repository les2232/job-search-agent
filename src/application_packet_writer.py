"""Save generated application packets to local folders."""

from datetime import date, datetime
import json
from pathlib import Path
import re


PACKET_FILENAMES = {
    "job_summary": "job_summary.md",
    "score_explanation": "score_explanation.md",
    "resume_tailoring_notes": "resume_tailoring_notes.md",
    "tailored_resume": "tailored_resume.md",
    "cover_letter_draft": "cover_letter_draft.md",
    "recruiter_message": "recruiter_message.txt",
    "application_checklist": "application_checklist.md",
    "packet_json": "packet.json",
}
PACKET_INDEX_FILENAME = "packet_index.md"
PACKET_REVIEW_ORDER = [
    ("tailored_resume", "Tailored resume draft"),
    ("resume_tailoring_notes", "Resume tailoring notes"),
    ("cover_letter_draft", "Cover letter draft"),
    ("recruiter_message", "Recruiter message"),
    ("application_checklist", "Application checklist"),
    ("job_summary", "Job summary"),
    ("score_explanation", "Score explanation"),
    ("packet_json", "Packet data"),
]

RAW_TEXT_KEYS = {
    "raw_text",
    "job_text",
    "raw_job_text",
    "raw_job_description",
    "job_description",
}

DEFAULT_APPLICATION_STATUS = "Interested"


def save_application_packet(
    packet: dict[str, object],
    score_result: dict[str, object],
    output_root: str | Path = "applications",
    packet_date: date | None = None,
) -> dict[str, object]:
    """Save a generated packet without writing the raw job description."""
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)

    metadata = _get_metadata(score_result)
    packet_date = date.today() if packet_date is None else packet_date
    folder_name = build_packet_folder_name(metadata, packet_date)
    folder_path = _unique_folder_path(root / folder_name)
    folder_path.mkdir(parents=True)

    output_paths = {
        name: folder_path / filename for name, filename in PACKET_FILENAMES.items()
    }

    output_paths["job_summary"].write_text(
        _build_job_summary(metadata, score_result),
        encoding="utf-8",
    )
    output_paths["score_explanation"].write_text(
        _build_score_explanation(score_result),
        encoding="utf-8",
    )
    output_paths["resume_tailoring_notes"].write_text(
        _build_resume_tailoring_notes(packet),
        encoding="utf-8",
    )
    output_paths["tailored_resume"].write_text(
        str(packet.get("tailored_resume_draft", "")),
        encoding="utf-8",
    )
    output_paths["cover_letter_draft"].write_text(
        str(packet.get("cover_letter_draft", "")),
        encoding="utf-8",
    )
    output_paths["recruiter_message"].write_text(
        str(packet.get("recruiter_message", "")),
        encoding="utf-8",
    )
    output_paths["application_checklist"].write_text(
        _build_application_checklist(packet),
        encoding="utf-8",
    )
    output_paths["packet_json"].write_text(
        json.dumps(
            _build_packet_payload(packet, score_result, metadata, packet_date),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    output_paths["packet_index"] = folder_path / PACKET_INDEX_FILENAME
    output_paths["packet_index"].write_text(
        build_packet_review_index(output_paths),
        encoding="utf-8",
    )

    return {
        "folder_path": folder_path,
        "output_paths": output_paths,
    }


def build_packet_review_index(output_paths: dict[str, Path]) -> str:
    """Build a deterministic Markdown index for generated packet files."""
    review_items = []
    for key, label in PACKET_REVIEW_ORDER:
        path = output_paths.get(key)
        if isinstance(path, Path) and path.exists():
            review_items.append(f"- [{label}]({path.name})")

    if not review_items:
        review_items.append("- No generated packet files were found.")

    return "\n".join(
        [
            "# Application Packet Review Index",
            "",
            (
                "Generated drafts must be reviewed before use. Confirm every "
                "resume, cover letter, and outreach claim is true and supported."
            ),
            "",
            "## Recommended Review Order",
            "",
            *review_items,
            "",
        ]
    )


def build_packet_folder_name(
    metadata: dict[str, str],
    packet_date: date,
) -> str:
    company = safe_slug(metadata.get("company"), "unknown-company")
    title = safe_slug(metadata.get("title"), "unknown-role")
    return f"{packet_date.isoformat()}_{company}_{title}"


def safe_slug(value: object, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback

    text = value.strip().lower()
    if not text or text == "unknown":
        return fallback

    slug = re.sub(r"[^a-z0-9]+", "-", text)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or fallback


def _unique_folder_path(folder_path: Path) -> Path:
    if not folder_path.exists():
        return folder_path

    counter = 2
    while True:
        candidate = folder_path.with_name(f"{folder_path.name}-{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


def _get_metadata(score_result: dict[str, object]) -> dict[str, str]:
    metadata = score_result.get("job_metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    return {
        "title": _safe_text(metadata.get("title"), "Unknown"),
        "company": _safe_text(metadata.get("company"), "Unknown"),
        "location": _safe_text(metadata.get("location"), "Unknown"),
        "work_mode": _safe_text(metadata.get("work_mode"), "Unknown"),
        "source_url": _safe_text(metadata.get("source_url"), ""),
    }


def _safe_text(value: object, fallback: str = "") -> str:
    if not isinstance(value, str) or not value.strip():
        return fallback
    return value.strip()


def _build_job_summary(
    metadata: dict[str, str],
    score_result: dict[str, object],
) -> str:
    return "\n".join(
        [
            "# Job Summary",
            "",
            f"- Title: {metadata['title']}",
            f"- Company: {metadata['company']}",
            f"- Location: {metadata['location']}",
            f"- Work mode: {metadata['work_mode']}",
            f"- Source URL: {metadata['source_url'] or 'None'}",
            f"- Score: {score_result.get('score', 'Unknown')}/100",
            f"- Recommendation: {score_result.get('recommendation', 'Unknown')}",
            f"- Matched keywords: {_format_inline_list(score_result.get('matched_keywords'))}",
            f"- Concerns: {_format_inline_list(score_result.get('concerns'))}",
            "",
        ]
    )


def _build_score_explanation(score_result: dict[str, object]) -> str:
    explanation = score_result.get("explanation")
    if not isinstance(explanation, dict):
        return "# Score Explanation\n\nNo score explanation was available.\n"

    return "\n".join(
        [
            "# Score Explanation",
            "",
            str(explanation.get("fit_summary", "")),
            "",
            _format_markdown_list("Strengths", explanation.get("strengths")),
            _format_markdown_list("Gaps", explanation.get("gaps")),
            _format_markdown_list("Concerns", explanation.get("concerns")),
            _format_markdown_list(
                "Tailoring Suggestions",
                explanation.get("tailoring_suggestions"),
            ),
            "",
        ]
    )


def _build_resume_tailoring_notes(packet: dict[str, object]) -> str:
    strategy_sections = packet.get("resume_strategy_sections")
    if isinstance(strategy_sections, dict):
        return _build_structured_resume_tailoring_notes(packet, strategy_sections)

    return "\n".join(
        [
            "# Resume Tailoring Notes",
            "",
            str(packet.get("positioning_summary", "")),
            "",
            f"Apply recommendation: {packet.get('apply_recommendation', '')}",
            "",
            _format_markdown_list("Resume Focus Areas", packet.get("resume_focus_areas")),
            _format_markdown_list(
                "Suggested Resume Bullets",
                packet.get("resume_bullet_suggestions"),
            ),
            _format_markdown_list(
                "Keywords To Include Honestly",
                packet.get("keywords_to_include_honestly"),
            ),
            _format_markdown_list(
                "Keywords To Verify Or Avoid",
                packet.get("keywords_to_avoid_or_verify"),
            ),
            _format_markdown_list("Risk Notes", packet.get("risk_notes")),
            "",
        ]
    )


def _build_structured_resume_tailoring_notes(
    packet: dict[str, object],
    strategy_sections: dict[object, object],
) -> str:
    return "\n".join(
        [
            "# Resume Tailoring Notes",
            "",
            _format_decision_summary(packet.get("decision_summary")),
            "## Fit Verdict",
            "",
            f"{strategy_sections.get('fit_verdict', 'Review Fit')}",
            "",
            str(strategy_sections.get("fit_summary", "")).strip(),
            "",
            "## Apply Recommendation",
            "",
            str(
                strategy_sections.get(
                    "apply_recommendation",
                    packet.get("apply_recommendation", ""),
                )
            ).strip(),
            "",
            _format_markdown_list(
                "Strong / Supported Overlap",
                strategy_sections.get("supported_overlap"),
            ),
            _format_markdown_list(
                "Major Requirements To Verify Before Applying",
                strategy_sections.get("major_requirements_to_verify"),
            ),
            _format_evidence_summary(packet.get("evidence_summary")),
            _format_markdown_list(
                "Transferable Support Evidence",
                strategy_sections.get("transferable_support_evidence"),
            ),
            _format_markdown_list(
                "Apply Only If",
                strategy_sections.get("apply_only_if"),
            ),
            _format_markdown_list(
                "Consider Skipping Or Deprioritizing If",
                strategy_sections.get("consider_skipping_if"),
            ),
            _format_resume_bullets(packet.get("resume_bullet_suggestions")),
            _format_markdown_list(
                "Keywords / Themes To Include Honestly",
                packet.get("keywords_to_include_honestly"),
            ),
            _format_markdown_list(
                "Keywords To Verify Or Avoid",
                packet.get("keywords_to_avoid_or_verify"),
            ),
            _format_markdown_list(
                "Missing Proof Next Actions",
                packet.get("missing_proof_actions"),
            ),
            _format_markdown_list("Risk Notes", packet.get("risk_notes")),
            "",
        ]
    )


def _format_decision_summary(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    why = _as_string_list(value.get("why"))
    lines = [
        "## Decision Summary",
        "",
        f"- Decision: {value.get('decision', 'Review')}",
    ]
    lines.extend(f"- Why: {item}" for item in why)
    lines.append(f"- Next action: {value.get('next_action', 'Review before applying.')}")
    return "\n".join(lines) + "\n"


def _format_evidence_summary(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    sections = [
        ("Supported Evidence", value.get("supported_evidence")),
        ("Partial Evidence", value.get("partial_evidence")),
        ("Missing Proof", value.get("missing_proof")),
        ("Needs Verification", value.get("needs_verification")),
    ]
    parts = ["## Evidence Summary", ""]
    for label, items in sections:
        parts.append(f"### {label}")
        parts.append("")
        rows = _evidence_rows(items)
        parts.extend(f"- {row}" for row in rows)
        parts.append("")
    return "\n".join(parts)


def _evidence_rows(values: object) -> list[str]:
    if not isinstance(values, list) or not values:
        return ["None"]
    rows = []
    for value in values:
        if not isinstance(value, dict):
            continue
        requirement = str(value.get("requirement", "")).strip()
        notes = str(value.get("notes", "")).strip()
        if notes:
            rows.append(f"{requirement}: {notes}")
        elif requirement:
            rows.append(requirement)
    return rows or ["None"]


def _format_resume_bullets(values: object) -> str:
    items = _as_string_list(values)
    cleaned_items = []
    lead_in = ""
    for item in items:
        if item.startswith("Use only if true:"):
            lead_in = "Use only if true:"
            item = item.removeprefix("Use only if true:").strip()
        cleaned_items.append(item)
    if not cleaned_items:
        return "## Suggested Resume Bullets\n\n- None\n"
    parts = ["## Suggested Resume Bullets", ""]
    if lead_in:
        parts.extend([lead_in, ""])
    parts.extend(f"- {item}" for item in cleaned_items)
    return "\n".join(parts) + "\n"


def _build_application_checklist(packet: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Application Checklist",
            "",
            _format_markdown_list("Checklist", packet.get("application_checklist")),
            "",
            _format_markdown_list("Risk Notes", packet.get("risk_notes")),
            "",
        ]
    )


def _build_packet_payload(
    packet: dict[str, object],
    score_result: dict[str, object],
    metadata: dict[str, str],
    packet_date: date,
) -> dict[str, object]:
    return {
        "created_date": packet_date.isoformat(),
        "application_tracking": {
            "status": DEFAULT_APPLICATION_STATUS,
            "status_updated_at": _current_timestamp(),
            "applied_date": None,
            "notes": "",
            "next_action_date": None,
            "next_action_note": "",
        },
        "job_metadata": metadata,
        "score_summary": {
            "score": score_result.get("score"),
            "recommendation": score_result.get("recommendation"),
            "matched_keywords": _as_string_list(score_result.get("matched_keywords")),
            "missing_keywords": _as_string_list(score_result.get("missing_keywords")),
            "concerns": _as_string_list(score_result.get("concerns")),
            "job_requirements": _sanitize_packet_value(
                score_result.get("job_requirements"),
            ),
            "explanation": score_result.get("explanation"),
        },
        "application_packet": _sanitize_packet_value(packet),
    }


def _sanitize_packet_value(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_packet_value(item)
            for key, item in value.items()
            if str(key) not in RAW_TEXT_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_packet_value(item) for item in value]
    return value


def _current_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _format_markdown_list(label: str, values: object) -> str:
    items = _as_string_list(values)
    if not items:
        return f"## {label}\n\n- None\n"
    return f"## {label}\n\n" + "\n".join(f"- {item}" for item in items) + "\n"


def _format_inline_list(values: object) -> str:
    items = _as_string_list(values)
    if not items:
        return "None"
    return ", ".join(items)


def _as_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value).strip()]
