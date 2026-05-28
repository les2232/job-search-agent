# Job Search Agent

A private, local-first Python project for evaluating job postings, scoring role
fit, and tracking application opportunities with sample data.

This milestone reads a plain-text job description, parses basic fields, scores
it with keyword rules, prints a recommendation, and saves a local CSV result.

## Run

Run the default sample job:

```powershell
python .\src\main.py
```

Run a specific `.txt` job posting file:

```powershell
python .\src\main.py .\data\sample_job.txt
python .\src\main.py .\path\to\another_job.txt
```

Generate local draft application materials from a job posting and your local
resume/profile file:

```powershell
python .\src\main.py generate-application .\data\sample_job.txt --resume .\data\profile\resume_base.md
```

The resume/profile file must be created locally by you. A good starting path is
`data/profile/resume_base.md`. Keep it factual and include only details you are
comfortable storing on your own machine.

## Local UI

Install the UI dependency:

```powershell
python -m pip install -r requirements.txt
```

Run the local browser UI:

```powershell
streamlit run ui_app.py
```

The UI is organized as a local job-search cockpit with four tabs:

- `Dashboard`: tracker totals, status/recommendation counts, follow-up counts,
  and a rule-based recommended next action.
- `Score a Job`: paste or upload a `.txt` posting, score it, review matched
  keywords/concerns, and save it to the tracker.
- `Tracker`: filter tracked jobs by status or recommendation and update job
  status.
- `Application Packets`: generate local job-specific packets and preview
  existing `match_notes.md` files.

Everything remains local; `data/jobs.csv`, `data/profile/`, and `output/` are
ignored by Git.

## Configuration

Default scoring rules live in `config.example.json`. They include the starting
score, keyword point values, recommendation thresholds, positive keywords, and
concern keywords.

To tune scoring for your own local use, create `config.local.json` in the
project root. If that file exists, the app uses it instead of
`config.example.json`. Keep `config.local.json` local, do not commit it, and do
not put sensitive personal data in it.

## Local Tracker

Scored jobs are saved to `data/jobs.csv` with these fields: `title`,
`company`, `location`, `score`, `recommendation`, `status`, `notes`,
`source_url`, `date_found`, and `follow_up_date`.

New rows default to `status` of `New`, blank notes, blank source URL, today's
date for `date_found`, and a blank follow-up date. Before saving, the tracker
checks for an existing row with the same title and company. If one is already
tracked, the app skips the duplicate and prints a clear message.

`data/jobs.csv` is local-only and ignored by Git. Do not commit real job leads,
application notes, source URLs, or personal application details.

List tracked jobs:

```powershell
python .\src\main.py list
```

Filter tracked jobs:

```powershell
python .\src\main.py list --status New
python .\src\main.py list --recommendation Apply
```

Update a tracked job's status:

```powershell
python .\src\main.py update-status --title "Junior Python Data Analyst" --company "Example Analytics Studio" --status Applied
```

Repair the local tracker:

```powershell
python .\src\main.py repair-tracker
```

`repair-tracker` creates a timestamped backup before modifying `data/jobs.csv`.
It removes duplicate header rows, normalizes rows to the current schema, and
dedupes repeated jobs by title and company while preserving the first version.

## Application Packets

The `generate-application` command creates a job-specific folder in `output/`.
The folder name is based on the company and job title, for example:

```text
output/example-analytics-studio-junior-python-data-analyst/
```

Each packet includes:

```text
tailored_resume.md
cover_letter.md
match_notes.md
job_posting.txt
```

`job_posting.txt` preserves the original job posting text used for generation.

Draft generation is intentionally conservative. It reads the job posting and
your local resume/profile, finds configured keywords that appear in both, and
creates draft text from that local information. It does not use AI, call APIs,
scrape websites, or invent experience.

Every generated file includes this warning: "Draft only. Review carefully before
using. Do not include claims you cannot verify." Review all generated materials
manually before using them.

`data/profile/` and `output/` are ignored by Git. Do not commit real resumes,
profile facts, generated cover letters, or personal application materials.

## Safety Notes

- No real resumes, emails, job history, credentials, or API keys are included.
- `config.local.json` is ignored; use `config.example.json` for safe examples only.
- `data/jobs.csv` is generated locally and ignored by Git.
- `data/profile/` and `output/` are local-only and ignored by Git.
- The project does not scrape login-protected sites or automate applications.
