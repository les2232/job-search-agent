# Job Search Agent

A private, local-first Python app for scoring job postings, explaining role fit,
generating reviewable application packets, and tracking saved applications.

The project is intentionally conservative: it does not scrape job sites, call AI
or external APIs, store credentials, or auto-apply to jobs.

## Quick Start

### Windows

```powershell
git clone <repo-url>
cd job-search-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run ui_app.py
```

After the environment exists, you can also start the app with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_app.ps1
```

For CLI development and tests, install developer dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Run the sample job through the CLI:

```powershell
python .\src\main.py .\data\sample_job.txt
```

## What This App Does

- scores job postings you provide
- explains deterministic fit signals and gaps
- generates reviewable local application packet drafts
- keeps private profiles under ignored `local_profiles/`
- saves packet summaries without storing the raw job description in JSON

## What This App Does Not Do

- scrape job sites or search job boards for you
- store credentials or apply to jobs
- call ChatGPT, external AI APIs, or ChatGPT memory
- verify that every generated claim is true

## Current Feature Map

| Area | Module / Entry Point | What it does |
| --- | --- | --- |
| Job parsing | `src/job_parser.py` | Extracts job metadata from pasted or uploaded job text. |
| Fit scoring | `src/job_scorer.py` | Produces deterministic fit signals, concerns, requirements, and explanations. |
| Evidence adapter | `src/resume_evidence.py` | Normalizes profile, resume, and proof-library data into structured evidence items. |
| Tailoring engine | `src/resume_tailoring.py` | Matches job requirements against evidence and identifies strengths, weak matches, and gaps. |
| Resume draft builder | `src/tailored_resume_builder.py` | Builds a reviewable Markdown tailored resume draft from a tailoring plan. |
| Packet generation | `src/application_packet.py` | Builds the full deterministic application packet from score, profile, and evidence data. |
| Packet writing | `src/application_packet_writer.py` | Saves packet Markdown/JSON files and `packet_index.md` to local folders. |
| Saved packet review | `src/application_packet_reader.py` | Loads saved packet summaries and review sections in deterministic order. |
| Packet validation | `src/application_packet_validator.py` | Checks expected saved packet artifacts without modifying folders. |
| CLI | `src/main.py` | Scores jobs, saves/list packets, tracks status, and validates folders with `--validate-packet`. |
| UI | `ui_app.py` | Provides the Streamlit workflow for generating, saving, reviewing, and tracking packets. |

All generated materials are intended for human review before use. The project
favors deterministic local helpers over automatic submission or unsupported
claims.

## Run the App on Windows

From PowerShell:

```powershell
cd C:\Users\lesco\Desktop\job-search-agent
powershell -ExecutionPolicy Bypass -File .\scripts\run_app.ps1
```

The launcher activates `.venv` if it exists, then starts the Streamlit app.
The app runs locally and does not scrape job sites, store credentials, call
external AI APIs, or apply to jobs.

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

The UI is the easiest way to use the full workflow. The app opens as a calm
`Job Packet Studio` with a guided three-step flow:

1. Choose a profile.
2. Paste or upload a job posting.
3. Generate and review the application packet.

The selected profile controls which resume/profile text is used for packet
generation and which saved application folders are shown. If a private local
profile exists, the UI prefers it by default; otherwise the committed demo
profile is enough to try the app.

For job intake, paste the posting into the large text box or upload a saved
`.txt`, `.md`, `.html`, or `.htm` file. The app detects title, company,
location, and work mode from the text when it can. Manual corrections are
optional and hidden in an expander.

The default action is `Generate application packet`. That one button parses the
posting, scores the fit, suggests evidence from the selected profile, and builds
local draft materials. Review the compact summary card first, then open the
detailed draft tabs below it.

## Fastest Way To Add A Job Posting

1. Open a job page you already chose.
2. Select the job posting text, or select the whole page if that is easier.
3. Paste it into the large `Job posting text` box.
4. Check the detected title, company, location, and work mode.
5. Click `Generate application packet`.

Messy copied page text is okay. The app tries to remove common navigation,
cookie banners, duplicate lines, share/footer fragments, and blank-line spam
before parsing. It keeps the cleaned preview visible in an expander so you can
quickly check what will be used.

You can also upload a local `.txt`, `.md`, `.html`, or `.htm` file saved from a
job page. HTML files are converted to readable text locally. If you paste a job
URL, the app can show it as a source link, but it does not fetch the URL, scrape
the page, ask for credentials, or apply to the job.

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

Profile facts are local deterministic inputs. The app reads only the selected
profile files on disk, then applies rule-based matching; it does not use
ChatGPT memory, call external AI APIs, or infer hidden background facts.

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
  "profile_id": "candidate",
  "display_name": "Candidate",
  "target_roles": ["IT Support", "Technical Support"],
  "notes": "Private local profile."
}
```

Put private profile facts in `resume_base.md`, for example:

```text
# Candidate Name

- N years of IT support experience.
- Help desk, technical support, user-facing troubleshooting, account access
  support, endpoint support, Microsoft 365 support, classroom/AV technology
  support, documentation, escalation, and technical operations support.
```

Keep real names, employers, resumes, and personal proof details under
`local_profiles/`; that folder is ignored by Git. The committed
`profiles/default/` profile is generic demo/template data only.

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

## Job Intake Options

In the Streamlit guided builder, Step 2 supports several ways to add a job
posting:

- paste job text directly
- upload a saved `.txt`, `.md`, `.html`, or `.htm` job post file
- load a fake example or committed sample fixture for testing
- use the optional browser-capture bookmarklet

Paste remains the most reliable option. The main workflow does not import job
URLs, search job boards, crawl links, bypass logins, scrape feeds, ask for job
board credentials, or auto-apply. Employer-facing materials still require manual
review.

Browser capture is optional. It uses a bookmarklet: a small browser bookmark
whose URL starts with `javascript:`.

Recommended setup:

1. Drag `Capture Job Posting` from the app to your bookmarks bar.
2. Open a job posting you already chose.
3. Highlight the job description when possible.
4. Click the `Capture Job Posting` bookmark.
5. Upload the downloaded `captured-job-posting.txt` file back into the app.

Backup setup: copy the bookmarklet code manually, create a new bookmark named
`Capture Job Posting`, and paste the code into the bookmark's URL or Location
field. Do not paste the bookmarklet into the address bar. If setup is
frustrating, use the fast fallback: highlight the job description, press
Ctrl+C, switch to Paste text mode, and paste it into the review box.

The app shows captured text in the same review/edit box used by paste and file
upload. If you do not highlight anything, the bookmarklet falls back to visible
page text, which may include extra clutter.

Browser capture does not search job boards, crawl pages, bypass blocked content,
collect cookies, read local storage, capture passwords, or submit applications.
Some pages still produce messy text, so review the capture before analysis.

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
When a selected local profile clearly covers a support requirement, such as a
2+ year IT support/help desk/technical support requirement covered by a profile
showing enough years of IT support, the packet lists that requirement as
supported evidence instead of a missing proof item.

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

## Evidence Suggestions + Tailored Resume Draft

The guided UI auto-suggests evidence status and notes from the selected
profile's `resume_base.md` when you generate a packet. These suggestions are
review aids, not verified truth. Use the compact result to see what looks
supported and what needs review before using any employer-facing draft.

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
include a `Project Evidence To Use` section. They can also make cover letters
and recruiter messages more specific when a proof block clearly matches the
role. Review all employer-facing text before using it, and do not include
claims you cannot explain in an interview.

Saved packets go under:

```text
applications/<profile_id>/YYYY-MM-DD_company-slug_title-slug/
```

Each saved packet includes:

```text
packet_index.md
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

## Saved Packet Review Workflow

Saved packet folders are review bundles, not ready-to-submit applications. Use
them as local, deterministic drafts and confirm every claim before applying.

Recommended workflow:

1. Generate an application packet from the Streamlit app or CLI.
2. Open the saved packet folder under `applications/<profile_id>/`.
3. Start with `packet_index.md` for the recommended review order.
4. Review `tailored_resume.md` before using any resume wording.
5. Check supporting files when present: `resume_tailoring_notes.md`,
   `cover_letter_draft.md`, `recruiter_message.txt`,
   `application_checklist.md`, `job_summary.md`, `score_explanation.md`, and
   `packet.json`.
6. Validate the saved folder from PowerShell:

The Streamlit UI also displays the saved packet folder path in a selectable
text block after saving or reviewing a packet. On Windows, copy that path and
open the folder directly, then start with `packet_index.md` for the recommended
review order.

```powershell
python .\src\main.py --validate-packet "applications\<profile_id>\<saved-folder>"
```

The validator checks required review artifacts:

- `packet_index.md`
- `tailored_resume.md`
- `packet.json`

It reports missing optional files separately from missing required files. A
valid folder only means the expected artifacts are present; it does not mean the
drafts are accurate or ready to submit. Manually confirm all claims, dates,
skills, project details, and experience before applying.

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
