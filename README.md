# Job Search Agent

A private, local-first Python app for scoring job postings, explaining role fit,
generating reviewable application packets, and tracking saved applications.

The project is intentionally conservative: it does not scrape job sites, call AI
or external APIs, store credentials, or auto-apply to jobs.

## Quick Start

Install developer dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Run the sample job through the CLI:

```powershell
python .\src\main.py .\data\sample_job.txt
```

Install the UI dependency:

```powershell
python -m pip install -r requirements.txt
```

Run the local browser UI:

```powershell
streamlit run ui_app.py
```

## Streamlit UI

The UI is the easiest way to use the full workflow.

Choose a candidate profile at the top of the app before scoring or reviewing
saved applications. The selected profile controls which resume/profile text is
used for packet generation and which saved application folders are shown.

- `Dashboard`: high-level tracker and saved-application counts.
- `Today`: applications that are overdue, due soon, ready to apply, or missing
  follow-up dates.
- `Score a Job`: paste or upload a `.txt` job posting, score it, review the
  explanation, generate an application packet, save it, and save the job to the
  tracker.
- `Tracker`: review the local CSV tracker and update basic job statuses.
- `Application Packets`: older file-based draft generation from a job file and
  local resume/profile file.
- `Saved applications`: review saved packets, filter/sort them, update status,
  notes, applied dates, and next-action dates.

Everything runs locally on your machine.

## CLI Usage

Score the default sample:

```powershell
python .\src\main.py
```

Score a specific job posting:

```powershell
python .\src\main.py .\path\to\job.txt
python .\src\main.py .\path\to\job.txt --profile default
```

Show the deterministic application packet in the CLI:

```powershell
python .\src\main.py .\data\sample_job.txt --packet
python .\src\main.py .\data\sample_job.txt --profile default --packet
```

Save the generated packet under `applications/`:

```powershell
python .\src\main.py .\data\sample_job.txt --packet --save-packet
python .\src\main.py .\data\sample_job.txt --profile default --packet --save-packet
```

List saved packets:

```powershell
python .\src\main.py --list-packets
python .\src\main.py --list-packets --profile default
python .\src\main.py --list-packets --status Tailoring
python .\src\main.py --list-packets --min-score 70
python .\src\main.py --list-packets --needs-attention
python .\src\main.py --list-packets --overdue
```

Update a saved packet:

```powershell
python .\src\main.py --update-packet-status "applications\folder-name" --status Tailoring --next-action-date 2026-06-04 --next-action-note "Finish resume tailoring."
```

Show today's attention queue:

```powershell
python .\src\main.py --today
python .\src\main.py --today --profile default
```

## Profiles

Profiles keep different people's resume notes and saved application packets
separate.

The committed demo profile lives at:

```text
profiles/default/
  profile.json
  resume_base.md
```

Use it for testing only. For real private profiles, create ignored local folders:

```text
local_profiles/<profile_id>/
  profile.json
  resume_base.md
```

Example `profile.json`:

```json
{
  "profile_id": "leslie",
  "display_name": "Leslie",
  "target_roles": ["IT Support", "Technical Support"],
  "notes": "Private local profile."
}
```

Saved application packets are profile-specific:

```text
applications/<profile_id>/YYYY-MM-DD_company-slug_title-slug/
```

Existing legacy packets directly under `applications/` are still shown for the
`default` profile so older local packets remain visible.

## Scoring Flow

The app parses job metadata from labeled fields when available:

- title
- company
- location
- work mode

If labels are missing, it falls back to the top lines of the posting. Metadata
that cannot be found stays `Unknown`.

For copied job-board posts, add a short clean header above the pasted text so
generic site labels such as `Job details` or `Job type` are not mistaken for job
metadata:

```text
Job Title: Full-Stack Developer
Company: FEI Systems
Location: Remote
Work Mode: Remote
Job Type: Full-time

Full Job Description:
Paste the job-board description here.
```

Store real beta-user job posting files under ignored local folders such as:

```text
local_profiles/<profile_id>/job_postings/first-job.txt
```

Then score the file with the matching private profile:

```powershell
python .\src\main.py .\local_profiles\<profile_id>\job_postings\first-job.txt --profile <profile_id> --packet
```

Scoring rules live in `config.example.json`. You can create an ignored
`config.local.json` to tune local scoring. The score explanation shows:

- fit summary
- strengths
- gaps
- concerns
- tailoring suggestions

## Application Packets

The `--packet` flow creates deterministic, reviewable guidance from the score
result and optional local profile text. It includes:

- positioning summary
- apply recommendation
- resume focus areas
- editable resume bullet suggestions
- keywords to include honestly
- keywords to verify or avoid
- short cover letter draft
- recruiter message
- application checklist
- risk notes

The cover letter draft is employer-facing. Internal cautions and verification
reminders stay in the risk notes, checklist, score explanation, and resume
tailoring notes.

Saved packets go under:

```text
applications/<profile_id>/YYYY-MM-DD_company-slug_title-slug/
```

Each saved packet includes:

```text
job_summary.md
score_explanation.md
resume_tailoring_notes.md
cover_letter_draft.md
recruiter_message.txt
application_checklist.md
packet.json
```

Saved packets do not include the full raw job description.

## Saved Applications

Saved applications are read from `applications/*/packet.json`. The dashboard can
filter by status, recommendation, apply recommendation, work mode, score,
company, title/company text, attention state, overdue state, and due dates.

Supported saved-application statuses:

- `Interested`
- `Tailoring`
- `Ready to Apply`
- `Applied`
- `Interview`
- `Offer`
- `Rejected`
- `Archived`

Next-action tracking supports:

- next action date
- next action note
- applied date
- notes
- computed overdue and needs-attention flags

The `Today` view groups applications into overdue, due today, due soon, ready to
apply, applied without follow-up, and other attention items.

## Local Tracker

The older CSV tracker still exists at `data/jobs.csv`. It is local-only and
ignored by Git.

```powershell
python .\src\main.py list
python .\src\main.py list --status New
python .\src\main.py list --recommendation Apply
python .\src\main.py update-status --title "Junior Python Data Analyst" --company "Example Analytics Studio" --status Applied
python .\src\main.py repair-tracker
```

## Privacy Notes

Ignored local files and folders include:

- `data/jobs.csv`
- `data/profile/`
- `local_profiles/`
- `output/`
- `applications/`
- `config.local.json`
- local resume drafts such as `resume_*.md` and `resume_*.txt`

Do not commit real resumes, personal job leads, generated cover letters,
application notes, credentials, or private profile data.

Risk notes and review checklists include the warning:

```text
Draft only. Review carefully before using. Do not include claims you cannot verify.
```

Review every generated packet manually before using it.
