"""Local Streamlit UI for the job search agent."""

from collections import Counter
import html
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import quote

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
    load_saved_packet_review_sections,
    sort_saved_application_packets,
    update_application_tracking,
)
from application_packet_export import build_saved_packet_zip
from application_packet_validator import validate_saved_packet_folder
from application_packet_writer import save_application_packet
from job_parser import parse_job_text
from job_packet_agent import run_job_packet_agent
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
MAX_IMPORTED_JOB_BYTES = 1_000_000
MAX_CAPTURED_JOB_CHARS = 100_000
MIN_CAPTURED_JOB_CHARS = 80
JOB_SAMPLE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "jobs"
MIN_USEFUL_JOB_CHARS = 350
MIN_USEFUL_JOB_LINES = 8

NOISY_JOB_PAGE_LINES = {
    "apply",
    "apply now",
    "save",
    "save job",
    "share",
    "share job",
    "source link",
    "copy link",
    "job details",
    "sign in",
    "sign up",
    "create alert",
    "create job alert",
    "careers",
    "home",
    "jobs",
    "search jobs",
    "view all jobs",
    "similar jobs",
    "report job",
    "print",
    "back to search results",
}
NOISY_JOB_PAGE_PREFIXES = (
    "accept all cookies",
    "accept cookies",
    "by using this site",
    "cookie",
    "cookies",
    "privacy policy",
    "terms of use",
    "terms and conditions",
    "we use cookies",
    "this website uses cookies",
    "enable javascript",
    "skip to main content",
    "posted on",
    "share this job",
    "source:",
    "follow us",
    "connect with us",
    "all rights reserved",
    "©",
)
SOURCE_URL_PATTERN = re.compile(r"https?://[^\s<>)\"']+", flags=re.IGNORECASE)


GENERIC_EXAMPLE_JOB_TEXT = """Job Title: IT Support Specialist
Company: Example Organization
Location: Remote
Work Mode: Remote
Job Type: Full-time

Full Job Description:
We are looking for an IT Support Specialist to help employees resolve technical issues, document repeatable fixes, and escalate complex problems when needed.

Requirements:
- 2+ years of IT support, help desk, or technical support experience
- Experience supporting end users with account access, Microsoft 365, and endpoint troubleshooting
- Clear documentation habits and careful communication
"""


def main() -> None:
    st.set_page_config(page_title="Job Packet Studio", layout="wide")
    inject_app_styles()
    render_app_header()
    _show_welcome_section()

    render_step_card(
        "Step 1: Choose profile",
        "Pick the resume/profile facts the packet should use.",
    )
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


def welcome_steps() -> list[str]:
    return [
        "Pick a candidate profile. Demo profiles are committed examples; private profiles live in ignored local_profiles/ folders.",
        "Paste, upload, or load a sample job posting that you chose.",
        "Generate a reviewable packet with deterministic fit, evidence suggestions, resume notes, draft wording, checklist, and risks.",
        "Review every claim manually before applying outside this app. Everything stays local.",
    ]


def local_profile_setup_steps(profile_id: str = "candidate") -> list[str]:
    safe_id = profile_id.strip() or "candidate"
    return [
        f"Create local_profiles/{safe_id}/profile.json.",
        f"Create local_profiles/{safe_id}/resume_base.md.",
        "Keep real resume details, proof blocks, and saved job posting files under local_profiles/.",
        "Do not commit local_profiles/; it is ignored by Git.",
        "The app reads these local files directly; it does not use ChatGPT memory.",
    ]


def example_job_posting_text() -> str:
    return GENERIC_EXAMPLE_JOB_TEXT


def inject_app_styles() -> None:
    st.markdown(app_style_css(), unsafe_allow_html=True)


def app_style_css() -> str:
    return """
<style>
:root {
  --studio-accent: #2f6f73;
  --studio-accent-soft: #e8f3f2;
  --studio-border: #d8e1df;
  --studio-card: #f8fbfa;
  --studio-text-soft: #4f6363;
  --studio-warning: #8a5a00;
  --studio-warning-bg: #fff6dd;
  --studio-success: #206a43;
  --studio-success-bg: #eaf6ef;
}
.block-container {
  padding-top: 1.6rem;
  max-width: 1320px;
}
.studio-hero {
  border: 1px solid #b8cbc8;
  border-radius: 14px;
  padding: 1.55rem 1.65rem 1.25rem 1.65rem;
  background: #ffffff;
  box-shadow: 0 1px 0 rgba(18, 45, 46, 0.06);
  margin-bottom: .8rem;
}
.studio-eyebrow {
  color: var(--studio-accent);
  font-weight: 700;
  letter-spacing: 0;
  margin-bottom: .2rem;
}
.studio-hero h1 {
  margin: 0;
  color: #183536;
  font-size: 2.35rem;
  line-height: 1.15;
}
.studio-subtitle {
  color: #274849;
  font-size: 1.08rem;
  margin: .45rem 0 .8rem 0;
  max-width: 760px;
}
.studio-safety {
  display: inline-flex;
  gap: .45rem;
  align-items: center;
  border: 1px solid #d7e2df;
  border-radius: 999px;
  padding: .26rem .64rem;
  background: #f7faf9;
  color: #496162;
  font-size: .9rem;
}
.studio-workflow {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
  margin: .9rem 0 1.1rem 0;
}
.studio-workflow-step {
  border: 1px solid #c6d7d4;
  border-radius: 12px;
  background: #f7faf9;
  padding: .9rem .95rem;
}
.studio-workflow-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.65rem;
  height: 1.65rem;
  border-radius: 999px;
  background: var(--studio-accent);
  color: #ffffff;
  font-weight: 700;
  margin-right: .45rem;
}
.studio-workflow-title {
  color: #1e3d3e;
  font-weight: 700;
}
.studio-workflow-helper {
  color: #536b6b;
  margin: .45rem 0 0 0;
  font-size: .92rem;
}
.studio-step {
  border: 1px solid #c9d9d6;
  border-radius: 12px;
  padding: 1rem 1.1rem;
  background: #ffffff;
  margin: 1rem 0 .8rem 0;
}
.studio-step h2 {
  font-size: 1.2rem;
  margin: 0 0 .25rem 0;
}
.studio-step p {
  color: var(--studio-text-soft);
  margin: 0;
}
.studio-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem;
  margin: .45rem 0 .65rem 0;
}
.studio-chip, .studio-badge {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  border-radius: 999px;
  border: 1px solid var(--studio-border);
  background: #ffffff;
  color: #263f40;
  padding: .32rem .68rem;
  font-size: .92rem;
  line-height: 1.25;
}
.studio-chip strong {
  color: var(--studio-accent);
}
.studio-badge.success {
  border-color: #b7dec6;
  background: var(--studio-success-bg);
  color: var(--studio-success);
}
.studio-badge.warning {
  border-color: #ead391;
  background: var(--studio-warning-bg);
  color: var(--studio-warning);
}
.studio-summary {
  border: 1px solid var(--studio-border);
  border-radius: 16px;
  padding: 1rem 1.15rem;
  background: #ffffff;
  margin: .7rem 0 1rem 0;
}
.studio-summary h3 {
  margin: 0 0 .35rem 0;
  font-size: 1.2rem;
}
.studio-summary-meta {
  color: var(--studio-text-soft);
  margin-bottom: .65rem;
}
.studio-muted {
  color: var(--studio-text-soft);
}
@media (max-width: 760px) {
  .studio-workflow {
    grid-template-columns: 1fr;
  }
  .studio-hero {
    padding: 1.2rem 1.1rem 1rem 1.1rem;
  }
  .studio-hero h1 {
    font-size: 1.9rem;
  }
}
</style>
""".strip()


def render_app_header() -> None:
    st.markdown(app_header_html(), unsafe_allow_html=True)


def app_header_html() -> str:
    return (
        """
<section class="studio-hero">
  <div class="studio-eyebrow">Local application workspace</div>
  <h1>Job Packet Studio</h1>
  <p class="studio-subtitle">Paste a job posting, generate a local review packet, then decide manually.</p>
  <span class="studio-safety">Local-first: no scraping, credentials, external AI API calls, or auto-apply.</span>
</section>
"""
        + workflow_strip_html()
    ).strip()


def workflow_strip_html() -> str:
    steps = [
        ("1", "Choose profile", "Use the demo profile or a private local profile."),
        ("2", "Paste or upload job", "Add only job text you chose to provide."),
        ("3", "Generate packet", "Review drafts and decide outside the app."),
    ]
    step_html = []
    for number, title, helper in steps:
        step_html.append(
            '<div class="studio-workflow-step">'
            f'<span class="studio-workflow-number">{html.escape(number)}</span>'
            f'<span class="studio-workflow-title">{html.escape(title)}</span>'
            f'<p class="studio-workflow-helper">{html.escape(helper)}</p>'
            "</div>"
        )
    return '<section class="studio-workflow">' + "".join(step_html) + "</section>"


def render_step_card(title: str, helper: str, status: str = "") -> None:
    st.markdown(step_card_html(title, helper, status), unsafe_allow_html=True)


def step_card_html(title: str, helper: str, status: str = "") -> str:
    status_html = f"<div>{status_badge_html(status)}</div>" if status else ""
    return (
        '<section class="studio-step">'
        f"<h2>{html.escape(title)}</h2>"
        f"<p>{html.escape(helper)}</p>"
        f"{status_html}"
        "</section>"
    )


def status_badge_html(status: str, label: str | None = None) -> str:
    normalized = status.strip().lower().replace("_", "-")
    badge_class = "success" if normalized in {"ready", "looks-good", "success"} else "warning"
    if label is None:
        label = "Looks usable" if badge_class == "success" else "Needs review"
    return (
        f'<span class="studio-badge {badge_class}">'
        f"<strong>{html.escape(label)}</strong>"
        f"</span>"
    )


def detected_detail_chips(
    details: dict[str, object] | None,
    source_url: object = "",
) -> list[str]:
    if not isinstance(details, dict):
        return []
    chip_values = [
        ("Title", details.get("title")),
        ("Company", details.get("company")),
        ("Work mode", details.get("work_mode")),
        ("Location", details.get("location")),
        ("Source", source_url),
    ]
    chips = []
    for label, value in chip_values:
        clean_value = str(value or "").strip()
        if not clean_value or clean_value.lower() == "unknown":
            continue
        chips.append(
            '<span class="studio-chip">'
            f"<strong>{html.escape(label)}:</strong> {html.escape(clean_value)}"
            "</span>"
        )
    return chips


def render_detected_detail_chips(
    details: dict[str, object] | None,
    source_url: object = "",
) -> None:
    chips = detected_detail_chips(details, source_url)
    if chips:
        st.markdown(
            '<div class="studio-chip-row">' + "".join(chips) + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Detected job details will appear here after you paste or upload text.")


def job_empty_state_text() -> str:
    return (
        "Paste the whole job page here - the app will clean common clutter. "
        "You can also upload .txt, .md, .html, or .htm files."
    )


def clean_job_posting_text(text: str) -> str:
    """Return conservative readable job text from messy copied page content."""
    if not text:
        return ""
    readable_text = extract_readable_html_text(text) if _looks_like_html(text) else text
    normalized_text = html_unescape_job_text(readable_text)
    cleaned_lines = []
    seen_lines = set()
    previous_blank = False
    for raw_line in normalized_text.splitlines():
        line = _clean_job_posting_line(raw_line)
        if not line:
            if cleaned_lines and not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
            continue
        previous_blank = False
        if _is_noisy_job_page_line(line):
            continue
        duplicate_key = _normalize_duplicate_line(line)
        if duplicate_key in seen_lines:
            continue
        seen_lines.add(duplicate_key)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def html_unescape_job_text(text: str) -> str:
    return (
        html.unescape(text)
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u00a0", " ")
        .replace("â€œ", '"')
        .replace("â€", '"')
        .replace("â€™", "'")
        .replace("â€“", "-")
        .replace("â€”", "-")
        .replace("â€¢", "-")
    )


def extract_job_url(text: str) -> str | None:
    match = SOURCE_URL_PATTERN.search(text or "")
    if not match:
        return None
    return match.group(0).rstrip(".,;]")


def summarize_job_input_quality(text: str) -> dict[str, object]:
    clean_text = clean_job_posting_text(text)
    lines = [line for line in clean_text.splitlines() if line.strip()]
    has_requirements = any(
        marker in clean_text.lower()
        for marker in ["requirement", "qualification", "responsibilities", "experience", "skills"]
    )
    is_useful = (
        len(clean_text) >= MIN_USEFUL_JOB_CHARS
        and len(lines) >= MIN_USEFUL_JOB_LINES
        and has_requirements
    )
    if is_useful:
        message = "Looks good. The posting has enough text to score and generate a packet."
    elif not clean_text.strip():
        message = "Paste the job title, company, responsibilities, qualifications, and salary/location if available."
    else:
        message = "Needs more text. You can paste the whole job page; the app will try to clean it."
    return {
        "status": "looks_good" if is_useful else "needs_more_text",
        "message": message,
        "cleaned_text": clean_text,
        "character_count": len(clean_text),
        "line_count": len(lines),
        "source_url": extract_job_url(text),
    }


def read_uploaded_job_file(payload: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".md", ".html", ".htm"}:
        raise ValueError("Upload a .txt, .md, or saved .html job posting file.")
    return clean_job_posting_text(extract_uploaded_job_text(payload, filename))


def _clean_job_posting_line(line: str) -> str:
    clean_line = " ".join(str(line).strip().split())
    return clean_line.strip(" \t|")


def _normalize_duplicate_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip().lower())


def _is_noisy_job_page_line(line: str) -> bool:
    normalized = _normalize_duplicate_line(line).strip(" .:|")
    if normalized in NOISY_JOB_PAGE_LINES:
        return True
    if SOURCE_URL_PATTERN.fullmatch(line.strip()):
        return True
    if any(normalized.startswith(prefix) for prefix in NOISY_JOB_PAGE_PREFIXES):
        return True
    if normalized.startswith(("facebook", "linkedin", "twitter", "x ")) and len(normalized.split()) <= 4:
        return True
    return False


def packet_start_here_items(packet: dict[str, object]) -> list[str]:
    items = []
    decision_summary = packet.get("decision_summary")
    if isinstance(decision_summary, dict):
        decision = str(decision_summary.get("decision", "Review")).strip()
        next_action = str(decision_summary.get("next_action", "")).strip()
        if decision:
            items.append(f"Decision: {decision}.")
        if next_action:
            items.append(f"Next action: {next_action}")

    evidence_summary = packet.get("evidence_summary")
    if isinstance(evidence_summary, dict):
        supported = _evidence_item_labels(evidence_summary.get("supported_evidence"))
        partial = _evidence_item_labels(evidence_summary.get("partial_evidence"))
        missing = _evidence_item_labels(evidence_summary.get("missing_proof"))
        needs_review = _evidence_item_labels(evidence_summary.get("needs_verification"))
        if supported:
            items.append("Supported evidence: " + _format_list_preview(supported) + ".")
        if partial:
            items.append("Partial evidence to strengthen: " + _format_list_preview(partial) + ".")
        if missing or needs_review:
            review_items = missing + needs_review
            items.append("Verify before claiming: " + _format_list_preview(review_items) + ".")

    if not items:
        items.append("Start by reviewing the packet checklist, risk notes, and tailored resume draft.")
    items.append("Save the packet only after checking that every claim is true.")
    return _dedupe(items)


def _evidence_item_labels(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    labels = []
    for value in values:
        if isinstance(value, dict):
            requirement = str(value.get("requirement", "")).strip()
            if requirement:
                labels.append(requirement)
    return labels


def _format_list_preview(values: list[str], limit: int = 3) -> str:
    preview = values[:limit]
    if not preview:
        return "none"
    if len(values) > limit:
        preview.append(f"{len(values) - limit} more")
    return ", ".join(preview)


def _show_welcome_section() -> None:
    with st.expander("How this local app works", expanded=False):
        st.markdown("**Simple workflow**")
        for step in welcome_steps():
            st.write(f"- {step}")
        st.info(
            "Everything stays on this computer. The app does not scrape job sites, "
            "store credentials, call external AI APIs, or apply for jobs."
        )


def _show_guided_packet_builder(
    profile: dict[str, object],
    applications_dir: Path,
) -> None:
    render_step_card(
        "Step 2: Add job posting",
        "Paste a posting or upload a saved file. The app only uses text you provide on this computer.",
    )

    uploaded_file = st.file_uploader(
        "Upload a saved job posting",
        type=["txt", "md", "html", "htm"],
        key="builder_simple_upload",
    )
    _load_uploaded_job_text_into_session(uploaded_file)

    with st.expander("Other local intake helpers"):
        st.caption(
            "These are optional. Paste or upload is still the fastest path. "
            "The app does not scrape job sites, ask for credentials, or apply to jobs."
        )
        helper_mode = st.radio(
            "Helper",
            ["Safe example", "Sample fixture", "Clipboard help", "Browser capture"],
            key="builder_helper_mode",
            horizontal=True,
        )
        _show_local_intake_helper(helper_mode)

    job_text = st.text_area(
        "Job posting text",
        height=360,
        key="builder_job_text",
        placeholder=job_empty_state_text(),
    )
    st.caption(job_empty_state_text())

    quality_summary = summarize_job_input_quality(job_text)
    cleaned_job_text = str(quality_summary["cleaned_text"])
    _show_job_input_quality(quality_summary)

    detected_job = parse_job_text(cleaned_job_text) if cleaned_job_text.strip() else None
    detail_overrides = _show_detected_job_details(
        detected_job,
        quality_summary.get("source_url"),
    )

    render_step_card(
        "Step 3: Generate packet",
        "One click scores the fit, suggests evidence, and builds local drafts for review.",
    )
    generate_clicked = st.button(
        "Generate application packet",
        type="primary",
        key="builder_generate_application_packet",
    )

    if generate_clicked:
        with st.spinner("Generating local packet..."):
            full_job_text = _build_guided_job_text(
                cleaned_job_text,
                title=detail_overrides.get("title", ""),
                company=detail_overrides.get("company", ""),
                location=detail_overrides.get("location", ""),
                work_mode=detail_overrides.get("work_mode", ""),
            )
            if not full_job_text.strip():
                st.error(
                    "Paste the job title, company, responsibilities, qualifications, "
                    "and salary/location if available. You can paste the whole job page; "
                    "the app will try to clean it."
                )
            else:
                job = parse_job_text(
                    full_job_text,
                    title=detail_overrides.get("title", ""),
                    company=detail_overrides.get("company", ""),
                    location=detail_overrides.get("location", ""),
                )
                score_details = score_job(job)
                source_url = str(quality_summary.get("source_url") or "")
                if source_url:
                    _attach_source_url(score_details, source_url)
                evidence_answers = _suggest_evidence_answers(
                    profile,
                    _evidence_requirements(score_details),
                )
                packet = generate_application_packet(
                    score_details,
                    profile.get("resume_text"),
                    evidence_answers=evidence_answers,
                )
                st.session_state["builder_job"] = job
                st.session_state["builder_score_details"] = score_details
                st.session_state["builder_full_job_text"] = full_job_text
                st.session_state["builder_source_url"] = source_url
                st.session_state["builder_analysis_key"] = _score_analysis_key(score_details)
                st.session_state["builder_evidence_answers"] = evidence_answers
                st.session_state["builder_packet"] = packet
                st.session_state["builder_packet_analysis_key"] = _score_analysis_key(score_details)
                st.session_state.pop("builder_saved_packet", None)
                st.session_state.pop("builder_agent_review", None)
                st.session_state.pop("builder_agent_analysis_key", None)

    job = st.session_state.get("builder_job")
    score_details = st.session_state.get("builder_score_details")
    packet = st.session_state.get("builder_packet")
    if isinstance(job, dict) and isinstance(score_details, dict) and isinstance(packet, dict):
        _show_generated_packet_result(job, score_details, packet, applications_dir)
    else:
        st.info("Paste or upload a posting, check the detected details, then generate the packet.")


def _load_uploaded_job_text_into_session(uploaded_file: object | None) -> None:
    if uploaded_file is None:
        return
    name = str(getattr(uploaded_file, "name", "job-posting.txt"))
    payload = uploaded_file.getvalue()
    upload_key = f"{name}:{len(payload)}"
    if st.session_state.get("builder_uploaded_job_key") == upload_key:
        return
    st.session_state["builder_job_text"] = read_uploaded_job_file(payload, name)
    st.session_state["builder_uploaded_job_key"] = upload_key
    st.success("Loaded uploaded job text. Review it below before generating.")
    st.rerun()


def job_text_from_upload_bytes(payload: bytes, filename: str) -> str:
    return read_uploaded_job_file(payload, filename)


def _show_job_input_quality(summary: dict[str, object]) -> None:
    clean_text = str(summary.get("cleaned_text") or "")
    source_url = summary.get("source_url")
    if source_url:
        st.caption(f"Source link found: {source_url}")
    if summary.get("status") == "looks_good":
        st.markdown(
            status_badge_html("looks-good", "Looks usable") + f" {html.escape(str(summary['message']))}",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            status_badge_html("needs-review", "Needs more text")
            + f" {html.escape(str(summary['message']))}",
            unsafe_allow_html=True,
        )
    if clean_text:
        with st.expander("Cleaned posting preview"):
            st.text_area(
                "Cleaned text used for detection and packet generation",
                value=clean_text,
                height=240,
                key="builder_cleaned_job_preview",
                disabled=True,
            )


def _attach_source_url(score_details: dict[str, object], source_url: str) -> None:
    metadata = score_details.get("job_metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        score_details["job_metadata"] = metadata
    metadata["source_url"] = source_url


def _show_local_intake_helper(helper_mode: str) -> None:
    if helper_mode == "Safe example":
        st.caption("This generic posting is fake demo text. It is not a real job lead.")
        st.code(example_job_posting_text(), language="text")
        if st.button("Use generic example", key="builder_use_generic_example"):
            st.session_state["builder_job_text"] = example_job_posting_text()
            st.success("Loaded generic example text. Review it below before generating.")
        return

    if helper_mode == "Sample fixture":
        sample_jobs = _sample_job_files()
        if not sample_jobs:
            st.info("No sample job fixtures were found.")
            return
        sample_options = {path.stem.replace("_", " ").title(): path for path in sample_jobs}
        selected_label = st.selectbox(
            "Sample job",
            list(sample_options),
            key="builder_sample_job",
        )
        if st.button("Use sample fixture", key="builder_use_sample_job"):
            sample_text = sample_options[selected_label].read_text(encoding="utf-8")
            st.session_state["builder_job_text"] = clean_imported_job_text(sample_text)
            st.success("Loaded sample job. Review it below before generating.")
        return

    if helper_mode == "Clipboard help":
        st.info(
            "For privacy, this local Python app does not read your clipboard directly. "
            "Click in the job text box and press Ctrl+V to paste."
        )
        return

    if helper_mode == "Browser capture":
        _show_browser_capture_helper()


def _show_browser_capture_helper() -> None:
    _show_job_intake_mode("Browser capture")


def _show_detected_job_details(
    job: dict[str, object] | None,
    source_url: object = "",
) -> dict[str, str]:
    if not isinstance(job, dict):
        st.info("Detected job details will appear here after you paste or upload text.")
        return {}

    st.markdown("**Detected details**")
    render_detected_detail_chips(job, source_url)

    with st.expander("Edit detected details"):
        st.caption("Only change these if the automatic detection is wrong or missing.")
        field_cols = st.columns(4)
        title = field_cols[0].text_input(
            "Job title",
            value=_editable_detected_value(job.get("title")),
            key="builder_title",
        )
        company = field_cols[1].text_input(
            "Company",
            value=_editable_detected_value(job.get("company")),
            key="builder_company",
        )
        location = field_cols[2].text_input(
            "Location",
            value=_editable_detected_value(job.get("location")),
            key="builder_location",
        )
        detected_work_mode = _editable_detected_value(job.get("work_mode"))
        work_modes = ["", "Remote", "Hybrid", "On-site", "Unknown"]
        work_mode = field_cols[3].selectbox(
            "Work mode",
            work_modes,
            index=work_modes.index(detected_work_mode) if detected_work_mode in work_modes else 0,
            key="builder_work_mode",
        )
    return {
        "title": title,
        "company": company,
        "location": location,
        "work_mode": work_mode,
    }


def _editable_detected_value(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "unknown":
        return ""
    return text


def _show_generated_packet_result(
    job: dict[str, object],
    score_details: dict[str, object],
    packet: dict[str, object],
    applications_dir: Path,
) -> None:
    saved_packet = st.session_state.get("builder_saved_packet")
    _show_compact_packet_result(job, score_details, packet, applications_dir, saved_packet)
    _show_builder_save_controls(packet, score_details, applications_dir)
    saved_packet = st.session_state.get("builder_saved_packet")
    if isinstance(saved_packet, dict):
        st.success(f"Saved packet: {saved_packet['folder_path']}")
    with st.expander("Fit and evidence details"):
        _show_analysis_summary(job, score_details, {"proof_blocks": []})
        _show_analysis_details(score_details)
    _show_packet_preview(packet, score_details, applications_dir)


def _show_compact_packet_result(
    job: dict[str, object],
    score_details: dict[str, object],
    packet: dict[str, object],
    applications_dir: Path,
    saved_packet: object,
) -> None:
    render_packet_summary_card(
        packet_summary_card_data(job, score_details, packet, applications_dir, saved_packet)
    )

    save_location = packet_save_location(applications_dir, saved_packet)
    _show_saved_packet_folder_location(save_location)


def packet_save_location(applications_dir: Path, saved_packet: object) -> str:
    if isinstance(saved_packet, dict):
        return str(saved_packet.get("folder_path") or applications_dir)
    return str(applications_dir)


def saved_packet_folder_note(folder_path: object) -> str:
    path_text = saved_packet_folder_path(folder_path)
    return (
        f"Saved packet folder: {path_text}. "
        "Start with packet_index.md for the recommended review order."
    )


def saved_packet_folder_path(folder_path: object) -> str:
    return str(folder_path or "applications/<profile_id>/<saved-folder>")


def _show_saved_packet_folder_location(
    folder_path: object,
    validation_result: object = None,
) -> None:
    st.caption(saved_packet_folder_note(folder_path))
    st.code(saved_packet_folder_path(folder_path), language="text")
    if isinstance(validation_result, dict):
        _show_saved_packet_validation(validation_result)
        _show_saved_packet_zip_download(folder_path, validation_result)


def packet_validation_status_text(validation_result: dict[str, object]) -> str:
    if validation_result.get("is_valid"):
        return "Packet validation: valid"
    return "Packet validation: needs attention"


def packet_validation_required_text(validation_result: dict[str, object]) -> str:
    present_files = _as_tuple_items(validation_result.get("present_files"))
    found = [
        filename
        for filename in ["packet_index.md", "tailored_resume.md", "packet.json"]
        if filename in present_files
    ]
    if not found:
        return "Required files found: none"
    return "Required files found: " + ", ".join(found)


def packet_validation_missing_required_items(
    validation_result: dict[str, object],
) -> list[str]:
    return _as_tuple_items(validation_result.get("missing_required_files"))


def packet_validation_missing_optional_items(
    validation_result: dict[str, object],
) -> list[str]:
    return _as_tuple_items(validation_result.get("missing_optional_files"))


def saved_packet_zip_download_enabled(validation_result: dict[str, object]) -> bool:
    return bool(validation_result.get("is_valid"))


def saved_packet_zip_filename(folder_path: object) -> str:
    folder_name = Path(saved_packet_folder_path(folder_path)).name
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", folder_name).strip("-")
    if not safe_name:
        safe_name = "saved-packet"
    return f"{safe_name}.zip"


def _show_saved_packet_validation(validation_result: dict[str, object]) -> None:
    status_text = packet_validation_status_text(validation_result)
    required_text = packet_validation_required_text(validation_result)
    missing_required = packet_validation_missing_required_items(validation_result)
    missing_optional = packet_validation_missing_optional_items(validation_result)

    if validation_result.get("is_valid"):
        st.success(f"{status_text}. {required_text}.")
    else:
        st.warning(status_text)
        if missing_required:
            st.write("Missing required files:")
            _show_plain_list(missing_required)
        else:
            st.write(required_text)

    if missing_optional:
        with st.expander("Missing optional packet files"):
            _show_plain_list(missing_optional)


def _show_saved_packet_zip_download(
    folder_path: object,
    validation_result: dict[str, object],
) -> None:
    if not saved_packet_zip_download_enabled(validation_result):
        return

    try:
        zip_bytes = build_saved_packet_zip(saved_packet_folder_path(folder_path))
    except ValueError as error:
        st.warning(str(error))
        return

    st.download_button(
        "Download saved packet ZIP",
        data=zip_bytes,
        file_name=saved_packet_zip_filename(folder_path),
        mime="application/zip",
        key=f"saved_packet_zip_{saved_packet_zip_filename(folder_path)}",
    )


def packet_summary_card_data(
    job: dict[str, object],
    score_details: dict[str, object],
    packet: dict[str, object],
    applications_dir: Path,
    saved_packet: object,
) -> dict[str, object]:
    return {
        "score": score_details.get("score", "Unknown"),
        "recommendation": str(score_details.get("recommendation", "Unknown")),
        "title": str(job.get("title", "Unknown")),
        "company": str(job.get("company", "Unknown")),
        "supported": top_packet_supported_items(packet),
        "review": top_packet_review_items(packet),
        "actions": packet_next_actions(packet),
        "save_location": packet_save_location(applications_dir, saved_packet),
    }


def render_packet_summary_card(summary: dict[str, object]) -> None:
    st.markdown(packet_summary_card_html(summary), unsafe_allow_html=True)


def packet_summary_card_html(summary: dict[str, object]) -> str:
    title = html.escape(str(summary.get("title", "Unknown")))
    company = html.escape(str(summary.get("company", "Unknown")))
    score = html.escape(str(summary.get("score", "Unknown")))
    recommendation = html.escape(str(summary.get("recommendation", "Unknown")))
    save_location = html.escape(str(summary.get("save_location", "")))
    return (
        '<section class="studio-summary">'
        "<h3>Packet summary</h3>"
        f'<div class="studio-summary-meta">{title} at {company}</div>'
        '<div class="studio-chip-row">'
        f'<span class="studio-chip"><strong>Match score:</strong> {score}/100</span>'
        f'<span class="studio-chip"><strong>Recommendation:</strong> {recommendation}</span>'
        "</div>"
        "<strong>Top supported evidence</strong>"
        f"{html_list(summary.get('supported'))}"
        "<strong>Top review items</strong>"
        f"{html_list(summary.get('review'))}"
        "<strong>Next actions</strong>"
        f"{html_list(summary.get('actions'))}"
        f'<div class="studio-muted">Saved packet location: {save_location}</div>'
        "</section>"
    )


def html_list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return '<p class="studio-muted">None.</p>'
    items = "".join(f"<li>{html.escape(str(value))}</li>" for value in values)
    return f"<ul>{items}</ul>"


def top_packet_supported_items(packet: dict[str, object], limit: int = 3) -> list[str]:
    evidence = packet.get("evidence_summary")
    if not isinstance(evidence, dict):
        return []
    supported = _evidence_item_labels(evidence.get("supported_evidence"))
    partial = _evidence_item_labels(evidence.get("partial_evidence"))
    return (supported + partial)[:limit]


def top_packet_review_items(packet: dict[str, object], limit: int = 3) -> list[str]:
    evidence = packet.get("evidence_summary")
    if not isinstance(evidence, dict):
        return _as_tuple_items(packet.get("keywords_to_avoid_or_verify"))[:limit]
    missing = _evidence_item_labels(evidence.get("missing_proof"))
    needs_review = _evidence_item_labels(evidence.get("needs_verification"))
    return (missing + needs_review)[:limit]


def packet_next_actions(packet: dict[str, object], limit: int = 3) -> list[str]:
    actions = []
    decision_summary = packet.get("decision_summary")
    if isinstance(decision_summary, dict):
        next_action = str(decision_summary.get("next_action", "")).strip()
        if next_action:
            actions.append(next_action)
    actions.extend(_as_tuple_items(packet.get("missing_proof_actions")))
    actions.append("Review every draft claim before applying manually.")
    actions.append("Save the packet if you want to keep these local files.")
    return _dedupe(actions)[:limit]


def _show_job_intake_mode(intake_mode: str) -> None:
    if intake_mode == "Paste text":
        st.info(
            "Paste the job description into the review box below. Include the title, "
            "company, location, requirements, and responsibilities when possible."
        )
        return

    if intake_mode == "Upload file":
        uploaded_file = st.file_uploader(
            "Upload saved job posting",
            type=["txt", "md", "html", "htm"],
            key="builder_job_upload",
        )
        st.caption("Supported formats: .txt, .md, .html, .htm. PDF import is not included yet.")
        if uploaded_file is not None and st.button("Use Uploaded File", key="builder_use_upload"):
            imported_text = extract_uploaded_job_text(
                uploaded_file.getvalue(),
                uploaded_file.name,
            )
            st.session_state["builder_job_text"] = imported_text
            st.success("Loaded uploaded file. Review and edit it below before analysis.")
        return

    if intake_mode == "Use sample job":
        sample_jobs = _sample_job_files()
        if not sample_jobs:
            st.info("No sample job fixtures were found.")
            return
        sample_options = {path.stem.replace("_", " ").title(): path for path in sample_jobs}
        selected_label = st.selectbox(
            "Sample job",
            list(sample_options),
            key="builder_sample_job",
        )
        if st.button("Use Sample Job", key="builder_use_sample_job"):
            sample_text = sample_options[selected_label].read_text(encoding="utf-8")
            st.session_state["builder_job_text"] = clean_imported_job_text(sample_text)
            st.session_state["builder_import_url"] = ""
            st.success("Loaded sample job. Review and edit it below before analysis.")
        return

    if intake_mode == "Browser capture":
        st.info(
            "Browser Capture lets you grab job text from a page you already have open. "
            "It works best when you highlight the job description first."
        )
        st.markdown("**Recommended setup**")
        st.markdown(browser_capture_bookmarklet_link_markdown())
        st.caption("Drag **Capture Job Posting** to your bookmarks bar. You only need to do this once.")
        for step in browser_capture_recommended_steps():
            st.markdown(f"- {step}")

        with st.expander("How do I add the bookmark?"):
            st.markdown("**Chrome / Edge**")
            for step in browser_capture_chrome_edge_steps():
                st.markdown(f"- {step}")
            st.markdown("**Firefox**")
            for step in browser_capture_firefox_steps():
                st.markdown(f"- {step}")

        with st.expander("Manual setup / Show bookmarklet code"):
            st.caption(
                "Copy this code, then paste it into the URL or Location field of a new browser bookmark."
            )
            for step in browser_capture_manual_steps():
                st.markdown(f"- {step}")
            st.code(build_browser_capture_bookmarklet(), language="javascript")
            st.caption("Do not paste this into the address bar. Save it as the bookmark URL.")

        st.markdown("**Use it on a job posting**")
        for step in browser_capture_usage_steps():
            st.markdown(f"- {step}")

        st.info(
            "Still stuck? Fast fallback: highlight the job description, press Ctrl+C, "
            "switch to Paste text mode, and paste it into the review box."
        )
        st.caption(" ".join(browser_capture_safety_notes()))
        st.markdown(
            "After clicking the bookmarklet, your browser downloads "
            "`captured-job-posting.txt`. Upload that file here, then review/edit "
            "the imported text before analysis."
        )
        captured_file = st.file_uploader(
            "Upload bookmarklet capture",
            type=["txt", "md", "html", "htm"],
            key="builder_browser_capture_upload",
        )
        if captured_file is not None and st.button("Load Captured Text", key="builder_load_capture"):
            try:
                captured_text = clean_captured_job_text(
                    extract_uploaded_job_text(captured_file.getvalue(), captured_file.name)
                )
            except ValueError as error:
                st.warning(str(error))
            else:
                st.session_state["builder_job_text"] = captured_text
                if len(captured_text) < MIN_CAPTURED_JOB_CHARS:
                    st.warning(
                        "This capture looks short. Try highlighting the job description before "
                        "clicking the bookmarklet, then upload the new captured-job-posting.txt file."
                    )
                else:
                    st.success("Loaded captured text. Review and edit it below before analysis.")


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


def extract_uploaded_job_text(content: bytes, filename: str) -> str:
    text = content.decode("utf-8", errors="replace")
    suffix = Path(filename).suffix.lower()
    if suffix in {".html", ".htm"} or _looks_like_html(text):
        return extract_readable_html_text(text)
    return clean_imported_job_text(text)


def extract_readable_html_text(html: str) -> str:
    parser = _ReadableHTMLTextParser()
    parser.feed(html)
    parser.close()
    return clean_imported_job_text(" ".join(parser.text_parts))


def clean_imported_job_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    lines = [line.strip() for line in normalized.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def clean_captured_job_text(
    text: str,
    max_chars: int = MAX_CAPTURED_JOB_CHARS,
) -> str:
    cleaned = clean_imported_job_text(text)
    if len(cleaned) > max_chars:
        raise ValueError(
            f"Captured text is too large ({len(cleaned)} characters). "
            f"Select only the job description or use a file under {max_chars} characters."
        )
    return cleaned


def choose_browser_capture_text(
    selected_text: str,
    body_text: str,
    title: str = "",
    url: str = "",
    max_chars: int = MAX_CAPTURED_JOB_CHARS,
) -> str:
    captured = selected_text.strip() or body_text.strip()
    captured = captured[:max_chars]
    header = []
    if title.strip():
        header.append(f"Page Title: {title.strip()}")
    if url.strip():
        header.append(f"Page URL: {url.strip()}")
    if header:
        header.extend(["", "Captured Job Text:", ""])
    return clean_imported_job_text("\n".join(header) + captured)


def browser_capture_setup_steps() -> list[str]:
    return browser_capture_recommended_steps() + browser_capture_manual_steps()


def browser_capture_recommended_steps() -> list[str]:
    return [
        "Show your bookmarks bar.",
        'Drag the "Capture Job Posting" link to the bookmarks bar.',
        "Open a job posting you already chose.",
        "Highlight the job description.",
        "Click the bookmark.",
        "Upload captured-job-posting.txt below.",
    ]


def browser_capture_manual_steps() -> list[str]:
    return [
        "Copy the bookmarklet code.",
        'Create a browser bookmark named "Capture Job Posting."',
        "Paste the copied code into the bookmark URL or Location field.",
        "Do not paste the bookmarklet into the address bar.",
    ]


def browser_capture_chrome_edge_steps() -> list[str]:
    return [
        "Press Ctrl+Shift+B to show the bookmarks bar if needed.",
        'Drag the "Capture Job Posting" link to the bookmarks bar.',
        "If dragging does not work, right-click the bookmarks bar and choose Add page.",
        'Name it "Capture Job Posting."',
        "Paste the bookmarklet code into the URL field.",
    ]


def browser_capture_firefox_steps() -> list[str]:
    return [
        "Press Ctrl+Shift+B or enable the Bookmarks Toolbar if needed.",
        'Drag the "Capture Job Posting" link to the toolbar.',
        "If dragging does not work, right-click the toolbar and choose New Bookmark.",
        'Name it "Capture Job Posting."',
        "Make sure the Location field contains the javascript: bookmarklet code, not the job page URL.",
    ]


def browser_capture_usage_steps() -> list[str]:
    return [
        "Open a job posting you already chose.",
        "Highlight only the job description when possible.",
        'Click the "Capture Job Posting" bookmark.',
        "Upload the downloaded captured-job-posting.txt file below.",
        "Review and edit the imported text before clicking Generate application packet.",
    ]


def browser_capture_safety_notes() -> list[str]:
    return [
        "If you do not highlight anything, the bookmarklet captures visible page text and may include extra clutter.",
        "It does not collect cookies, local storage, passwords, or hidden fields.",
        "It does not crawl pages or apply to jobs.",
    ]


def browser_capture_bookmarklet_link_markdown() -> str:
    bookmarklet = build_browser_capture_bookmarklet()
    if bookmarklet.startswith("javascript:"):
        bookmarklet = "javascript:" + quote(bookmarklet.removeprefix("javascript:"), safe="")
    return f"[Capture Job Posting]({bookmarklet})"


def build_browser_capture_bookmarklet(max_chars: int = MAX_CAPTURED_JOB_CHARS) -> str:
    script = (
        "(()=>{"
        f"const max={max_chars};"
        "const sel=(window.getSelection&&window.getSelection().toString())||'';"
        "const body=(document.body&&document.body.innerText)||'';"
        "let text=(sel.trim()?sel:body).slice(0,max);"
        "const out=['Page Title: '+document.title,'Page URL: '+location.href,'','Captured Job Text:','',text].join('\\n');"
        "if(text.trim().length<80){alert('Captured text is short. Select the job description first if possible.');}"
        "const blob=new Blob([out],{type:'text/plain'});"
        "const a=document.createElement('a');"
        "a.href=URL.createObjectURL(blob);"
        "a.download='captured-job-posting.txt';"
        "document.body.appendChild(a);"
        "a.click();"
        "a.remove();"
        "setTimeout(()=>URL.revokeObjectURL(a.href),1000);"
        "})();"
    )
    return "javascript:" + script


def _sample_job_files() -> list[Path]:
    if not JOB_SAMPLE_DIR.exists():
        return []
    return sorted(path for path in JOB_SAMPLE_DIR.glob("*.txt") if path.is_file())


def _charset_from_content_type(content_type: str) -> str:
    match = re.search(r"charset=([^;]+)", content_type, flags=re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip().strip('"')


def _looks_like_html(text: str) -> bool:
    return bool(re.search(r"<\s*(html|body|div|p|br|section|article)\b", text, re.IGNORECASE))


class _ReadableHTMLTextParser(HTMLParser):
    """Small readable-text extractor for user-provided public job pages."""

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if tag.lower() in {"p", "br", "li", "div", "section", "article", "h1", "h2", "h3"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag.lower() in {"p", "li", "div", "section", "article", "h1", "h2", "h3"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        clean_data = data.strip()
        if clean_data:
            self.text_parts.append(clean_data)


def _show_builder_save_controls(
    packet: dict[str, object],
    score_details: dict[str, object],
    applications_dir: Path,
) -> None:
    existing_packets = list_saved_application_packets(applications_dir)
    duplicates = _find_duplicate_saved_packets(score_details, existing_packets)
    st.caption(f"Packets for this profile save under: {applications_dir}")

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
            type="secondary",
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


def _show_job_packet_agent_review(
    score_details: dict[str, object],
    profile: dict[str, object],
) -> None:
    analysis_key = _score_analysis_key(score_details)
    profile_id = str(profile.get("profile_id", "profile"))
    agent_key = (analysis_key, profile_id)
    if st.session_state.get("builder_agent_analysis_key") != agent_key:
        job_text = str(st.session_state.get("builder_full_job_text", "")).strip()
        if not job_text:
            return
        try:
            st.session_state["builder_agent_review"] = run_job_packet_agent(
                job_text,
                profile,
            )
            st.session_state["builder_agent_analysis_key"] = agent_key
        except ValueError as error:
            st.session_state["builder_agent_review"] = {"warnings": [str(error)]}
            st.session_state["builder_agent_analysis_key"] = agent_key

    agent_review = st.session_state.get("builder_agent_review")
    if not isinstance(agent_review, dict):
        return

    with st.expander("Job Packet Agent"):
        st.caption(
            "Deterministic review of the same local parse, score, and packet-generation workflow."
        )
        role_summary = agent_review.get("role_summary")
        score_summary = agent_review.get("score_summary")
        focus = agent_review.get("resume_focus_recommendations")

        if isinstance(role_summary, dict):
            st.markdown(
                "**Role:** "
                f"{role_summary.get('title', 'Unknown')} at {role_summary.get('company', 'Unknown')}"
            )
            st.caption(
                f"Location: {role_summary.get('location', 'Unknown')} | "
                f"Work mode: {role_summary.get('work_mode', 'Unknown')}"
            )

        if isinstance(score_summary, dict):
            st.markdown(
                "**Fit:** "
                f"{score_summary.get('score', 'Unknown')}/100 | "
                f"{score_summary.get('recommendation', 'Unknown')}"
            )
            fit_summary = str(score_summary.get("fit_summary", "")).strip()
            if fit_summary:
                st.write(fit_summary)

        if isinstance(focus, dict):
            cols = st.columns(2)
            with cols[0]:
                st.markdown("**Resume focus**")
                _show_plain_list(focus.get("top_resume_focus_areas"))
            with cols[1]:
                st.markdown("**Verify before claiming**")
                _show_plain_list(focus.get("requirements_to_verify"))

        st.markdown("**Warnings**")
        _show_plain_list(agent_review.get("warnings"))
        st.markdown("**Next actions**")
        _show_plain_list(agent_review.get("next_actions"))


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
    applications_dir: Path | None = None,
    review_sections: object = None,
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
    _show_packet_start_here(packet, applications_dir)

    preview_tabs = st.tabs(
        [
            "Resume focus",
            "Tailored resume draft",
            "Cover letter",
            "Recruiter message",
            "Checklist",
            "Risk notes",
            "Details / metadata",
        ]
    )
    with preview_tabs[0]:
        _show_plain_list(packet.get("resume_focus_areas"))
        _show_resume_strategy(packet)
    with preview_tabs[1]:
        st.caption(
            "Reviewable Markdown draft. Check every claim before using it in an application."
        )
        st.markdown(
            _review_section_content(
                review_sections,
                "tailored_resume",
                str(packet.get("tailored_resume_draft", "")),
            )
        )
    with preview_tabs[2]:
        st.text(str(packet.get("cover_letter_draft", "")))
    with preview_tabs[3]:
        st.text(str(packet.get("recruiter_message", "")))
    with preview_tabs[4]:
        _show_plain_list(packet.get("application_checklist"))
    with preview_tabs[5]:
        _show_plain_list(packet.get("risk_notes"))
    with preview_tabs[6]:
        _show_decision_summary(packet.get("decision_summary"))
        _show_score_explanation(score_details.get("explanation"))


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


def _show_packet_start_here(
    packet: dict[str, object],
    applications_dir: Path | None = None,
) -> None:
    with st.container(border=True):
        st.markdown("**Start here**")
        for item in packet_start_here_items(packet):
            st.write(f"- {item}")
        if applications_dir is not None:
            st.write(f"- Saved packet files will go under: {applications_dir}")


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

    _show_saved_packet_folder_location(
        packet_details["folder_path"],
        validate_saved_packet_folder(packet_details["folder_path"]),
    )
    _show_saved_packet_status_controls(packet_details, key_prefix="guided_saved_status")
    _show_packet_preview(
        packet_details["application_packet"],
        packet_details["score_summary"],
        review_sections=_saved_review_sections(packet_details),
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

    _show_saved_packet_folder_location(
        packet_details["folder_path"],
        validate_saved_packet_folder(packet_details["folder_path"]),
    )
    _show_saved_packet_status_controls(packet_details, key_prefix="advanced_saved_status")
    _show_saved_packet_details(
        packet_details["application_packet"],
        _saved_review_sections(packet_details),
    )


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
    _next_action = st.date_input(
        "Next action date",
        value=None,
        key=f"{widget_key}_next_action_date",
    )
    next_action_date = _next_action.isoformat() if _next_action else ""
    next_action_note = st.text_input(
        "Next action note",
        value=str(tracking.get("next_action_note") or ""),
        key=f"{widget_key}_next_action_note",
    )

    applied_date = None
    if status in {"Applied", "Interview", "Offer", "Rejected", "Archived"}:
        _applied = st.date_input(
            "Applied date",
            value=None,
            key=f"{widget_key}_applied_date",
        )
        applied_date = _applied.isoformat() if _applied else ""

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


def _show_saved_packet_details(packet: object, review_sections: object = None) -> None:
    if not isinstance(packet, dict):
        st.info("No saved packet details were found.")
        return

    st.subheader("Packet Details")
    st.write(packet.get("positioning_summary", "No positioning summary found."))
    st.info(str(packet.get("apply_recommendation", "No apply recommendation found.")))
    _show_saved_packet_index(review_sections)
    with st.expander("Tailored resume draft", expanded=True):
        st.caption(
            "Reviewable Markdown draft. Check every claim before using it in an application."
        )
        st.markdown(
            _review_section_content(
                review_sections,
                "tailored_resume",
                str(packet.get("tailored_resume_draft", "")),
            )
        )
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


def _show_saved_packet_index(review_sections: object) -> None:
    index_content = _review_section_content(review_sections, "packet_index")
    if not index_content:
        st.caption("Start with packet_index.md when it is present in the saved packet folder.")
        return

    with st.expander("Packet review index", expanded=True):
        st.caption("Start with packet_index.md for the recommended saved-folder review order.")
        st.markdown(index_content)


def _review_section_content(
    review_sections: object,
    key: str,
    fallback: str = "",
) -> str:
    if not isinstance(review_sections, list):
        return fallback
    for section in review_sections:
        if not isinstance(section, dict):
            continue
        if section.get("key") == key and section.get("exists"):
            content = section.get("content")
            if isinstance(content, str) and content.strip():
                return content
    return fallback


def _saved_review_sections(packet_details: dict[str, object]) -> list[dict[str, object]]:
    sections = packet_details.get("review_sections")
    if isinstance(sections, list):
        return sections
    folder_path = packet_details.get("folder_path")
    if isinstance(folder_path, Path):
        return load_saved_packet_review_sections(folder_path)
    return []


def _show_profile_selector() -> dict[str, object]:
    profiles = list_profiles(PROFILES_ROOT, LOCAL_PROFILES_ROOT)
    if not profiles:
        st.error("No profiles found. Add profiles/default/profile.json or a local profile.")
        st.stop()

    has_local_profile = any(bool(profile.get("is_local")) for profile in profiles)
    st.caption("Demo profiles are safe examples. Private profiles live under ignored local_profiles/.")
    st.caption("No ChatGPT memory is used; profile facts are matched deterministically from local files.")
    profile_options = {
        _format_profile_label(profile): profile
        for profile in profiles
    }
    profile_labels = list(profile_options)
    selected_label = st.selectbox(
        "Profile",
        profile_labels,
        index=default_profile_index(list(profile_options.values())),
        key="profile_selector",
    )
    profile = profile_options[selected_label]

    if profile.get("is_default") and not profile.get("is_local"):
        st.markdown(
            status_badge_html("needs-review", "Demo profile")
            + " Using safe example data. Create a private local profile when you want real resume details.",
            unsafe_allow_html=True,
        )
    elif profile.get("is_local"):
        st.markdown(
            status_badge_html("looks-good", "Private local profile")
            + " Using files under ignored local_profiles/.",
            unsafe_allow_html=True,
        )
    if not has_local_profile:
        st.caption("No private profile found yet. You can keep testing with the demo profile.")
        with st.expander("Add a private local profile later"):
            st.caption(
                "Optional: demo profiles are safe for testing. For real applications, "
                "create these ignored local files when you are ready."
            )
            for step in local_profile_setup_steps():
                st.write(f"- {step}")
            st.code(
                '{\n'
                '  "profile_id": "candidate",\n'
                '  "display_name": "Candidate",\n'
                '  "target_roles": ["IT Support", "Technical Support"],\n'
                '  "notes": "Private local profile."\n'
                '}',
                language="json",
            )
    if not profile.get("resume_text"):
        st.info("This profile does not have resume_base.md text yet.")

    with st.expander("Profile details"):
        st.caption(f"Profile ID: {profile['profile_id']} | Source: {profile['source']}")
        st.caption(f"Profile path: {profile['profile_path']}")
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
        return f"{label} - Private local"
    return f"{label} - Demo"


def default_profile_index(profiles: list[dict[str, object]]) -> int:
    if not profiles:
        return 0
    local_indexes = [
        index
        for index, profile in enumerate(profiles)
        if bool(profile.get("is_local"))
    ]
    if len(local_indexes) == 1:
        return local_indexes[0]
    if local_indexes:
        return local_indexes[0]
    for index, profile in enumerate(profiles):
        if str(profile.get("profile_id")) == DEFAULT_PROFILE_ID:
            return index
    return 0


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
