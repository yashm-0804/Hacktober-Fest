# Build report: voice symptom check (build/voice)

2026-10-30 11:43 IST · Commits: fbfa5c8 (VOICE-1), f07ebeb (VOICE-2), c1f9ea0 (VOICE-3), e8a3acf (VOICE-1/2 Hindi fix)

Branch merges cleanly into current main: a scratch worktree of main plus build/voice gives `116 passed, 1 skipped` (scratch worktree removed afterwards).

## VOICE-1 core/stt.py `transcribe(wav_bytes) -> {"text", "language", "seconds", "error"}` · Status: done
- Used: faster-whisper 1.2.1 (ctranslate2 4.8.4, onnxruntime 1.31.1 for VAD, huggingface-hub 2.4.0), numpy, and the stdlib `wave` module. Model "base" (env WHISPER_MODEL), device cpu, compute_type int8, loaded once with `lru_cache`.
- Decisions:
  - **WAV is decoded with the stdlib `wave` module + numpy, not `faster_whisper.audio.decode_audio`.** The shared venv has PyAV 19.0.2, and with it decode_audio fails (`TypeError: open() got an unexpected keyword argument 'metadata_errors'`). `st.audio_input` always gives PCM WAV, and the code resamples to 16 kHz mono with `np.interp`. Non-WAV input still falls back to decode_audio and returns a clean error.
  - **Language:** `detect_language` is run, then the result is restricted to the more likely of en/hi. Unrestricted Whisper labels Hindi as Urdu.
  - **Hindi prompt:** when the language is hi, a Devanagari `initial_prompt` is passed. Without it, base output Hindi as Urdu script (`سینے میں درد`) or romanised text, which the Devanagari red-flag rules can't match. With it, the output is Devanagari.
  - `vad_filter=True` and `condition_on_previous_text=False`, so silence gives empty text and no hallucination.
  - It never raises. Empty, too-short and non-audio input each return an `error` string.
- Files: core/stt.py
- Verified by:
  - Pre-download: `WhisperModel('base', 'cpu', 'int8')` → `download+load base: 8.8s` (first time, includes the download). In a new process with the model cached, the first `transcribe` (load plus transcribe) took **1.87 s**, and warm calls took **0.54 s** on the 2.6 s clip.
  - English: `say` → `/tmp/claude-voice-test.wav` → `{'text': 'I have a headache and fever for two days.', 'language': 'en', 'seconds': 0.55, 'error': None}`
  - Hindi (`say -v Lekha "सीने में दर्द हो रहा है और पसीना आ रहा है"`) → `'सीने में दर्द हुर हा है आर पसीना आर हा है'`, language hi, 0.77 s, red flag `chest_pain` matched. Before the prompt fix it gave Urdu script and no flag.
  - Model comparison on the Hindi clips: `small` (load 23.3 s first time, about 1.5 s per clip) is cleaner (`'सीने में दर्द हो रहा है, और पसीना आ रहा है'`). Both base and small are now in the HF cache, so `WHISPER_MODEL=small` is a one-line switch if Hindi quality matters more than speed.
  - Tests: silence, empty, garbage and too-short input all return errors without raising; an 8 kHz WAV resamples to 16k; the Hindi speech regression test is skipped where macOS `say` is unavailable.

## VOICE-2 core/triage.py `triage(symptoms_text) -> dict` + data/red_flags.json · Status: done
- Used: google-genai 2.34 (fallback path only); `core.llm.generate_json` when present (it is on main now).
- Decisions:
  - **14 rules** in red_flags.json: chest pain, breathing, unconscious, stroke, worst headache, meningitis (stiff neck + fever), vomiting blood, black stools (URGENT), severe abdominal pain (URGENT), infant fever (URGENT, with a "<3 months → hospital now" message), seizure, suicidal (Tele-MANAS 14416), anaphylaxis, heavy bleeding. Each covers English, Hinglish, Devanagari and a few Urdu-script variants (whatever Whisper may output).
  - **Two small schema extensions:**
    - An optional `"all_of": [[group], [group]]`, used by meningitis and infant fever, so that "stiff neck" or "fever" alone does not fire.
    - A `"*"` wildcard for 0–3 words (`"pain in * chest"` matches "pain in my chest").
  - **Matching:** ASCII phrases match on word boundaries ("I am fit" does not match "fits"). Devanagari and Urdu phrases match as substrings, because `\b` breaks on combining vowel signs.
  - **Narrow English negation:** "no", "not", "without" and similar in the 2 words before a phrase suppress it ("no chest pain, just cough" → none), but "no fever but chest pain" still fires.
  - **urgency_source:** I added a 4th value, `"default"`, for the case where Gemma failed and no rule fired. Urgency is then SEE_DOCTOR and `error` says so.
  - Final urgency = max(rules, Gemma). Code only raises urgency. An invalid Gemma urgency is ignored.
  - Empty text makes no Gemma call. The patient text sits inside `<patient>` tags, and the prompt says to treat it as data.
  - Fallback (`# FALLBACK until llm.generate_json is merged`): a direct google-genai call with a 90 s timeout, one retry, its own .env loader, and the key redacted from errors. The import is `try/except ImportError`. Note: any ImportError inside core/llm.py (e.g. a missing core/prompts.py) also lands on the fallback, which still works.
- Files: core/triage.py, data/red_flags.json, tests/test_triage.py
- Verified by:
  - `.venv/bin/python -m pytest -q` → `53 passed` on the branch: 18 red-flag positives (English, Hinglish, Devanagari), 7 no-false-positive cases (including "mild headache", "I am fit and fine", "stiff neck" alone, "no chest pain"), the max-urgency logic with a monkeypatched Gemma (rules raise SELF_CARE→EMERGENCY; rules never lower Gemma's EMERGENCY; "both"), an invalid Gemma urgency, Gemma error and crash paths (red flags still give EMERGENCY; default SEE_DOCTOR with an error), and empty text.
  - Live, fallback path on this branch: `triage("I have had stomach pain and mild fever since yesterday")` → **33.1 s**, `SEE_DOCTOR` / `gemma`, causes Gastroenteritis, Food poisoning, Stomach infection; self-care ORS/rest/bland food; summary "The patient has been experiencing stomach pain and a mild fever since yesterday."
  - Live, fallback: `triage("chest pain and sweating")` → **32.5 s**, `EMERGENCY` / `both`, red flag chest_pain ("…Call 108 / 112 now. Do not drive yourself."), causes Heart-related issues, Acid reflux, Anxiety.
  - Live via **main's real `llm.generate_json`** (scratch copy): stomach case 33.3 s, SEE_DOCTOR/gemma. Chest case 35.6 s, EMERGENCY/both; its trace shows a Gemini `500 INTERNAL` on attempt 1, then success on attempt 2.

## VOICE-3 pages/1_Symptom_Check.py (+ small edits to app.py and pages/2_Doctor_Console.py) · Status: done
- Used: Streamlit 1.66.1 (`st.audio_input`, `st.status`, `st.link_button`, `@st.fragment(run_every=3)`, `st.switch_page`).
- Decisions:
  - **Input:** `st.audio_input` → transcribe once per recording (keyed by sha256) → an editable text area (key `sym_text`), which you can also type into directly. A caption shows "Heard in Hindi in 0.8s…".
  - **Instant warning signs:** "Check" runs the code red-flag rules instantly and shows them inside the status box *before* Gemma answers, since Gemma takes about 33 s. The status label shows the elapsed seconds.
  - **Banner:** a text label plus colour: EMERGENCY red "Call 108 (ambulance) / 112 now" with the matched red-flag messages; URGENT orange "See a doctor today"; SEE_DOCTOR amber; SELF_CARE green. It also shows the urgency source.
  - **"🏥 Hospitals near me"** (`st.link_button` to the Google Maps URL) is always shown exactly once: full-width primary under the banner for URGENT/EMERGENCY, a normal button otherwise, and also before any check.
  - **Results:** possible causes, each tagged "*possible, not a diagnosis*"; self-care; questions for the doctor; a trace expander.
  - **"🩺 Ask a doctor":**
    - It calls `store.save_case(context=transcript, allergies="", image_path=None, payload={"kind": "symptom_check", "transcript", **triage})`, then `open_escalation(case_id, -1, transcript, [], transcript)`, then a system message: `Symptom check: <URGENCY>. Patient says: "…". Red flags: …. Possible causes (AI, not diagnosis): ….`
    - The payload adds `kind` and `transcript` keys beside the triage JSON, so the console can render without guessing.
    - A chat panel follows, as `@st.fragment(run_every=3)`, the same as app.py.
  - **"Use as my prescription context →"** sets `voice_context` and calls `st.switch_page("app.py")`. app.py pops it into `ctx` once (2 lines after `ss_init()`), so later edits are not overwritten.
  - **Doctor Console:**
    - The open list labels med_index -1 rows as "🗣 Symptom check" (not "line 0").
    - Selecting one shows `symptom_view`: the transcript, urgency and source, red flags, possible causes and the patient's questions, then the chat.
    - There are no Confirm buttons. The old code path would have crashed with `meds[-1]` on an empty list.
  - Footer disclaimer, with 108/112 and Tele-MANAS 14416.
- Files: pages/1_Symptom_Check.py, pages/2_Doctor_Console.py (surgical), app.py (2 lines)
- Verified by (AppTest, inside pytest):
  - **Symptom Check flow:** the page renders without exceptions with the title "Symptom Check". Typing "chest pain and sweating" and clicking Check shows the EMERGENCY banner with "Call 108". Clicking Ask a doctor creates one open escalation with med_index -1, and its first message is a system message starting `Symptom check: EMERGENCY`.
  - **Doctor Console:** with a symptom escalation selected it renders without exceptions, shows "Symptom check" and EMERGENCY, and has no "Confirm…" buttons.
  - **app.py prefill:** `at.session_state['voice_context']='stomach pain…'` → the `ctx` text area holds that value, `voice_context` is removed, and it persists on rerun. No exceptions.

## New dependencies (main session: add to requirements.txt)
- `faster-whisper>=1.2.1` (pulls ctranslate2, onnxruntime, huggingface-hub, tokenizers). Already installed into the shared venv.
- `numpy` is already a transitive dependency (pandas).

## Integration needed
- requirements.txt: add `faster-whisper>=1.2.1`.
- .env.example (not mine): add `WHISPER_MODEL=base   # or "small": better Hindi, about 1.5 s/clip, 23 s first load`.
- README (not mine): mention that the first voice use downloads about 140 MB of Whisper base weights to `~/.cache/huggingface` (already cached on this machine for base and small).
- After merge, `core.llm.generate_json` is picked up automatically (verified). The fallback in triage.py can be deleted once main is merged, but it is harmless if left.

## Blockers
- None.

## Suggested items
- Doctor Console: a "Mark answered" button for symptom escalations. They currently stay in the open list, because there is no medicine to confirm.
- Optional: set `WHISPER_MODEL=small` for the demo if a Hindi voice clip is part of the storyline. It is noticeably more accurate (see the VOICE-1 timings).
- Gemma triage takes about 33 s. The UI shows red flags instantly and an elapsed-seconds spinner, but for the demo, pre-warm the exact demo phrase if llm's cache covers generate_json. The merged llm caches by prompt, so the second identical call should be instant.
