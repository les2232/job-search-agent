from resume_tailoring import PLAN_KEYS, build_tailoring_plan


PROFILE_EVIDENCE = [
    {
        "id": "python_streamlit_project",
        "skills": ["Python", "Streamlit", "automation"],
        "sections": ["Projects", "Technical Skills"],
        "evidence": "Built a local-first Python/Streamlit job application assistant.",
        "resume_bullet": (
            "Built a local-first Python/Streamlit assistant that parses job postings, "
            "scores fit, and generates reviewable application materials."
        ),
    },
    {
        "id": "support_workflow_project",
        "skills": ["IT support", "documentation"],
        "sections": ["Experience", "Projects"],
        "evidence": "Documented support workflows and routed common user issues.",
        "resume_bullet": "Documented technical support workflows and guided users through repeatable troubleshooting steps.",
    },
    {
        "id": "api_project",
        "skills": ["REST integrations"],
        "aliases": ["API"],
        "sections": ["Projects"],
        "evidence": "Built JSON integration experiments.",
        "resume_bullet": "Built REST/JSON integration experiments that connected local tools to structured data sources.",
    },
]


def test_strong_requirement_match_selects_right_bullet() -> None:
    plan = build_tailoring_plan(["Python"], PROFILE_EVIDENCE)

    assert plan["skills_to_emphasize"] == ["Python"]
    assert plan["sections_to_prioritize"] == ["Projects", "Technical Skills"]
    assert plan["selected_bullets"] == [PROFILE_EVIDENCE[0]["resume_bullet"]]
    assert plan["matched_evidence"][0]["evidence_id"] == "python_streamlit_project"
    assert plan["matched_evidence"][0]["match_type"] == "strong"


def test_missing_requirement_becomes_gap() -> None:
    plan = build_tailoring_plan(["AWS"], PROFILE_EVIDENCE)

    assert plan["selected_bullets"] == []
    assert plan["gaps"] == ["AWS"]
    assert any("Missing evidence for AWS" in warning for warning in plan["review_warnings"])


def test_weak_partial_match_becomes_warning_without_selected_bullet() -> None:
    plan = build_tailoring_plan(["technical support workflows"], PROFILE_EVIDENCE)

    assert plan["matched_evidence"] == []
    assert plan["selected_bullets"] == []
    assert plan["weak_matches"][0]["evidence_id"] == "support_workflow_project"
    assert plan["weak_matches"][0]["match_type"] == "weak"
    assert any("Weak match for technical support workflows" in warning for warning in plan["review_warnings"])


def test_no_evidence_means_no_invented_bullet() -> None:
    plan = build_tailoring_plan(["Python", "Streamlit"], [])

    assert plan["matched_evidence"] == []
    assert plan["weak_matches"] == []
    assert plan["selected_bullets"] == []
    assert plan["gaps"] == ["Python", "Streamlit"]
    assert "No profile evidence was provided" in " ".join(plan["review_warnings"])


def test_output_contains_stable_top_level_keys() -> None:
    plan = build_tailoring_plan(["Python"], PROFILE_EVIDENCE)

    assert list(plan) == PLAN_KEYS


def test_matching_is_deterministic() -> None:
    first = build_tailoring_plan(["Python", {"requirement": "API"}, "AWS"], PROFILE_EVIDENCE)
    second = build_tailoring_plan(["Python", {"requirement": "API"}, "AWS"], PROFILE_EVIDENCE)

    assert first == second


def test_duplicate_bullets_are_not_selected_repeatedly() -> None:
    plan = build_tailoring_plan(["Python", "Streamlit", "automation"], PROFILE_EVIDENCE)

    assert plan["selected_bullets"] == [PROFILE_EVIDENCE[0]["resume_bullet"]]
    assert plan["skills_to_emphasize"] == ["Python", "Streamlit", "automation"]


def test_alias_match_supports_requirement_dicts() -> None:
    plan = build_tailoring_plan(
        [{"requirement": "API integration"}],
        PROFILE_EVIDENCE,
    )

    assert plan["selected_bullets"] == [PROFILE_EVIDENCE[2]["resume_bullet"]]
    assert plan["matched_evidence"][0]["evidence_id"] == "api_project"
