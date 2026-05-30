"""Run end-to-end packet smoke checks using committed fixtures and temp output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from application_packet import generate_application_packet
from application_packet_writer import save_application_packet
from job_parser import parse_job_text
from job_scorer import score_job


FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures"
JOB_FIXTURES = {
    "arrivia_ai_agent": FIXTURE_ROOT / "jobs" / "arrivia_ai_agent_builder.txt",
    "fei_full_stack": FIXTURE_ROOT / "jobs" / "fei_full_stack_developer.txt",
}
PROFILE_FIXTURE = FIXTURE_ROOT / "profiles" / "test_profile" / "resume_base.md"


class SmokeFailure(AssertionError):
    """Raised when a smoke check finds a broken packet flow."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test packet generation flow.")
    parser.add_argument(
        "--fixture",
        choices=["all", *JOB_FIXTURES],
        default="all",
        help="Fixture to run. Defaults to all.",
    )
    args = parser.parse_args(argv)

    fixture_names = list(JOB_FIXTURES) if args.fixture == "all" else [args.fixture]
    try:
        for fixture_name in fixture_names:
            _run_fixture(fixture_name)
    except SmokeFailure as error:
        print(f"FAIL {error}")
        return 1

    print("All smoke checks passed.")
    return 0


def _run_fixture(fixture_name: str) -> None:
    fixture_path = JOB_FIXTURES[fixture_name]
    job_text = fixture_path.read_text(encoding="utf-8")
    profile_text = PROFILE_FIXTURE.read_text(encoding="utf-8")
    job = parse_job_text(job_text)
    score_result = score_job(job)
    packet = generate_application_packet(score_result, profile_text)

    with TemporaryDirectory(prefix="packet-flow-smoke-") as temp_dir:
        result = save_application_packet(packet, score_result, Path(temp_dir))
        output_paths = result["output_paths"]
        notes = output_paths["resume_tailoring_notes"].read_text(encoding="utf-8")
        payload = json.loads(output_paths["packet_json"].read_text(encoding="utf-8"))

    if fixture_name == "arrivia_ai_agent":
        _assert_arrivia(job, score_result, notes, payload)
        print("PASS Arrivia AI Agent packet flow")
    elif fixture_name == "fei_full_stack":
        _assert_fei(job, score_result, notes, payload)
        print("PASS FEI Full-Stack stretch packet flow")
    else:
        raise SmokeFailure(f"Unknown fixture: {fixture_name}")


def _assert_arrivia(
    job: dict[str, object],
    score_result: dict[str, object],
    notes: str,
    payload: dict[str, object],
) -> None:
    hard_requirements = _hard_requirements(score_result)
    matched_keywords = {str(value).lower() for value in score_result["matched_keywords"]}
    packet_text = str(payload)

    _require(job["title"] == "AI Agent Builder", "Arrivia title did not parse.")
    _require(job["company"] == "Arrivia, Inc.", "Arrivia company did not parse.")
    _require(job["work_mode"] == "Remote", "Arrivia work mode did not parse as Remote.")
    for keyword in ["python", "sql", "apis", "automation", "data", "remote"]:
        _require(keyword in matched_keywords, f"Arrivia missing matched keyword: {keyword}")
    for requirement in [
        "AI agent / agentic workflows",
        "LLM / large language model workflows",
        "Prompt engineering",
        "Agent-building tools or LLM platforms",
        "Python scripting/development",
        "SQL / data workflows",
        "API integration",
        "Automation workflows",
        "Object-oriented design patterns",
    ]:
        _require(requirement in hard_requirements, f"Arrivia missing requirement: {requirement}")
    for expected_text in [
        "AI agent or automation workflow experience",
        "LLM or large language model workflow experience",
        "Prompt engineering or prompting experience",
        "API integration experience",
        "Python scripting/development",
        "SQL/data workflow experience",
        "Object-oriented design patterns",
    ]:
        _require(expected_text in notes, f"Arrivia notes missing: {expected_text}")
    for stale_text in [".NET/C#", "Angular/TypeScript", "comparable full-stack development work"]:
        _require(stale_text not in packet_text, f"Arrivia packet has stale text: {stale_text}")
    _require("raw_text" not in packet_text, "Arrivia packet JSON included raw_text.")


def _assert_fei(
    job: dict[str, object],
    score_result: dict[str, object],
    notes: str,
    payload: dict[str, object],
) -> None:
    hard_requirements = _hard_requirements(score_result)
    packet_text = str(payload)

    _require(job["title"] == "Full-Stack Developer", "FEI title did not parse.")
    _require(job["company"] == "FEI Systems", "FEI company did not parse.")
    for requirement in [
        "C# / .NET 5+",
        "Angular 16+",
        "TypeScript",
        "AWS serverless",
        "Domain Driven Design",
        "Service Oriented Architecture",
        "Unit testing",
        "Test Driven Development",
    ]:
        _require(requirement in hard_requirements, f"FEI missing requirement: {requirement}")
    _require("Stretch Role" in notes, "FEI packet did not mark stretch role.")
    _require("Apply Only If" in notes, "FEI packet missing apply guidance.")
    _require("Consider Skipping Or Deprioritizing If" in notes, "FEI packet missing skip guidance.")
    _require("raw_text" not in packet_text, "FEI packet JSON included raw_text.")


def _hard_requirements(score_result: dict[str, object]) -> list[str]:
    requirements = score_result.get("job_requirements")
    if not isinstance(requirements, dict):
        return []
    values = requirements.get("hard_requirements")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


if __name__ == "__main__":
    raise SystemExit(main())
