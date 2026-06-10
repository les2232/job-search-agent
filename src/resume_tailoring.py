"""Build deterministic resume tailoring plans from job requirements and evidence."""

import re
from typing import Any


PLAN_KEYS = [
    "skills_to_emphasize",
    "sections_to_prioritize",
    "selected_bullets",
    "matched_evidence",
    "weak_matches",
    "gaps",
    "review_warnings",
    "tailoring_summary",
]

ALIASES = {
    "api": {"api", "apis", "rest api", "rest apis", "api integration", "integrations"},
    "automation": {"automation", "workflow automation", "automated workflows", "workflow"},
    "documentation": {"documentation", "technical documentation", "knowledge base"},
    "python": {"python", "python scripting", "python development"},
    "sql": {"sql", "sqlite", "sql server", "database", "relational database"},
    "streamlit": {"streamlit"},
    "technical support": {
        "technical support",
        "it support",
        "help desk",
        "service desk",
        "user support",
        "end user support",
        "troubleshooting",
    },
    "testing": {"testing", "unit testing", "pytest", "test automation"},
}

STOPWORDS = {
    "and",
    "for",
    "in",
    "of",
    "or",
    "the",
    "to",
    "with",
}


def build_tailoring_plan(
    job_requirements: object,
    profile_evidence: object,
) -> dict[str, object]:
    """Return a stable, evidence-based resume tailoring plan."""
    requirements = _normalize_requirements(job_requirements)
    evidence_items = _normalize_evidence_items(profile_evidence)

    matched_evidence = []
    weak_matches = []
    gaps = []
    selected_bullets = []
    skills_to_emphasize = []
    sections_to_prioritize = []
    review_warnings = []
    selected_bullet_keys = set()

    for requirement in requirements:
        best_strong = _find_first_match(requirement, evidence_items, strong=True)
        if best_strong is not None:
            evidence = best_strong
            matched_evidence.append(_match_record(requirement, evidence, "strong"))
            _append_unique(skills_to_emphasize, requirement["label"])
            for section in evidence["sections"]:
                _append_unique(sections_to_prioritize, section)
            bullet = evidence["resume_bullet"]
            bullet_key = _normalize_label(bullet)
            if bullet and bullet_key not in selected_bullet_keys:
                selected_bullets.append(bullet)
                selected_bullet_keys.add(bullet_key)
            continue

        weak = _find_first_match(requirement, evidence_items, strong=False)
        if weak is not None:
            weak_matches.append(_match_record(requirement, weak, "weak"))
            review_warnings.append(
                f"Weak match for {requirement['label']}: review before using this claim."
            )
            continue

        gaps.append(requirement["label"])
        review_warnings.append(
            f"Missing evidence for {requirement['label']}: do not add an unsupported resume claim."
        )

    if not requirements:
        review_warnings.append("No job requirements were provided.")
    if requirements and not evidence_items:
        review_warnings.append("No profile evidence was provided; no resume bullets were selected.")

    return {
        "skills_to_emphasize": skills_to_emphasize,
        "sections_to_prioritize": sections_to_prioritize,
        "selected_bullets": selected_bullets,
        "matched_evidence": matched_evidence,
        "weak_matches": weak_matches,
        "gaps": gaps,
        "review_warnings": _dedupe(review_warnings),
        "tailoring_summary": _tailoring_summary(
            len(matched_evidence),
            len(weak_matches),
            len(gaps),
        ),
    }


def _normalize_requirements(job_requirements: object) -> list[dict[str, str]]:
    if not isinstance(job_requirements, list):
        return []
    requirements = []
    for value in job_requirements:
        label = ""
        if isinstance(value, str):
            label = value
        elif isinstance(value, dict):
            for key in ["requirement", "label", "name", "skill"]:
                item = value.get(key)
                if isinstance(item, str) and item.strip():
                    label = item
                    break
        label = " ".join(label.split()).strip()
        if label:
            normalized = _normalize_label(label)
            requirements.append(
                {
                    "label": label,
                    "normalized": normalized,
                    "canonical": _canonical_label(normalized),
                }
            )
    return requirements


def _normalize_evidence_items(profile_evidence: object) -> list[dict[str, object]]:
    if isinstance(profile_evidence, dict):
        raw_items = profile_evidence.get("evidence") or profile_evidence.get("items") or []
    else:
        raw_items = profile_evidence
    if not isinstance(raw_items, list):
        return []

    items = []
    for index, value in enumerate(raw_items):
        if not isinstance(value, dict):
            continue
        skills = _string_list(value.get("skills"))
        aliases = _string_list(value.get("aliases"))
        sections = _string_list(value.get("sections"))
        evidence_text = _safe_text(value.get("evidence"))
        resume_bullet = _safe_text(value.get("resume_bullet"))
        searchable_values = skills + aliases + sections + [evidence_text, resume_bullet]
        normalized_terms = {_normalize_label(item) for item in skills + aliases if _normalize_label(item)}
        canonical_terms = {_canonical_label(term) for term in normalized_terms}
        searchable_text = _normalize_label(" ".join(searchable_values))
        items.append(
            {
                "id": _safe_text(value.get("id")) or f"evidence_{index + 1}",
                "skills": skills,
                "sections": sections,
                "evidence": evidence_text,
                "resume_bullet": resume_bullet,
                "normalized_terms": normalized_terms,
                "canonical_terms": canonical_terms,
                "searchable_text": searchable_text,
            }
        )
    return items


def _find_first_match(
    requirement: dict[str, str],
    evidence_items: list[dict[str, object]],
    strong: bool,
) -> dict[str, object] | None:
    for evidence in evidence_items:
        if strong and _strong_match(requirement, evidence):
            return evidence
        if not strong and _weak_match(requirement, evidence):
            return evidence
    return None


def _strong_match(requirement: dict[str, str], evidence: dict[str, object]) -> bool:
    normalized = requirement["normalized"]
    canonical = requirement["canonical"]
    normalized_terms = evidence["normalized_terms"]
    canonical_terms = evidence["canonical_terms"]
    if normalized in normalized_terms:
        return True
    if canonical != normalized and canonical in canonical_terms:
        return True
    return canonical in normalized_terms


def _weak_match(requirement: dict[str, str], evidence: dict[str, object]) -> bool:
    if _strong_match(requirement, evidence):
        return False
    requirement_tokens = _meaningful_tokens(requirement["normalized"])
    if not requirement_tokens:
        return False
    evidence_tokens = _meaningful_tokens(str(evidence["searchable_text"]))
    overlap = requirement_tokens.intersection(evidence_tokens)
    if not overlap:
        return False
    return len(overlap) >= 2 or len(requirement_tokens) == 1


def _match_record(
    requirement: dict[str, str],
    evidence: dict[str, object],
    match_type: str,
) -> dict[str, object]:
    return {
        "requirement": requirement["label"],
        "evidence_id": evidence["id"],
        "match_type": match_type,
        "evidence": evidence["evidence"],
        "resume_bullet": evidence["resume_bullet"],
    }


def _tailoring_summary(strong_count: int, weak_count: int, gap_count: int) -> str:
    return (
        f"Found {strong_count} verified match(es), {weak_count} weak match(es), "
        f"and {gap_count} gap(s). Use selected bullets only after manual review."
    )


def _canonical_label(normalized: str) -> str:
    for canonical, aliases in ALIASES.items():
        normalized_aliases = {_normalize_label(alias) for alias in aliases}
        if normalized in normalized_aliases:
            return canonical
    return normalized


def _normalize_label(value: object) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _meaningful_tokens(value: str) -> set[str]:
    return {
        token
        for token in _normalize_label(value).split()
        if token and token not in STOPWORDS and len(token) > 1
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _safe_text(value: object) -> str:
    return str(value).strip() if isinstance(value, str) else ""


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _dedupe(values: list[str]) -> list[str]:
    deduped = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped
