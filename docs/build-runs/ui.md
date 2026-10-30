# Build report: ui (build/ui)

2026-10-30 11:28 IST · Commits: 78dff1e, 6766b1f, 39d2fa8, 5fd89b0

## STORE core/store.py: SQLite cases / escalations / messages · Status: done
- Used: stdlib sqlite3 (`check_same_thread=False`, a fresh connection per call, 10 s busy timeout), hashlib.
- Decisions:
  - DB path comes from `APP_DB` and is read on every call, so tests can point it at a temp file. The default is `<repo>/app.db`, which is already gitignored.
  - Schema is created lazily on every connection with `CREATE TABLE IF NOT EXISTS`.
  - Added `update_case(id, payload)` so the patient page can persist the case after a resolution. Added `save_upload(bytes) -> cache/uploads/<sha256>.jpg`.
  - `add_message` rejects any sender other than patient, doctor or system.
  - `get_escalation` and `list_open` return `candidates` and `resolution` already parsed from JSON. `get_case` returns `payload` parsed.
- Files: core/store.py, tests/test_store.py
- Verified by: `.venv/bin/python -m pytest tests/ -q` → `11 passed` (store: case round-trip and update, escalation → messages → resolve → list_open empty, content-addressed upload).

## FE-1 Patient page (app.py): context, photo/typed input, analyze with live status, results · Status: done
- Used: Streamlit 1.66.1 (`st.status`, `st.tabs`, `st.camera_input`, `st.fragment`, `st.chat_message`/`st.chat_input`), pandas tables.
- Decisions:
  - `pipeline.analyze` runs in a worker thread. The main thread polls every 0.5 s and updates the `st.status` label with the current step and the elapsed seconds, so the timer keeps moving during a 40 s+ Gemma call.
  - The **Type it** text overrides the photo when it is non-empty. That makes it the deterministic fallback when the API is slow.
  - **Load demo case** uses an `on_click` callback. It sets the context and allergies (`demo_assets/allergies.txt`, falling back to "penicillin") and loads the prescription and strip bytes. The page shows them with the caption "Synthetic demo prescription". A file_uploader can't be pre-filled, so the bytes live in session_state and a **Clear demo images** button removes them.
  - Medicine cards show the band as a coloured badge that always carries a TEXT label (HIGH ✓ / MEDIUM ⚠ / LOW ✕). The status chips are Auto-matched / Needs confirmation / ⏳ Awaiting doctor / ✅ Confirmed by doctor / ☑ Picked by you.
  - **MEDIUM:** a "Pick the right medicine" radio plus a "Use this medicine" button, which records `picked_by_patient`. That is a 4th status, beyond the 3 in the brief, because a patient pick is not a doctor confirmation. There is also an "Ask a doctor" button.
  - **LOW:** an error line plus a full-width primary "🩺 Ask a doctor" button.
  - **Safety alerts** are sorted HIGH → REVIEW → INFO. The strip check is a big MATCH ✓ / MISMATCH ✕ / NOT PRESCRIBED ✕ card.
  - **Results sections:**
    - Dose schedule table with Morning, Afternoon, Night, Bedtime and As needed, plus any extra slot names `safety.schedule` returns.
    - Jan Aushadhi table and `st.metric` "Save about ₹X/month", labelled indicative.
    - Hindi summary expander, open by default.
    - Trace expander with step, model/backend, seconds and cache hit.
    - Disclaimer footer.
  - Theme is forced light and the base font is 17 px.
- Files: app.py, .streamlit/config.toml
- Verified by:
  - `pytest tests/test_pipeline.py::test_ui_patient_typed_flow`: AppTest types "Dolo 650 TDS\nCombiflam SOS", clicks Analyze → no exception. "Step 3" and the raw text render, and the Hindi and pipeline-trace expanders are present.
  - A scratch AppTest of the photo + strip path with the real demo_assets images → `mode: photo meds: 1 strip: MATCH`, and the image was saved to `cache/uploads/<sha>.jpg`.
  - A scratch AppTest with a forced MEDIUM band → the radio rendered, and picking "Alt Brand" gave `status: picked_by_patient Alt Brand`.
  - Live run: `.venv/bin/streamlit run app.py --server.port 8599 --server.headless true` → `curl /_stcore/health` = `ok`, `/` = 200, `/Doctor_Console` = 200. The server was killed afterwards.

## FE-2 Ask a doctor: escalation, templated system message, live patient chat · Status: done
- Decisions:
  - `ask_doctor(i)` calls `open_escalation(case_id, i, raw, candidates, context)`, then adds a TEMPLATE system message with no Gemma call: "AushNexa could not confidently read line N: '<raw>'. Top candidates: A (salts), B (salts), C (salts). Patient context: … Allergies: … Reasons: …".
  - `doctor_chat_panel` is an `@st.fragment(run_every=3)` that shows each escalation's status and history, with a `st.chat_input` for the patient. When an escalation becomes `resolved`, it runs `apply_resolution(by="doctor")` and then `recheck`, updates session_state and the DB, and calls `st.rerun(scope="app")`. The card then flips to "✅ Confirmed by doctor" and the alerts are recomputed.
- Files: app.py
- Verified by: `pytest tests/test_pipeline.py::test_ui_ask_doctor_and_doctor_console`. It runs the full round trip:
  1. Analyze "Celemax 500 OD" with a forced LOW band.
  2. Click "Ask a doctor" → the escalation is open and the system message contains "could not confidently read line 1".
  3. Doctor Console: Open → Other medicine "Calcimax" → Confirm other → the escalation is resolved and the last message is "Confirmed: Calcimax".
  4. The patient page reruns → `status == confirmed_by_doctor` and `rechecked is True`.

## FE-3 Doctor Console (pages/2_Doctor_Console.py) · Status: done
- Decisions:
  - The open-escalation list is an `@st.fragment(run_every=3)`. Its "Open" button stores the selected id and calls `st.rerun(scope="app")`.
  - The detail view shows:
    - the prescription image from the case `image_path` ("No photo (typed prescription)" otherwise);
    - the line as read, the patient context and the allergies;
    - the confidence band, value and reasons;
    - the top-3 table with salts, match score, Gemma "fits?" and the Gemma fit note, taken from the stored case payload.
  - The chat is its own `@st.fragment(run_every=3)` with a doctor `st.chat_input`.
  - There is a "Confirm: <candidate>" button per candidate, plus an "Other medicine" input and a "Confirm other" button. Both call `store.resolve` with `{"name"}` or `{"free_text"}` and post "Confirmed: <name>".
- Files: pages/2_Doctor_Console.py
- Verified by: the same AppTest as FE-2 (renders with the title "Doctor Console", no exception, the confirm flow works), and live `curl /Doctor_Console` → 200.

## FE-4 Pipeline (core/pipeline.py): parse_typed, analyze, recheck, apply_resolution · Status: done
- Used: concurrent.futures (`read_prescription` and `read_strip` run in parallel, max 2 workers, matching the plan's limit of 2 concurrent Gemma calls), regex.
- Decisions:
  - **`parse_typed`:**
    - The frequency token is OD/BD/BID/TDS/TID/QID/SOS/HS/STAT, upper-cased into `dose_and_frequency`.
    - Strength is number+unit when there is a unit (`"625 mg"`), otherwise the bare number (`"650"`).
    - `brand_or_drug` is the text before the frequency or duration token, with "Tab/Cap/…" prefixes removed and turned into `form`.
    - Duration comes from "x 5 days" or "for 5 days".
  - **`analyze`:**
    - `analyze(..., on_step=None)` takes an optional progress callback, which is backward compatible with the contract.
    - ONE `assess_context` call covers every (med, candidate) pair. Fits are stored per med as `fits[candidate_name] = {fits, reason}`; an entry with no `candidate` key goes to the top candidate.
    - `confidence.score` gets the top candidate's fit. A med with no candidates is forced to LOW.
    - Status is HIGH → `auto`, otherwise `needs_confirmation`.
  - **Safety checks:** these run on every med, using the selected candidate or else the top-1, so a LOW Celemax still raises the penicillin/cephalosporin caution until a doctor corrects it.
  - **Strip:** `strip_check` gets `{label, salts}` from `match.candidates(strip brand, strip strength)[0]`, plus the extra keys `strength`, `raw_text` and `brand_or_drug`.
  - **Schedule:** if `safety.schedule(full freq)` returns nothing, the code retries with the bare frequency token.
  - **`_trace`:** the Gemma steps from llm, plus timed code steps (parse_typed, match.candidates xN, confidence.score, the safety bundle).
  - **Hindi fallback:** an English template when Gemma returns no summary.
  - **Error handling:** every external call is wrapped. Errors go to `case["errors"]` (shown as warnings) and never crash the page.
  - **`apply_resolution(case, i, resolution, by="doctor")`:** returns a deep copy and never mutates its input. `{"name"}` picks from the stored candidates; a name not in the list, or `{"free_text"}`, is re-matched with `match.candidates(text, read strength)`. If nothing matches, the typed name is used with no salts.
  - **`recheck`:** re-scores confidence from the stored fits (no Gemma), skips meds a human has decided, re-runs every code check, and sets `rechecked=True`.
- Files: core/pipeline.py, tests/test_pipeline.py
- Verified by:
  - `.venv/bin/python -m pytest tests/ -q` → `11 passed in 0.88s`, which covers `parse_typed` (spec example exact dict, multi-line, units/form/duration, no-freq), analyze typed, analyze photo+strip, and apply_resolution/recheck.
  - **Integration check against the REAL core modules** from `build/core` (match/confidence/safety plus data), in a scratch copy: all 11 tests pass. The 4-line demo prescription with the stub llm gives:
    - DUPLICATE paracetamol HIGH;
    - ALLERGY penicillin/Augmentin HIGH;
    - CROSS_REACTIVITY cefuroxime REVIEW;
    - savings ₹1045/month;
    - the expected schedule.
    After `apply_resolution(3, {"free_text": "Calcimax"})` and `recheck`, the med resolves to "Calcimax ISO Capsule (calcium carbonate + calcitriol)" and the cross-reactivity alert disappears.
  - The real `build/ai` `assess_context` signature and fit shape match the stub (`{"index","candidate","fits","reason"}`).

## Integration needed
- None required. app.py, the Doctor Console and the pipeline import only the contracted functions, and they work with both the stubs and the real `build/core` modules.
- Merge note: `.gitignore` already covers `app.db` and `cache/`. Uploads go to `cache/uploads/`.

## Blockers
- None.

## Suggested items
- **Demo risk for the core owner.** With the real `build/core`, "Dolo 650 TDS" comes out MEDIUM (0.85), not HIGH. The LASA rule finds "Spirodin 650 Tablet MR (doxofylline)" 10 points behind, because the shared "650" inflates the fuzzy score of a different-salt brand. Beat 3/4 would then show Dolo as MEDIUM. Consider scoring LASA rivals on the name without strength digits, or requiring the rival to share a first letter or a minimum name similarity.
- Celemax with the stub llm (fit=None) is MEDIUM (0.82). It reaches LOW only once real Gemma returns fit=no, so warm the demo cache and check beat 5 lands at 11:50 as planned.
- Optional: a "Reset case" button on the patient page for repeated demo runs. Re-clicking Analyze already clears the escalations.
