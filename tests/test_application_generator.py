from pathlib import Path

import pytest

from application_generator import (
    REVIEW_WARNING,
    find_matching_keywords,
    generate_application_materials,
)


def test_find_matching_keywords_returns_overlap_only() -> None:
    job_text = "This role uses Python, SQL, dashboards, and Linux."
    resume_text = "Fake example profile with Python and SQL experience."
    keywords = ["python", "sql", "dashboard", "linux"]

    assert find_matching_keywords(job_text, resume_text, keywords) == [
        "python",
        "sql",
    ]


def test_generate_application_materials_creates_output_files(
    tmp_path: Path,
) -> None:
    job_path = tmp_path / "job.txt"
    resume_path = tmp_path / "resume_base.md"
    output_dir = tmp_path / "output"
    job_path.write_text(
        """Title: Junior Python Analyst
Company: Fake Example Company
Location: Remote

Use Python and SQL to support dashboards.
""",
        encoding="utf-8",
    )
    resume_path.write_text(
        """# Fake Example Resume

- Used Python and SQL in class projects.
""",
        encoding="utf-8",
    )

    result = generate_application_materials(job_path, resume_path, output_dir)
    output_paths = result["output_paths"]

    assert output_paths["resume"].exists()
    assert output_paths["cover_letter"].exists()
    assert output_paths["match_notes"].exists()
    assert result["matching_keywords"] == ["python", "sql"]


def test_generate_application_materials_requires_resume_file(
    tmp_path: Path,
) -> None:
    job_path = tmp_path / "job.txt"
    job_path.write_text("Title: Analyst", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="resume/profile"):
        generate_application_materials(
            job_path,
            tmp_path / "missing_resume.md",
            tmp_path / "output",
        )


def test_generated_materials_include_review_warning(tmp_path: Path) -> None:
    job_path = tmp_path / "job.txt"
    resume_path = tmp_path / "resume_base.md"
    output_dir = tmp_path / "output"
    job_path.write_text(
        "Title: Analyst\nCompany: Fake Company\nLocation: Remote\nPython role.",
        encoding="utf-8",
    )
    resume_path.write_text("Fake resume with Python.", encoding="utf-8")

    result = generate_application_materials(job_path, resume_path, output_dir)

    for output_path in result["output_paths"].values():
        assert REVIEW_WARNING in output_path.read_text(encoding="utf-8")
