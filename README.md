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

## Safety Notes

- No real resumes, emails, job history, credentials, or API keys are included.
- `config.local.json` is ignored; use `config.example.json` for safe examples only.
- `data/jobs.csv` is generated locally and ignored by Git.
- The project does not scrape login-protected sites or automate applications.
