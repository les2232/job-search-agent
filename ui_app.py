"""Local Streamlit UI for the job search agent."""

from collections import Counter
from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from application_generator import generate_application_materials
from application_packet import generate_application_packet
from application_packet_reader import (
    APPLICATION_STATUSES,
    SORT_OPTIONS,
    count_saved_applications_by_status,
    filter_saved_application_packets,
    get_today_application_queue,
    list_saved_application_packets,
    load_saved_application_packet,
    sort_saved_application_packets,
    update_application_tracking,
)
from application_packet_writer import save_application_packet
from job_parser import parse_job_text
from job_scorer import score_job
from profile_manager import DEFAULT_PROFILE_ID
from profile_manager import append_proof_block
from profile_manager import list_profiles
from profile_manager import profile_applications_dir
from tracker import filter_tracked_jobs
from tracker import read_tracked_jobs
from tracker import save_job_result
from tracker import update_job_status


JOBS_CSV_PATH = PROJECT_ROOT / "data" / "jobs.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"
APPLICATIONS_DIR = PROJECT_ROOT / "applications"
DEFAULT_RESUME_PATH = PROJECT_ROOT / "data" / "profile" / "resume_base.md"
PROFILES_ROOT = PROJECT_ROOT / "profiles"
LOCAL_PROFILES_ROOT = PROJECT_ROOT / "local_profiles"
STATUS_OPTIONS = ["New", "Applied", "Interview", "Rejected", "Saved", "Archived"]
EVIDENCE_STATUS_OPTIONS = ["Not sure", "Strong evidence", "Some evidence", "No evidence"]


def main() -> None:
    st.set_page_config(page_title="Application Packet Builder", layout="wide")
    st.title("Application Packet Builder")
    st.write(
        "Paste a job posting, review the fit, generate a local application packet, "
        "and save it under the selected profile."
    )

    st.subheader("Step 1: Choose Profile")
    selected_profile = _show_profile_selector()
    selected_applications_dir = profile_applications_dir(
        APPLICATIONS_DIR,
        selected_profile,
    )
    legacy_root = _legacy_root_for_profile(selected_profile)

    _show_guided_packet_builder(selected_profile, selected_applications_dir)
    st.divider()
    with st.expander("Review saved packets"):
        _show_saved_packet_review(selected_profile, selected_applications_dir, legacy_root)
    st.divider()

    tracked_jobs = read_tracked_jobs(JOBS_CSV_PATH)
    with st.expander("Advanced tools: dashboard, tracker, and legacy packet generator"):
        dashboard_tab, today_tab, score_tab, tracker_tab, packets_tab, saved_tab = st.tabs(
            [
                "Dashboard",
                "Today",
                "Score a Job",
                "Tracker",
                "Application Packets",
                "Saved applications",
            ]
        )

        with dashboard_tab:
            _show_dashboard(
                tracked_jobs,
                selected_profile,
                selected_applications_dir,
                legacy_root,
            )

        with today_tab:
            _show_today_tab(selected_profile, selected_applications_dir, legacy_root)

        with score_tab:
            _show_score_job_tab(selected_profile, selected_applications_dir)

        with tracker_tab:
            _show_tracker_tab(tracked_jobs)

        with packets_tab:
            _show_application_packets_tab(selected_profile)

        with saved_tab:
            _show_saved_applications_tab(
                selected_profile,
                selected_applications_dir,
                legacy_root,
            )


def _show_guided_packet_builder(
    profile: dict[str, object],
    applications_dir: Path,
) -> None:
    st.divider()
    st.header("Step 2: Paste Job")
    st.caption("Main flow: paste a posting, analyze fit, review evidence, generate drafts, then decide the next action.")

    title = ""
    company = ""
    location = ""
    work_mode = ""
    job_type = ""
    with st.expander("Optional clean header fields"):
        st.caption(
            "Use these when copied job-board text starts with boilerplate. "
            "They are prepended as clean labels before analysis."
        )
        field_cols = st.columns(5)
        title = field_cols[0].text_input("Job Title", key="builder_title")
        company = field_cols[1].text_input("Company", key="builder_company")
        location = field_cols[2].text_input("Location", key="builder_location")
        work_mode = field_cols[3].selectbox(
            "Work Mode",
            ["", "Remote", "Hybrid", "On-site", "Unknown"],
            key="builder_work_mode",
        )
        job_type = field_cols[4].text_input("Job Type", key="builder_job_type")

    job_text = st.text_area(
        "Paste job posting here",
        height=320,
        key="builder_job_text",
        placeholder=(
            "Paste the full copied posting here. Indeed/job-board headers are okay; "
            "use the optional fields above when the copied text starts with boilerplate."
        ),
    )
    st.caption("Copied Indeed/job-board postings are okay. Add clean header fields only when needed.")

    if st.button("Analyze Job", type="primary", key="builder_analyze"):
        full_job_text = _build_guided_job_text(
            job_text,
            title=title,
            company=company,
            location=location,
            work_mode=work_mode,
            job_type=job_type,
        )
        if not full_job_text.strip():
            st.error("Paste a job posting before analyzing.")
        else:
            job = parse_job_text(
                full_job_text,
                title=title,
                company=company,
                location=location,
            )
            score_details = score_job(job)
            st.session_state["builder_job"] = job
            st.session_state["builder_score_details"] = score_details
            st.session_state["builder_full_job_text"] = full_job_text
            st.session_state["builder_analysis_key"] = _score_analysis_key(score_details)
            st.session_state.pop("builder_packet", None)
            st.session_state.pop("builder_packet_analysis_key", None)
            st.session_state.pop("builder_saved_packet", None)

    job = st.session_state.get("builder_job")
    score_details = st.session_state.get("builder_score_details")
    if isinstance(job, dict) and isinstance(score_details, dict):
        _show_builder_analysis(job, score_details, profile, applications_dir)
    else:
        st.info("Paste a posting and click Analyze Job to start.")


def _build_guided_job_text(
    job_text: str,
    title: str = "",
    company: str = "",
    location: str = "",
    work_mode: str = "",
    job_type: str = "",
) -> str:
    header_lines = []
    for label, value in [
        ("Job Title", title),
        ("Company", company),
        ("Location", location),
        ("Work Mode", work_mode),
        ("Job Type", job_type),
    ]:
        clean_value = value.strip()
        if clean_value and clean_value.lower() != "unknown":
            header_lines.append(f"{label}: {clean_value}")

    body = job_text.strip()
    if not header_lines:
        return body
    if body:
        return "\n".join(header_lines + ["", "Full Job Description:", body])
    return "\n".join(header_lines)


def _show_builder_analysis(
    job: dict[str, object],
    score_details: dict[str, object],
    profile: dict[str, object],
    applications_dir: Path,
) -> None:
    st.divider()
    st.header("Step 3: Review Fit")
    _show_analysis_summary(job, score_details, profile)

    analysis_key = _score_analysis_key(score_details)
    if st.session_state.get("builder_packet_analysis_key") != analysis_key:
        st.session_state.pop("builder_packet", None)
        st.session_state.pop("builder_packet_analysis_key", None)
        st.session_state.pop("builder_saved_packet", None)

    with st.expander("Detailed fit analysis"):
        _show_analysis_details(score_details)

    st.divider()
    st.header("Step 4: Review Evidence")
    evidence_answers = _show_evidence_check(profile, score_details, analysis_key)

    generate_clicked = False
    st.divider()
    st.header("Step 5: Generate Packet")
    st.caption("Generate reviewable drafts using the parsed job, fit analysis, profile, proof blocks, and evidence answers.")
    if _is_skip_recommendation(score_details):
        with st.expander("Generate a packet for this Skip role anyway"):
            st.caption(
                "Use this only for testing, saving for later, or a deliberate exception."
            )
            generate_clicked = st.button(
                "Generate Packet Anyway",
                key="builder_generate_packet_anyway",
            )
    else:
        generate_clicked = st.button(
            "Generate Packet",
            type="primary",
            key="builder_generate_packet",
        )

    if generate_clicked:
        st.session_state["builder_packet"] = generate_application_packet(
            score_details,
            profile.get("resume_text"),
            evidence_answers=evidence_answers,
        )
        st.session_state["builder_packet_analysis_key"] = analysis_key
        st.session_state["builder_evidence_answers"] = evidence_answers
        st.session_state.pop("builder_saved_packet", None)

    packet = st.session_state.get("builder_packet")
    if not isinstance(packet, dict):
        st.info("Review the fit and evidence suggestions, then generate the packet drafts.")
        return

    _show_packet_preview(packet, score_details)
    _show_next_action_section(packet, score_details)
    _show_builder_save_controls(packet, score_details, applications_dir)

    saved_packet = st.session_state.get("builder_saved_packet")
    if isinstance(saved_packet, dict):
        st.success(f"Saved packet: {saved_packet['folder_path']}")
        st.caption("Review saved packets below, or open that folder from your file browser.")


def _show_builder_save_controls(
    packet: dict[str, object],
    score_details: dict[str, object],
    applications_dir: Path,
) -> None:
    existing_packets = list_saved_application_packets(applications_dir)
    duplicates = _find_duplicate_saved_packets(score_details, existing_packets)

    if duplicates:
        st.warning(
            "A packet for this job already exists. Save another version only if "
            "you intentionally want to keep a new copy."
        )
        st.caption(
            "Existing packet: "
            + _format_saved_packet_label(duplicates[0])
        )
        save_clicked = st.button(
            "Save as New Version",
            type="secondary",
            key="builder_save_duplicate_packet",
        )
    else:
        save_clicked = st.button(
            "Save Packet",
            type="primary",
            key="builder_save_packet",
        )

    if save_clicked:
        save_result = save_application_packet(packet, score_details, applications_dir)
        st.session_state["builder_saved_packet"] = save_result


def _show_analysis_details(score_details: dict[str, object]) -> None:
    st.subheader("Fit Details")
    detail_cols = st.columns(2)
    with detail_cols[0]:
        _show_inline_list("Matched / supported overlap", score_details.get("matched_keywords"))
        _show_inline_list(
            "Hard requirements detected",
            _job_requirement_list(score_details, "hard_requirements"),
        )
    with detail_cols[1]:
        _show_inline_list(
            "Experience requirements",
            _job_requirement_list(score_details, "experience_requirements"),
        )
        _show_inline_list("Concerns", score_details.get("concerns"))


def _show_analysis_summary(
    job: dict[str, object],
    score_details: dict[str, object],
    profile: dict[str, object],
) -> None:
    title = str(job.get("title", "Unknown"))
    company = str(job.get("company", "Unknown"))
    recommendation = str(score_details.get("recommendation", "Unknown"))
    score = score_details.get("score", "Unknown")
    hard_requirement_count = len(_job_requirement_list(score_details, "hard_requirements"))

    metric_cols = st.columns(4)
    metric_cols[0].metric("Recommendation", recommendation)
    metric_cols[1].metric("Score", f"{score}/100")
    metric_cols[2].metric("Role", title)
    metric_cols[3].metric("Hard requirements", str(hard_requirement_count))
    st.caption(
        f"{title} at {company} | Location: {job.get('location', 'Unknown')} | "
        f"Work mode: {job.get('work_mode', 'Unknown')}"
    )

    guidance = _recommendation_guidance(score_details)
    if guidance["tone"] == "success":
        st.success(guidance["message"])
    elif guidance["tone"] == "warning":
        st.warning(guidance["message"])
    else:
        st.info(guidance["message"])

    suggestions = _suggest_evidence_answers(profile, _evidence_requirements(score_details))
    missing_or_review = [
        requirement
        for requirement, suggestion in suggestions.items()
        if suggestion["status"] in {"Not sure", "No evidence"}
    ]
    proof_names = _suggested_proof_block_names(profile, score_details)

    summary_cols = st.columns(3)
    with summary_cols[0]:
        st.markdown("**Strongest matches**")
        _show_plain_list(_as_tuple_items(score_details.get("matched_keywords"))[:5])
    with summary_cols[1]:
        st.markdown("**Needs evidence review**")
        _show_plain_list(missing_or_review[:5])
    with summary_cols[2]:
        st.markdown("**Suggested proof blocks**")
        _show_plain_list(proof_names[:4])


def _show_evidence_check(
    profile: dict[str, object],
    score_details: dict[str, object],
    analysis_key: tuple[object, ...],
) -> dict[str, dict[str, str]]:
    requirements = _evidence_requirements(score_details)
    if not requirements:
        return {}

    suggestions = _suggest_evidence_answers(profile, requirements)
    summary_counts = _evidence_suggestion_counts(suggestions)
    st.subheader("Evidence Check")
    st.caption(
        "Auto-suggestions come from the selected profile. Review before generating; suggestions are not verified truth."
    )
    metric_cols = st.columns(4)
    metric_cols[0].metric("Strong", summary_counts["Strong evidence"])
    metric_cols[1].metric("Some", summary_counts["Some evidence"])
    metric_cols[2].metric("Needs review", summary_counts["Not sure"])
    metric_cols[3].metric("No evidence", summary_counts["No evidence"])
    st.caption(
        "Use suggested evidence by leaving the prefilled values unchanged, "
        "or edit any status/notes that are wrong."
    )

    evidence_answers = {}
    profile_id = str(profile.get("profile_id", "profile"))
    analysis_slug = _requirement_slug("|".join(str(item) for item in analysis_key))
    groups = [
        ("Suggested Supported Evidence", ["Strong evidence", "Some evidence"], False),
        ("Needs Review", ["Not sure"], True),
        ("Missing / No Evidence", ["No evidence"], False),
    ]
    for label, statuses, expanded in groups:
        grouped_requirements = [
            requirement
            for requirement in requirements
            if suggestions[requirement]["status"] in statuses
        ]
        if not grouped_requirements:
            continue
        with st.expander(f"{label} ({len(grouped_requirements)})", expanded=expanded):
            for requirement in grouped_requirements:
                suggestion = suggestions[requirement]
                requirement_slug = _requirement_slug(requirement)
                key_prefix = f"evidence_{profile_id}_{analysis_slug}_{requirement_slug}"
                st.markdown(f"**{requirement}**")
                st.caption(f"Suggested: {suggestion['status']} - {suggestion['notes']}")
                status = st.selectbox(
                    "Evidence status",
                    EVIDENCE_STATUS_OPTIONS,
                    index=EVIDENCE_STATUS_OPTIONS.index(suggestion["status"]),
                    key=f"{key_prefix}_status",
                )
                notes = st.text_area(
                    "Evidence notes",
                    value=suggestion["notes"],
                    key=f"{key_prefix}_notes",
                    height=80,
                    placeholder="Example: Built small API projects in coursework and used REST APIs in local tools.",
                )
                evidence_answers[requirement] = {
                    "status": status,
                    "notes": notes.strip(),
                }
    return evidence_answers


def _suggested_proof_block_names(
    profile: dict[str, object],
    score_details: dict[str, object],
) -> list[str]:
    proof_blocks = profile.get("proof_blocks")
    if not isinstance(proof_blocks, list):
        return []
    requirements = _evidence_requirements(score_details)
    names = []
    for block in proof_blocks:
        if any(_proof_block_matches_requirement(block, requirement.lower()) for requirement in requirements):
            name = str(block.get("name", "")).strip()
            if name and name not in names:
                names.append(name)
    return names


def _suggest_evidence_answers(
    profile: dict[str, object],
    requirements: list[str],
) -> dict[str, dict[str, str]]:
    profile_text = str(profile.get("resume_text") or "")
    proof_blocks = profile.get("proof_blocks")
    if not isinstance(proof_blocks, list):
        proof_blocks = []
    return {
        requirement: _suggest_evidence_for_requirement(
            profile_text,
            requirement,
            proof_blocks=proof_blocks,
        )
        for requirement in requirements
    }


def _suggest_evidence_for_requirement(
    profile_text: str,
    requirement: str,
    proof_blocks: list[dict[str, object]] | None = None,
) -> dict[str, str]:
    normalized_profile = profile_text.lower()
    normalized_requirement = requirement.lower()
    use_carefully = _profile_marks_use_carefully(normalized_profile, normalized_requirement)

    if use_carefully:
        return {
            "status": "Not sure",
            "notes": (
                "Auto-suggested from profile: this area is marked use carefully. "
                "Do not include unless there is direct project/work evidence."
            ),
        }

    proof_suggestion = _suggest_from_proof_blocks(normalized_requirement, proof_blocks or [])
    if proof_suggestion:
        return proof_suggestion

    if "python" in normalized_requirement:
        return _suggest_from_markers(
            normalized_profile,
            ["python", "flask", "streamlit", "automation scripts", "local tooling", "coursework"],
            "Strong evidence",
            "Some evidence",
            "Profile mentions Python, Flask/Streamlit tools, automation workflows, or local tooling. Verify exact examples before using.",
        )
    if "api" in normalized_requirement:
        return _suggest_from_markers(
            normalized_profile,
            ["rest api", "rest apis", "json", "openai api", "api tooling", "backend", "fastapi"],
            "Some evidence",
            "Some evidence",
            "Profile mentions REST APIs/JSON/OpenAI API or backend/API-related project work. Confirm concrete examples.",
        )
    if "sql" in normalized_requirement or "data" in normalized_requirement or "database" in normalized_requirement:
        return _suggest_from_markers(
            normalized_profile,
            ["sql", "sqlite", "dashboards", "logs", "data analysis", "reports", "data-backed"],
            "Some evidence",
            "Some evidence",
            "Profile mentions SQL/SQLite, dashboards, logs, reports, or data-backed troubleshooting. Confirm exact examples.",
        )
    if "prompt" in normalized_requirement:
        if _has_strong_ai_evidence(normalized_profile):
            return {
                "status": "Strong evidence",
                "notes": (
                    "Auto-suggested from profile: explicit production/deployed/"
                    "professional AI or LLM system evidence appears in the profile. "
                    "Confirm the exact example before using."
                ),
            }
        return _suggest_from_markers(
            normalized_profile,
            ["prompt engineering", "openai api", "codex", "ai-assisted", "structured prompting"],
            "Some evidence",
            "Some evidence",
            "Profile mentions prompt engineering or AI-assisted workflow design. Avoid overstating production experience.",
        )
    if (
        "llm" in normalized_requirement
        or "large language" in normalized_requirement
        or "ai agent" in normalized_requirement
        or "agentic" in normalized_requirement
        or "agent-building" in normalized_requirement
    ):
        if _has_strong_ai_evidence(normalized_profile):
            return {
                "status": "Strong evidence",
                "notes": (
                    "Auto-suggested from profile: explicit production/deployed/"
                    "professional AI or LLM system evidence appears in the profile. "
                    "Confirm the exact example before using."
                ),
            }
        return _suggest_from_markers(
            normalized_profile,
            ["openai api", "assistant", "packet builder", "ai tooling", "local assistant", "agent"],
            "Some evidence",
            "Not sure",
            "Profile suggests AI assistant/tooling project exposure. Do not claim production agent experience unless supported.",
        )
    if "automation" in normalized_requirement or "workflow" in normalized_requirement:
        return _suggest_from_markers(
            normalized_profile,
            ["workflow automation", "automation projects", "packet generation", "assistant projects", "scripts", "process improvement"],
            "Some evidence",
            "Some evidence",
            "Profile mentions workflow automation and local tool/project work. Confirm specific project examples.",
        )
    if "cloud" in normalized_requirement or "deployment" in normalized_requirement or "aws" in normalized_requirement:
        return _suggest_from_markers(
            normalized_profile,
            ["cloud", "deployment", "deployed", "aws", "azure", "serverless"],
            "Some evidence",
            "Not sure",
            "Profile mentions cloud or deployment exposure. Verify before claiming deployed or production experience.",
        )
    if "unit testing" in normalized_requirement or "test driven" in normalized_requirement or "testing" in normalized_requirement:
        return _suggest_from_markers(
            normalized_profile,
            ["pytest", "unit testing", "evaluation scripts", "validation"],
            "Some evidence",
            "Not sure",
            "Profile may mention pytest, unit testing, or validation scripts. Confirm exact project evidence.",
        )
    return {
        "status": "Not sure",
        "notes": "Review manually against resume, projects, coursework, or work examples.",
    }


def _suggest_from_proof_blocks(
    normalized_requirement: str,
    proof_blocks: list[dict[str, object]],
) -> dict[str, str] | None:
    matching_blocks = [
        block
        for block in proof_blocks
        if _proof_block_matches_requirement(block, normalized_requirement)
    ]
    if not matching_blocks:
        return None

    names = [str(block.get("name", "")).strip() for block in matching_blocks if str(block.get("name", "")).strip()]
    name_text = _format_names(names[:3])
    if not name_text:
        return None

    if "python" in normalized_requirement:
        return {
            "status": "Strong evidence",
            "notes": (
                f"Auto-suggested from profile: profile evidence includes {name_text} "
                "with Python-related work. Verify exact bullets before using."
            ),
        }
    if "api" in normalized_requirement:
        return {
            "status": "Some evidence",
            "notes": (
                f"Auto-suggested from profile: profile evidence includes {name_text} "
                "with API or JSON workflow exposure. Confirm concrete examples."
            ),
        }
    if "sql" in normalized_requirement or "data" in normalized_requirement or "database" in normalized_requirement:
        return {
            "status": "Some evidence",
            "notes": (
                f"Auto-suggested from profile: profile evidence includes {name_text} "
                "with SQLite logging/reporting, dashboards, or data-backed troubleshooting."
            ),
        }
    if "automation" in normalized_requirement or "workflow" in normalized_requirement:
        return {
            "status": "Some evidence",
            "notes": (
                f"Auto-suggested from profile: profile evidence includes workflow automation "
                f"in {name_text}. Confirm exact examples."
            ),
        }
    if (
        "prompt" in normalized_requirement
        or "llm" in normalized_requirement
        or "large language" in normalized_requirement
        or "ai agent" in normalized_requirement
        or "agentic" in normalized_requirement
        or "agent-building" in normalized_requirement
    ):
        if any(_has_strong_ai_evidence(_proof_block_search_text(block)) for block in matching_blocks):
            return {
                "status": "Strong evidence",
                "notes": (
                    f"Auto-suggested from profile: profile evidence includes {name_text} "
                    "with explicit production/deployed/professional AI evidence. Confirm the exact example before using."
                ),
            }
        return {
            "status": "Some evidence",
            "notes": (
                f"Auto-suggested from profile: profile evidence includes {name_text} "
                "with AI assistant/tooling or prompt workflow exposure. Do not claim production experience unless supported."
            ),
        }
    return {
        "status": "Some evidence",
        "notes": (
            f"Auto-suggested from profile: profile evidence includes {name_text}. "
            "Confirm exact bullets before using."
        ),
    }


def _proof_block_matches_requirement(
    proof_block: dict[str, object],
    normalized_requirement: str,
) -> bool:
    text = _proof_block_search_text(proof_block)
    marker_groups = []
    if "python" in normalized_requirement:
        marker_groups.append(["python"])
    if "api" in normalized_requirement:
        marker_groups.append(["api", "apis", "json", "openai api", "broker/data api"])
    if "sql" in normalized_requirement or "data" in normalized_requirement or "database" in normalized_requirement:
        marker_groups.append(["sql", "sqlite", "pandas", "dashboard", "report", "logs", "data"])
    if "automation" in normalized_requirement or "workflow" in normalized_requirement:
        marker_groups.append(["automation", "workflow", "packet generation", "cli", "support tools"])
    if any(marker in normalized_requirement for marker in ["ai agent", "llm", "large language", "prompt", "agentic", "agent-building"]):
        marker_groups.append(["openai", "prompt", "assistant", "ai", "agent", "codex"])
    if not marker_groups:
        marker_groups.append([normalized_requirement])
    return any(any(marker in text for marker in markers) for markers in marker_groups)


def _proof_block_search_text(proof_block: dict[str, object]) -> str:
    values = [str(proof_block.get("name", ""))]
    for key in ["tools", "bullets", "target_role_tags"]:
        value = proof_block.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value)
    values.append(str(proof_block.get("raw_text", "")))
    return " ".join(values).lower()


def _format_names(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return " / ".join(names)


def _suggest_from_markers(
    normalized_profile: str,
    markers: list[str],
    matched_status: str,
    unmatched_status: str,
    note: str,
) -> dict[str, str]:
    if any(marker in normalized_profile for marker in markers):
        return {"status": matched_status, "notes": f"Auto-suggested from profile: {note}"}
    return {
        "status": unmatched_status,
        "notes": "Review manually; profile text did not clearly prove this requirement.",
    }


def _has_strong_ai_evidence(normalized_profile: str) -> bool:
    return any(
        marker in normalized_profile
        for marker in [
            "production ai agent",
            "deployed ai agent",
            "professional ai engineering",
            "enterprise llm workflow",
            "owned production llm",
            "owned production agent",
            "production llm/agent system",
            "deployed agentic system",
            "real users using the ai agent",
            "customers using the ai agent",
        ]
    )


def _profile_marks_use_carefully(
    normalized_profile: str,
    normalized_requirement: str,
) -> bool:
    careful_markers = {
        ".net": [".net", "c#"],
        "c#": [".net", "c#"],
        "angular": ["angular"],
        "typescript": ["typescript-heavy", "typescript"],
        "kubernetes": ["kubernetes"],
        "docker": ["docker"],
        "devops": ["advanced devops", "devops"],
        "cloud": ["cloud platforms", "cloud"],
        "deployment": ["cloud platforms", "deployment"],
        "production ml": ["production ml", "ml engineering"],
    }
    if "skills to use carefully" not in normalized_profile and "use carefully" not in normalized_profile:
        return False
    return any(
        marker in normalized_profile and any(term in normalized_requirement for term in terms)
        for marker, terms in careful_markers.items()
    )


def _evidence_suggestion_counts(
    suggestions: dict[str, dict[str, str]],
) -> dict[str, int]:
    counts = {
        "Strong evidence": 0,
        "Some evidence": 0,
        "Not sure": 0,
        "No evidence": 0,
    }
    for suggestion in suggestions.values():
        status = suggestion.get("status", "Not sure")
        if status not in counts:
            status = "Not sure"
        counts[status] += 1
    return counts


def _show_packet_preview(
    packet: dict[str, object],
    score_details: dict[str, object],
) -> None:
    st.subheader("Packet Draft Preview")
    st.caption("These are local drafts. Review every claim before sending anything to an employer.")
    strategy = packet.get("resume_strategy_sections")
    fit_verdict = ""
    if isinstance(strategy, dict):
        fit_verdict = str(strategy.get("fit_verdict") or "")
    if fit_verdict:
        st.success(f"Fit Verdict: {fit_verdict}")
    st.info(str(packet.get("apply_recommendation", "")))

    preview_tabs = st.tabs(
        [
            "Tailored Resume",
            "Cover Letter",
            "Recruiter Message",
            "Checklist",
            "Resume Strategy",
            "Decision Summary",
            "Score Explanation",
            "Risk Notes",
        ]
    )
    with preview_tabs[0]:
        st.markdown(str(packet.get("tailored_resume_draft", "")))
    with preview_tabs[1]:
        st.text(str(packet.get("cover_letter_draft", "")))
    with preview_tabs[2]:
        st.text(str(packet.get("recruiter_message", "")))
    with preview_tabs[3]:
        _show_plain_list(packet.get("application_checklist"))
    with preview_tabs[4]:
        _show_resume_strategy(packet)
    with preview_tabs[5]:
        _show_decision_summary(packet.get("decision_summary"))
    with preview_tabs[6]:
        _show_score_explanation(score_details.get("explanation"))
    with preview_tabs[7]:
        _show_plain_list(packet.get("risk_notes"))


def _show_next_action_section(
    packet: dict[str, object],
    score_details: dict[str, object],
) -> None:
    st.divider()
    st.header("Step 6: Decide Next Action")
    recommendation = str(score_details.get("recommendation", "Unknown"))
    decision = "Review"
    decision_summary = packet.get("decision_summary")
    if isinstance(decision_summary, dict):
        decision = str(decision_summary.get("decision", "Review"))
    st.caption(
        f"Recommendation: {recommendation}. Decision summary: {decision}. "
        "Use this as a working note before saving or applying."
    )
    next_action = st.radio(
        "What should happen next?",
        [
            "Edit resume first",
            "Apply today",
            "Save for later",
            "Skip/deprioritize",
        ],
        key="builder_next_action_choice",
        horizontal=True,
    )
    next_action_notes = {
        "Edit resume first": "Review the tailored resume draft, replace generic bullets with real examples, then decide whether to apply.",
        "Apply today": "Use the packet as a checklist, review all claims, then submit manually outside this app.",
        "Save for later": "Save the packet and revisit it from the saved packet review queue.",
        "Skip/deprioritize": "Save only if you want a record; otherwise move on to a stronger posting.",
    }
    st.info(next_action_notes[next_action])


def _show_decision_summary(value: object) -> None:
    if not isinstance(value, dict):
        st.caption("No decision summary was generated.")
        return
    st.subheader(str(value.get("decision", "Review")))
    _show_plain_list(value.get("why"))
    st.markdown("**Next action**")
    st.write(str(value.get("next_action", "Review before applying.")))


def _show_resume_strategy(packet: dict[str, object]) -> None:
    strategy = packet.get("resume_strategy_sections")
    if isinstance(strategy, dict):
        st.subheader(str(strategy.get("fit_verdict", "Review Fit")))
        st.write(str(strategy.get("fit_summary", "")))
        st.markdown("**Strong / Supported Overlap**")
        _show_plain_list(strategy.get("supported_overlap"))
        st.markdown("**Major Requirements To Verify Before Applying**")
        _show_plain_list(strategy.get("major_requirements_to_verify"))
        st.markdown("**Evidence Summary**")
        _show_evidence_summary(packet.get("evidence_summary"))
        st.markdown("**Apply Only If**")
        _show_plain_list(strategy.get("apply_only_if"))
        st.markdown("**Consider Skipping Or Deprioritizing If**")
        _show_plain_list(strategy.get("consider_skipping_if"))
        st.markdown("**Transferable Support Evidence**")
        _show_plain_list(strategy.get("transferable_support_evidence"))
    else:
        _show_plain_list(packet.get("resume_focus_areas"))

    st.markdown("**Suggested Resume Bullets**")
    _show_plain_list(packet.get("resume_bullet_suggestions"))
    st.markdown("**Keywords / Themes To Include Honestly**")
    _show_plain_list(packet.get("keywords_to_include_honestly"))
    st.markdown("**Keywords To Verify Or Avoid**")
    _show_plain_list(packet.get("keywords_to_avoid_or_verify"))
    st.markdown("**Missing Proof Next Actions**")
    _show_plain_list(packet.get("missing_proof_actions"))


def _show_evidence_summary(value: object) -> None:
    if not isinstance(value, dict):
        st.caption("No evidence answers were provided.")
        return
    for label, key in [
        ("Supported evidence", "supported_evidence"),
        ("Partial evidence", "partial_evidence"),
        ("Missing proof", "missing_proof"),
        ("Needs verification", "needs_verification"),
    ]:
        st.markdown(f"*{label}*")
        items = value.get(key)
        if not isinstance(items, list) or not items:
            st.caption("None.")
            continue
        for item in items:
            if isinstance(item, dict):
                notes = str(item.get("notes") or "")
                suffix = f": {notes}" if notes else ""
                st.write(f"- {item.get('requirement', 'Requirement')}{suffix}")


def _show_saved_packet_review(
    profile: dict[str, object],
    applications_dir: Path,
    legacy_root: Path | None,
) -> None:
    st.header("Review Saved Packets")
    st.caption(f"Profile: {profile['display_name']}")
    st.caption(
        "Saved packets are local application prep folders. They are not submitted "
        "anywhere; use them to decide, tailor, and track next actions."
    )
    saved_packets = list_saved_application_packets(applications_dir, legacy_root=legacy_root)
    if not saved_packets:
        st.info("No saved packets for this profile yet.")
        return

    saved_packets = sort_saved_application_packets(saved_packets, "Newest saved first")
    show_duplicate_versions = st.checkbox(
        "Show older duplicate versions",
        key="guided_show_duplicate_versions",
    )
    table_packets = _saved_packets_for_queue(
        saved_packets,
        include_duplicate_versions=show_duplicate_versions,
    )
    table_rows = [_saved_packet_table_row(packet) for packet in table_packets]
    st.dataframe(table_rows, width="stretch", hide_index=True)

    packet_options = {
        _format_saved_packet_label(packet): packet
        for packet in table_packets
    }
    selected_label = st.selectbox(
        "Preview saved packet",
        list(packet_options),
        key="guided_saved_packet_preview",
    )
    selected_packet = packet_options[selected_label]
    packet_details = load_saved_application_packet(selected_packet["folder_path"])
    if packet_details is None:
        st.warning("This saved packet could not be loaded.")
        return

    st.caption(f"Saved folder: {packet_details['folder_path']}")
    _show_saved_packet_status_controls(packet_details, key_prefix="guided_saved_status")
    _show_packet_preview(
        packet_details["application_packet"],
        packet_details["score_summary"],
    )


def _saved_packet_table_row(packet: dict[str, object]) -> dict[str, object]:
    version_count = int(packet.get("duplicate_version_count", 1) or 1)
    job_label = str(packet["title"])
    if version_count > 1:
        job_label = f"{job_label} ({version_count} versions)"

    return {
        "Saved date": packet["saved_date"],
        "Job": job_label,
        "Company": packet["company"],
        "Score": packet["score"],
        "Recommendation": packet["recommendation"],
        "Status": packet["status"],
        "Next action": packet["next_action"],
        "Next action date": packet["next_action_date"],
    }


def _show_dashboard(
    tracked_jobs: list[dict[str, str]],
    profile: dict[str, object],
    applications_dir: Path,
    legacy_root: Path | None,
) -> None:
    st.header("Dashboard")

    status_counts = Counter(row["status"] or "Unknown" for row in tracked_jobs)
    recommendation_counts = Counter(
        row["recommendation"] or "Unknown" for row in tracked_jobs
    )
    apply_new_count = _count_apply_new_jobs(tracked_jobs)
    follow_up_count = sum(1 for row in tracked_jobs if row["follow_up_date"])

    metric_cols = st.columns(4)
    metric_cols[0].metric("Tracked jobs", len(tracked_jobs))
    metric_cols[1].metric("Apply + New", apply_new_count)
    metric_cols[2].metric("Follow-ups set", follow_up_count)
    metric_cols[3].metric(
        "Saved applications",
        len(list_saved_application_packets(applications_dir, legacy_root=legacy_root)),
    )
    st.caption(f"Saved application metrics use profile: {profile['display_name']}")

    status_col, recommendation_col = st.columns(2)
    with status_col:
        st.subheader("By Status")
        _show_counter(status_counts)

    with recommendation_col:
        st.subheader("By Recommendation")
        _show_counter(recommendation_counts)

    st.subheader("Recommended Next Action")
    next_action = _get_recommended_next_action(
        tracked_jobs,
        apply_new_count,
        follow_up_count,
    )
    if tracked_jobs:
        st.info(next_action)
    else:
        st.warning(next_action)


def _show_today_tab(
    profile: dict[str, object],
    applications_dir: Path,
    legacy_root: Path | None,
) -> None:
    st.header("Today")
    st.caption(f"Profile: {profile['display_name']}")
    saved_packets = list_saved_application_packets(applications_dir, legacy_root=legacy_root)
    if not saved_packets:
        st.info("No saved applications found yet.")
        return

    queue = get_today_application_queue(saved_packets)
    total_items = sum(len(items) for items in queue.values())

    metric_cols = st.columns(5)
    metric_cols[0].metric("Needs attention", total_items)
    metric_cols[1].metric("Overdue", len(queue["overdue"]))
    metric_cols[2].metric("Due today", len(queue["due_today"]))
    metric_cols[3].metric("Due soon", len(queue["due_soon"]))
    metric_cols[4].metric(
        "Applied follow-up",
        len(queue["applied_without_follow_up"]),
    )
    st.metric("Ready to apply", len(queue["ready_to_apply_without_date"]))

    if total_items == 0:
        st.success("No saved applications need attention today.")
        return

    _show_today_group("Overdue", queue["overdue"])
    _show_today_group("Due today", queue["due_today"])
    _show_today_group("Due soon", queue["due_soon"])
    _show_today_group("Ready to apply", queue["ready_to_apply_without_date"])
    _show_today_group(
        "Applied: add follow-up date",
        queue["applied_without_follow_up"],
    )
    _show_today_group("Other needs attention", queue["other_needs_attention"])
    st.caption("Update dates and statuses from the Saved applications tab.")


def _show_today_group(label: str, applications: list[dict[str, object]]) -> None:
    if not applications:
        return

    with st.expander(f"{label} ({len(applications)})", expanded=True):
        for application in applications:
            st.write(f"**{application['title']}** at {application['company']}")
            st.write(f"Status: {application['status']} | Score: {application['score']}")
            st.write(f"Next action date: {application['next_action_date'] or 'Not set'}")
            st.write(f"Next action note: {application['next_action_note'] or 'None'}")
            st.write(f"Attention: {application['attention_reason']}")
            st.caption(str(application["folder_path"]))
            st.divider()


def _show_score_job_tab(
    profile: dict[str, object],
    applications_dir: Path,
) -> None:
    st.header("Score a Job")
    st.caption(f"Scoring with profile: {profile['display_name']}")
    job_text = _get_job_text_input("score")

    if st.button("Score job", type="primary", key="score_job_button"):
        if not job_text.strip():
            st.error("Paste a job posting or upload a .txt file before scoring.")
        else:
            job = parse_job_text(job_text)
            score_details = score_job(job)
            st.session_state["scored_job"] = job
            st.session_state["score_details"] = score_details
            st.session_state["scored_job_text"] = job_text
            st.session_state.pop("save_message", None)
            st.session_state.pop("score_application_packet", None)
            st.session_state.pop("saved_score_application_packet", None)

    job = st.session_state.get("scored_job")
    score_details = st.session_state.get("score_details")
    if not job or not score_details:
        st.caption("Score a posting to review fit and save it to the tracker.")
        return

    _show_score_summary(job, score_details, profile, applications_dir)

    if st.button("Save to tracker", key="score_save_to_tracker"):
        save_result = save_job_result(JOBS_CSV_PATH, job, score_details)
        st.session_state["save_message"] = save_result

    save_message = st.session_state.get("save_message")
    if save_message:
        if save_message["saved"]:
            st.success(save_message["message"])
        else:
            st.info(save_message["message"])


def _show_tracker_tab(tracked_jobs: list[dict[str, str]]) -> None:
    st.header("Tracker")

    if not tracked_jobs:
        st.info("No tracked jobs yet. Score a posting and save it to start.")
        return

    status_options = ["All"] + sorted(
        {row["status"] for row in tracked_jobs if row["status"]}
    )
    recommendation_options = ["All"] + sorted(
        {row["recommendation"] for row in tracked_jobs if row["recommendation"]}
    )

    filter_cols = st.columns(2)
    selected_status = filter_cols[0].selectbox(
        "Status",
        status_options,
        key="tracker_filter_status",
    )
    selected_recommendation = filter_cols[1].selectbox(
        "Recommendation",
        recommendation_options,
        key="tracker_filter_recommendation",
    )

    filtered_jobs = filter_tracked_jobs(
        tracked_jobs,
        status=None if selected_status == "All" else selected_status,
        recommendation=(
            None if selected_recommendation == "All" else selected_recommendation
        ),
    )

    high_priority_jobs = [
        row
        for row in filtered_jobs
        if row["recommendation"].lower() == "apply"
        and row["status"].lower() == "new"
    ]
    if high_priority_jobs:
        st.success(
            f"{len(high_priority_jobs)} high-priority job(s): Apply recommendation and New status."
        )

    st.dataframe(filtered_jobs, width="stretch", hide_index=True)
    _show_status_update_controls(filtered_jobs)


def _show_application_packets_tab(profile: dict[str, object]) -> None:
    st.header("Application Packets")

    job_path_text = st.text_input(
        "Job posting file path",
        value=str(PROJECT_ROOT / "data" / "sample_job.txt"),
        key="legacy_packet_job_path",
    )
    resume_path_text = st.text_input(
        "Local resume/profile path",
        value=str(profile.get("resume_path") or DEFAULT_RESUME_PATH),
        key="legacy_packet_resume_path",
    )

    if st.button("Generate packet", type="primary", key="legacy_generate_packet"):
        try:
            result = generate_application_materials(
                Path(job_path_text),
                Path(resume_path_text),
                OUTPUT_DIR,
            )
        except (FileNotFoundError, ValueError) as error:
            st.error(str(error))
        else:
            st.success(f"Generated packet: {result['output_dir']}")
            st.write("Generated files:")
            for output_path in result["output_paths"].values():
                st.write(str(output_path))

    packet_dirs = _list_packet_dirs()
    if not packet_dirs:
        st.info("No application packets found yet.")
        return

    st.subheader("Existing Packets")
    selected_packet = st.selectbox(
        "Packet folder",
        packet_dirs,
        format_func=lambda path: path.name,
        key="legacy_packet_folder",
    )
    st.write(str(selected_packet))

    match_notes_path = selected_packet / "match_notes.md"
    if match_notes_path.exists():
        st.subheader("Match Notes Preview")
        st.markdown(match_notes_path.read_text(encoding="utf-8"))
    else:
        st.caption("No match_notes.md file found in this packet.")


def _show_saved_applications_tab(
    profile: dict[str, object],
    applications_dir: Path,
    legacy_root: Path | None,
) -> None:
    st.header("Saved applications")
    st.caption(f"Profile: {profile['display_name']}")

    saved_packets = list_saved_application_packets(applications_dir, legacy_root=legacy_root)
    if not saved_packets:
        st.info("No saved application packets found yet.")
        return

    _show_saved_application_metrics(saved_packets)
    filtered_packets = _show_saved_application_filters(saved_packets)
    if not filtered_packets:
        st.info("No saved applications match the current filters.")
        return

    table_rows = [
        {
            "saved_date": packet["saved_date"],
            "title": packet["title"],
            "company": packet["company"],
            "location": packet["location"],
            "work_mode": packet["work_mode"],
            "score": packet["score"],
            "recommendation": packet["recommendation"],
            "status": packet["status"],
            "status_updated_at": packet["status_updated_at"],
            "applied_date": packet["applied_date"],
            "next_action_date": packet["next_action_date"],
            "next_action_note": packet["next_action_note"],
            "needs_attention": packet["needs_attention"],
            "attention_reason": packet["attention_reason"],
            "apply_recommendation": packet["apply_recommendation"],
            "next_action": packet["next_action"],
            "matched_keywords": packet["matched_keywords_count"],
            "concerns": packet["concern_count"],
            "folder_path": str(packet["folder_path"]),
        }
        for packet in filtered_packets
    ]
    st.dataframe(table_rows, width="stretch", hide_index=True)

    packet_options = {
        _format_saved_packet_label(packet): packet
        for packet in filtered_packets
    }
    selected_label = st.selectbox(
        "View packet details",
        list(packet_options),
        key="advanced_saved_packet_details",
    )
    selected_packet = packet_options[selected_label]
    packet_details = load_saved_application_packet(selected_packet["folder_path"])
    if packet_details is None:
        st.warning("This saved packet could not be loaded.")
        return

    st.caption(f"Saved folder: {packet_details['folder_path']}")
    _show_saved_packet_status_controls(packet_details, key_prefix="advanced_saved_status")
    _show_saved_packet_details(packet_details["application_packet"])


def _show_saved_application_metrics(saved_packets: list[dict[str, object]]) -> None:
    status_counts = count_saved_applications_by_status(saved_packets)
    st.metric("Total saved applications", len(saved_packets))

    metric_cols = st.columns(4)
    for index, status in enumerate(APPLICATION_STATUSES):
        metric_cols[index % 4].metric(status, status_counts[status])


def _show_saved_application_filters(
    saved_packets: list[dict[str, object]],
) -> list[dict[str, object]]:
    st.subheader("Filters")
    status_options = ["All"] + APPLICATION_STATUSES
    recommendation_options = ["All"] + sorted(
        {str(packet["recommendation"]) for packet in saved_packets}
    )
    apply_recommendation_options = ["All"] + sorted(
        {str(packet["apply_recommendation"]) for packet in saved_packets}
    )
    work_mode_options = ["All"] + sorted(
        {str(packet["work_mode"]) for packet in saved_packets}
    )

    filter_cols = st.columns(4)
    selected_status = filter_cols[0].selectbox(
        "Status",
        status_options,
        key="saved_filter_status",
    )
    selected_recommendation = filter_cols[1].selectbox(
        "Recommendation",
        recommendation_options,
        key="saved_filter_recommendation",
    )
    selected_work_mode = filter_cols[2].selectbox(
        "Work mode",
        work_mode_options,
        key="saved_filter_work_mode",
    )
    selected_sort = filter_cols[3].selectbox(
        "Sort",
        SORT_OPTIONS,
        key="saved_filter_sort",
    )

    search_cols = st.columns(4)
    selected_apply_recommendation = search_cols[0].selectbox(
        "Apply recommendation",
        apply_recommendation_options,
        key="saved_filter_apply_recommendation",
    )
    min_score = search_cols[1].number_input(
        "Minimum score",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        key="saved_filter_min_score",
    )
    company_search = search_cols[2].text_input(
        "Company search",
        key="saved_filter_company_search",
    )
    text_search = search_cols[3].text_input(
        "Title/company search",
        key="saved_filter_text_search",
    )
    attention_cols = st.columns(3)
    needs_attention = attention_cols[0].checkbox(
        "Needs attention",
        key="saved_filter_needs_attention",
    )
    overdue = attention_cols[1].checkbox(
        "Overdue",
        key="saved_filter_overdue",
    )
    due_within_7_days = attention_cols[2].checkbox(
        "Due within 7 days",
        key="saved_filter_due_within_7_days",
    )

    filtered_packets = filter_saved_application_packets(
        saved_packets,
        status=None if selected_status == "All" else selected_status,
        recommendation=(
            None if selected_recommendation == "All" else selected_recommendation
        ),
        apply_recommendation=(
            None
            if selected_apply_recommendation == "All"
            else selected_apply_recommendation
        ),
        work_mode=None if selected_work_mode == "All" else selected_work_mode,
        min_score=int(min_score) if min_score else None,
        company_search=company_search or None,
        text_search=text_search or None,
        needs_attention=needs_attention,
        overdue=overdue,
        due_within_days=7 if due_within_7_days else None,
    )
    return sort_saved_application_packets(filtered_packets, selected_sort)


def _show_saved_packet_status_controls(
    packet_details: dict[str, object],
    key_prefix: str,
) -> None:
    tracking = packet_details.get("application_tracking")
    if not isinstance(tracking, dict):
        tracking = {}
    widget_key = _packet_widget_key(packet_details, key_prefix)

    current_status = str(tracking.get("status", "Interested"))
    if current_status not in APPLICATION_STATUSES:
        current_status = "Interested"

    st.subheader("Application Status")
    status = st.selectbox(
        "Status",
        APPLICATION_STATUSES,
        index=APPLICATION_STATUSES.index(current_status),
        key=f"{widget_key}_status",
    )
    notes = st.text_area(
        "Notes",
        value=str(tracking.get("notes") or ""),
        height=90,
        key=f"{widget_key}_notes",
    )
    next_action_date = st.text_input(
        "Next action date",
        value=str(tracking.get("next_action_date") or ""),
        placeholder="YYYY-MM-DD",
        key=f"{widget_key}_next_action_date",
    )
    next_action_note = st.text_input(
        "Next action note",
        value=str(tracking.get("next_action_note") or ""),
        key=f"{widget_key}_next_action_note",
    )

    applied_date = None
    if status in {"Applied", "Interview", "Offer", "Rejected", "Archived"}:
        applied_date = st.text_input(
            "Applied date",
            value=str(tracking.get("applied_date") or ""),
            placeholder="YYYY-MM-DD",
            key=f"{widget_key}_applied_date",
        )

    if st.button("Update application status", key=f"{widget_key}_update"):
        result = update_application_tracking(
            packet_details["folder_path"],
            status,
            notes=notes,
            applied_date=applied_date,
            next_action_date=next_action_date,
            next_action_note=next_action_note,
        )
        if result["updated"]:
            st.success(result["message"])
            st.rerun()
        else:
            st.warning(result["message"])


def _show_saved_packet_details(packet: object) -> None:
    if not isinstance(packet, dict):
        st.info("No saved packet details were found.")
        return

    st.subheader("Packet Details")
    st.write(packet.get("positioning_summary", "No positioning summary found."))
    st.info(str(packet.get("apply_recommendation", "No apply recommendation found.")))
    _show_packet_list("Resume focus areas", packet.get("resume_focus_areas"), expanded=True)
    _show_packet_list(
        "Suggested resume bullets",
        packet.get("resume_bullet_suggestions"),
    )
    _show_packet_list(
        "Keywords to include honestly",
        packet.get("keywords_to_include_honestly"),
    )
    _show_packet_list(
        "Keywords to verify or avoid",
        packet.get("keywords_to_avoid_or_verify"),
    )
    with st.expander("Cover letter draft"):
        st.text(str(packet.get("cover_letter_draft", "")))
    with st.expander("Recruiter message"):
        st.text(str(packet.get("recruiter_message", "")))
    _show_packet_list("Application checklist", packet.get("application_checklist"))
    _show_packet_list("Risk notes", packet.get("risk_notes"))


def _show_profile_selector() -> dict[str, object]:
    profiles = list_profiles(PROFILES_ROOT, LOCAL_PROFILES_ROOT)
    if not profiles:
        st.error("No profiles found. Add profiles/default/profile.json or a local profile.")
        st.stop()

    st.subheader("Candidate Profile")
    profile_options = {
        _format_profile_label(profile): profile
        for profile in profiles
    }
    selected_label = st.selectbox(
        "Profile",
        list(profile_options),
        key="profile_selector",
    )
    profile = profile_options[selected_label]

    st.caption(f"Profile ID: {profile['profile_id']} | Source: {profile['source']}")
    st.caption(f"Profile path: {profile['profile_path']}")
    if profile.get("is_default") and not profile.get("is_local"):
        st.warning(
            "You are using the generic default profile. Put real private profiles "
            "under local_profiles/ so resumes and saved applications stay separate."
        )
    elif profile.get("is_local"):
        st.success("Using an ignored local profile.")
    if not profile.get("resume_text"):
        st.info("This profile does not have resume_base.md text yet.")

    _show_proof_library(profile)

    if st.session_state.get("active_profile_id") != profile["profile_id"]:
        st.session_state["active_profile_id"] = profile["profile_id"]
        st.session_state.pop("score_application_packet", None)
        st.session_state.pop("saved_score_application_packet", None)
    return profile


def _show_proof_library(profile: dict[str, object]) -> None:
    profile_id = str(profile.get("profile_id", "profile"))
    proof_blocks = profile.get("proof_blocks")
    if not isinstance(proof_blocks, list):
        proof_blocks = []

    with st.expander("Profile / Proof Library"):
        st.caption(
            "Proof blocks are the evidence the app uses to support resume claims. "
            "Add projects, work examples, coursework, or tools you can explain in an interview."
        )
        if proof_blocks:
            st.markdown("**Existing proof blocks**")
            for block in proof_blocks:
                with st.container(border=True):
                    st.markdown(f"**{block.get('name', 'Untitled proof block')}**")
                    tools = block.get("tools")
                    if isinstance(tools, list) and tools:
                        st.caption("Tools / skills: " + ", ".join(str(tool) for tool in tools))
                    bullets = block.get("bullets")
                    if isinstance(bullets, list):
                        for bullet in bullets[:3]:
                            st.write(f"- {bullet}")
        else:
            st.info("No proof blocks found yet.")

        if not profile.get("is_local"):
            st.warning(
                "Create or select a local profile before saving private proof library data."
            )
            return

        st.markdown("**Add proof block**")
        with st.form(f"proof_library_add_{profile_id}"):
            name = st.text_input("Project / experience name")
            tools = st.text_input("Tools / skills", placeholder="Python, Streamlit, SQLite")
            bullets = st.text_area(
                "Evidence bullets",
                height=130,
                placeholder="Add one bullet per line. Use claims you can explain in an interview.",
            )
            use_carefully = st.text_area(
                "Use carefully notes",
                height=70,
                placeholder="Optional: list claims or tools to avoid overstating.",
            )
            target_tags = st.text_input(
                "Target role tags",
                placeholder="Optional: AI automation, backend, support engineering",
            )
            submitted = st.form_submit_button("Add Proof Block")

        if submitted:
            if not name.strip() or not bullets.strip():
                st.warning("Add a project name and at least one evidence bullet.")
                return
            append_proof_block(
                profile["resume_path"],
                name,
                tools,
                bullets,
                use_carefully_notes=use_carefully,
                target_role_tags=target_tags,
            )
            st.success("Proof block added to the selected local profile.")
            st.rerun()


def _get_job_text_input(key_prefix: str) -> str:
    pasted_text = st.text_area("Paste job posting text", height=260, key=f"{key_prefix}_text")
    uploaded_file = st.file_uploader(
        "Or upload a .txt job posting",
        type=["txt"],
        key=f"{key_prefix}_upload",
    )

    if uploaded_file is None:
        return pasted_text

    return uploaded_file.getvalue().decode("utf-8")


def _show_score_summary(
    job: dict[str, str],
    score_details: dict[str, object],
    profile: dict[str, object],
    applications_dir: Path,
) -> None:
    with st.container(border=True):
        st.subheader("Score Summary")
        title_col, company_col, location_col = st.columns(3)
        title_col.metric("Title", job["title"])
        company_col.metric("Company", job["company"])
        location_col.metric("Location", job["location"])
        st.caption(f"Work mode: {job.get('work_mode', 'Unknown')}")

        score_col, recommendation_col = st.columns(2)
        score_col.metric("Score", f"{score_details['score']}/100")
        recommendation_col.metric(
            "Recommendation",
            str(score_details["recommendation"]),
        )

        matched_keywords = _format_list(score_details["matched_keywords"])
        concerns = _format_list(score_details["concerns"])
        st.write(f"Matched keywords: {matched_keywords}")
        st.write(f"Concerns: {concerns}")
        _show_score_explanation(score_details.get("explanation"))
        _show_application_packet_prompt(score_details, profile, applications_dir)


def _show_score_explanation(explanation: object) -> None:
    if not isinstance(explanation, dict):
        st.caption("No score explanation was saved for this packet.")
        return

    st.subheader("Why this score?")
    st.write(str(explanation.get("fit_summary", "")))
    _show_explanation_list("Strengths", explanation.get("strengths"))
    _show_explanation_list("Gaps", explanation.get("gaps"))
    _show_explanation_list("Concerns", explanation.get("concerns"))
    _show_explanation_list(
        "Tailoring suggestions",
        explanation.get("tailoring_suggestions"),
    )


def _show_application_packet_prompt(
    score_details: dict[str, object],
    profile: dict[str, object],
    applications_dir: Path,
) -> None:
    st.subheader("Application packet")
    if st.button("Generate application packet", key="score_generate_application_packet"):
        st.session_state["score_application_packet"] = generate_application_packet(
            score_details,
            profile.get("resume_text"),
        )
        st.session_state.pop("saved_score_application_packet", None)

    packet = st.session_state.get("score_application_packet")
    if not isinstance(packet, dict):
        st.caption(
            "Generate a reviewable packet with resume focus areas, draft wording, "
            "a recruiter message, checklist, and risk notes."
        )
        return

    st.write(packet["positioning_summary"])
    st.info(str(packet["apply_recommendation"]))
    if st.button("Save application packet", key="score_save_application_packet"):
        save_result = save_application_packet(packet, score_details, applications_dir)
        st.session_state["saved_score_application_packet"] = save_result

    saved_packet = st.session_state.get("saved_score_application_packet")
    if isinstance(saved_packet, dict):
        st.success(f"Saved packet: {saved_packet['folder_path']}")

    _show_packet_list("Resume focus areas", packet["resume_focus_areas"], expanded=True)
    _show_packet_list(
        "Suggested resume bullets",
        packet["resume_bullet_suggestions"],
        expanded=True,
    )
    _show_packet_list(
        "Keywords to include honestly",
        packet["keywords_to_include_honestly"],
    )
    _show_packet_list(
        "Keywords to verify or avoid",
        packet["keywords_to_avoid_or_verify"],
    )
    with st.expander("Cover letter draft"):
        st.text(packet["cover_letter_draft"])
    with st.expander("Recruiter message"):
        st.text(packet["recruiter_message"])
    _show_packet_list("Application checklist", packet["application_checklist"])
    _show_packet_list("Risk notes", packet["risk_notes"])


def _show_packet_list(label: str, values: object, expanded: bool = False) -> None:
    if not isinstance(values, list):
        return

    with st.expander(label, expanded=expanded):
        if not values:
            st.caption("None.")
            return
        for value in values:
            st.write(f"- {value}")


def _show_inline_list(label: str, values: object) -> None:
    st.markdown(f"**{label}**")
    _show_plain_list(values)


def _show_plain_list(values: object) -> None:
    if not isinstance(values, list) or not values:
        st.caption("None.")
        return
    for value in values:
        st.write(f"- {value}")


def _show_explanation_list(label: str, values: object) -> None:
    if not isinstance(values, list):
        return

    with st.expander(label, expanded=label in {"Strengths", "Tailoring suggestions"}):
        for value in values:
            st.write(f"- {value}")


def _show_status_update_controls(filtered_jobs: list[dict[str, str]]) -> None:
    st.subheader("Update Status")
    if not filtered_jobs:
        st.caption("No jobs match the current filters.")
        return

    job_options = {
        _format_job_label(row): row
        for row in filtered_jobs
    }
    selected_label = st.selectbox(
        "Job",
        list(job_options),
        key="tracker_status_job",
    )
    new_status = st.selectbox(
        "New status",
        STATUS_OPTIONS,
        key="tracker_new_status",
    )

    if st.button("Update status", key="tracker_update_status"):
        selected_job = job_options[selected_label]
        result = update_job_status(
            JOBS_CSV_PATH,
            selected_job["title"],
            selected_job["company"],
            new_status,
        )
        if result["updated"]:
            st.success(result["message"])
            st.rerun()
        else:
            st.warning(result["message"])


def _show_counter(counter: Counter) -> None:
    if not counter:
        st.caption("None yet.")
        return

    for label, count in sorted(counter.items()):
        st.write(f"{label}: {count}")


def _count_apply_new_jobs(tracked_jobs: list[dict[str, str]]) -> int:
    return sum(
        1
        for row in tracked_jobs
        if row["recommendation"].lower() == "apply"
        and row["status"].lower() == "new"
    )


def _get_recommended_next_action(
    tracked_jobs: list[dict[str, str]],
    apply_new_count: int,
    follow_up_count: int,
) -> str:
    if not tracked_jobs:
        return "Score your first job posting."
    if apply_new_count:
        return "Review high-match New jobs and generate packets."
    if follow_up_count:
        return "Check follow-up dates and update statuses."
    return "Score another role or update statuses for jobs already in progress."


def _list_packet_dirs() -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []

    return sorted(path for path in OUTPUT_DIR.iterdir() if path.is_dir())


def _read_optional_text(path: Path) -> str | None:
    if not path.exists():
        return None

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return None

    return text


def _format_job_label(row: dict[str, str]) -> str:
    title = row["title"] or "Unknown title"
    company = row["company"] or "Unknown company"
    status = row["status"] or "Unknown"
    recommendation = row["recommendation"] or "Unknown"
    return f"{title} at {company} ({status}, {recommendation})"


def _format_saved_packet_label(packet: dict[str, object]) -> str:
    title = packet["title"] or "Unknown title"
    company = packet["company"] or "Unknown company"
    saved_date = packet["saved_date"] or "Unknown date"
    status = packet["status"] or "Interested"
    return f"{title} at {company} ({saved_date}, {status})"


def _format_profile_label(profile: dict[str, object]) -> str:
    label = f"{profile['display_name']} ({profile['profile_id']})"
    if profile.get("is_local"):
        return f"{label} - local"
    return label


def _legacy_root_for_profile(profile: dict[str, object]) -> Path | None:
    if profile.get("profile_id") == DEFAULT_PROFILE_ID:
        return APPLICATIONS_DIR
    return None


def _recommendation_guidance(score_details: dict[str, object]) -> dict[str, str]:
    recommendation = str(score_details.get("recommendation", "")).strip().lower()
    if recommendation == "apply":
        return {
            "tone": "success",
            "message": (
                "This looks worth turning into a packet. Review the fit details, "
                "then generate the packet."
            ),
        }
    if recommendation == "skip":
        return {
            "tone": "warning",
            "message": (
                "This role is probably not worth a full packet unless you are "
                "intentionally testing or saving it for later."
            ),
        }
    if _is_stretch_role(score_details):
        return {
            "tone": "warning",
            "message": (
                "Generate a packet only if the candidate has real evidence for "
                "the major requirements."
            ),
        }
    return {
        "tone": "info",
        "message": (
            "This may be worth applying to, but review the gaps before generating "
            "a packet."
        ),
    }


def _is_skip_recommendation(score_details: dict[str, object]) -> bool:
    return str(score_details.get("recommendation", "")).strip().lower() == "skip"


def _is_stretch_role(score_details: dict[str, object]) -> bool:
    explanation = score_details.get("explanation")
    if isinstance(explanation, dict):
        fit_summary = str(explanation.get("fit_summary", "")).lower()
        if "stretch" in fit_summary:
            return True
    return len(_job_requirement_list(score_details, "hard_requirements")) >= 6


def _find_duplicate_saved_packets(
    score_details: dict[str, object],
    saved_packets: list[dict[str, object]],
) -> list[dict[str, object]]:
    target_identity = _packet_identity_from_score(score_details)
    return [
        packet
        for packet in saved_packets
        if _packet_identity_from_saved_packet(packet) == target_identity
    ]


def _saved_packets_for_queue(
    saved_packets: list[dict[str, object]],
    include_duplicate_versions: bool = False,
) -> list[dict[str, object]]:
    if include_duplicate_versions:
        return saved_packets

    latest_by_identity: dict[tuple[str, str], dict[str, object]] = {}
    version_counts: Counter[tuple[str, str]] = Counter()
    for packet in saved_packets:
        identity = _packet_identity_from_saved_packet(packet)
        version_counts[identity] += 1
        if identity not in latest_by_identity:
            latest_by_identity[identity] = dict(packet)

    latest_packets = []
    for identity, packet in latest_by_identity.items():
        packet["duplicate_version_count"] = version_counts[identity]
        latest_packets.append(packet)
    return latest_packets


def _packet_identity_from_score(score_details: dict[str, object]) -> tuple[str, str]:
    metadata = score_details.get("job_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return (
        _normalize_packet_identity_value(metadata.get("company")),
        _normalize_packet_identity_value(_clean_packet_title(metadata.get("title"))),
    )


def _packet_identity_from_saved_packet(packet: dict[str, object]) -> tuple[str, str]:
    return (
        _normalize_packet_identity_value(packet.get("company")),
        _normalize_packet_identity_value(_clean_packet_title(packet.get("title"))),
    )


def _clean_packet_title(value: object) -> str:
    if not isinstance(value, str):
        return ""
    title = value.strip()
    for separator in [" Who ", " who ", " With ", " with "]:
        if separator in title:
            return title.split(separator, 1)[0].strip()
    return title


def _normalize_packet_identity_value(value: object) -> str:
    text = str(value or "").strip().lower()
    normalized = "".join(character if character.isalnum() else " " for character in text)
    return " ".join(normalized.split())


def _format_list(value: object) -> str:
    if isinstance(value, list) and value:
        return ", ".join(str(item) for item in value)
    return "None"


def _packet_widget_key(packet_details: dict[str, object], prefix: str) -> str:
    folder_path = str(packet_details.get("folder_path", "unknown_packet"))
    safe_path = "".join(
        character if character.isalnum() else "_"
        for character in folder_path
    ).strip("_")
    return f"{prefix}_{safe_path or 'unknown_packet'}"


def _evidence_requirements(score_details: dict[str, object]) -> list[str]:
    requirements = []
    requirements.extend(_job_requirement_list(score_details, "hard_requirements"))
    requirements.extend(_job_requirement_list(score_details, "experience_requirements"))
    return _dedupe(requirements)


def _requirement_slug(value: object) -> str:
    text = str(value or "").strip().lower()
    slug = "".join(character if character.isalnum() else "-" for character in text)
    return "-".join(part for part in slug.split("-") if part) or "requirement"


def _score_analysis_key(score_details: dict[str, object]) -> tuple[object, ...]:
    metadata = score_details.get("job_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return (
        metadata.get("title"),
        metadata.get("company"),
        metadata.get("location"),
        metadata.get("work_mode"),
        score_details.get("score"),
        score_details.get("recommendation"),
        tuple(_as_tuple_items(score_details.get("matched_keywords"))),
        tuple(_as_tuple_items(score_details.get("concerns"))),
        tuple(_job_requirement_list(score_details, "hard_requirements")),
        tuple(_job_requirement_list(score_details, "experience_requirements")),
    )


def _as_tuple_items(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _job_requirement_list(score_details: dict[str, object], key: str) -> list[str]:
    requirements = score_details.get("job_requirements")
    if not isinstance(requirements, dict):
        return []
    values = requirements.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value).strip()]


def _dedupe(values: list[str]) -> list[str]:
    deduped = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


if __name__ == "__main__":
    main()
