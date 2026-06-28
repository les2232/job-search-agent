from ui_app import (
    app_header_html,
    build_browser_capture_bookmarklet,
    browser_capture_bookmarklet_link_markdown,
    browser_capture_chrome_edge_steps,
    browser_capture_firefox_steps,
    browser_capture_manual_steps,
    browser_capture_recommended_steps,
    browser_capture_safety_notes,
    browser_capture_setup_steps,
    browser_capture_usage_steps,
    choose_browser_capture_text,
    clean_captured_job_text,
    clean_job_posting_text,
    clean_imported_job_text,
    default_profile_index,
    detected_detail_chips,
    _evidence_suggestion_counts,
    _evidence_requirements,
    example_job_posting_text,
    extract_readable_html_text,
    extract_uploaded_job_text,
    _find_duplicate_saved_packets,
    html_list,
    extract_job_url,
    job_empty_state_text,
    job_text_from_upload_bytes,
    packet_next_actions,
    packet_validation_missing_optional_items,
    packet_validation_missing_required_items,
    packet_validation_required_text,
    packet_validation_status_text,
    saved_packet_zip_download_enabled,
    saved_packet_zip_filename,
    packet_summary_card_data,
    packet_summary_card_html,
    read_uploaded_job_file,
    _recommendation_guidance,
    _requirement_slug,
    _review_section_content,
    _saved_review_sections,
    saved_packet_folder_path,
    saved_packet_folder_note,
    draft_packet_folder_note,
    local_profile_setup_steps,
    packet_start_here_items,
    _saved_packet_table_row,
    _saved_packets_for_queue,
    _score_analysis_key,
    _suggest_evidence_answers,
    _suggest_evidence_for_requirement,
    summarize_job_input_quality,
    status_badge_html,
    step_card_html,
    top_packet_review_items,
    top_packet_supported_items,
    welcome_steps,
    workflow_strip_html,
)


PROFILE_TEXT = """
## Technical Skills
Python, Flask, Streamlit, SQL, SQLite, REST APIs, JSON, OpenAI API,
prompt engineering, workflow automation, dashboards, reports, pytest.

## Strongest Positioning
Engineer transitioning from IT with local tooling, automation projects,
assistant projects, data-backed troubleshooting, documentation, and support.

## Skills To Use Carefully
Only emphasize these when there is direct project evidence: cloud platforms,
Kubernetes, Docker, Angular, TypeScript-heavy frontend, .NET, C#,
production ML engineering, advanced DevOps.
"""


def test_welcome_steps_explain_local_reviewable_workflow() -> None:
    text = " ".join(welcome_steps())

    assert "Pick a candidate profile" in text
    assert "Paste, upload, or load a sample job posting" in text
    assert "deterministic fit" in text
    assert "reviewable packet" in text
    assert "Review every claim manually" in text
    assert "Everything stays local" in text


def test_header_highlights_first_action_and_privacy_boundary() -> None:
    header = app_header_html()

    assert "Job Packet Studio" in header
    assert "Paste a job posting, generate a local review packet, then decide manually." in header
    assert "Local-first" in header
    assert "no scraping" in header
    assert "external AI API calls" in header
    assert "auto-apply" in header


def test_workflow_strip_shows_three_visible_steps() -> None:
    strip = workflow_strip_html()

    assert "Choose profile" in strip
    assert "Paste or upload job" in strip
    assert "Generate packet" in strip
    assert "demo profile" in strip
    assert "job text you chose to provide" in strip
    assert "Review drafts" in strip


def test_local_profile_setup_steps_keep_private_data_ignored() -> None:
    steps = local_profile_setup_steps("candidate")
    text = " ".join(steps)

    assert "local_profiles/candidate/profile.json" in text
    assert "local_profiles/candidate/resume_base.md" in text
    assert "Do not commit local_profiles" in text
    assert "does not use ChatGPT memory" in text


def test_example_job_posting_text_is_generic_and_support_oriented() -> None:
    text = example_job_posting_text()

    assert "Example Organization" in text
    assert "2+ years of IT support" in text
    assert "Microsoft 365" in text
    assert "leslie" not in text.lower()
    assert "password" not in text.lower()


def test_status_badge_html_includes_accessible_text_and_state_class() -> None:
    ready = status_badge_html("looks-good", "Looks usable")
    weak = status_badge_html("needs-review", "Needs more text")

    assert "Looks usable" in ready
    assert "success" in ready
    assert "Needs more text" in weak
    assert "warning" in weak


def test_detected_detail_chips_skip_unknowns_and_escape_values() -> None:
    chips = detected_detail_chips(
        {
            "title": "AI Developer",
            "company": "Example <Studio>",
            "work_mode": "Remote",
            "location": "Unknown",
        },
        source_url="https://example.com/job",
    )
    text = " ".join(chips)

    assert "AI Developer" in text
    assert "Example &lt;Studio&gt;" in text
    assert "Remote" in text
    assert "https://example.com/job" in text
    assert "Location" not in text


def test_packet_summary_card_helpers_include_scan_targets(tmp_path) -> None:
    packet = {
        "decision_summary": {"next_action": "Verify evidence before applying."},
        "evidence_summary": {
            "supported_evidence": [{"requirement": "Python automation"}],
            "partial_evidence": [],
            "missing_proof": [{"requirement": "Production ML"}],
            "needs_verification": [],
        },
        "missing_proof_actions": ["Production ML: verify before claiming."],
    }
    data = packet_summary_card_data(
        {"title": "AI Developer", "company": "Example Studio"},
        {"score": 78, "recommendation": "Maybe"},
        packet,
        tmp_path,
        {"folder_path": "applications/default/example"},
    )
    html = packet_summary_card_html(data)

    assert data["supported"] == ["Python automation"]
    assert data["review"] == ["Production ML"]
    assert "AI Developer" in html
    assert "78/100" in html
    assert "Maybe" in html
    assert "Python automation" in html
    assert "Production ML" in html
    assert "Saved packet location" in html
    assert "applications/default/example" in html


def test_packet_summary_card_uses_draft_copy_before_save(tmp_path) -> None:
    data = packet_summary_card_data(
        {"title": "AI Developer", "company": "Example Studio"},
        {"score": 78, "recommendation": "Maybe"},
        {"decision_summary": {}, "evidence_summary": {}},
        tmp_path,
        None,
    )
    html = packet_summary_card_html(data)

    assert data["is_saved"] is False
    assert "Click Save Packet to write files under" in html
    assert "Saved packet location" not in html


def test_empty_state_and_step_card_text_are_plain_and_local() -> None:
    empty_text = job_empty_state_text()
    card = step_card_html("Step 2: Add job posting", "Paste locally.")

    assert "Paste the whole job page here" in empty_text
    assert ".html" in empty_text
    assert "Step 2: Add job posting" in card
    assert "Paste locally." in card


def test_html_list_escapes_items_and_handles_empty() -> None:
    assert "None." in html_list([])
    assert "&lt;verify&gt;" in html_list(["<verify>"])


def test_packet_start_here_items_summarize_supported_and_review_items() -> None:
    items = packet_start_here_items(
        {
            "decision_summary": {
                "decision": "Apply Carefully",
                "next_action": "Tailor carefully and verify unresolved requirements.",
            },
            "evidence_summary": {
                "supported_evidence": [
                    {"requirement": "2+ years IT support experience"},
                ],
                "partial_evidence": [
                    {"requirement": "API integration experience"},
                ],
                "missing_proof": [
                    {"requirement": "7+ years endpoint support experience"},
                ],
                "needs_verification": [
                    {"requirement": "Escalation experience"},
                ],
            },
        }
    )
    text = " ".join(items)

    assert "Decision: Apply Carefully." in items
    assert "Supported evidence: 2+ years IT support experience." in items
    assert "Partial evidence to strengthen: API integration experience." in items
    assert "Verify before claiming" in text
    assert "Save the packet only after checking that every claim is true." in items


def test_default_profile_index_prefers_one_local_profile() -> None:
    profiles = [
        {"profile_id": "default", "is_local": False},
        {"profile_id": "candidate", "is_local": True},
    ]

    assert default_profile_index(profiles) == 1


def test_default_profile_index_uses_demo_default_when_no_local_profile() -> None:
    profiles = [
        {"profile_id": "other", "is_local": False},
        {"profile_id": "default", "is_local": False},
    ]

    assert default_profile_index(profiles) == 1


def test_job_text_from_upload_bytes_accepts_txt_md_and_saved_html() -> None:
    assert job_text_from_upload_bytes(b"Title: Support Role", "job.txt") == "Title: Support Role"
    assert job_text_from_upload_bytes(b"# Role\r\n\r\nRemote", "job.md") == "# Role\nRemote"
    html_text = job_text_from_upload_bytes(
        b"<html><body><nav>Apply now</nav><h1>Support Analyst</h1><p>Requirements: SQL and documentation.</p></body></html>",
        "job.html",
    )

    assert "Support Analyst" in html_text
    assert "Requirements: SQL and documentation." in html_text
    assert "Apply now" not in html_text


def test_read_uploaded_job_file_rejects_unsupported_files() -> None:
    try:
        read_uploaded_job_file(b"%PDF", "job.pdf")
    except ValueError as error:
        assert ".txt, .md, or saved .html" in str(error)
    else:
        raise AssertionError("PDF upload should not be accepted by the simple intake helper")


def test_clean_job_posting_text_removes_common_page_noise_and_duplicates() -> None:
    messy_text = """
    Home
    Apply now
    Save job
    Job Title: IT Support Specialist
    Example Organization
    Remote


    We use cookies to improve your experience.
    Responsibilities:
    Responsibilities:
    Troubleshoot Microsoft 365 access issues for employees.
    Qualifications:
    - SQL
    - IT support
    Share job
    All rights reserved.
    """

    cleaned = clean_job_posting_text(messy_text)

    assert "Apply now" not in cleaned
    assert "Save job" not in cleaned
    assert "We use cookies" not in cleaned
    assert "Share job" not in cleaned
    assert cleaned.count("Responsibilities:") == 1
    assert "- SQL" in cleaned
    assert "- IT support" in cleaned
    assert "Troubleshoot Microsoft 365 access issues" in cleaned


def test_extract_job_url_detects_source_without_fetching() -> None:
    text = "Source: https://example.com/jobs/123?ref=abc. Paste follows."

    assert extract_job_url(text) == "https://example.com/jobs/123?ref=abc"


def test_summarize_job_input_quality_distinguishes_weak_and_useful_text() -> None:
    weak = summarize_job_input_quality("Apply now\nSave job\nRemote")
    useful = summarize_job_input_quality(
        """
        Job Title: IT Support Specialist
        Company: Example Organization
        Location: Remote
        Responsibilities:
        Troubleshoot Microsoft 365 access issues for employees.
        Document repeatable support fixes.
        Escalate complex endpoint problems.
        Qualifications:
        2+ years of IT support or help desk experience.
        Experience with account access and endpoint troubleshooting.
        Strong communication and careful documentation habits.
        Salary range: $55,000 - $65,000
        """
    )

    assert weak["status"] == "needs_more_text"
    assert "Needs more text" in str(weak["message"])
    assert useful["status"] == "looks_good"
    assert "Looks good" in str(useful["message"])


def test_compact_packet_helpers_pull_top_supported_review_and_actions() -> None:
    packet = {
        "decision_summary": {
            "next_action": "Tailor carefully and verify unresolved requirements.",
        },
        "evidence_summary": {
            "supported_evidence": [
                {"requirement": "2+ years IT support experience"},
                {"requirement": "Microsoft 365 support"},
            ],
            "partial_evidence": [
                {"requirement": "Endpoint troubleshooting"},
            ],
            "missing_proof": [
                {"requirement": "7+ years administration experience"},
            ],
            "needs_verification": [
                {"requirement": "Escalation ownership"},
            ],
        },
        "missing_proof_actions": [
            "7+ years administration experience: verify before claiming.",
        ],
    }

    assert top_packet_supported_items(packet) == [
        "2+ years IT support experience",
        "Microsoft 365 support",
        "Endpoint troubleshooting",
    ]
    assert top_packet_review_items(packet) == [
        "7+ years administration experience",
        "Escalation ownership",
    ]
    assert packet_next_actions(packet)[:2] == [
        "Tailor carefully and verify unresolved requirements.",
        "7+ years administration experience: verify before claiming.",
    ]


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


def test_saved_packet_folder_note_points_to_index() -> None:
    path = saved_packet_folder_path("applications/default/2026-06-13_example_role")
    note = saved_packet_folder_note("applications/default/2026-06-13_example_role")

    assert path == "applications/default/2026-06-13_example_role"
    assert "Saved packet folder: applications/default/2026-06-13_example_role." in note
    assert "Start with packet_index.md" in note
    assert "recommended review order" in note


def test_saved_packet_folder_note_handles_missing_path() -> None:
    path = saved_packet_folder_path("")
    note = saved_packet_folder_note("")

    assert path == "applications/<profile_id>/<saved-folder>"
    assert "applications/<profile_id>/<saved-folder>" in note
    assert "packet_index.md" in note


def test_draft_packet_folder_note_avoids_saved_language() -> None:
    note = draft_packet_folder_note("applications/default/2026-06-13_example_role")

    assert "Draft generated, not saved yet" in note
    assert "Click Save Packet to write files under:" in note
    assert "applications/default/2026-06-13_example_role" in note
    assert "Saved packet folder" not in note


def test_packet_validation_summary_reports_valid_required_files() -> None:
    validation_result = {
        "is_valid": True,
        "present_files": [
            "packet_index.md",
            "tailored_resume.md",
            "packet.json",
            "cover_letter_draft.md",
        ],
        "missing_required_files": [],
        "missing_optional_files": [],
    }

    assert packet_validation_status_text(validation_result) == "Packet validation: valid"
    assert packet_validation_required_text(validation_result) == (
        "Required files found: packet_index.md, tailored_resume.md, packet.json"
    )
    assert packet_validation_missing_required_items(validation_result) == []
    assert packet_validation_missing_optional_items(validation_result) == []


def test_packet_validation_summary_separates_missing_file_types() -> None:
    validation_result = {
        "is_valid": False,
        "present_files": ["packet.json"],
        "missing_required_files": ["packet_index.md", "tailored_resume.md"],
        "missing_optional_files": ["cover_letter_draft.md"],
    }

    assert (
        packet_validation_status_text(validation_result)
        == "Packet validation: needs attention"
    )
    assert packet_validation_required_text(validation_result) == (
        "Required files found: packet.json"
    )
    assert packet_validation_missing_required_items(validation_result) == [
        "packet_index.md",
        "tailored_resume.md",
    ]
    assert packet_validation_missing_optional_items(validation_result) == [
        "cover_letter_draft.md"
    ]


def test_packet_validation_summary_handles_nonexistent_folder_result() -> None:
    validation_result = {
        "is_valid": False,
        "present_files": [],
        "missing_required_files": [
            "packet_index.md",
            "tailored_resume.md",
            "packet.json",
        ],
        "missing_optional_files": [],
        "warnings": ["Packet folder does not exist: applications/missing"],
    }

    assert (
        packet_validation_status_text(validation_result)
        == "Packet validation: needs attention"
    )
    assert packet_validation_required_text(validation_result) == (
        "Required files found: none"
    )
    assert packet_validation_missing_required_items(validation_result) == [
        "packet_index.md",
        "tailored_resume.md",
        "packet.json",
    ]
    assert packet_validation_missing_optional_items(validation_result) == []


def test_saved_packet_zip_download_is_enabled_only_for_valid_packets() -> None:
    assert saved_packet_zip_download_enabled({"is_valid": True}) is True
    assert saved_packet_zip_download_enabled({"is_valid": False}) is False
    assert saved_packet_zip_download_enabled({}) is False


def test_saved_packet_zip_filename_uses_safe_packet_folder_name() -> None:
    assert (
        saved_packet_zip_filename(
            r"applications\default\2026-06-13 Example Role"
        )
        == "2026-06-13-Example-Role.zip"
    )
    assert saved_packet_zip_filename("") == "saved-folder.zip"


def test_review_section_content_prefers_saved_file_and_falls_back() -> None:
    sections = [
        {
            "key": "packet_index",
            "exists": True,
            "content": "# Application Packet Review Index\n\n- [Tailored resume draft](tailored_resume.md)",
        },
        {
            "key": "tailored_resume",
            "exists": True,
            "content": "# Tailored Resume Draft\n\nSaved file draft.",
        },
        {
            "key": "cover_letter_draft",
            "exists": False,
            "content": "# Missing",
        },
    ]

    assert _review_section_content(sections, "tailored_resume", "packet fallback") == (
        "# Tailored Resume Draft\n\nSaved file draft."
    )
    assert _review_section_content(sections, "packet_index", "") == (
        "# Application Packet Review Index\n\n- [Tailored resume draft](tailored_resume.md)"
    )
    assert _review_section_content(sections, "cover_letter_draft", "packet fallback") == (
        "packet fallback"
    )
    assert _review_section_content([], "tailored_resume", "packet fallback") == (
        "packet fallback"
    )
    assert _review_section_content([], "packet_index", "") == ""


def test_saved_review_sections_uses_loaded_sections_without_rereading() -> None:
    loaded_sections = [{"key": "tailored_resume", "exists": True, "content": "Loaded"}]

    assert _saved_review_sections({"review_sections": loaded_sections}) == loaded_sections


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


def test_evidence_requirement_helpers_are_stable() -> None:
    score_result = _score_result(
        hard_requirements=[
            "API integration",
            "LLM / large language model workflows",
        ],
    )
    score_result["job_requirements"]["experience_requirements"] = ["3+ years automation experience"]

    assert _requirement_slug("LLM / large language model workflows") == "llm-large-language-model-workflows"
    assert _evidence_requirements(score_result) == [
        "API integration",
        "LLM / large language model workflows",
        "3+ years automation experience",
    ]


def test_html_extraction_removes_scripts_and_keeps_visible_text() -> None:
    html = """
    <html>
      <head><style>.hidden { display: none; }</style><script>alert('x')</script></head>
      <body>
        <h1>AI Agent Builder</h1>
        <div>Company: Arrivia, Inc.</div>
        <p>Build Python automation workflows and API integrations.</p>
      </body>
    </html>
    """

    text = extract_readable_html_text(html)

    assert "AI Agent Builder" in text
    assert "Arrivia, Inc." in text
    assert "Python automation workflows" in text
    assert "alert" not in text
    assert "display: none" not in text


def test_uploaded_html_and_text_are_cleaned() -> None:
    html_text = extract_uploaded_job_text(
        b"<html><body><h1>Developer</h1><style>bad</style><p>Remote role</p></body></html>",
        "job.html",
    )
    plain_text = extract_uploaded_job_text(
        b"Title: Developer\r\n\r\n\r\nCompany: Example",
        "job.txt",
    )

    assert "Developer" in html_text
    assert "Remote role" in html_text
    assert "bad" not in html_text
    assert plain_text == "Title: Developer\nCompany: Example"


def test_clean_imported_job_text_collapses_whitespace() -> None:
    assert clean_imported_job_text("Line 1\r\n\r\n\r\n  Line   2  ") == "Line 1\nLine 2"


def test_browser_capture_prefers_selected_text_over_body_text() -> None:
    captured = choose_browser_capture_text(
        "Selected job description with Python and SQL.",
        "Whole page navigation noise and unrelated text.",
        title="Example Role",
        url="https://example.com/job",
    )

    assert "Selected job description" in captured
    assert "Whole page navigation noise" not in captured
    assert "Page Title: Example Role" in captured
    assert "Page URL: https://example.com/job" in captured


def test_browser_capture_falls_back_to_body_text_and_applies_limit() -> None:
    captured = choose_browser_capture_text(
        "",
        "abcdef",
        max_chars=3,
    )

    assert captured == "abc"


def test_clean_captured_job_text_enforces_size_limit() -> None:
    try:
        clean_captured_job_text("x" * 20, max_chars=10)
    except ValueError as error:
        assert "too large" in str(error)
    else:
        raise AssertionError("Oversized capture should fail")


def test_browser_capture_bookmarklet_is_local_and_selection_first() -> None:
    bookmarklet = build_browser_capture_bookmarklet(max_chars=50000)

    assert bookmarklet.startswith("javascript:")
    assert "window.getSelection" in bookmarklet
    assert "document.body.innerText" in bookmarklet
    assert "captured-job-posting.txt" in bookmarklet
    assert "localStorage" not in bookmarklet
    assert "cookie" not in bookmarklet.lower()


def test_browser_capture_instructions_explain_setup_and_daily_use() -> None:
    setup_text = " ".join(browser_capture_setup_steps())
    recommended_text = " ".join(browser_capture_recommended_steps())
    manual_text = " ".join(browser_capture_manual_steps())
    usage_text = " ".join(browser_capture_usage_steps())
    browser_help = " ".join(browser_capture_chrome_edge_steps() + browser_capture_firefox_steps())

    assert "Drag" in recommended_text
    assert "bookmarks bar" in recommended_text
    assert "Create a browser bookmark" in setup_text
    assert "URL or Location field" in manual_text
    assert "Do not paste the bookmarklet into the address bar" in manual_text
    assert "Open a job posting" in usage_text
    assert "Highlight only the job description" in usage_text
    assert "captured-job-posting.txt" in usage_text
    assert "Ctrl+Shift+B" in browser_help
    assert "If dragging does not work" in browser_help
    assert "URL field" in browser_help
    assert "Location field" in browser_help


def test_browser_capture_bookmarklet_link_supports_drag_setup() -> None:
    link = browser_capture_bookmarklet_link_markdown()

    assert link.startswith("[Capture Job Posting](javascript:")
    assert "captured-job-posting.txt" in link
    assert "localStorage" not in link
    assert "cookie" not in link.lower()


def test_browser_capture_safety_notes_exclude_scraping_and_sensitive_storage() -> None:
    safety_text = " ".join(browser_capture_safety_notes())

    assert "visible page text" in safety_text
    assert "cookies" in safety_text
    assert "local storage" in safety_text
    assert "passwords" in safety_text
    assert "crawl pages" in safety_text
    assert "apply to jobs" in safety_text


def test_evidence_suggestion_helper_prefills_supported_python_api_and_sql() -> None:
    python_suggestion = _suggest_evidence_for_requirement(
        PROFILE_TEXT,
        "Python scripting/development",
    )
    api_suggestion = _suggest_evidence_for_requirement(
        PROFILE_TEXT,
        "API integration experience",
    )
    sql_suggestion = _suggest_evidence_for_requirement(
        PROFILE_TEXT,
        "SQL/data workflow experience",
    )

    assert python_suggestion["status"] in {"Strong evidence", "Some evidence"}
    assert "Auto-suggested from profile" in python_suggestion["notes"]
    assert "Python" in python_suggestion["notes"]
    assert api_suggestion["status"] == "Some evidence"
    assert "REST APIs" in api_suggestion["notes"]
    assert sql_suggestion["status"] == "Some evidence"
    assert "SQL/SQLite" in sql_suggestion["notes"]


def test_evidence_suggestion_helper_keeps_ai_agent_exposure_cautious() -> None:
    suggestion = _suggest_evidence_for_requirement(
        PROFILE_TEXT,
        "LLM / large language model workflow experience",
    )
    agent_suggestion = _suggest_evidence_for_requirement(
        PROFILE_TEXT,
        "Agent-building tools or LLM platform experience",
    )
    prompt_suggestion = _suggest_evidence_for_requirement(
        PROFILE_TEXT,
        "Prompt engineering or prompting experience",
    )

    assert suggestion["status"] == "Some evidence"
    assert "project exposure" in suggestion["notes"]
    assert suggestion["status"] != "Strong evidence"
    assert agent_suggestion["status"] == "Some evidence"
    assert prompt_suggestion["status"] == "Some evidence"


def test_evidence_suggestion_helper_requires_explicit_production_ai_for_strong() -> None:
    profile_text = PROFILE_TEXT + "\nOwned production LLM/agent system used by real users."

    suggestion = _suggest_evidence_for_requirement(
        profile_text,
        "AI agent or automation workflow experience",
    )

    assert suggestion["status"] == "Strong evidence"
    assert "production/deployed" in suggestion["notes"]


def test_evidence_suggestion_helper_respects_use_carefully_skills() -> None:
    cloud_suggestion = _suggest_evidence_for_requirement(
        PROFILE_TEXT,
        "Cloud tools or deployment experience",
    )
    dotnet_suggestion = _suggest_evidence_for_requirement(
        PROFILE_TEXT,
        "C# / .NET 5+ professional experience",
    )
    angular_suggestion = _suggest_evidence_for_requirement(
        PROFILE_TEXT,
        "Angular 16+ and TypeScript",
    )

    assert cloud_suggestion["status"] in {"Not sure", "No evidence"}
    assert "use carefully" in cloud_suggestion["notes"]
    assert dotnet_suggestion["status"] in {"Not sure", "No evidence"}
    assert "use carefully" in dotnet_suggestion["notes"]
    assert angular_suggestion["status"] in {"Not sure", "No evidence"}
    assert "use carefully" in angular_suggestion["notes"]


def test_evidence_suggestions_are_not_all_not_sure_when_profile_has_matches() -> None:
    requirements = [
        "Python scripting/development",
        "API integration experience",
        "Cloud tools or deployment experience",
        "LLM / large language model workflow experience",
    ]
    suggestions = _suggest_evidence_answers(
        {"resume_text": PROFILE_TEXT},
        requirements,
    )
    counts = _evidence_suggestion_counts(suggestions)

    assert counts["Some evidence"] + counts["Strong evidence"] >= 3
    assert suggestions["Cloud tools or deployment experience"]["status"] == "Not sure"


def test_evidence_suggestions_mention_matching_proof_blocks() -> None:
    proof_blocks = [
        {
            "name": "Job Search Automation Tool",
            "tools": ["Python", "Streamlit", "JSON", "pytest"],
            "bullets": [
                "Built a local-first Python tool with validation checks and packet generation."
            ],
            "raw_text": "Python Streamlit JSON pytest packet generation",
        },
        {
            "name": "IT Support Assistant",
            "tools": ["Python", "Flask", "SQLite", "OpenAI API", "JSON"],
            "bullets": ["Developed retrieval and support workflows."],
            "raw_text": "Python Flask SQLite OpenAI API JSON support workflows",
        },
        {
            "name": "TradeOS / Dashboard Project",
            "tools": ["Python", "Pandas", "SQLite/event logging", "API workflows"],
            "bullets": ["Created dashboards, reporting, and API workflow concepts."],
            "raw_text": "Pandas SQLite dashboards reporting API workflows",
        },
    ]

    suggestions = _suggest_evidence_answers(
        {
            "resume_text": PROFILE_TEXT,
            "proof_blocks": proof_blocks,
        },
        [
            "Python scripting/development",
            "API integration experience",
            "SQL/data workflow experience",
            "Automation workflow experience",
        ],
    )

    assert "Job Search Automation Tool" in suggestions["Python scripting/development"]["notes"]
    assert "IT Support Assistant" in suggestions["API integration experience"]["notes"]
    assert "TradeOS / Dashboard Project" in suggestions["SQL/data workflow experience"]["notes"]
    assert "Job Search Automation Tool" in suggestions["Automation workflow experience"]["notes"]
