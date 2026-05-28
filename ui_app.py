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
    list_saved_application_packets,
    load_saved_application_packet,
    sort_saved_application_packets,
    update_application_tracking,
)
from application_packet_writer import save_application_packet
from job_parser import parse_job_text
from job_scorer import score_job
from tracker import filter_tracked_jobs
from tracker import read_tracked_jobs
from tracker import save_job_result
from tracker import update_job_status


JOBS_CSV_PATH = PROJECT_ROOT / "data" / "jobs.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"
APPLICATIONS_DIR = PROJECT_ROOT / "applications"
DEFAULT_RESUME_PATH = PROJECT_ROOT / "data" / "profile" / "resume_base.md"
STATUS_OPTIONS = ["New", "Applied", "Interview", "Rejected", "Saved", "Archived"]


def main() -> None:
    st.set_page_config(page_title="Job Search Agent", layout="wide")
    st.title("Job Search Agent")

    tracked_jobs = read_tracked_jobs(JOBS_CSV_PATH)
    dashboard_tab, score_tab, tracker_tab, packets_tab, saved_tab = st.tabs(
        [
            "Dashboard",
            "Score a Job",
            "Tracker",
            "Application Packets",
            "Saved applications",
        ]
    )

    with dashboard_tab:
        _show_dashboard(tracked_jobs)

    with score_tab:
        _show_score_job_tab()

    with tracker_tab:
        _show_tracker_tab(tracked_jobs)

    with packets_tab:
        _show_application_packets_tab()

    with saved_tab:
        _show_saved_applications_tab()


def _show_dashboard(tracked_jobs: list[dict[str, str]]) -> None:
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
        len(list_saved_application_packets(APPLICATIONS_DIR)),
    )

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


def _show_score_job_tab() -> None:
    st.header("Score a Job")
    job_text = _get_job_text_input("score")

    if st.button("Score job", type="primary"):
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

    _show_score_summary(job, score_details)

    if st.button("Save to tracker"):
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
    selected_status = filter_cols[0].selectbox("Status", status_options)
    selected_recommendation = filter_cols[1].selectbox(
        "Recommendation",
        recommendation_options,
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

    st.dataframe(filtered_jobs, use_container_width=True, hide_index=True)
    _show_status_update_controls(filtered_jobs)


def _show_application_packets_tab() -> None:
    st.header("Application Packets")

    job_path_text = st.text_input(
        "Job posting file path",
        value=str(PROJECT_ROOT / "data" / "sample_job.txt"),
    )
    resume_path_text = st.text_input(
        "Local resume/profile path",
        value=str(DEFAULT_RESUME_PATH),
    )

    if st.button("Generate packet", type="primary"):
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
    )
    st.write(str(selected_packet))

    match_notes_path = selected_packet / "match_notes.md"
    if match_notes_path.exists():
        st.subheader("Match Notes Preview")
        st.markdown(match_notes_path.read_text(encoding="utf-8"))
    else:
        st.caption("No match_notes.md file found in this packet.")


def _show_saved_applications_tab() -> None:
    st.header("Saved applications")

    saved_packets = list_saved_application_packets(APPLICATIONS_DIR)
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
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    packet_options = {
        _format_saved_packet_label(packet): packet
        for packet in filtered_packets
    }
    selected_label = st.selectbox("View packet details", list(packet_options))
    selected_packet = packet_options[selected_label]
    packet_details = load_saved_application_packet(selected_packet["folder_path"])
    if packet_details is None:
        st.warning("This saved packet could not be loaded.")
        return

    st.caption(f"Saved folder: {packet_details['folder_path']}")
    _show_saved_packet_status_controls(packet_details)
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
    selected_status = filter_cols[0].selectbox("Status", status_options)
    selected_recommendation = filter_cols[1].selectbox(
        "Recommendation",
        recommendation_options,
    )
    selected_work_mode = filter_cols[2].selectbox("Work mode", work_mode_options)
    selected_sort = filter_cols[3].selectbox("Sort", SORT_OPTIONS)

    search_cols = st.columns(4)
    selected_apply_recommendation = search_cols[0].selectbox(
        "Apply recommendation",
        apply_recommendation_options,
    )
    min_score = search_cols[1].number_input(
        "Minimum score",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
    )
    company_search = search_cols[2].text_input("Company search")
    text_search = search_cols[3].text_input("Title/company search")
    attention_cols = st.columns(3)
    needs_attention = attention_cols[0].checkbox("Needs attention")
    overdue = attention_cols[1].checkbox("Overdue")
    due_within_7_days = attention_cols[2].checkbox("Due within 7 days")

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


def _show_saved_packet_status_controls(packet_details: dict[str, object]) -> None:
    tracking = packet_details.get("application_tracking")
    if not isinstance(tracking, dict):
        tracking = {}

    current_status = str(tracking.get("status", "Interested"))
    if current_status not in APPLICATION_STATUSES:
        current_status = "Interested"

    st.subheader("Application Status")
    status = st.selectbox(
        "Status",
        APPLICATION_STATUSES,
        index=APPLICATION_STATUSES.index(current_status),
    )
    notes = st.text_area(
        "Notes",
        value=str(tracking.get("notes") or ""),
        height=90,
    )
    next_action_date = st.text_input(
        "Next action date",
        value=str(tracking.get("next_action_date") or ""),
        placeholder="YYYY-MM-DD",
    )
    next_action_note = st.text_input(
        "Next action note",
        value=str(tracking.get("next_action_note") or ""),
    )

    applied_date = None
    if status in {"Applied", "Interview", "Offer", "Rejected", "Archived"}:
        applied_date = st.text_input(
            "Applied date",
            value=str(tracking.get("applied_date") or ""),
            placeholder="YYYY-MM-DD",
        )

    if st.button("Update application status"):
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
        _show_application_packet_prompt(score_details)


def _show_score_explanation(explanation: object) -> None:
    if not isinstance(explanation, dict):
        return

    st.subheader("Why this score?")
    st.write(explanation["fit_summary"])
    _show_explanation_list("Strengths", explanation["strengths"])
    _show_explanation_list("Gaps", explanation["gaps"])
    _show_explanation_list("Concerns", explanation["concerns"])
    _show_explanation_list(
        "Tailoring suggestions",
        explanation["tailoring_suggestions"],
    )


def _show_application_packet_prompt(score_details: dict[str, object]) -> None:
    st.subheader("Application packet")
    if st.button("Generate application packet"):
        profile_text = _read_optional_text(DEFAULT_RESUME_PATH)
        st.session_state["score_application_packet"] = generate_application_packet(
            score_details,
            profile_text,
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
    if st.button("Save application packet"):
        save_result = save_application_packet(packet, score_details, APPLICATIONS_DIR)
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
    selected_label = st.selectbox("Job", list(job_options))
    new_status = st.selectbox("New status", STATUS_OPTIONS)

    if st.button("Update status"):
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


def _format_list(value: object) -> str:
    if isinstance(value, list) and value:
        return ", ".join(str(item) for item in value)
    return "None"


if __name__ == "__main__":
    main()
