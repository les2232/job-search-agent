"""Parse plain-text job descriptions into a small structured record."""

import html
import logging
import re


LOGGER = logging.getLogger(__name__)
DEBUG_PREVIEW_CHARS = 300

TITLE_LABELS = ["Title", "Job Title", "Position", "Job Position", "Role"]
COMPANY_LABELS = ["Company", "Employer", "Organization"]
LOCATION_LABELS = ["Location", "Job Location", "Work Location"]
WORK_MODE_LABELS = ["Work Mode", "Work Arrangement"]
WORK_MODE_KEYWORDS = ["remote", "hybrid", "on-site", "onsite", "on site"]
BOILERPLATE_LINES = {
    "apply",
    "apply now",
    "back to search results",
    "equal opportunity employer",
    "full job description",
    "here's how the job details align with your profile.",
    "home",
    "job details",
    "job type",
    "jobs",
    "required skills/experience",
    "save job",
    "search jobs",
    "share job",
    "similar jobs",
    "this employer is required to notify all applicants",
}
NON_TITLE_STARTS = {
    "about",
    "about the company",
    "about the job",
    "benefits",
    "compensation",
    "description",
    "job description",
    "how you'll contribute",
    "how you’ll contribute",
    "overview",
    "required skills",
    "required skills/experience",
    "requirements",
    "responsibilities",
    "summary",
    "use",
    "work eligibility",
    "we",
    "you",
    "your skills and approach",
}
COMPANY_INTRO_SKIP_WORDS = {"I", "It", "Our", "The", "This", "We", "You"}


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

    work_mode = _normalize_work_mode(
        _first_known_value(
            labeled_work_mode,
            _infer_work_mode([parsed_location]),
            _infer_work_mode(top_lines),
        )
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
    title = _infer_title_from_heading(lines)
    if title != "Unknown":
        return title
    for line in lines[:5]:
        if _looks_like_title(line):
            return line
    title = _infer_title_from_description(lines)
    if title != "Unknown":
        return title
    return "Unknown"


def _infer_company(lines: list[str], parsed_title: str) -> str:
    previous_section = ""
    for line in lines[:20]:
        normalized_section = _normalized_heading(line)
        if line == parsed_title or _looks_like_location(line):
            previous_section = normalized_section if _is_section_heading(line) else previous_section
            continue
        if _extract_title_from_heading(line) != "Unknown":
            continue
        if _is_section_heading(line):
            previous_section = normalized_section
            continue
        if _looks_like_sentence(line):
            company = _infer_company_from_intro(line, previous_section)
            if company != "Unknown":
                return company
            continue
        if _looks_like_company(line):
            return _strip_company_prefix(line)
        previous_section = normalized_section if _is_section_heading(line) else previous_section
    return "Unknown"


def _infer_location(lines: list[str]) -> str:
    for line in lines[:20]:
        if _looks_like_location(line):
            return line
    return "Unknown"


def _infer_work_mode(lines: list[str]) -> str:
    search_text = " ".join(lines[:20]).lower()
    if re.search(r"\bremote\s+with\s+travel\b", search_text):
        return "Remote"
    if re.search(r"\b(all roles are|this role is|role is|position is)\s+remote\b", search_text):
        return "Remote"
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


def _normalize_work_mode(value: str) -> str:
    if value == "Unknown":
        return value
    inferred = _infer_work_mode([value])
    return inferred if inferred != "Unknown" else value


def _looks_like_title(line: str) -> bool:
    normalized = line.strip().lower()
    if (
        not normalized
        or normalized.startswith(("-", "*", "•"))
        or _is_boilerplate_line(line)
        or _looks_like_location(line)
        or _looks_like_sentence(line)
        or _is_section_heading(line)
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
    if _looks_like_sentence(line):
        return False
    if any(keyword in lowered for keyword in WORK_MODE_KEYWORDS):
        return True
    if "united states" in lowered:
        return True
    return re.search(r"\b[A-Z][a-zA-Z .'-]+,\s*[A-Z]{2}\b", line) is not None


def _looks_like_sentence(line: str) -> bool:
    return line.endswith(".") or len(line.split()) > 14


def _is_section_heading(line: str) -> bool:
    normalized = _normalized_heading(line)
    return normalized in NON_TITLE_STARTS


def _is_boilerplate_line(line: str) -> bool:
    normalized = _normalized_heading(line)
    return normalized in BOILERPLATE_LINES or any(
        normalized.startswith(value)
        for value in BOILERPLATE_LINES
        if len(value.split()) > 3
    )


def _normalized_heading(line: str) -> str:
    return line.strip().lower().rstrip(":")


def _infer_company_from_intro(line: str, previous_section: str = "") -> str:
    clean_line = line.strip()
    at_match = re.match(r"^At\s+([A-Z][A-Za-z0-9 &'.,-]+?)(?:[,.]\s|\.\.\.|$)", clean_line)
    if at_match:
        return at_match.group(1).strip(" .,-")

    if previous_section != "about the company":
        return "Unknown"

    intro_match = re.match(
        r"^([A-Z][A-Za-z0-9 &'.,-]{1,80}?)\s+(?:is|are)\s+",
        clean_line,
    )
    if not intro_match:
        return "Unknown"
    company = intro_match.group(1).strip(" .,-")
    if company.split(" ", 1)[0] in COMPANY_INTRO_SKIP_WORDS:
        return "Unknown"
    return company


def _infer_title_from_heading(lines: list[str]) -> str:
    for line in lines[:20]:
        title = _extract_title_from_heading(line)
        if title != "Unknown":
            return title
    return "Unknown"


def _extract_title_from_heading(line: str) -> str:
    if _is_section_heading(line):
        return "Unknown"
    patterns = [
        r"\byour\s+role\s+as\s+(?:an?\s+)?(.+)$",
        r"\bthe\s+role\s*[:\-–]\s*(.+)$",
        r"\brole\s*[:\-–]\s*(.+)$",
        r"\bposition\s*[:\-–]\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, line, flags=re.IGNORECASE)
        if match:
            return _clean_inferred_title(match.group(1))
    return "Unknown"


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


def _clean_inferred_title(value: str) -> str:
    clean_value = re.split(r"\s+[-–]\s+|\s+[|]\s+", value.strip(), maxsplit=1)[0]
    clean_value = clean_value.strip(" .:-–")
    if not clean_value or _is_section_heading(clean_value) or _looks_like_sentence(clean_value):
        return "Unknown"
    if len(clean_value.split()) > 10:
        return "Unknown"
    return clean_value


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
