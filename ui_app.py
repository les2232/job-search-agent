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
from job_parser import parse_job_text
from job_scorer import score_job
from tracker import filter_tracked_jobs
from tracker import read_tracked_jobs
from tracker import save_job_result
from tracker import update_job_status


JOBS_CSV_PATH = PROJECT_ROOT / "data" / "jobs.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_RESUME_PATH = PROJECT_ROOT / "data" / "profile" / "resume_base.md"
STATUS_OPTIONS = ["New", "Applied", "Interview", "Rejected", "Saved", "Archived"]


def main() -> None:
    st.set_page_config(page_title="Job Search Agent", layout="wide")
    st.title("Job Search Agent")

    tracked_jobs = read_tracked_jobs(JOBS_CSV_PATH)
    dashboard_tab, score_tab, tracker_tab, packets_tab = st.tabs(
        ["Dashboard", "Score a Job", "Tracker", "Application Packets"]
    )

    with dashboard_tab:
        _show_dashboard(tracked_jobs)

    with score_tab:
        _show_score_job_tab()

    with tracker_tab:
        _show_tracker_tab(tracked_jobs)

    with packets_tab:
        _show_application_packets_tab()


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
    metric_cols[3].metric("Application packets", len(_list_packet_dirs()))

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

    packet = st.session_state.get("score_application_packet")
    if not isinstance(packet, dict):
        st.caption(
            "Generate a reviewable packet with resume focus areas, draft wording, "
            "a recruiter message, checklist, and risk notes."
        )
        return

    st.write(packet["positioning_summary"])
    st.info(str(packet["apply_recommendation"]))
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


def _format_list(value: object) -> str:
    if isinstance(value, list) and value:
        return ", ".join(str(item) for item in value)
    return "None"


if __name__ == "__main__":
    main()
