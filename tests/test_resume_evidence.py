from pathlib import Path
from textwrap import dedent

from resume_evidence import (
    build_profile_evidence,
    extract_resume_bullets_from_text,
    load_profile_evidence_from_path,
    normalize_evidence_item,
)
from resume_tailoring import build_tailoring_plan


def test_normalizes_complete_evidence_item() -> None:
    item = normalize_evidence_item(
        {
            "id": "python_streamlit_project",
            "skills": ["Python", "Streamlit", "automation"],
            "sections": ["Projects", "Technical Skills"],
            "evidence": "Built a local-first Python/Streamlit job application assistant.",
            "resume_bullet": "Built a local-first Python/Streamlit assistant.",
            "source": "project",
        }
    )

    assert item == {
        "id": "python_streamlit_project",
        "skills": ["Python", "Streamlit", "automation"],
        "sections": ["Projects", "Technical Skills"],
        "evidence": "Built a local-first Python/Streamlit job application assistant.",
        "resume_bullet": "Built a local-first Python/Streamlit assistant.",
        "source": "project",
    }


def test_handles_missing_optional_fields_safely() -> None:
    item = normalize_evidence_item(
        {
            "skills": ["Python"],
            "evidence": "Python scripting project.",
        }
    )

    assert item["id"] == "python-scripting-project"
    assert item["skills"] == ["Python"]
    assert item["sections"] == ["Resume"]
    assert item["resume_bullet"] == ""
    assert item["source"] == "profile"


def test_supports_field_aliases() -> None:
    item = normalize_evidence_item(
        {
            "resumeBullet": "Built REST integrations.",
            "tags": "API, JSON",
            "section": "Projects",
            "description": "REST integration project.",
            "category": "project",
        }
    )

    assert item["skills"] == ["API", "JSON"]
    assert item["sections"] == ["Projects"]
    assert item["evidence"] == "REST integration project."
    assert item["resume_bullet"] == "Built REST integrations."
    assert item["source"] == "project"


def test_supports_dict_wrappers_with_common_keys() -> None:
    evidence = build_profile_evidence(
        {
            "items": [{"skill": "Python", "bullet": "Built Python tools."}],
            "proof_blocks": [
                {
                    "name": "Support Assistant",
                    "tools": ["Flask", "SQLite"],
                    "bullets": ["Built support workflows."],
                }
            ],
            "projects": [{"skills": ["Streamlit"], "summary": "Dashboard project."}],
        }
    )

    assert [item["id"] for item in evidence] == [
        "built-python-tools",
        "support-assistant",
        "dashboard-project",
    ]
    assert evidence[1]["source"] == "project"
    assert evidence[1]["resume_bullet"] == "Built support workflows."


def test_generates_deterministic_ids_when_missing() -> None:
    raw = {"skills": ["Python"], "evidence": "Built Python workflow automation."}

    first = normalize_evidence_item(raw)
    second = normalize_evidence_item(raw)

    assert first["id"] == "built-python-workflow-automation"
    assert first["id"] == second["id"]


def test_does_not_invent_bullets_or_skills() -> None:
    item = normalize_evidence_item({"evidence": "Documented support workflows."})

    assert item["skills"] == []
    assert item["resume_bullet"] == ""
    assert item["evidence"] == "Documented support workflows."


def test_filters_unusable_empty_records() -> None:
    evidence = build_profile_evidence(
        [
            {},
            {"skills": []},
            {"bullet": "Built local tooling."},
        ]
    )

    assert len(evidence) == 1
    assert evidence[0]["resume_bullet"] == "Built local tooling."


def test_extract_resume_bullets_from_text_uses_existing_bullets_only() -> None:
    evidence = extract_resume_bullets_from_text(
        """
        # Candidate

        ## Projects
        - Built a local-first packet generator.
        * Added smoke tests.
        """
    )

    assert [item["resume_bullet"] for item in evidence] == [
        "Built a local-first packet generator.",
        "Added smoke tests.",
    ]
    assert evidence[0]["sections"] == ["Projects"]
    assert evidence[0]["skills"] == []


def test_load_profile_evidence_from_path_reads_resume_base(tmp_path: Path) -> None:
    profile_dir = tmp_path / "profile"
    profile_dir.mkdir()
    (profile_dir / "resume_base.md").write_text(
        dedent(
            """
            # Profile

            ## Project Evidence / Proof Library

            ### Job Search Automation Tool

            **Tools / Skills:** Python, Streamlit

            * Built a local-first packet generator.
            """
        ),
        encoding="utf-8",
    )

    evidence = load_profile_evidence_from_path(profile_dir)

    assert evidence[0]["id"] == "job-search-automation-tool"
    assert evidence[0]["skills"] == ["Python", "Streamlit"]
    assert evidence[0]["resume_bullet"] == "Built a local-first packet generator."


def test_profile_evidence_is_compatible_with_tailoring_plan() -> None:
    evidence = build_profile_evidence(
        {
            "proof_blocks": [
                {
                    "name": "Job Search Automation Tool",
                    "tools": ["Python", "Streamlit", "automation"],
                    "bullets": [
                        "Built a local-first Python/Streamlit assistant that parses job postings."
                    ],
                }
            ]
        }
    )

    plan = build_tailoring_plan(["Python", "AWS"], evidence)

    assert plan["selected_bullets"] == [
        "Built a local-first Python/Streamlit assistant that parses job postings."
    ]
    assert plan["matched_evidence"][0]["evidence_id"] == "job-search-automation-tool"
    assert plan["gaps"] == ["AWS"]
