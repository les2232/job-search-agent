"""Local Streamlit UI for the job search agent."""

from pathlib import Path
import sys

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from application_generator import generate_application_materials
from job_parser import parse_job_text
from job_scorer import score_job
from tracker import read_tracked_jobs, save_job_result


JOBS_CSV_PATH = PROJECT_ROOT / "data" / "jobs.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"


def main() -> None:
    st.set_page_config(page_title="Job Search Agent", layout="wide")
    st.title("Job Search Agent")

    job_text = _get_job_text_input()

    if st.button("Score job", type="primary"):
        if not job_text.strip():
            st.error("Paste a job posting or upload a .txt file before scoring.")
        else:
            job = parse_job_text(job_text)
            score_details = score_job(job)
            st.session_state["scored_job"] = job
            st.session_state["score_details"] = score_details
            st.session_state.pop("save_message", None)

    job = st.session_state.get("scored_job")
    score_details = st.session_state.get("score_details")
    if job and score_details:
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

    _show_application_generator(job_text)
    _show_tracked_jobs()


def _get_job_text_input() -> str:
    pasted_text = st.text_area("Paste job posting text", height=260)
    uploaded_file = st.file_uploader("Or upload a .txt job posting", type=["txt"])

    if uploaded_file is None:
        return pasted_text

    return uploaded_file.getvalue().decode("utf-8")


def _show_score_summary(
    job: dict[str, str],
    score_details: dict[str, object],
) -> None:
    with st.container(border=True):
        st.subheader("Score")
        title_col, company_col, location_col = st.columns(3)
        title_col.metric("Title", job["title"])
        company_col.metric("Company", job["company"])
        location_col.metric("Location", job["location"])

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


def _show_application_generator(job_text: str) -> None:
    with st.container(border=True):
        st.subheader("Application Packet")
        resume_path_text = st.text_input(
            "Local resume/profile path",
            value=str(PROJECT_ROOT / "data" / "profile" / "resume_base.md"),
        )

        if st.button("Generate application packet"):
            if not job_text.strip():
                st.error("Paste or upload a job posting before generating a packet.")
                return

            temp_job_path = OUTPUT_DIR / "_ui_job_posting.txt"
            try:
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                temp_job_path.write_text(job_text, encoding="utf-8")
                result = generate_application_materials(
                    temp_job_path,
                    Path(resume_path_text),
                    OUTPUT_DIR,
                )
            except (FileNotFoundError, ValueError) as error:
                st.error(str(error))
                return
            finally:
                if temp_job_path.exists():
                    temp_job_path.unlink()

            st.success(f"Generated packet: {result['output_dir']}")
            st.write("Files:")
            for output_path in result["output_paths"].values():
                st.write(str(output_path))


def _show_tracked_jobs() -> None:
    st.subheader("Tracked Jobs")
    tracked_jobs = read_tracked_jobs(JOBS_CSV_PATH)

    if not tracked_jobs:
        st.caption("No tracked jobs yet.")
        return

    st.dataframe(tracked_jobs, use_container_width=True, hide_index=True)


def _format_list(value: object) -> str:
    if isinstance(value, list) and value:
        return ", ".join(str(item) for item in value)
    return "None"


if __name__ == "__main__":
    main()
