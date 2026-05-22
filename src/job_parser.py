"""Parse plain-text job descriptions into a small structured record."""


def parse_job_text(job_text: str) -> dict[str, str]:
    """Extract basic fields from a job description.

    The sample format uses simple labels such as "Title:", "Company:", and
    "Location:". If a label is missing, the parser returns "Unknown" so the
    rest of the workflow can still run.
    """
    return {
        "title": _find_labeled_value(job_text, "Title"),
        "company": _find_labeled_value(job_text, "Company"),
        "location": _find_labeled_value(job_text, "Location"),
        "raw_text": job_text.strip(),
    }


def _find_labeled_value(job_text: str, label: str) -> str:
    prefix = f"{label}:"

    for line in job_text.splitlines():
        clean_line = line.strip()
        if clean_line.lower().startswith(prefix.lower()):
            value = clean_line[len(prefix) :].strip()
            return value or "Unknown"

    return "Unknown"
