"""Generate local Markdown application drafts from user-provided materials."""

from pathlib import Path
import re

from config_loader import load_scoring_config
from job_parser import parse_job_text


REVIEW_WARNING = (
    "Draft only. Review carefully before using. "
    "Do not include claims you cannot verify."
)

OUTPUT_FILENAMES = {
    "resume": "tailored_resume.md",
    "cover_letter": "cover_letter.md",
    "match_notes": "match_notes.md",
    "job_posting": "job_posting.txt",
}


def generate_application_materials(
    job_path: Path,
    resume_path: Path,
    output_dir: Path,
) -> dict[str, object]:
    """Create local Markdown drafts for a job and resume/profile."""
    job_text = _read_required_text(job_path, "job posting")
    resume_text = _read_required_text(resume_path, "resume/profile")
    job = parse_job_text(job_text)
    matching_keywords = find_matching_keywords(job_text, resume_text)

    output_dir = output_dir / make_application_slug(job["company"], job["title"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = {
        name: output_dir / filename for name, filename in OUTPUT_FILENAMES.items()
    }

    output_paths["job_posting"].write_text(job_text, encoding="utf-8")
    output_paths["resume"].write_text(
        build_resume_draft(job, resume_text, matching_keywords),
        encoding="utf-8",
    )
    output_paths["cover_letter"].write_text(
        build_cover_letter_draft(job, matching_keywords),
        encoding="utf-8",
    )
    output_paths["match_notes"].write_text(
        build_match_notes(job, matching_keywords),
        encoding="utf-8",
    )

    return {
        "job": job,
        "matching_keywords": matching_keywords,
        "output_dir": output_dir,
        "output_paths": output_paths,
    }


def make_application_slug(company: str, title: str) -> str:
    """Return a safe folder slug for a company and job title."""
    combined_text = f"{company} {title}".lower()
    slug = re.sub(r"[^a-z0-9]+", "-", combined_text)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "unknown-job"


def find_matching_keywords(
    job_text: str,
    resume_text: str,
    keywords: list[str] | None = None,
) -> list[str]:
    """Return configured keywords that appear in both job and resume text."""
    if keywords is None:
        config = load_scoring_config()
        keywords = config["positive_keywords"]

    job_text_lower = job_text.lower()
    resume_text_lower = resume_text.lower()
    matches = []

    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in job_text_lower and keyword_lower in resume_text_lower:
            matches.append(keyword)

    return matches


def build_resume_draft(
    job: dict[str, str],
    resume_text: str,
    matching_keywords: list[str],
) -> str:
    """Build a conservative tailored resume draft."""
    return "\n".join(
        [
            "# Tailored Resume Draft",
            "",
            f"> {REVIEW_WARNING}",
            "",
            f"Target role: {job['title']}",
            f"Target company: {job['company']}",
            f"Location: {job['location']}",
            "",
            "## Matching Keywords Found In Your Resume",
            _format_bullets(matching_keywords),
            "",
            "## Base Resume Content",
            "",
            resume_text.strip(),
            "",
        ]
    )


def build_cover_letter_draft(
    job: dict[str, str],
    matching_keywords: list[str],
) -> str:
    """Build a simple cover letter draft without adding unverifiable claims."""
    keyword_sentence = _format_inline_list(matching_keywords)

    return "\n".join(
        [
            "# Cover Letter Draft",
            "",
            f"> {REVIEW_WARNING}",
            "",
            "Dear Hiring Team,",
            "",
            (
                f"I am interested in the {job['title']} role at "
                f"{job['company']}. Based on my provided resume/profile, "
                f"the overlap I found with this posting includes: "
                f"{keyword_sentence}."
            ),
            "",
            (
                "I would welcome the chance to discuss how the background "
                "documented in my resume may fit this role. I will review this "
                "draft carefully before using it and remove anything I cannot "
                "verify."
            ),
            "",
            "Sincerely,",
            "[Your Name]",
            "",
        ]
    )


def build_match_notes(job: dict[str, str], matching_keywords: list[str]) -> str:
    """Build notes that help the user review the draft manually."""
    return "\n".join(
        [
            "# Match Notes",
            "",
            f"> {REVIEW_WARNING}",
            "",
            f"- Title: {job['title']}",
            f"- Company: {job['company']}",
            f"- Location: {job['location']}",
            f"- Matching keywords: {_format_inline_list(matching_keywords)}",
            "",
            "Review checklist:",
            "- Confirm every claim appears in your resume/profile.",
            "- Remove anything that is not true or cannot be verified.",
            "- Add personal details only in your local ignored files.",
            "",
        ]
    )


def _read_required_text(path: Path, label: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Could not find {label} file: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"{label.title()} file is empty: {path}")

    return text


def _format_bullets(values: list[str]) -> str:
    if not values:
        return "- None found"
    return "\n".join(f"- {value}" for value in values)


def _format_inline_list(values: list[str]) -> str:
    if not values:
        return "no configured keyword overlap found"
    return ", ".join(values)
