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


def _run_packet_flow(fixture_name: str, tmp_path: Path) -> tuple[dict[str, object], dict[str, object], str, dict[str, object]]:
    job_text = (FIXTURE_ROOT / "jobs" / fixture_name).read_text(encoding="utf-8")
    job = parse_job_text(job_text)
    score_result = score_job(job)
    packet = generate_application_packet(score_result, PROFILE_TEXT)
    result = save_application_packet(packet, score_result, tmp_path)
    notes = result["output_paths"]["resume_tailoring_notes"].read_text(encoding="utf-8")
    payload = json.loads(result["output_paths"]["packet_json"].read_text(encoding="utf-8"))
    return job, score_result, notes, payload


def test_arrivia_ai_agent_packet_flow_smoke(tmp_path: Path) -> None:
    job, score_result, notes, payload = _run_packet_flow(
        "arrivia_ai_agent_builder.txt",
        tmp_path,
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
    assert ".NET/C#" not in packet_text
    assert "Angular/TypeScript" not in packet_text
    assert "comparable full-stack development work" not in packet_text
    assert "raw_text" not in packet_text


def test_fei_full_stack_packet_flow_smoke(tmp_path: Path) -> None:
    job, score_result, notes, payload = _run_packet_flow(
        "fei_full_stack_developer.txt",
        tmp_path,
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
    assert "raw_text" not in packet_text
