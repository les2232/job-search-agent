from application_packet import REVIEW_WARNING, generate_application_packet
from job_scorer import extract_job_requirements


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

PROOF_LIBRARY_PROFILE_TEXT = """
Profile includes Python scripts, SQL reports, API experiments, automation projects,
documentation, data troubleshooting, and IT support.

## Project Evidence / Proof Library

### Job Search Automation Tool

**Tools / Skills:** Python, Streamlit, Markdown, JSON, CSV, pytest, Git/GitHub, local-first automation

* Built a local-first Python tool that parses job posting text, scores role fit with configurable rules, tracks opportunities, and generates job-specific application materials.
* Created CLI and Streamlit workflows for scoring jobs, reviewing a tracker, and producing tailored resume/cover-letter packet drafts while keeping sensitive resume and job-search data local.

### IT Support Assistant

**Tools / Skills:** Python, Flask, SQLite, retrieval logic, local knowledge base, OpenAI API, JSON-style responses, evaluation scripts, technical documentation

* Developed a Flask-based internal IT support assistant that routes user questions to approved local knowledge base content and produces guided troubleshooting responses.
* Implemented Python routing/retrieval logic, response profiles, optional OpenAI API support, SQLite request/feedback logging, and evaluation scripts.

### TradeOS / Dashboard Project

**Tools / Skills:** Python, Streamlit, Pandas, SQLite/event logging, YAML configuration, API workflows, Git/GitHub, testing, dashboard design

* Built Python-based trading research and dashboard tooling with Streamlit views, SQLite/event logging, YAML configuration, Pandas data workflows, and structured reporting.
* Worked with broker/data API workflow concepts through Alpaca-related project tooling, emphasizing paper/simulated trading and operator visibility.
"""


def _score_result(
    score: int,
    recommendation: str,
    title: str = "Junior Python Support Analyst",
    company: str = "Example Studio",
    location: str = "Remote",
) -> dict[str, object]:
    return {
        "job_metadata": {
            "title": title,
            "company": company,
            "location": location,
            "work_mode": "Remote" if location != "Unknown" else "Unknown",
        },
        "score": score,
        "recommendation": recommendation,
        "matched_keywords": ["python", "documentation", "troubleshooting"],
        "missing_keywords": ["sql", "linux"],
        "concerns": [],
        "explanation": {
            "fit_summary": "Example explanation.",
            "strengths": ["Matched fit keywords: python, documentation"],
            "gaps": ["Potential gaps to review: sql, linux."],
            "concerns": ["No concern keywords or metadata issues were found."],
            "tailoring_suggestions": ["Emphasize verified experience."],
        },
    }


def _fei_score_result() -> dict[str, object]:
    return {
        "job_metadata": {
            "title": "Full-Stack Developer Who Shares Our Commitment",
            "company": "FEI Systems",
            "location": "Remote",
            "work_mode": "Remote",
        },
        "score": 65,
        "recommendation": "Maybe",
        "matched_keywords": ["sql", "git", "remote"],
        "missing_keywords": [
            "python",
            "api",
            "apis",
            "automation",
            "dashboard",
            "dashboards",
            "data",
            "linux",
        ],
        "concerns": [],
        "explanation": {
            "fit_summary": "Possible fit with gaps to review.",
            "strengths": ["Matched fit keywords: sql, git, remote"],
            "gaps": ["Potential gaps to review: python, api, linux."],
            "concerns": ["No concern keywords or metadata issues were found."],
            "tailoring_suggestions": ["Review gaps before applying."],
        },
        "job_requirements": extract_job_requirements(FEI_JOB_TEXT),
        "raw_text": FEI_JOB_TEXT,
    }


def _arrivia_score_result() -> dict[str, object]:
    return {
        "job_metadata": {
            "title": "AI Agent Builder",
            "company": "Arrivia, Inc.",
            "location": "Austin, TX",
            "work_mode": "Remote",
        },
        "score": 80,
        "recommendation": "Apply",
        "matched_keywords": ["python", "sql", "apis", "automation", "data", "remote"],
        "missing_keywords": ["dashboard", "linux"],
        "concerns": [],
        "explanation": {
            "fit_summary": "Strong overlap with AI/automation requirements to verify.",
            "strengths": ["Matched fit keywords: python, sql, apis, automation, data, remote"],
            "gaps": ["Role-specific hard requirements to verify."],
            "concerns": ["No concern keywords or metadata issues were found."],
            "tailoring_suggestions": ["Review AI/automation evidence before applying."],
        },
        "job_requirements": extract_job_requirements(ARRIVIA_AI_JOB_TEXT),
        "raw_text": ARRIVIA_AI_JOB_TEXT,
    }


def test_generate_application_packet_high_score() -> None:
    packet = generate_application_packet(
        _score_result(85, "Apply"),
        "Fake profile with IT support, Python, Flask, and documentation projects.",
    )

    assert "strong target" in packet["positioning_summary"]
    assert packet["apply_recommendation"].startswith("Apply")
    assert any("Python" in item for item in packet["keywords_to_include_honestly"])
    assert len(packet["resume_bullet_suggestions"]) >= 3


def test_generate_application_packet_medium_score() -> None:
    packet = generate_application_packet(_score_result(65, "Maybe"))

    assert packet["apply_recommendation"].startswith("Maybe")
    assert "honestly address" in packet["apply_recommendation"]
    assert "sql" in packet["keywords_to_avoid_or_verify"]


def test_generate_application_packet_low_score() -> None:
    packet = generate_application_packet(_score_result(45, "Skip"))

    assert "lower priority" in packet["positioning_summary"]
    assert packet["apply_recommendation"].startswith("Lower priority")


def test_generate_application_packet_uses_fallback_wording_for_unknown_metadata() -> None:
    packet = generate_application_packet(
        _score_result(
            60,
            "Maybe",
            title="Unknown",
            company="Unknown",
            location="Unknown",
        )
    )

    assert "this role" in packet["positioning_summary"]
    assert "the organization" in packet["positioning_summary"]
    assert "Unknown" not in packet["cover_letter_draft"]
    assert "Unknown" not in packet["recruiter_message"]


def test_generate_application_packet_does_not_include_raw_job_description() -> None:
    score_result = _score_result(85, "Apply")
    score_result["raw_text"] = "Python role with private details " * 50

    packet_text = str(generate_application_packet(score_result))

    assert "private details" not in packet_text
    assert str(score_result["raw_text"]) not in packet_text


def test_generate_application_packet_does_not_invent_metrics_or_certifications() -> None:
    packet_text = str(generate_application_packet(_score_result(85, "Apply")))

    assert "%" not in packet_text
    assert "Certified" not in packet_text
    assert "certified" not in packet_text
    assert "Led a team" not in packet_text
    assert "Expert in" not in packet_text


def test_generate_application_packet_bullets_are_editable_suggestions() -> None:
    packet = generate_application_packet(_score_result(85, "Apply"))

    bullets = packet["resume_bullet_suggestions"]

    assert len(bullets) >= 3
    assert all("Use only if true:" in str(bullet) or str(bullet).startswith("Do not present") for bullet in bullets)
    assert REVIEW_WARNING in packet["risk_notes"]


def test_cover_letter_draft_is_employer_facing_without_internal_warnings() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        (
            "Local IT support, user communication, troubleshooting, documentation, "
            "and classroom AV troubleshooting."
        ),
    )
    cover_letter = packet["cover_letter_draft"]

    assert "FEI Systems" in cover_letter
    assert "Full-Stack Developer" in cover_letter
    assert "Full-Stack Developer Who Shares Our Commitment" not in cover_letter
    assert "Draft only" not in cover_letter
    assert "Review carefully" not in cover_letter
    assert "verify" not in cover_letter.lower()
    assert "claims you cannot" not in cover_letter.lower()
    assert "tailor my resume" not in cover_letter.lower()
    assert "appears relevant" not in cover_letter.lower()
    assert "posting appears" not in cover_letter.lower()
    assert "Remote / Remote" not in cover_letter
    assert "sql, git, and remote" not in cover_letter.lower()


def test_maybe_cover_letter_is_polished_but_cautious() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, and documentation.",
    )
    cover_letter = packet["cover_letter_draft"]

    assert "I am interested in learning more" in cover_letter
    assert "where my background could be most useful" in cover_letter
    assert "Maybe" not in cover_letter


def test_cover_letter_does_not_claim_missing_keywords_as_experience() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, and documentation.",
    )
    cover_letter = packet["cover_letter_draft"].lower()

    for missing_keyword in [
        "python",
        "api",
        "automation",
        "dashboard",
        "linux",
        "c#",
        ".net",
        "angular",
        "aws",
        "domain driven",
        "test driven",
    ]:
        assert missing_keyword not in cover_letter


def test_safety_reminders_stay_outside_cover_letter() -> None:
    packet = generate_application_packet(_fei_score_result())

    assert REVIEW_WARNING in packet["risk_notes"]
    assert any("only where your resume/profile supports them" in item for item in packet["application_checklist"])
    assert REVIEW_WARNING not in packet["cover_letter_draft"]


def test_cover_letter_includes_company_mission_reason_when_available() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, and documentation.",
    )
    cover_letter = packet["cover_letter_draft"]

    assert "health and human services" in cover_letter
    assert "support people who depend on those services" in cover_letter
    assert "database-backed systems" in cover_letter
    assert "version control" in cover_letter
    assert "remote collaboration" in cover_letter


def test_packet_highlights_fei_hard_requirements_to_verify() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, documentation, git, and SQL.",
    )
    focus_text = " ".join(packet["resume_focus_areas"])
    risk_text = " ".join(packet["risk_notes"])

    assert "Strong / supported overlap" in focus_text
    assert "Git/version control" in focus_text
    assert "SQL/database work" in focus_text
    assert "Major requirements to verify" in focus_text
    assert "C# / .NET 5+ professional experience" in focus_text
    assert "Angular 16+ and TypeScript" in focus_text
    assert "Required years of full-stack software development experience" in focus_text
    assert "AWS serverless" in risk_text
    assert "Domain Driven Design and Service Oriented Architecture" in risk_text
    assert "Unit testing and Test Driven Development" in risk_text


def test_fei_resume_strategy_sections_are_scannable_and_bulleted() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        (
            "Local IT support, user communication, troubleshooting, documentation, "
            "classroom AV troubleshooting, git, and SQL."
        ),
    )
    strategy = packet["resume_strategy_sections"]

    assert strategy["fit_verdict"] == "Stretch Role"
    assert "Full-Stack Developer at FEI Systems" in strategy["fit_summary"]
    assert "Full-Stack Developer Who Shares Our Commitment" not in strategy["fit_summary"]
    assert "Git/version control, if supported by coursework" in " ".join(strategy["supported_overlap"])
    assert "SQL/database work, if supported by database queries" in " ".join(strategy["supported_overlap"])
    assert "C# / .NET 5+ professional experience" in strategy["major_requirements_to_verify"]
    assert "Angular 16+ and TypeScript" in strategy["major_requirements_to_verify"]
    assert "AWS serverless or similar cloud services" in strategy["major_requirements_to_verify"]
    assert "Domain Driven Design and Service Oriented Architecture" in strategy["major_requirements_to_verify"]
    assert "Unit testing and Test Driven Development" in strategy["major_requirements_to_verify"]
    assert "Required years of full-stack software development experience" in strategy["major_requirements_to_verify"]
    assert any("Do not present support, classroom, or AV troubleshooting" in item for item in strategy["transferable_support_evidence"])
    assert len(strategy["apply_only_if"]) >= 4
    assert len(strategy["consider_skipping_if"]) >= 3


def test_fei_keywords_to_include_are_human_readable_themes() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        (
            "Local IT support, user communication, troubleshooting, documentation, "
            "classroom AV troubleshooting, git, and SQL."
        ),
    )
    keyword_text = " ".join(packet["keywords_to_include_honestly"])

    assert "SQL / database-backed troubleshooting, only if supported." in packet["keywords_to_include_honestly"]
    assert "Git / version control, only if supported." in packet["keywords_to_include_honestly"]
    assert "Remote collaboration." in packet["keywords_to_include_honestly"]
    assert "Technical documentation." in packet["keywords_to_include_honestly"]
    assert "User-facing troubleshooting." in packet["keywords_to_include_honestly"]
    assert "Clear communication and follow-through." in packet["keywords_to_include_honestly"]
    assert keyword_text != "sql git remote"


def test_packet_does_not_list_unrelated_config_keywords_as_fei_gaps() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, documentation, git, and SQL.",
    )
    gap_text = " ".join(packet["keywords_to_avoid_or_verify"]).lower()

    assert "python" not in gap_text
    assert "dashboard" not in gap_text
    assert "linux" not in gap_text


def test_packet_marks_fei_role_as_stretch_when_hard_requirements_are_unsupported() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, user communication, troubleshooting, documentation, git, and SQL.",
    )
    packet_text = " ".join(packet["resume_focus_areas"] + packet["risk_notes"])

    assert "Fit Verdict: Stretch Role" in packet["positioning_summary"]
    assert "Full-Stack Developer Who Shares Our Commitment" not in packet["positioning_summary"]
    assert "likely a stretch" in packet["positioning_summary"]
    assert packet_text.count("likely a stretch") == 0
    assert "C# / .NET" in packet_text
    assert "Angular/TypeScript" in packet_text
    assert "cloud/serverless" in packet_text
    assert "testing" in packet_text
    assert "architecture" in packet_text


def test_fei_strategy_notes_include_apply_skip_guidance_and_translated_support() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        (
            "Local IT support, user communication, troubleshooting, documentation, "
            "classroom AV troubleshooting, git, and SQL."
        ),
    )
    focus_text = " ".join(packet["resume_focus_areas"])

    assert "Apply only if:" in focus_text
    assert "Consider skipping or deprioritizing if:" in focus_text
    assert "user-facing technical troubleshooting" in focus_text
    assert "Do not present it as software development experience" in focus_text
    assert "classroom/AV troubleshooting" not in focus_text


def test_fei_resume_bullets_are_conditional_and_evidence_based() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, documentation, troubleshooting, git, and SQL.",
    )
    bullets = packet["resume_bullet_suggestions"]
    bullet_text = " ".join(bullets)

    assert all("Use only if true:" in bullet or bullet.startswith("Do not present") for bullet in bullets)
    assert "Used Git/version control" in bullet_text
    assert "Worked with SQL" in bullet_text
    assert "Documented technical workflows" in bullet_text
    assert "Troubleshot technical systems used by real users" in bullet_text
    assert "Tailored documentation or support workflows around" not in bullet_text


def test_fei_risk_notes_are_concise_and_role_specific() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, documentation, troubleshooting, git, and SQL.",
    )
    risk_text = " ".join(packet["risk_notes"])

    assert REVIEW_WARNING in packet["risk_notes"]
    assert "Major role requirements to verify before applying" in risk_text
    assert "Stretch-role risk" in risk_text
    assert risk_text.count("This role is likely a stretch") == 0
    assert "python" not in risk_text.lower()
    assert "dashboard" not in risk_text.lower()
    assert "linux" not in risk_text.lower()


def test_ai_agent_packet_uses_ai_automation_strategy_without_full_stack_leakage() -> None:
    packet = generate_application_packet(
        _arrivia_score_result(),
        (
            "Profile includes Python scripts, SQL reports, API experiments, "
            "automation projects, documentation, data troubleshooting, and IT support."
        ),
    )
    strategy = packet["resume_strategy_sections"]
    strategy_text = str(strategy)
    risk_text = " ".join(packet["risk_notes"])

    assert strategy["fit_verdict"] == "Strong Target"
    assert "Python, if supported" in strategy_text
    assert "APIs / integrations" in strategy_text
    assert "Automation or workflow improvement" in strategy_text
    assert "AI agent or automation workflow experience" in strategy_text
    assert "LLM or large language model workflow experience" in strategy_text
    assert "Prompt engineering or prompting experience" in strategy_text
    assert "Object-oriented design patterns" in strategy_text
    assert "production AI engineering experience" in strategy_text
    assert "AI agent or automation workflow experience" in risk_text
    assert ".NET/C#" not in strategy_text
    assert "Angular/TypeScript" not in strategy_text
    assert "comparable full-stack development work" not in strategy_text
    assert "dashboard" not in risk_text.lower()
    assert "linux" not in risk_text.lower()


def test_ai_agent_cover_letter_mentions_automation_without_false_ai_claims() -> None:
    packet = generate_application_packet(
        _arrivia_score_result(),
        (
            "Profile includes Python scripts, SQL reports, API experiments, "
            "automation projects, documentation, data troubleshooting, and IT support."
        ),
    )
    cover_letter = packet["cover_letter_draft"]
    cover_letter_lower = cover_letter.lower()

    assert "AI Agent Builder" in cover_letter
    assert "Arrivia, Inc." in cover_letter
    assert "AI and automation workflows" in cover_letter
    assert "API integrations" in cover_letter
    assert "automation and workflow improvement" in cover_letter
    assert "data-backed problem solving" in cover_letter
    assert "production ai agent" not in cover_letter_lower
    assert "llm framework expertise" not in cover_letter_lower
    assert "professional ai engineering experience" not in cover_letter_lower
    assert "Arrivia, Inc.." not in cover_letter
    assert ".net" not in cover_letter_lower
    assert "angular" not in cover_letter_lower


def test_evidence_answers_drive_decision_summary_and_missing_proof() -> None:
    packet = generate_application_packet(
        _arrivia_score_result(),
        (
            "Profile includes Python scripts, SQL reports, API experiments, "
            "automation projects, documentation, data troubleshooting, and IT support."
        ),
        evidence_answers={
            "Python scripting/development": {
                "status": "Strong evidence",
                "notes": "Python scripts and local automation tools.",
            },
            "API integration": {
                "status": "Some evidence",
                "notes": "REST API project and JSON integrations.",
            },
            "SQL / data workflows": {
                "status": "Some evidence",
                "notes": "SQLite reports and data troubleshooting.",
            },
            "LLM / large language model workflows": {
                "status": "No evidence",
                "notes": "",
            },
        },
    )

    decision = packet["decision_summary"]
    evidence = packet["evidence_summary"]
    tailored_resume = packet["tailored_resume_draft"]

    assert decision["decision"] in {"Apply Carefully", "Deprioritize"}
    assert any(item["requirement"] == "Python scripting/development" for item in evidence["supported_evidence"])
    assert any(item["requirement"] == "API integration experience" for item in evidence["partial_evidence"])
    assert any(item["requirement"] == "LLM or large language model workflow experience" for item in evidence["missing_proof"])
    assert any("LLM" in action for action in packet["missing_proof_actions"])
    assert "Tailored Resume Draft" in tailored_resume
    assert "Python scripting/development" in tailored_resume
    assert "API integration experience" in tailored_resume
    assert "LLM or large language model workflow experience" in tailored_resume


def test_tailored_resume_does_not_claim_unsupported_fei_requirements() -> None:
    packet = generate_application_packet(
        _fei_score_result(),
        "Local IT support, documentation, troubleshooting, git, SQL, and pytest.",
        evidence_answers={
            "C# / .NET 5+": {"status": "No evidence", "notes": ""},
            "Angular 16+": {"status": "No evidence", "notes": ""},
            "AWS serverless": {"status": "No evidence", "notes": ""},
            "Unit testing": {"status": "Some evidence", "notes": "pytest tests in Python projects."},
        },
    )
    tailored_resume = packet["tailored_resume_draft"]

    assert "Tailored Resume Draft" in tailored_resume
    assert "C# / .NET 5+ professional experience" in tailored_resume
    assert "Angular 16+ and TypeScript" in tailored_resume
    assert "Connected C# / .NET" not in tailored_resume
    assert "Connected Angular" not in tailored_resume
    assert "pytest tests in Python projects" in tailored_resume


def test_tailored_resume_separates_resume_draft_from_internal_review_notes() -> None:
    packet = generate_application_packet(
        _arrivia_score_result(),
        (
            "Profile includes Python scripts, SQL reports, REST APIs, OpenAI API, "
            "prompt engineering, workflow automation, documentation, and IT support."
        ),
        evidence_answers={
            "Python scripting/development": {
                "status": "Strong evidence",
                "notes": (
                    "Auto-suggested from profile: Profile mentions Python scripts "
                    "and local automation tools. Verify exact examples before using."
                ),
            },
            "API integration": {
                "status": "Some evidence",
                "notes": (
                    "Auto-suggested from profile: Profile mentions REST APIs/JSON. "
                    "Confirm concrete examples."
                ),
            },
            "Prompt engineering": {
                "status": "Some evidence",
                "notes": (
                    "Auto-suggested from profile: Profile mentions prompt engineering. "
                    "Avoid overstating production experience."
                ),
            },
        },
    )
    tailored_resume = packet["tailored_resume_draft"]
    resume_section = tailored_resume.split("## Internal Review Notes", 1)[0]
    internal_section = tailored_resume.split("## Internal Review Notes", 1)[1]

    assert "## Resume Summary Draft" in tailored_resume
    assert "## Resume Bullet Candidates" in tailored_resume
    assert "## Internal Review Notes" in tailored_resume
    assert "### Needs Verification" in tailored_resume
    assert "### Skills To Avoid Unless Proven" in tailored_resume
    assert "### Missing Proof Next Actions" in tailored_resume
    assert "Auto-suggested from profile" not in tailored_resume
    assert "profile appears to mention" not in tailored_resume
    assert "Verify the exact claim before using" not in tailored_resume
    assert "Review and, if true, connect" not in tailored_resume
    assert "Connected Python scripting/development to verified evidence" not in tailored_resume
    assert "Used AI-assisted tooling or prompt-driven workflows" in resume_section
    assert "API integration experience: partial evidence" in internal_section
    assert "Confirm every claim is true." in tailored_resume


def test_tailored_resume_includes_relevant_project_evidence_blocks() -> None:
    packet = generate_application_packet(
        _arrivia_score_result(),
        PROOF_LIBRARY_PROFILE_TEXT,
        evidence_answers={
            "Python scripting/development": {"status": "Strong evidence", "notes": "Python projects."},
            "API integration": {"status": "Some evidence", "notes": "API projects."},
            "SQL / data workflows": {"status": "Some evidence", "notes": "SQLite reports."},
            "Automation workflows": {"status": "Some evidence", "notes": "Automation workflows."},
            "AI agent / agentic workflows": {"status": "Some evidence", "notes": "Assistant tooling."},
            "Prompt engineering": {"status": "Some evidence", "notes": "Prompt workflows."},
        },
    )
    tailored_resume = packet["tailored_resume_draft"]

    assert "## Project Evidence To Use" in tailored_resume
    assert "Job Search Automation Tool - supports" in tailored_resume
    assert "IT Support Assistant - supports" in tailored_resume
    assert "TradeOS / Dashboard Project - supports" in tailored_resume
    assert "Built a local-first Python and Streamlit application" in tailored_resume
    assert "Developed a Flask-based IT support assistant" in tailored_resume
    assert "Built Streamlit dashboard/reporting tools" in tailored_resume
    assert "Production AI engineering" not in tailored_resume.split("## Internal Review Notes", 1)[0]
