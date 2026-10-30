# AushNexa (TBD): build checklist

This file is the source of truth for what's built. Item IDs are stable; tests, bugs and the iteration log refer to them.
Mark an item `[x]` only when it is **verified**, not merely written.

Progress: MUST 14/16 · SHOULD 7/9 · Last updated 2026-10-30 11:45 by /hack-build (all 4 sections merged; 116 tests pass)

Legend: `[slice]` = part of the first thin end-to-end slice · `needs: X-n` = a dependency · (M) MUST · (S) SHOULD
Parallel sections: **1 Data and safety core**, **2 AI** and **3 UI** can run at the same time against the interfaces in docs/PLAN.md.

## 0 · Setup and repo

- [x] **SET-1** (M) [slice] Repo `code/aushnexa/`: skeleton (`app.py`, `pages/`, `core/`, `data/`, `scripts/`, `tests/`), `requirements.txt`, `.gitignore` (.env, app.db, cache/), `.env.example`, MIT LICENSE, README stub naming `gemma-4-26b-a4b-it`
  - Used: git, uv, Python 3.12
  - Decisions: Single Streamlit app; .env gitignored
  - Files: README.md, LICENSE, .gitignore, .env.example, requirements.txt
  - Verified by: Commit 233aa3b; `git check-ignore .env` ok

## 1 · Data and safety core (pure Python)

- [x] **DATA-1** (M) [slice] `scripts/build_data.py`: `updated_indian_medicine_data.csv` → `data/medicines.csv.gz` (active rows; base_name; salts as JSON `{salt, strength}`; desc of 300 characters)
  - Used: pandas
  - Decisions: Active allopathy rows only; salts parsed from short_composition1/2
  - Files: scripts/build_data.py, data/medicines.csv.gz
  - Verified by: 241,987 rows in 2 s; Dolo 650, Combiflam, Augmentin 625 Duo and Calcimax ISO spot-checked
- [x] **DATA-2** (M) [slice] `core/match.py` `candidates(name, strength, k=3)`: rapidfuzz, strength-aware, loaded once (cached)
  - needs: DATA-1
  - Used: rapidfuzz WRatio over base_name, lru_cache
  - Decisions: Strength boost +5; de-duplicated by salt_key
  - Files: core/match.py, tests/test_match.py
  - Verified by: pytest; 70–90 ms per call; see docs/build-runs/core.md
- [x] **DATA-3** (M) [slice] `core/confidence.py` `score()`, using the formula and bands in PLAN.md, with a breakdown dict. Group candidates by salt signature first. **LASA rule:** a different-salt rival within 12 points caps the band at MEDIUM, and with fit=no or unsure as well it becomes LOW
  - needs: DATA-2
  - Used: Formula from PLAN.md
  - Decisions: LASA needs a different salt within 12 points on BOTH the match score and the name-only similarity (fixes the Spirodin 650 false positive)
  - Files: core/confidence.py, tests/test_confidence.py
  - Verified by: pytest: Dolo 650 HIGH; Celcimax with rival ≤ MEDIUM
- [x] **SAFE-1** (M) [slice] `core/safety.py`: `duplicates()` (salt overlap, including inside combinations, and summing the strength per dose) and `allergy()` with `data/allergy_classes.json`, plus a penicillin → cephalosporin cross-reactivity REVIEW caution
  - Used: allergy_classes.json
  - Decisions: The duplicate detail sums the mg per dose; penicillin→cephalosporin gives a REVIEW
  - Files: core/safety.py, data/allergy_classes.json
  - Verified by: pytest; Test Lab cases 1–3
- [x] **SAFE-2** (M) `strip_check()`: MATCH / MISMATCH (strength) / NOT_PRESCRIBED
  - needs: DATA-2
  - Used: Salt and strength normalisation
  - Decisions: Same salts, different strength = MISMATCH
  - Files: core/safety.py
  - Verified by: pytest
- [x] **SAFE-3** (M) `jan_aushadhi()` with `data/jan_aushadhi.json` (about 12 salts, labelled indicative), plus a monthly ₹ saved figure
  - Used: jan_aushadhi.json (12 indicative salts)
  - Decisions: Source string on every entry
  - Files: core/safety.py, data/jan_aushadhi.json
  - Verified by: pytest
- [x] **SAFE-4** (S) `schedule(freq)`: OD/BD/TDS/QID/SOS/HS/AC/PC → slots
  - Used: Token regex
  - Decisions: Unknown → []
  - Files: core/safety.py
  - Verified by: pytest
- [x] **TEST-1** (S) `tests/test_safety.py` plus `core/testlab.py` with 4 preset cases (fever duplicate; penicillin vs Augmentin; sulfa vs HCTZ (Telma-H); a clean regimen with no alerts)
  - needs: SAFE-1
  - Used: pytest plus core/testlab.py
  - Decisions: 4 real-data cases
  - Files: core/testlab.py, tests/test_safety.py
  - Verified by: 4/4 pass; AppTest of the Test Lab page shows '4/4 passed'

## 2 · AI (Gemma 4)

- [x] **AI-1** (M) [slice] `core/llm.py`:
  - backend switch (`LLM_BACKEND` gemini|ollama);
  - `GEMMA_MODEL` default `gemma-4-26b-a4b-it`;
  - 3 retries with backoff;
  - disk cache keyed by sha256 of image + prompt + model;
  - JSON extraction;
  - `_trace` entries (model, seconds, cache_hit);
  - never raises.
  - Used: google-genai 2.34, requests (Ollama), Pillow
  - Decisions: Call-time backend; Semaphore(2); disk cache; GEMMA_TIMEOUT_S / GEMMA_BUDGET_S env overrides (defaults raised to 150/300 in .env)
  - Files: core/llm.py, tests/test_llm.py
  - Verified by: 16 offline tests; live: cache hit in 0.001 s; see docs/build-runs/ai.md
- [x] **AI-2** (M) [slice] `read_prescription(image)`: the spike prompt with fewer fields
  - needs: AI-1
  - Used: gemma-4-26b-a4b-it
  - Decisions: The model's own confidence is dropped
  - Files: core/llm.py, core/prompts.py
  - Verified by: Live on 62qlxpSw: 6/6 found, Oflox excluded, 82 s; the demo Rx read all 4 correctly in 92.5 s
- [x] **AI-3** (M) `read_strip(image)` (M) and `read_report(image)` (S, since the report photo is a SHOULD)
  - needs: AI-1
  - Used: gemma-4-26b-a4b-it
  - Decisions: read_report is a SHOULD (offline-tested only)
  - Files: core/llm.py, core/prompts.py
  - Verified by: Live strip read: 'PARACETAMOL TABLETS I.P.' 500 mg in 43 s
- [x] **AI-4** (M) `assess_context(context, meds)`: whether each medicine fits the condition (using the candidates' `desc`), plus a Hindi summary, with an English template fallback
  - needs: AI-1
  - Used: gemma-4-26b-a4b-it, one call per case
  - Decisions: A fit for each (med, candidate) pair; English fallback on failure
  - Files: core/llm.py, core/prompts.py
  - Verified by: Live 127 s: Celemax=no, Calcimax=yes; Hindi ok; the 504 fallback was seen live without an exception
- [ ] **AI-5** (S) Ollama backend verified with `gemma4:e4b` (the speed and output on one sample are recorded)
  - needs: AI-1
  - Used:
  - Decisions:
  - Files:
  - Verified by:

## 3 · UI (Streamlit)

- [x] **FE-1** (M) [slice] `app.py` Patient flow:
  - context (symptoms, allergies, optional report photo);
  - prescription (photo or camera or typed);
  - a progress state with elapsed seconds;
  - a medicines table with confidence band and breakdown;
  - alert cards (HIGH/REVIEW/INFO with text labels);
  - a disclaimer.
  - needs: DATA-3, SAFE-1, AI-2
  - Used: Streamlit 1.66
  - Decisions: Fourth status 'Picked by you' for MEDIUM self-picks
  - Files: app.py, core/pipeline.py
  - Verified by: AppTest typed flow; health check ok on :8599; see docs/build-runs/ui.md
- [x] **FE-2** (M) Doctor escalation:
  - `core/store.py` (SQLite);
  - an "Ask a doctor" button on MEDIUM/LOW rows;
  - `pages/2_Doctor_Console.py` (open list, chat, confirm a candidate or type a name);
  - live update through `st.fragment(run_every=3)`, then a re-run of the checks.
  - needs: FE-1
  - Used: SQLite (core/store.py), st.fragment(run_every=3)
  - Decisions: Escalation message from a template (no Gemma call); recheck re-runs code only
  - Files: core/store.py, pages/2_Doctor_Console.py, app.py
  - Verified by: AppTest: Ask a doctor → doctor confirms Calcimax → patient sees Confirmed; the cephalosporin alert disappears
- [x] **FE-3** (M) Strip upload → MATCH/MISMATCH card; a Jan Aushadhi table with ₹ saved; the Hindi summary
  - needs: FE-1, SAFE-2, SAFE-3, AI-3, AI-4
  - Used: pipeline + safety
  - Decisions: Jan Aushadhi labelled indicative
  - Files: app.py
  - Verified by: AppTest renders the strip, Jan Aushadhi and Hindi sections
- [x] **FE-4** (S) A pipeline trace expander (Gemma calls and code checks); a sidebar backend toggle (Gemini / Ollama)
  - needs: FE-1, AI-1
  - Used: Trace from llm plus code steps
  - Decisions: The sidebar radio sets LLM_BACKEND
  - Files: app.py, core/pipeline.py
  - Verified by: AppTest
- [x] **FE-5** (S) `pages/3_Test_Lab.py`: run the 4 cases, then a pass/fail table
  - needs: TEST-1
  - Used: Streamlit
  - Decisions: n/a
  - Files: pages/3_Test_Lab.py
  - Verified by: AppTest: 4/4 passed

## 3b · Voice symptom check (added 11:32 at the user's request; cut at 12:50 if it isn't solid)

- [x] **VOICE-1** (S) Voice → text: `st.audio_input` → faster-whisper (open source, local, Hindi + English) in `core/stt.py`
  - Used: faster-whisper 1.2 (base, CPU int8), WAV read directly
  - Decisions: A Devanagari prompt so Hindi comes out in Hindi script (otherwise Urdu or romanised)
  - Files: core/stt.py
  - Verified by: 1.87 s first transcription, then 0.54 s per clip; the `say` clip transcribed exactly; Hindi chest-pain test; see docs/build-runs/voice.md
- [x] **VOICE-2** (S) Triage in `core/triage.py`:
  - Gemma 4 gives possible causes (never a diagnosis), self-care advice and an urgency level.
  - **Code red-flag rules** (`data/red_flags.json`) can only raise the urgency.
  - EMERGENCY → call 108/112.
  - needs: VOICE-1, AI-1
  - Used: llm.generate_json + data/red_flags.json (14 rules)
  - Decisions: Code can only raise urgency; all-of rules; wildcard; negation; 'default' source when Gemma fails
  - Files: core/triage.py, data/red_flags.json, tests/test_triage.py
  - Verified by: Live: stomach pain → SEE_DOCTOR in 33 s; chest pain + sweating → EMERGENCY (rules + Gemma) in 32 s
- [x] **VOICE-3** (S) `pages/1_Symptom_Check.py`:
  - record or type the symptoms, then show the triage card;
  - a "Hospitals near me" Google Maps link;
  - "Ask a doctor", which reuses the store and the Doctor Console;
  - "Use as my prescription context", which pre-fills Step 1 of app.py.
  - needs: VOICE-2, FE-2
  - Used: Streamlit st.audio_input, link_button, store, st.fragment
  - Decisions: The Doctor Console handles symptom escalations (chat only)
  - Files: pages/1_Symptom_Check.py, app.py (pre-fill), pages/2_Doctor_Console.py
  - Verified by: AppTest for the page, the console and the pre-fill; 116 tests pass after the merge

## 4 · Demo and ship

- [ ] **DEMO-1** (M) The team's own demo assets:
  - a synthetic handwriting-font prescription with Dolo 650 TDS, Combiflam SOS, Augmentin 625 Duo BD and a messy Calcimax OD (beat 5 must land LOW);
  - a strip photo of paracetamol 500;
  - all run once, so the results are cached.
  - needs: FE-3
  - Used:
  - Decisions:
  - Files:
  - Verified by:
- [ ] **DOC-1** (M) README:
  - what it is;
  - the model `gemma-4-26b-a4b-it`;
  - architecture;
  - run steps;
  - data attribution (junioralive MIT dataset; Jan Aushadhi prices are indicative);
  - "built from scratch on 2026-10-30, concept from AushNexa";
  - what is mocked (a teammate plays the doctor);
  - the disclaimer.
  - Used:
  - Decisions:
  - Files:
  - Verified by:
