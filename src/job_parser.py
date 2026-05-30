"""Parse plain-text job descriptions into a small structured record."""

import html
import logging
import re


LOGGER = logging.getLogger(__name__)
DEBUG_PREVIEW_CHARS = 300

TITLE_LABELS = ["Title", "Job Title", "Position", "Role"]
COMPANY_LABELS = ["Company", "Employer", "Organization"]
LOCATION_LABELS = ["Location", "Job Location", "Work Location"]
WORK_MODE_LABELS = ["Work Mode", "Work Arrangement"]
WORK_MODE_KEYWORDS = ["remote", "hybrid", "on-site", "onsite", "on site"]
BOILERPLATE_LINES = {
    "equal opportunity employer",
    "full job description",
    "here's how the job details align with your profile.",
    "job details",
    "job type",
    "required skills/experience",
    "this employer is required to notify all applicants",
}
NON_TITLE_STARTS = {
    "about",
    "benefits",
    "description",
    "job description",
    "overview",
    "required skills",
    "required skills/experience",
    "requirements",
    "responsibilities",
    "summary",
    "use",
    "we",
    "you",
}


def parse_job_text(
    job_text: str,
    title: str = "",
    company: str = "",
    location: str = "",
) -> dict[str, object]:
    """Extract basic fields from a job description.

    The sample format uses simple labels such as "Title:", "Company:", and
    "Location:". If a label is missing, the parser returns "Unknown" so the
    rest of the workflow can still run.
    """
    clean_text = job_text.strip()
    labeled_title = _find_first_labeled_value(job_text, TITLE_LABELS)
    labeled_company = _find_first_labeled_value(job_text, COMPANY_LABELS)
    labeled_location = _find_first_labeled_value(job_text, LOCATION_LABELS)
    labeled_work_mode = _find_first_labeled_value(job_text, WORK_MODE_LABELS)
    top_lines = _get_top_lines(job_text)

    parsed_title = _first_known_value(title, labeled_title)
    parsed_company = _first_known_value(company, labeled_company)
    parsed_location = _first_known_value(location, labeled_location)
    fallback_path = "explicit fields"

    if parsed_title == "Unknown":
        parsed_title = _infer_title(top_lines)
        fallback_path = "top-line inference"

    if parsed_company == "Unknown":
        parsed_company = _infer_company(top_lines, parsed_title)
        fallback_path = "top-line inference"

    if parsed_location == "Unknown":
        parsed_location = _infer_location(top_lines)
        fallback_path = "top-line inference"

    work_mode = _first_known_value(
        labeled_work_mode,
        _infer_work_mode([parsed_location]),
        _infer_work_mode(top_lines),
    )
    parser_debug = {
        "raw_preview": clean_text[:DEBUG_PREVIEW_CHARS],
        "parsed_title": parsed_title,
        "parsed_company": parsed_company,
        "parsed_location": parsed_location,
        "parsed_work_mode": work_mode,
        "fallback_path": fallback_path,
    }
    LOGGER.debug(
        "Parsed job metadata: raw_preview=%r title=%r company=%r "
        "location=%r work_mode=%r fallback_path=%r",
        parser_debug["raw_preview"],
        parsed_title,
        parsed_company,
        parsed_location,
        work_mode,
        fallback_path,
    )

    return {
        "title": parsed_title,
        "company": parsed_company,
        "location": parsed_location,
        "work_mode": work_mode,
        "raw_text": clean_text,
        "parser_debug": parser_debug,
    }


def _find_first_labeled_value(job_text: str, labels: list[str]) -> str:
    for label in labels:
        value = _find_labeled_value(job_text, label)
        if value != "Unknown":
            return value
    return "Unknown"


def _find_labeled_value(job_text: str, label: str) -> str:
    pattern = re.compile(rf"^{re.escape(label)}\s*:\s*(.+)$", flags=re.IGNORECASE)
    for line in job_text.splitlines():
        clean_line = _clean_copied_line(line)
        match = pattern.match(clean_line)
        if match:
            value = _clean_copied_line(match.group(1))
            return value or "Unknown"

    return "Unknown"


def _get_top_lines(job_text: str, limit: int = 50) -> list[str]:
    lines = []
    for line in job_text.splitlines():
        clean_line = _clean_copied_line(line)
        if clean_line and not _is_boilerplate_line(clean_line):
            lines.append(clean_line)
    return lines[:limit]


def _clean_copied_line(line: str) -> str:
    text = html.unescape(line).replace("\u00a0", " ").strip()
    if text in {"&", "Â"}:
        return ""
    return text


def _first_known_value(*values: str) -> str:
    for value in values:
        if value and value.strip() and value.strip().lower() != "unknown":
            return value.strip()
    return "Unknown"


def _infer_title(lines: list[str]) -> str:
    for line in lines[:5]:
        if _looks_like_title(line):
            return line
    title = _infer_title_from_description(lines)
    if title != "Unknown":
        return title
    return "Unknown"


def _infer_company(lines: list[str], parsed_title: str) -> str:
    for line in lines[:8]:
        if line == parsed_title or _looks_like_location(line):
            continue
        if _is_section_heading(line) or _looks_like_sentence(line):
            company = _infer_company_from_intro(line)
            if company != "Unknown":
                return company
            continue
        if _looks_like_company(line):
            return _strip_company_prefix(line)
    return "Unknown"


def _infer_location(lines: list[str]) -> str:
    for line in lines[:20]:
        if _looks_like_location(line):
            return line
    return "Unknown"


def _infer_work_mode(lines: list[str]) -> str:
    search_text = " ".join(lines[:20]).lower()
    mode_positions = []
    for mode, keywords in [
        ("Remote", ["remote"]),
        ("Hybrid", ["hybrid"]),
        ("On-site", ["on-site", "onsite", "on site"]),
    ]:
        positions = [
            search_text.find(keyword)
            for keyword in keywords
            if search_text.find(keyword) != -1
        ]
        if positions:
            mode_positions.append((min(positions), mode))

    if not mode_positions:
        return "Unknown"

    return sorted(mode_positions)[0][1]


def _looks_like_title(line: str) -> bool:
    normalized = line.strip().lower()
    if (
        not normalized
        or normalized.startswith(("-", "*", "•"))
        or _is_boilerplate_line(line)
        or _looks_like_location(line)
        or _looks_like_sentence(line)
    ):
        return False
    if normalized in NON_TITLE_STARTS:
        return False
    if any(normalized.startswith(f"{word} ") for word in NON_TITLE_STARTS):
        return False
    return len(line.split()) <= 10


def _looks_like_company(line: str) -> bool:
    if _is_boilerplate_line(line) or _looks_like_sentence(line):
        return False
    return len(line.split()) <= 8


def _looks_like_location(line: str) -> bool:
    lowered = line.lower()
    if any(keyword in lowered for keyword in WORK_MODE_KEYWORDS):
        return True
    if "united states" in lowered:
        return True
    return re.search(r"\b[A-Z][a-zA-Z .'-]+,\s*[A-Z]{2}\b", line) is not None


def _looks_like_sentence(line: str) -> bool:
    return line.endswith(".") or len(line.split()) > 14


def _is_section_heading(line: str) -> bool:
    normalized = line.strip().lower().rstrip(":")
    return normalized in NON_TITLE_STARTS


def _is_boilerplate_line(line: str) -> bool:
    normalized = line.strip().lower().rstrip(":")
    return normalized in BOILERPLATE_LINES or any(
        normalized.startswith(value)
        for value in BOILERPLATE_LINES
        if len(value.split()) > 3
    )


def _infer_company_from_intro(line: str) -> str:
    match = re.match(r"^At\s+([A-Z][A-Za-z0-9 &'.,-]+?)(?:[,.]\s|\.\.\.|$)", line.strip())
    if not match:
        return "Unknown"
    return match.group(1).strip(" .,-")


def _infer_title_from_description(lines: list[str]) -> str:
    search_text = " ".join(lines[:12])
    match = re.search(
        r"\b(?:looking|hiring|searching)\s+for\s+(?:an?\s+)?([A-Za-z][A-Za-z0-9 +/#-]+?)(?:\s+to\b|[,.])",
        search_text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "Unknown"
    return _title_case_role(match.group(1))


def _title_case_role(value: str) -> str:
    titled_words = []
    for word in value.strip().split():
        titled_words.append("-".join(part.capitalize() for part in word.split("-")))
    return " ".join(titled_words)


def _strip_company_prefix(line: str) -> str:
    return re.sub(
        r"^(company|employer|organization)\s*[-–]\s*",
        "",
        line,
        flags=re.IGNORECASE,
    )
