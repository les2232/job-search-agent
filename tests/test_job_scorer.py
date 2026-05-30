from job_scorer import (
    NEGATIVE_KEYWORDS,
    POSITIVE_KEYWORDS,
    extract_job_requirements,
    score_job,
)


FEI_JOB_TEXT = """
FEI Systems builds technology solutions for health and human services.
We are looking for a Full-Stack Developer to work on case management software.

Required Skills/Experience
- 4+ years C#/.NET software development experience
- 3+ years Angular 16+ and TypeScript development
- SQL Server or relational database experience
- Git, Azure DevOps, and CI/CD pipelines
- 1+ years AWS serverless or similar cloud services
- Object-oriented design patterns
- Domain Driven Design
- Service Oriented Architecture
- Unit testing
- Test Driven Development
"""

ARRIVIA_AI_JOB_TEXT = """
Arrivia, Inc. is hiring an AI Agent Builder to improve automation workflows for
travel operations. This remote role will build AI agents and API integrations
that connect internal systems, data workflows, and user-facing support tools.

Required Skills/Experience
- Python scripting or Python development
- SQL and data workflows
- APIs and API integration
- Automation and workflow automation
- AI agent or agentic workflow experience
- LLM workflows and prompt engineering
- Object-oriented design patterns
"""


def test_score_job_clamps_to_100() -> None:
    job = {"raw_text": " ".join(POSITIVE_KEYWORDS)}

    assert score_job(job)["score"] == 100


def test_score_job_clamps_to_0() -> None:
    job = {"raw_text": " ".join(NEGATIVE_KEYWORDS)}

    assert score_job(job)["score"] == 0


def test_score_job_uses_custom_scoring_config() -> None:
    config = {
        "starting_score": 40,
        "positive_keyword_points": 20,
        "concern_keyword_penalty": 15,
        "apply_threshold": 70,
        "maybe_threshold": 50,
        "positive_keywords": ["python", "remote"],
        "concern_keywords": ["senior"],
    }
    job = {"raw_text": "Remote Python role with senior ownership."}

    score_details = score_job(job, config)

    assert score_details["score"] == 65
    assert score_details["recommendation"] == "Maybe"
    assert score_details["matched_keywords"] == ["python", "remote"]
    assert score_details["concerns"] == ["senior"]


def test_score_job_includes_high_score_explanation() -> None:
    job = {
        "title": "Junior Python Analyst",
        "company": "Example Studio",
        "location": "Remote",
        "work_mode": "Remote",
        "raw_text": " ".join(POSITIVE_KEYWORDS),
    }

    score_details = score_job(job)
    explanation = score_details["explanation"]

    assert score_details["recommendation"] == "Apply"
    assert "100/100" in explanation["fit_summary"]
    assert any("Matched fit keywords" in item for item in explanation["strengths"])
    assert any("Generate an application packet" in item for item in explanation["tailoring_suggestions"])


def test_score_job_includes_medium_score_explanation() -> None:
    config = {
        "starting_score": 50,
        "positive_keyword_points": 5,
        "concern_keyword_penalty": 8,
        "apply_threshold": 75,
        "maybe_threshold": 60,
        "positive_keywords": ["python", "sql", "remote"],
        "concern_keywords": ["senior"],
    }
    job = {
        "title": "Support Analyst",
        "company": "Example Studio",
        "location": "Remote",
        "work_mode": "Remote",
        "raw_text": "Python SQL support role.",
    }

    score_details = score_job(job, config)
    explanation = score_details["explanation"]

    assert score_details["score"] == 60
    assert score_details["recommendation"] == "Maybe"
    assert "gaps should be reviewed before applying" in explanation["fit_summary"]
    assert "remote" in score_details["missing_keywords"]


def test_score_job_includes_low_score_explanation() -> None:
    job = {
        "title": "Senior Sales Lead",
        "company": "Example Studio",
        "location": "Unknown",
        "work_mode": "Unknown",
        "raw_text": "Senior sales commission role with on-call expectations.",
    }

    score_details = score_job(job)
    explanation = score_details["explanation"]

    assert score_details["recommendation"] == "Skip"
    assert "may require skills or experience" in explanation["fit_summary"]
    assert any("Concern keywords found" in item for item in explanation["concerns"])


def test_score_job_explanation_mentions_unknown_metadata() -> None:
    job = {"raw_text": "Python documentation support role."}

    score_details = score_job(job)
    explanation = score_details["explanation"]

    assert any(
        "Job metadata did not parse cleanly" in item
        for item in explanation["concerns"]
    )
    assert any(
        "Work mode was not clearly detected" in item
        for item in explanation["concerns"]
    )


def test_score_job_explanation_does_not_include_full_raw_text() -> None:
    raw_text = "Python support role. " + ("private details " * 100)
    job = {
        "title": "Support Analyst",
        "company": "Example Studio",
        "location": "Remote",
        "work_mode": "Remote",
        "raw_text": raw_text,
    }

    explanation_text = str(score_job(job)["explanation"])

    assert raw_text not in explanation_text
    assert "private details" not in explanation_text


def test_extract_job_requirements_detects_fei_full_stack_requirements() -> None:
    requirements = extract_job_requirements(FEI_JOB_TEXT)

    hard_requirements = requirements["hard_requirements"]
    assert "C# / .NET 5+" in hard_requirements
    assert "Angular 16+" in hard_requirements
    assert "TypeScript" in hard_requirements
    assert "SQL Server / relational database" in hard_requirements
    assert "Git / Azure DevOps / CI/CD" in hard_requirements
    assert "AWS serverless" in hard_requirements
    assert "Object-oriented design patterns" in hard_requirements
    assert "Domain Driven Design" in hard_requirements
    assert "Service Oriented Architecture" in hard_requirements
    assert "Unit testing" in hard_requirements
    assert "Test Driven Development" in hard_requirements
    assert any("4+ years" in item for item in requirements["experience_requirements"])


def test_extract_job_requirements_detects_ai_automation_requirements() -> None:
    requirements = extract_job_requirements(ARRIVIA_AI_JOB_TEXT)

    hard_requirements = requirements["hard_requirements"]
    assert "AI agent / agentic workflows" in hard_requirements
    assert "LLM / large language model workflows" in hard_requirements
    assert "Prompt engineering" in hard_requirements
    assert "Python scripting/development" in hard_requirements
    assert "SQL / data workflows" in hard_requirements
    assert "API integration" in hard_requirements
    assert "Automation workflows" in hard_requirements
    assert "Object-oriented design patterns" in hard_requirements
    assert "C# / .NET 5+" not in hard_requirements
    assert "Angular 16+" not in hard_requirements


def test_score_explanation_for_ai_role_separates_overlap_and_verification() -> None:
    job = {
        "title": "AI Agent Builder",
        "company": "Arrivia, Inc.",
        "location": "Austin, TX",
        "work_mode": "Remote",
        "raw_text": ARRIVIA_AI_JOB_TEXT,
    }

    score_details = score_job(job)
    explanation = score_details["explanation"]
    explanation_text = str(explanation)

    assert "python" in score_details["matched_keywords"]
    assert "sql" in score_details["matched_keywords"]
    assert "apis" in score_details["matched_keywords"]
    assert "automation" in score_details["matched_keywords"]
    assert "data" in score_details["matched_keywords"]
    assert "AI/automation overlap to support with evidence" in explanation_text
    assert "Role-specific hard requirements to verify" in explanation_text
    assert "AI agent / agentic workflows" in explanation_text
    assert "For AI/automation roles" in explanation_text
    assert "C# / .NET" not in explanation_text
    assert "Angular" not in explanation_text


def test_score_explanation_marks_many_hard_requirements_as_stretch() -> None:
    job = {
        "title": "Full-Stack Developer",
        "company": "FEI Systems",
        "location": "Remote",
        "work_mode": "Remote",
        "raw_text": FEI_JOB_TEXT,
    }

    score_details = score_job(job)
    explanation = score_details["explanation"]

    assert "stretch role" in explanation["fit_summary"]
    assert any("C# / .NET" in item for item in explanation["gaps"])
    assert any("Experience requirements to verify" in item for item in explanation["gaps"])
