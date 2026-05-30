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

## Quick Smoke Test

Run this when you want a fast end-to-end packet check without touching private
profiles, `applications/`, or `data/jobs.csv`:

```powershell
python scripts\smoke_packet_flow.py --fixture all
```

You can also run one fixture at a time:

```powershell
python scripts\smoke_packet_flow.py --fixture arrivia_ai_agent
python scripts\smoke_packet_flow.py --fixture fei_full_stack
```

The smoke test parses committed fixture postings, scores them, generates packets,
writes them to a temporary directory, reads the Markdown/JSON back, and checks
that the Arrivia AI-agent packet and FEI stretch-role packet include the expected
role-specific guidance. It does not write real saved packets.

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

The packet also extracts common hard requirements from the posting, such as
languages/frameworks, databases, cloud/devops tools, testing practices,
architecture terms, and years-of-experience requirements. These extracted role
requirements are used for risk notes and resume tailoring guidance, so generic
target keywords are not treated as gaps unless the job actually asks for them.

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

## Evidence Check + Tailored Resume Draft

The guided UI includes an evidence check after job analysis. It auto-suggests
evidence status and notes from the selected profile's `resume_base.md`, then lets
you correct anything that is too generous, too cautious, or incomplete. For each
detected hard requirement, confirm whether the candidate has strong evidence,
some evidence, no evidence, or is not sure. Add or revise short notes that point
to real resume, project, coursework, or work examples.

The app uses those answers to generate:

- a decision summary
- supported, partial, missing, and needs-verification evidence groups
- missing-proof next actions
- a reviewable `tailored_resume.md` draft

The tailored resume draft is not a final resume. It is a local review aid that
must be checked manually before use. The app does not invent resume claims, and
you should remove unsupported skills, avoid fake metrics, and keep professional
experience separate from coursework or project exposure.

Evidence suggestions are intentionally conservative. Auto-suggested evidence is
not verified proof, especially for AI agents, LLM workflows, cloud/deployment,
and production engineering claims. Treat the generated resume bullets as
reviewable candidates, replace generic wording with real examples, and remove
anything you cannot support before applying.

### Proof Library

Private profiles can include a Markdown proof library in
`local_profiles/<profile_id>/resume_base.md`:

```text
## Project Evidence / Proof Library

### Project Name

**Tools / Skills:** Python, Streamlit, SQLite

* Evidence bullet you can explain in an interview.
```

The Streamlit app shows proof blocks for the selected profile and lets local
profiles append new private proof blocks from the UI. Proof library data should
stay under `local_profiles/`, which is ignored by Git. These proof blocks help
Evidence Check suggest specific project anchors and help `tailored_resume.md`
include a `Project Evidence To Use` section. Do not include claims you cannot
explain in an interview.

Saved packets go under:

```text
applications/<profile_id>/YYYY-MM-DD_company-slug_title-slug/
```

Each saved packet includes:

```text
job_summary.md
score_explanation.md
resume_tailoring_notes.md
tailored_resume.md
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
