import json
from pathlib import Path

from application_packet import generate_application_packet
from application_packet_writer import save_application_packet
from job_parser import parse_job_text
from job_scorer import score_job


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
PROFILE_TEXT = (
    FIXTURE_ROOT / "profiles" / "test_profile" / "resume_base.md"
).read_text(encoding="utf-8")


def _run_packet_flow(
    fixture_name: str,
    tmp_path: Path,
    evidence_answers: dict[str, dict[str, str]] | None = None,
) -> tuple[dict[str, object], dict[str, object], str, str, dict[str, object]]:
    job_text = (FIXTURE_ROOT / "jobs" / fixture_name).read_text(encoding="utf-8")
    job = parse_job_text(job_text)
    score_result = score_job(job)
    packet = generate_application_packet(
        score_result,
        PROFILE_TEXT,
        evidence_answers=evidence_answers,
    )
    result = save_application_packet(packet, score_result, tmp_path)
    notes = result["output_paths"]["resume_tailoring_notes"].read_text(encoding="utf-8")
    tailored_resume = result["output_paths"]["tailored_resume"].read_text(encoding="utf-8")
    payload = json.loads(result["output_paths"]["packet_json"].read_text(encoding="utf-8"))
    return job, score_result, notes, tailored_resume, payload


def test_arrivia_ai_agent_packet_flow_smoke(tmp_path: Path) -> None:
    job, score_result, notes, tailored_resume, payload = _run_packet_flow(
        "arrivia_ai_agent_builder.txt",
        tmp_path,
        evidence_answers={
            "Python scripting/development": {"status": "Strong evidence", "notes": "Python tools."},
            "API integration": {"status": "Some evidence", "notes": "REST API project."},
            "SQL / data workflows": {"status": "Some evidence", "notes": "SQLite reports."},
            "Automation workflows": {"status": "Some evidence", "notes": "Automation scripts."},
            "AI agent / agentic workflows": {"status": "Some evidence", "notes": "Assistant tooling project."},
            "LLM / large language model workflows": {"status": "Not sure", "notes": ""},
            "Prompt engineering": {"status": "Some evidence", "notes": "Structured prompts."},
            "Agent-building tools or LLM platforms": {"status": "Not sure", "notes": ""},
            "Object-oriented design patterns": {"status": "Not sure", "notes": ""},
        },
    )
    hard_requirements = score_result["job_requirements"]["hard_requirements"]
    matched_keywords = {keyword.lower() for keyword in score_result["matched_keywords"]}
    packet_text = str(payload)

    assert job["title"] == "AI Agent Builder"
    assert job["company"] == "Arrivia, Inc."
    assert job["work_mode"] == "Remote"
    assert {"python", "sql", "apis", "automation", "data", "remote"}.issubset(matched_keywords)
    assert "AI agent / agentic workflows" in hard_requirements
    assert "LLM / large language model workflows" in hard_requirements
    assert "Prompt engineering" in hard_requirements
    assert "Agent-building tools or LLM platforms" in hard_requirements
    assert "Python scripting/development" in hard_requirements
    assert "SQL / data workflows" in hard_requirements
    assert "API integration" in hard_requirements
    assert "Automation workflows" in hard_requirements
    assert "Object-oriented design patterns" in hard_requirements
    assert "AI agent or automation workflow experience" in notes
    assert "LLM or large language model workflow experience" in notes
    assert "Prompt engineering or prompting experience" in notes
    assert "API integration experience" in notes
    assert "Python scripting/development" in notes
    assert "SQL/data workflow experience" in notes
    assert "Tailored Resume Draft" in tailored_resume
    assert "Python scripting/development" in tailored_resume
    assert "API integration experience" in tailored_resume
    assert "Missing Proof To Resolve" in tailored_resume
    assert ".NET/C#" not in packet_text
    assert "Angular/TypeScript" not in packet_text
    assert "comparable full-stack development work" not in packet_text
    assert "raw_text" not in packet_text


def test_fei_full_stack_packet_flow_smoke(tmp_path: Path) -> None:
    job, score_result, notes, tailored_resume, payload = _run_packet_flow(
        "fei_full_stack_developer.txt",
        tmp_path,
        evidence_answers={
            "C# / .NET 5+": {"status": "No evidence", "notes": ""},
            "Angular 16+": {"status": "No evidence", "notes": ""},
            "TypeScript": {"status": "No evidence", "notes": ""},
            "AWS serverless": {"status": "No evidence", "notes": ""},
            "Domain Driven Design": {"status": "No evidence", "notes": ""},
            "Service Oriented Architecture": {"status": "No evidence", "notes": ""},
            "Unit testing": {"status": "Some evidence", "notes": "pytest tests."},
            "Test Driven Development": {"status": "Not sure", "notes": ""},
        },
    )
    hard_requirements = score_result["job_requirements"]["hard_requirements"]
    packet_text = str(payload)

    assert job["title"] == "Full-Stack Developer"
    assert job["company"] == "FEI Systems"
    assert "C# / .NET 5+" in hard_requirements
    assert "Angular 16+" in hard_requirements
    assert "TypeScript" in hard_requirements
    assert "AWS serverless" in hard_requirements
    assert "Domain Driven Design" in hard_requirements
    assert "Service Oriented Architecture" in hard_requirements
    assert "Unit testing" in hard_requirements
    assert "Test Driven Development" in hard_requirements
    assert "Stretch Role" in notes
    assert "Apply Only If" in notes
    assert "Consider Skipping Or Deprioritizing If" in notes
    assert "Tailored Resume Draft" in tailored_resume
    assert "Missing Proof To Resolve" in tailored_resume
    assert "Connected C# / .NET" not in tailored_resume
    assert "Connected Angular" not in tailored_resume
    assert "raw_text" not in packet_text
