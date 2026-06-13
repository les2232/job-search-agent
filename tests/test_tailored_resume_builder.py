from tailored_resume_builder import OUTPUT_KEYS, build_tailored_resume_draft


PLAN = {
    "skills_to_emphasize": ["Python", "Streamlit", "technical support"],
    "sections_to_prioritize": ["Projects", "Technical Skills"],
    "selected_bullets": [
        {
            "requirement": "Python",
            "evidence": "Built a local-first Python/Streamlit job application assistant.",
            "bullet": (
                "Built a local-first Python/Streamlit assistant that parses job "
                "postings, scores fit, and generates reviewable application materials."
            ),
        }
    ],
    "matched_evidence": [
        {
            "requirement": "Python",
            "evidence_id": "python_streamlit_project",
            "match_type": "strong",
            "evidence": "Built a local-first Python/Streamlit job application assistant.",
            "resume_bullet": (
                "Built a local-first Python/Streamlit assistant that parses job "
                "postings, scores fit, and generates reviewable application materials."
            ),
        }
    ],
    "weak_matches": [
        {
            "requirement": "technical support",
            "evidence_id": "support_project",
            "match_type": "weak",
            "evidence": "Documented support workflows.",
            "resume_bullet": "",
        }
    ],
    "gaps": ["AWS experience not strongly supported"],
    "review_warnings": ["Do not claim production cloud deployment unless verified."],
    "tailoring_summary": "Strong match for Python and Streamlit; review AWS requirement.",
}


def test_builds_markdown_from_normal_tailoring_plan() -> None:
    draft = build_tailored_resume_draft(PLAN, profile={"display_name": "Example Candidate"})

    assert list(draft) == OUTPUT_KEYS
    assert draft["included_sections"] == [
        "Tailored Resume Draft",
        "Candidate Summary",
        "Target Role Alignment",
        "Matched Requirements",
        "Strong Evidence Bullets",
        "Gaps or Weak Matches",
        "Suggested Resume Emphasis",
        "Review Warnings",
        "Human Review Checklist",
    ]
    assert "# Tailored Resume Draft" in draft["markdown"]
    assert "Candidate: Example Candidate" in draft["markdown"]
    assert "## Candidate Summary" in draft["markdown"]
    assert "## Target Role Alignment" in draft["markdown"]
    assert "Strong match for Python and Streamlit" in draft["markdown"]
    assert draft["selected_bullet_count"] == 1


def test_includes_matched_requirements_and_strong_evidence_bullets() -> None:
    draft = build_tailored_resume_draft(PLAN)

    assert "## Matched Requirements" in draft["markdown"]
    assert "Python: Built a local-first Python/Streamlit assistant" in draft["markdown"]
    assert "## Strong Evidence Bullets" in draft["markdown"]
    assert "Built a local-first Python/Streamlit assistant" in draft["markdown"]


def test_does_not_invent_bullets_when_selected_bullets_empty() -> None:
    draft = build_tailored_resume_draft({**PLAN, "selected_bullets": []})
    strong_bullet_section = draft["markdown"].split("## Strong Evidence Bullets", 1)[1].split(
        "## Gaps or Weak Matches",
        1,
    )[0]

    assert draft["selected_bullet_count"] == 0
    assert "- No verified resume bullets were selected." in draft["markdown"]
    assert "Built a local-first Python/Streamlit assistant" not in strong_bullet_section


def test_deduplicates_repeated_bullets() -> None:
    plan = {
        **PLAN,
        "selected_bullets": [
            "Built local tooling.",
            {"bullet": "Built local tooling."},
            {"resume_bullet": "Built local tooling."},
        ],
    }

    draft = build_tailored_resume_draft(plan)

    assert draft["selected_bullet_count"] == 1
    assert draft["markdown"].count("- Built local tooling.") == 1


def test_includes_gaps_and_review_warnings() -> None:
    draft = build_tailored_resume_draft(PLAN)

    assert draft["warnings"] == ["Do not claim production cloud deployment unless verified."]
    assert draft["gaps"] == ["AWS experience not strongly supported"]
    assert "## Gaps or Weak Matches" in draft["markdown"]
    assert "technical support: Documented support workflows." in draft["markdown"]
    assert "Do not claim production cloud deployment unless verified." in draft["markdown"]
    assert "AWS experience not strongly supported" in draft["markdown"]


def test_suggested_emphasis_uses_only_plan_skills_and_sections() -> None:
    draft = build_tailored_resume_draft(PLAN)

    assert "## Suggested Resume Emphasis" in draft["markdown"]
    assert "Emphasize Python only where existing evidence supports it." in draft["markdown"]
    assert "Review the Projects section for relevant supported examples." in draft["markdown"]
    assert "AWS" not in draft["markdown"].split("## Suggested Resume Emphasis", 1)[1]


def test_includes_human_review_checklist() -> None:
    draft = build_tailored_resume_draft(PLAN)

    assert "## Human Review Checklist" in draft["markdown"]
    assert "Confirm each bullet is true" in draft["markdown"]
    assert "Human review required" in draft["markdown"]


def test_handles_missing_optional_fields_safely() -> None:
    draft = build_tailored_resume_draft({})

    assert draft["selected_bullet_count"] == 0
    assert draft["warnings"] == []
    assert draft["gaps"] == []
    assert "No tailoring summary was provided." in draft["markdown"]
    assert "No resume emphasis areas were selected." in draft["markdown"]


def test_does_not_include_raw_job_text() -> None:
    draft = build_tailored_resume_draft(
        {
            **PLAN,
            "raw_job_text": "CONFIDENTIAL RAW JOB POSTING SHOULD NOT APPEAR",
            "job_text": "ANOTHER RAW JOB POSTING FIELD",
        }
    )

    assert "CONFIDENTIAL RAW JOB POSTING SHOULD NOT APPEAR" not in draft["markdown"]
    assert "ANOTHER RAW JOB POSTING FIELD" not in draft["markdown"]
    assert "raw_job_text" not in draft["metadata"]


def test_output_is_deterministic() -> None:
    first = build_tailored_resume_draft(PLAN, base_resume="# Resume", profile={"name": "A"})
    second = build_tailored_resume_draft(PLAN, base_resume="# Resume", profile={"name": "A"})

    assert first == second
