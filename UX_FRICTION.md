# UX Friction Audit: Job Packet Studio

## Executive Summary

The worst friction on the most common journey is that generating a packet and saving/tracking it are separate, weakly connected steps. After generation, the UI shows a "Saved packet location"/"Saved packet folder" message even before the packet is actually saved (`ui_app.py:954-955`, `ui_app.py:958-969`, `ui_app.py:1115`), while the actual save action is a secondary button below the summary (`ui_app.py:1509-1512`). Highest-impact low-effort fix: make the post-generation state explicit: "Draft generated, not saved yet," place the save action next to that state, and only show "Saved packet folder" after `builder_saved_packet` exists.

## Core User Goals

1. Generate a reviewable packet from a job posting.
2. Save a generated packet for later review.
3. Review or update a previously saved packet.
4. Triage saved applications for today / next action.
5. Add private profile proof evidence.
6. Use the legacy score/tracker workflow.

## Journey Maps

### Goal 1: Generate A Packet For A Job Posting

Total basic steps: 4. Optional correction/helper steps: +2 to +8.

1. Land on main app; first-load UI renders header, profile selector, guided builder, saved-packet expander, and advanced expander (`ui_app.py:128-153`).
2. Choose or accept a profile from the `Profile` selectbox (`ui_app.py:2879-2884`).
3. Add a posting either by uploading a saved file (`ui_app.py:675-679`) or pasting into `Job posting text` (`ui_app.py:695-700`).
4. Optional: open `Other local intake helpers` if using sample, generic example, clipboard help, or browser capture (`ui_app.py:682-693`). **Friction: hidden path / premature complexity for non-paste paths.**
5. Optional: inspect `Cleaned posting preview`, hidden behind an expander (`ui_app.py:814-821`). **Friction: hidden path for validating what the app will actually use.**
6. Optional: open `Edit detected details` and correct title/company/location/work mode (`ui_app.py:884-910`). **Friction: hidden correction path if detection is wrong.**
7. Click `Generate application packet` (`ui_app.py:717-720`).
8. Review generated output: compact summary renders first (`ui_app.py:925-955`), then packet preview tabs for resume focus, tailored resume, cover letter, recruiter message, checklist, risk notes, and metadata (`ui_app.py:2067-2119`).

Inline friction:

- After upload, `_load_uploaded_job_text_into_session()` shows success and immediately reruns (`ui_app.py:787-790`), so the confirmation is likely too fleeting. Type: missing feedback.
- The app shows detected details only after text exists (`ui_app.py:873-878`) and hides editing inside an expander (`ui_app.py:884-910`); if parsing is wrong, the recovery path is not in the main flow. Type: error recovery / hidden path.
- Optional helpers include browser capture inside an expander (`ui_app.py:682-693`) and then another detailed helper flow (`ui_app.py:1201-1262`), so non-paste users face nested setup steps. Type: hidden path / premature complexity.

### Goal 2: Save A Generated Packet

Total steps after generation: 2 to 3.

1. Generate a packet using Goal 1 (`ui_app.py:717-768`).
2. Find the save control below the compact summary; click `Save Packet` (`ui_app.py:1509-1512`) or `Save as New Version` if a duplicate is detected (`ui_app.py:1494-1507`).
3. Read the success message, which appears only after `builder_saved_packet` exists (`ui_app.py:934-936`).

Inline friction:

- Before saving, `_show_compact_packet_result()` still calls `_show_saved_packet_folder_location(save_location)` (`ui_app.py:943-955`), and `packet_save_location()` returns the applications directory when nothing has been saved (`ui_app.py:958-961`). The summary labels this as "Saved packet location" (`ui_app.py:1115`) and the folder note says "Saved packet folder" (`ui_app.py:964-969`). Type: unclear next step / misleading state.
- Save is a secondary button (`ui_app.py:1509-1512`) even though saving is the natural next step after generation. Type: unnecessary friction on main path.
- Duplicate handling gives a warning and a separate "Save as New Version" button (`ui_app.py:1494-1507`), but there is no "open existing packet instead" action. Type: dead end / unclear next step.

### Goal 3: Review Or Update A Previously Saved Packet

Total steps: 7 to 10.

1. Open the `Review saved packets` expander (`ui_app.py:147-148`).
2. If older duplicate versions matter, toggle `Show older duplicate versions` (`ui_app.py:2248-2251`).
3. Scan the dataframe of saved packets (`ui_app.py:2256-2257`).
4. Select a packet in `Preview saved packet` (`ui_app.py:2259-2267`).
5. Review folder path / validation area (`ui_app.py:2274-2277`, `ui_app.py:976-984`).
6. Update status from the `Status` selectbox (`ui_app.py:2736-2742`).
7. Optionally edit notes (`ui_app.py:2743-2748`), next action date (`ui_app.py:2749-2754`), next action note (`ui_app.py:2755-2759`), and applied date for terminal statuses (`ui_app.py:2761-2768`).
8. Click `Update application status` (`ui_app.py:2770-2778`).
9. Review packet tabs below the status form (`ui_app.py:2278-2283`, `ui_app.py:2067-2119`).

Inline friction:

- The whole saved-packet review path is hidden inside a collapsed expander on the main page (`ui_app.py:147-148`). Type: hidden path.
- The same saved packet can also be reviewed through Advanced tools > Saved applications (`ui_app.py:152-160`, `ui_app.py:2548-2616`), creating two overlapping review modes. Type: mode confusion.
- Existing dates are not prefilled into the date pickers; `value=None` is used for both next action and applied date (`ui_app.py:2749-2754`, `ui_app.py:2763-2768`). Updating status/notes can therefore erase a previously saved date if the user does not reselect it. Type: redundant input / error recovery risk.
- Successful status updates call `st.success()` and immediately rerun (`ui_app.py:2779-2781`), so confirmation may disappear. Type: missing feedback.

### Goal 4: Triage Saved Applications For Today / Next Action

Total steps: 5 to 9.

1. Open `Advanced tools: dashboard, tracker, and legacy packet generator` (`ui_app.py:152-153`).
2. Switch to `Today` tab in the advanced tab list (`ui_app.py:153-160`).
3. Review attention counts and groups (`ui_app.py:2350-2389`).
4. Notice the caption says updates happen from the Saved applications tab (`ui_app.py:2389`).
5. Switch to `Saved applications` tab (`ui_app.py:153-160`).
6. Optionally adjust filters (`ui_app.py:2628-2720`).
7. Select packet details (`ui_app.py:2593-2603`).
8. Update status/date/note and submit (`ui_app.py:2736-2778`).

Inline friction:

- The Today view is hidden inside Advanced tools (`ui_app.py:152-160`) even though "what needs attention today" is a primary triage goal. Type: hidden path.
- Today is read-only; the user must switch tabs to act on the items (`ui_app.py:2389`). Type: unnecessary steps / dead end.
- Saved applications filtering exposes many controls before the user selects an item (`ui_app.py:2628-2720`). Type: premature complexity.

### Goal 5: Add Private Profile Proof Evidence

Total in-app steps if a local profile already exists: 6. If no local profile exists: blocked in-app; requires external file creation.

1. Choose a profile from the profile selector (`ui_app.py:2879-2884`).
2. If no local profile exists, read the "No private profile found yet" caption (`ui_app.py:2899-2900`).
3. Open `Add a private local profile later` for setup instructions (`ui_app.py:2901-2916`). **Friction: setup path is informational only; the user must leave the app to create files.**
4. If a local profile exists, open `Profile / Proof Library` (`ui_app.py:2938-2942`).
5. Fill project name, tools, evidence bullets, use-carefully notes, and target tags (`ui_app.py:2965-2982`).
6. Click `Add Proof Block` (`ui_app.py:2982`).
7. If required fields are missing, read warning (`ui_app.py:2984-2987`); otherwise the app appends and reruns (`ui_app.py:2988-2997`).

Inline friction:

- Creating the first private profile cannot be completed in the UI; instructions are hidden behind an expander (`ui_app.py:2901-2916`). Type: hidden path / dead end.
- Proof-library add form is inside an expander and only appears for local profiles (`ui_app.py:2938-2962`). Type: hidden path.
- Success is followed immediately by `st.rerun()` (`ui_app.py:2996-2997`), so confirmation can disappear. Type: missing feedback.

### Goal 6: Use The Legacy Score/Tracker Workflow

Total steps: 8 to 11.

1. Open Advanced tools (`ui_app.py:152-153`).
2. Switch to `Score a Job` tab (`ui_app.py:153-160`).
3. Paste/upload job text through `_get_job_text_input()` (`ui_app.py:3000-3011`).
4. Click `Score job` (`ui_app.py:2415-2426`).
5. Review score summary (`ui_app.py:2434`, `ui_app.py:3014-3040`).
6. Click `Save to tracker` (`ui_app.py:2436-2445`).
7. Switch to `Tracker` tab (`ui_app.py:153-160`).
8. Filter status/recommendation if needed (`ui_app.py:2462-2480`).
9. Select a job and new status in update controls (`ui_app.py:3146-3167`).
10. Click `Update status` (`ui_app.py:3167-3179`).

Inline friction:

- The Score a Job flow overlaps with the primary guided builder but lives under Advanced tools (`ui_app.py:152-160`, `ui_app.py:2407-2445`). Type: mode confusion.
- The tracker save path is separate from the main packet save path; generating a packet in the main builder does not obviously save to the CSV tracker. Type: redundant workflow / unclear next step.
- Successful tracker status update calls `st.success()` and immediately reruns (`ui_app.py:3176-3177`), likely hiding confirmation. Type: missing feedback.

## Prioritized Friction Table

| Priority | Journey | Friction point | Type | Location | What the user experiences | Suggested fix |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | Generate + save packet | UI says "Saved packet location/folder" before the packet is saved. | Dead ends and unclear next steps | `ui_app.py:954-955`, `ui_app.py:958-969`, `ui_app.py:1115` | User may think files already exist or may not realize they still need to click Save. | Before save, label as "Packet will save under..." and show a prominent "Save Packet" action; after save, switch to "Saved packet folder." |
| P0 | Review/update saved packet | Date pickers do not preload saved dates. | Redundant input / error recovery | `ui_app.py:2749-2754`, `ui_app.py:2763-2768` | Updating notes/status can clear dates unless the user re-enters them. | Parse existing `tracking` dates and pass them as `value=` to `st.date_input`; preserve existing strings when no new date is selected. |
| P1 | Triage saved applications | Today is read-only and sends user elsewhere to act. | Unnecessary steps / dead end | `ui_app.py:2350-2389`, `ui_app.py:2389` | User sees what needs attention, then must manually switch tabs and find the same item. | Add inline "Open/update" controls per Today item or reuse saved-packet status controls within Today groups. |
| P1 | Review saved packet | Saved packet review is hidden in a collapsed expander. | Hidden path | `ui_app.py:147-148` | Returning users may not see where past packets live. | Promote saved packet queue to a visible section when saved packets exist, or show a visible "Review saved packets" button/card. |
| P1 | Generate packet | Upload success is immediately followed by rerun. | Missing feedback | `ui_app.py:787-790` | User may not see confirmation; the text area changes but the success message can vanish. | Store a transient message in session state and display it after rerun. |
| P1 | Review/update saved packet | Status update success is immediately followed by rerun. | Missing feedback | `ui_app.py:2779-2781` | User may not see whether the update worked. | Store post-update flash message in session state before rerun, then render it on next run. |
| P2 | Generate packet | Detection correction is hidden in an expander. | Error recovery / hidden path | `ui_app.py:884-910` | If title/company parsing is wrong, the correction affordance is easy to miss. | Show detected details with a small always-visible "Edit" toggle or inline editable chips. |
| P2 | Triage saved applications | Advanced tools hides dashboard/today/saved-applications workflows. | Hidden path / mode confusion | `ui_app.py:152-160` | Main user goals beyond first packet are treated as advanced. | After first saved packet, surface "Today" and "Saved applications" as top-level sections. |
| P2 | Saved applications | Filters appear before item selection and expose many choices. | Premature complexity | `ui_app.py:2628-2720` | User must scan many controls before viewing a packet. | Default to a simple queue first; move detailed filters into an "Advanced filters" expander. |
| P2 | Add proof evidence | First local profile setup cannot be completed in-app. | Dead end / hidden path | `ui_app.py:2899-2916` | User learns what files to create but must leave the app. | Provide a local-profile creation form that writes `local_profiles/<id>/profile.json` and `resume_base.md`. |
| P2 | Add proof evidence | Proof block success is immediately followed by rerun. | Missing feedback | `ui_app.py:2996-2997` | User may not see the success confirmation. | Use a session-state flash message after rerun. |
| P3 | Legacy tracker | Primary builder and Score a Job tab overlap. | Mode confusion | `ui_app.py:152-160`, `ui_app.py:2407-2445`, `ui_app.py:3065-3084` | User can generate/save packets from two places with different semantics. | Rename legacy flows clearly or fold useful tracker actions into the main builder. |
| P3 | Browser capture | Browser capture setup is nested and multi-step. | Hidden path / premature complexity | `ui_app.py:682-693`, `ui_app.py:1201-1262` | Users who cannot paste directly must open helper expander, choose a mode, read setup, then upload capture. | Keep paste/upload primary; add a single "Need help capturing from browser?" link that opens the capture instructions. |

## Quick Wins

1. Clarify unsaved packet state.
   - Edit `packet_save_location()` / `saved_packet_folder_note()` path usage around `ui_app.py:954-969`.
   - Suggested copy before save: "Packet drafts are generated in memory. Click Save Packet to write files under: ..."
   - Keep "Saved packet folder" only when `isinstance(saved_packet, dict)` is true (`ui_app.py:931-936`).

2. Preserve existing dates in saved packet status form.
   - Edit `ui_app.py:2749-2768`.
   - Parse `tracking.get("next_action_date")` and `tracking.get("applied_date")` into date objects for `value=`.
   - If date input returns `None`, keep the existing stored value instead of overwriting with `""`.

3. Make upload/status/proof success survive reruns.
   - For upload: replace immediate-only `st.success()` before `st.rerun()` (`ui_app.py:787-790`) with `st.session_state["flash"] = "..."; st.rerun()`.
   - For status update: same around `ui_app.py:2779-2781`.
   - For proof block: same around `ui_app.py:2996-2997`.

4. Add an "Open saved packets" callout after saving.
   - After `st.success(f"Saved packet: ...")` (`ui_app.py:934-936`), add a clear instruction or button-like link to the saved packet review section.

5. Turn Today items into actionable rows.
   - Start small: in `_show_today_group()` add folder path and "Update from Saved applications" label per item is already present (`ui_app.py:2392-2404`); make it more direct with the exact packet label to choose in Saved applications.

## Bigger Bets

1. Merge "Review saved packets" and "Saved applications."
   - Current top-level expander review (`ui_app.py:147-148`, `ui_app.py:2231-2283`) and advanced saved-applications tab (`ui_app.py:2548-2616`) overlap. A single saved-application workspace would reduce mode confusion.

2. Promote post-first-packet workflows out of Advanced tools.
   - Dashboard, Today, Tracker, and Saved applications are all behind one expander (`ui_app.py:152-160`). Once a user has saved packets, those are no longer advanced.

3. In-app private profile creation.
   - Current setup is instructional only (`ui_app.py:2899-2916`). A real first-run profile wizard would remove a major setup dead end while preserving local-first storage.

4. Main-path tracking integration.
   - Main builder saves packet folders (`ui_app.py:1509-1517`), while the CSV tracker is separate in Score a Job (`ui_app.py:2436-2445`). A unified "Save packet and add to tracker" decision would reduce redundant workflows.
