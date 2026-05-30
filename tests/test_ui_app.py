from ui_app import (
    _find_duplicate_saved_packets,
    _recommendation_guidance,
    _saved_packet_table_row,
    _saved_packets_for_queue,
    _score_analysis_key,
)


def _score_result(
    recommendation: str = "Maybe",
    title: str = "Full-Stack Developer Who Shares Our Commitment",
    company: str = "FEI Systems",
    hard_requirements: list[str] | None = None,
) -> dict[str, object]:
    return {
        "job_metadata": {
            "title": title,
            "company": company,
        },
        "recommendation": recommendation,
        "job_requirements": {
            "hard_requirements": hard_requirements or [],
        },
        "explanation": {
            "fit_summary": "This appears to be a stretch role.",
        },
    }


def _saved_packet(
    title: str = "Full-Stack Developer",
    company: str = "FEI Systems",
    saved_date: str = "2026-05-30",
    folder_path: str = "applications/default/2026-05-30_fei_full-stack",
) -> dict[str, object]:
    return {
        "saved_date": saved_date,
        "title": title,
        "company": company,
        "score": 65,
        "recommendation": "Maybe",
        "status": "Interested",
        "next_action": "Review score and decide whether to tailor.",
        "next_action_date": None,
        "folder_path": folder_path,
    }


def test_recommendation_guidance_handles_apply_maybe_stretch_and_skip() -> None:
    apply_guidance = _recommendation_guidance(
        _score_result(recommendation="Apply", hard_requirements=[]),
    )
    maybe_guidance = _recommendation_guidance(
        {
            **_score_result(recommendation="Maybe", hard_requirements=[]),
            "explanation": {"fit_summary": "Relevant overlap with gaps."},
        },
    )
    stretch_guidance = _recommendation_guidance(_score_result(recommendation="Maybe"))
    skip_guidance = _recommendation_guidance(_score_result(recommendation="Skip"))

    assert apply_guidance["tone"] == "success"
    assert "worth turning into a packet" in apply_guidance["message"]
    assert maybe_guidance["tone"] == "info"
    assert "review the gaps" in maybe_guidance["message"]
    assert stretch_guidance["tone"] == "warning"
    assert "real evidence" in stretch_guidance["message"]
    assert skip_guidance["tone"] == "warning"
    assert "probably not worth a full packet" in skip_guidance["message"]


def test_duplicate_detection_matches_company_and_cleaned_title() -> None:
    duplicates = _find_duplicate_saved_packets(
        _score_result(),
        [
            _saved_packet(title="Full-Stack Developer"),
            _saved_packet(title="Python Analyst", company="Other Company"),
        ],
    )

    assert len(duplicates) == 1
    assert duplicates[0]["company"] == "FEI Systems"


def test_saved_packet_queue_shows_latest_version_by_default() -> None:
    packets = [
        _saved_packet(
            saved_date="2026-05-30",
            folder_path="applications/default/latest",
        ),
        _saved_packet(
            saved_date="2026-05-29",
            folder_path="applications/default/older",
        ),
        _saved_packet(
            title="Python Analyst",
            company="Example Studio",
            folder_path="applications/default/python",
        ),
    ]

    queue_packets = _saved_packets_for_queue(packets)
    all_versions = _saved_packets_for_queue(packets, include_duplicate_versions=True)

    assert len(queue_packets) == 2
    assert len(all_versions) == 3
    fei_packet = next(packet for packet in queue_packets if packet["company"] == "FEI Systems")
    assert fei_packet["duplicate_version_count"] == 2


def test_saved_packet_table_row_reads_like_application_queue() -> None:
    row = _saved_packet_table_row(
        {
            **_saved_packet(),
            "duplicate_version_count": 2,
        }
    )

    assert list(row) == [
        "Saved date",
        "Job",
        "Company",
        "Score",
        "Recommendation",
        "Status",
        "Next action",
        "Next action date",
    ]
    assert row["Job"] == "Full-Stack Developer (2 versions)"


def test_score_analysis_key_changes_when_hard_requirements_change() -> None:
    original = _score_result(
        title="AI Agent Builder",
        company="Arrivia, Inc.",
        hard_requirements=["Object-oriented design patterns"],
    )
    updated = _score_result(
        title="AI Agent Builder",
        company="Arrivia, Inc.",
        hard_requirements=[
            "AI agent / agentic workflows",
            "LLM / large language model workflows",
            "Prompt engineering",
            "Object-oriented design patterns",
        ],
    )

    assert _score_analysis_key(original) != _score_analysis_key(updated)
