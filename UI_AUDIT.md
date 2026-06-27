# UI Audit: Job Packet Studio

## Executive Summary

Overall maturity: early but coherent single-file Streamlit UI. The app has a clear local-first product boundary, but the UI layer is still mostly handcrafted HTML/CSS plus Streamlit primitives in one large file.

Single biggest problem: active UI and legacy/dormant UI flows coexist in `ui_app.py`. This creates product drift and risk against the stated local-first/no-scraping direction.

Highest-impact low-effort fix: keep the active three-step builder as the only primary path and remove dormant UI paths as they are identified.

Verification: ran `python -m pytest tests\test_ui_app.py --basetemp .pytest_tmp_codex`; result: 52 passed. No in-repo axe/Lighthouse/eslint accessibility tooling exists, and adding it would require new dependencies, so accessibility findings below are static-source findings.

## UI Layer Map

- Framework: Streamlit, imported at `ui_app.py:15` with `import streamlit as st`.
- App entry point: `ui_app.py:133`, `st.set_page_config(page_title="Job Packet Studio", layout="wide")`.
- Main active flow: `main()` in `ui_app.py:133-164`.
  - Header: `render_app_header()` at `ui_app.py:135`, implementation at `ui_app.py:392-406`.
  - Workflow strip: `workflow_strip_html()` at `ui_app.py:409-424`.
  - Profile selector: `_show_profile_selector()` called at `ui_app.py:142`.
  - Guided packet builder: `_show_guided_packet_builder()` called at `ui_app.py:149`.
  - Saved packet review: expander at `ui_app.py:151-152`.
  - Advanced screens: expander and tabs at `ui_app.py:156-164`.
- Styling approach: injected raw CSS string via `st.markdown(app_style_css(), unsafe_allow_html=True)` at `ui_app.py:221`.
- Design tokens: local CSS custom properties at `ui_app.py:227-236`.
- Component library/design system: no external design system; the UI uses Streamlit primitives plus custom `.studio-*` classes.
- Most-trafficked screens/routes: no routes. The first screen is `main()` with header, welcome expander, profile selector, and guided packet builder. Secondary screens are the advanced tabs created at `ui_app.py:157-164`: Dashboard, Today, Score a Job, Tracker, Application Packets, Saved applications.

## Prioritized Findings

| Severity | Location | Issue | Principle violated | Fix |
| --- | --- | --- | --- | --- |
| Medium | `ui_app.py:660-667` | The first screen repeats workflow/privacy messaging immediately after the hero. Snippet: `with st.expander("Start here: how this local app works", expanded=True):` and `st.info("Everything stays on this computer...")`. This competes with the new always-visible workflow strip. | Visual hierarchy / competing focal points | Collapse by default or shorten to a single quiet note. Suggested edit: `with st.expander("How this local app works", expanded=False):`. |
| Medium | `ui_app.py:721-724` | Primary action has no loading/disabled state during packet generation. Snippet: `generate_clicked = st.button("Generate application packet", type="primary", key="builder_generate_application_packet")`. | Interaction states / feedback | Wrap generation work in `with st.spinner("Generating local packet..."):` after click, and optionally disable related inputs while processing if Streamlit version supports it. |
| Medium | `ui_app.py:2740-2746` | Saved application metrics wrap statuses across four columns by modulo. Snippet: `metric_cols = st.columns(4)` and `metric_cols[index % 4].metric(status, status_counts[status])`. This creates uneven visual grouping when status count changes. | Layout consistency / alignment | Use a stable grid helper or render statuses in a dataframe/table. If keeping metrics, define rows explicitly instead of modulo placement. |
| Medium | `ui_app.py:2764-2820` | Saved application filters use 4 columns, then 4 columns, then 3 columns. Snippets: `filter_cols = st.columns(4)`, `search_cols = st.columns(4)`, `attention_cols = st.columns(3)`. This is dense on desktop and awkward on narrow screens. | Layout & spacing / mobile ergonomics | Group filters into two-column rows or use expanders for advanced filters. Example: `left, right = st.columns(2)` for primary filters, with advanced filters collapsed. |
| Medium | `ui_app.py:887-910` | Detected details editor uses four equal columns inside an expander. Snippet: `field_cols = st.columns(4)`. Long labels/values can crowd, especially on tablet widths. | Responsive behavior / form ergonomics | Use two columns or stacked fields. Example: `field_cols = st.columns(2)` and place title/company row, location/work mode row. |
| Medium | `ui_app.py:2870-2888` | Date fields are plain text inputs. Snippet: `next_action_date = st.text_input("Next action date", placeholder="YYYY-MM-DD")` and `applied_date = st.text_input("Applied date", placeholder="YYYY-MM-DD")`. | Forms / validation timing / input semantics | Use `st.date_input` or validate immediately next to the field before submit. If storing strings, convert selected dates with `.isoformat()`. |
| Low | `ui_app.py:228-236` and `ui_app.py:243-363` | Token drift: some styles use CSS variables, many use one-off hex values. Snippets: `--studio-border: #d8e1df;`, then `border: 1px solid #b8cbc8;`, `background: #f7faf9;`, `color: #536b6b;`. | Consistency & drift / design tokens | Add tokens for surface, border-strong, helper-text, hero-text and replace one-off hexes. Example: `--studio-surface-soft: #f7faf9; --studio-border-strong: #b8cbc8;`. |
| Low | `ui_app.py:240` | Main content max width is a one-off hardcoded value. Snippet: `max-width: 1320px;`. | Layout tokens / magic numbers | Move to a token: `--studio-page-max: 1320px;` then `max-width: var(--studio-page-max);`. |
| Low | `ui_app.py:245`, `ui_app.py:289`, `ui_app.py:315`, `ui_app.py:361` | Spacing scale is handcrafted per component. Snippets: `padding: 1.55rem 1.65rem 1.25rem 1.65rem;`, `padding: .9rem .95rem;`, `padding: 1rem 1.1rem;`, `padding: 1rem 1.15rem;`. | Layout & spacing consistency | Define spacing tokens such as `--space-2: .5rem; --space-3: .75rem; --space-4: 1rem; --space-5: 1.25rem;` and normalize component padding. |
| Low | `ui_app.py:259`, `ui_app.py:264`, `ui_app.py:310`, `ui_app.py:320`, `ui_app.py:342`, `ui_app.py:367`, `ui_app.py:384` | Typography scale is ad hoc. Snippets: `font-size: 2.35rem;`, `font-size: 1.08rem;`, `font-size: .92rem;`, `font-size: 1.2rem;`, `font-size: 1.9rem;`. | Typography consistency | Add type tokens: `--font-title: 2.25rem; --font-section: 1.2rem; --font-body: 1rem; --font-small: .92rem;`. |
| Low | `ui_app.py:286` and `ui_app.py:288` | Workflow card border has low non-text contrast against its background. Snippet: `border: 1px solid #c6d7d4;` on `background: #f7faf9;`. Computed contrast: 1.42:1. | Color & contrast / component boundaries | For non-text UI boundaries, target at least 3:1 where the border communicates grouping. Use a darker border such as `#8aa7a3` against `#f7faf9` (about 2.37:1) or `#6f918c` (about 3.14:1). |
| Low | `ui_app.py:338-339` | Chip/badge border uses `var(--studio-border)` on white. Snippet: `border: 1px solid var(--studio-border); background: #ffffff;`. `#d8e1df` on white is 1.33:1. | Color & contrast / affordance clarity | Use a stronger token for chip borders, e.g. `--studio-border-control: #8aa7a3;` or rely less on border-only grouping. |
| Low | `ui_app.py:817-823` | Cleaned preview is hidden behind an expander and rendered as disabled text area. Snippet: `with st.expander("Cleaned posting preview")` and `disabled=True`. This is readable but not copy/edit friendly. | Interaction states / review workflow | Make preview collapsed only after quality passes, or provide a copyable `st.code(clean_text)` below the disabled field. |
| Low | `ui_app.py:1478` | Browser capture uses `alert(...)`. Snippet: `if(text.trim().length<80){alert('Captured text is short...');}`. Alerts are disruptive and not screen-reader friendly. | Accessibility / interaction feedback | Replace alert with downloadable text containing the warning or show warning after upload in Streamlit only. Existing upload warning at `ui_app.py:1280-1283` already covers this. |
| Low | `ui_app.py:3059-3118` | Proof Library combines read-only proof review and write form in one expander. Snippet: `with st.expander("Profile / Proof Library")`, then `st.markdown("**Existing proof blocks**")`, then `st.markdown("**Add proof block**")`. | Visual hierarchy / form focus | Split into two expanders: `Profile evidence` and `Add proof block`, or keep add form collapsed under its own nested expander. |

## Color Contrast Notes

Computed from actual colors in `app_style_css()`:

- Passes WCAG AA for normal text:
  - `#2f6f73` on `#ffffff`: 5.77:1.
  - `#4f6363` on `#ffffff`: 6.37:1.
  - `#496162` on `#f7faf9`: 6.31:1.
  - `#536b6b` on `#f7faf9`: 5.43:1.
  - `#206a43` on `#eaf6ef`: 5.91:1.
  - `#8a5a00` on `#fff6dd`: 5.50:1.
- Fails/weak for non-text boundaries where the border is the primary grouping cue:
  - `#c6d7d4` on `#f7faf9`: 1.42:1 at `ui_app.py:286-288`.
  - `#d8e1df` on `#ffffff`: 1.33:1 at `ui_app.py:338-339`.

No color-only status finding: current custom badges include text labels, e.g. `status_badge_html()` emits a label at `ui_app.py:448-450`.

## Quick Wins

1. Collapse the redundant welcome expander.
   - Edit `ui_app.py:660` from:
     ```python
     with st.expander("Start here: how this local app works", expanded=True):
     ```
     to:
     ```python
     with st.expander("How this local app works", expanded=False):
     ```

2. Add loading feedback to the primary packet button.
   - Edit after `ui_app.py:721-724`:
     ```python
     if generate_clicked:
         with st.spinner("Generating local packet..."):
             ...
     ```
   - Keep all existing packet generation logic inside the spinner block.

3. Replace saved-application date text fields with date inputs or immediate validation.
   - Edit `ui_app.py:2870-2888`.
   - Prefer:
     ```python
     selected_date = st.date_input("Next action date", value=None, key=f"{widget_key}_next_action_date")
     next_action_date = selected_date.isoformat() if selected_date else ""
     ```

4. Normalize CSS tokens.
   - Edit `ui_app.py:227-236` to add:
     ```css
     --studio-page-max: 1320px;
     --studio-surface-soft: #f7faf9;
     --studio-border-strong: #6f918c;
     --studio-space-4: 1rem;
     --studio-space-5: 1.25rem;
     ```
   - Replace one-off values at `ui_app.py:240`, `ui_app.py:245`, `ui_app.py:286`, `ui_app.py:288`, and `ui_app.py:315`.

5. Make dense filter rows easier to scan.
   - Edit `ui_app.py:2764-2820`.
   - Keep Status, Recommendation, Sort visible; move min score, company/title search, and attention checkboxes under an `Advanced filters` expander.

## One Thing Done Well

The custom text color choices in the active header/workflow CSS pass WCAG AA for normal text; the contrast problems are mostly weak borders and grouping affordances, not readable text.
