# AushNexa backend

The engine behind the AushNexa mobile app: a FastAPI REST API over a Python core that reads prescriptions with **Gemma 4**, matches every brand against 241,987 real Indian medicines, scores confidence, and runs deterministic safety checks.

> **Model:** `gemma-4-26b-a4b-it` (Gemma 4, open weights) via the **Gemini API**. Optional local backend: `gemma4:e4b` on Ollama.

## Run it

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
cp .env.example .env    # add your GEMINI_API_KEY from aistudio.google.com/apikey
```

```bash
.venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` lets a phone on the same Wi-Fi reach it. Interactive API docs are at `http://localhost:8000/docs`.

If the web app has been built (`cd ../mobile && npx expo export --platform web`, or just use `../run-website.sh`), the same server also serves it at `http://localhost:8000`, so the API and the website share one address.

`data/medicines.csv.gz` is prebuilt. The first transcription downloads the Whisper `base` weights (about 140 MB). For the local open-weights model, run `ollama pull gemma4:e4b` and switch to *Local Ollama* in the app's Settings (or set `LLM_BACKEND=ollama`).

### Configuration (`.env`)

| Variable | Default | What it does |
|---|---|---|
| `GEMINI_API_KEY` | none | Key for Gemma 4 on the Gemini API |
| `GEMMA_MODEL` | `gemma-4-26b-a4b-it` | Gemini API model |
| `LLM_BACKEND` | `gemini` | `gemini` or `ollama` (the app can switch it at runtime) |
| `OLLAMA_MODEL` / `OLLAMA_URL` | `gemma4:e4b` / `http://localhost:11434` | Local Gemma 4 |
| `GEMMA_FALLBACK` | none | `ollama`: retry a failed Gemini API call on the local model |
| `GEMMA_TIMEOUT_S` / `GEMMA_BUDGET_S` | 90 / 150 (`.env.example`: 150 / 300) | Per-attempt timeout and total budget per Gemma call, in seconds |
| `WHISPER_MODEL` | `base` | Whisper size; `small` is better for Hindi |
| `APP_DB` | `app.db` | SQLite file for cases and doctor chats |
| `CORS_ORIGINS` | `*` | Allowed origins for the web preview |
| `WEB_DIR` | `../mobile/dist` | Where the built website is served from |

## API

Slow work runs as a background job: `POST` returns `{"job_id"}` immediately, and the app polls `GET /api/jobs/{id}`, which lists each pipeline step as it happens.

| Method and path | Purpose |
|---|---|
| `GET /api/health` | Liveness, plus the active backend and model |
| `GET` / `PUT /api/settings` | Read the Gemma backend, or switch between `gemini` and `ollama` |
| `POST /api/analyze` | Start a prescription check. Multipart form: `context`, `allergies`, `rx_text` (typed lines win over a photo), `rx_image`, `strip_image`, `use_demo_images` |
| `GET /api/jobs/{id}` | Job status, steps and result (`{"case_id"}` for an analysis) |
| `GET /api/cases/{id}` | The full case (medicines, candidates, confidence, alerts, strip check, generics, schedule, Hindi summary, trace) and its doctor chats |
| `GET /api/cases/{id}/image` | The prescription photo, for the doctor |
| `POST /api/cases/{id}/meds/{i}/pick` | The patient picks a candidate for a *Please confirm* medicine. Code checks re-run |
| `POST /api/cases/{id}/meds/{i}/ask-doctor` | Open (or reuse) a doctor chat about one medicine |
| `POST /api/triage` | Start a symptom check. Warning-sign rules return instantly; the Gemma 4 result comes from the job |
| `POST /api/transcribe` | Speech to text with local Whisper. Accepts WAV, m4a (phones) and webm (browsers) |
| `POST /api/cases/{id}/ask-doctor` | Open a doctor chat about a symptom check |
| `GET /api/escalations?status=open` | The Doctor Console queue (`open`, `resolved` or `all`) |
| `GET /api/escalations/{id}` | One question with its messages, photo, candidates and confidence, or the triage |
| `POST /api/escalations/{id}/messages` | Send a chat message as `patient` or `doctor` |
| `POST /api/escalations/{id}/resolve` | The doctor confirms a candidate (`name`) or types the medicine (`free_text`). The patient's case is updated and re-checked |
| `GET /api/testlab` | Run the preset safety cases |
| `GET /api/demo`, `GET /api/demo/{file}` | The synthetic demo case and its images |
| `GET /` and any other non-API path | The website (`index.html` for app routes such as `/report`) |

**There is no authentication.** Anyone who can reach the server can read cases and answer as the doctor. Run it on a trusted network.

## How a prescription is checked

| Step | What happens | Who decides |
|---|---|---|
| 1. Context | Symptoms, conditions and allergies | n/a |
| 2. Read | Gemma 4 reads the photo (handwriting included) and the strip photo. Struck-out drugs are ignored; unreadable items are marked *unsure* | **Gemma 4** (vision) |
| 3. Match | Each reading is fuzzy-matched against 241,987 brands; the top 3 candidates come with their salts | Code (rapidfuzz) |
| 4. Fit | One Gemma call judges whether each candidate fits the patient's condition | **Gemma 4** (text) |
| 5. Confidence | Match strength, look-alike/sound-alike (LASA) penalty, strength check, the *unsure* flag and fit, giving HIGH / MEDIUM / LOW with reasons | Code |
| 6. Escalate | Unclear items go to a doctor chat; the doctor confirms the medicine | **Human** |
| 7. Safety | Duplicate salts (also inside combinations), allergy classes (penicillin → amoxicillin), penicillin → cephalosporin cross-reactivity, strip-vs-prescription strength mismatch | Code |
| 8. Output | Dose schedule, Hindi summary, Jan Aushadhi generics and ₹ saved per month | Gemma 4 + code |

Guardrails: Gemma never makes a safety decision, its self-reported confidence is ignored, and the prompts say "never invent a medicine". A Gemma failure degrades gracefully: the code checks still run and the case records which steps were skipped.

Evidence: on 5 real handwritten prescriptions Gemma 4 found 21 of 21 medicines and invented none ([details](docs/evidence/handwriting-spike-5-prescriptions.md)). A second test on 15 more found the matching bugs that let a wrong brand score HIGH; after the fixes, no known-wrong medicine scores HIGH ([details](docs/evidence/real-prescriptions-15.md)).

## Code map

| Path | What it is |
|---|---|
| `api.py` | FastAPI app: jobs, cases, doctor chat, triage, transcription |
| `core/pipeline.py` | `analyze()` (read → match → fit → score → check) and `recheck()` after a confirmation |
| `core/llm.py`, `core/prompts.py` | Gemma 4 on the Gemini API or Ollama: retries, time budget, disk cache, local fallback |
| `core/match.py` | Brand → salt candidates with look-alike-aware ranking |
| `core/confidence.py` | HIGH / MEDIUM / LOW scoring with human-readable reasons |
| `core/safety.py` | Duplicates, allergies, cross-reactivity, strip check, Jan Aushadhi, dose schedule |
| `core/triage.py`, `data/red_flags.json` | Symptom check: warning-sign rules (English and Hindi) plus Gemma 4 |
| `core/stt.py` | Whisper speech to text (WAV, m4a, webm) |
| `core/store.py` | SQLite store for cases, doctor chats and messages |
| `core/testlab.py` | Preset safety cases |
| `scripts/` | `build_data.py` (rebuild the brand table from the dataset), `make_demo_assets.py`, `warm_cache.py` (run the demo case once so the live demo comes from the Gemma cache) |

## Tests

```bash
.venv/bin/python -m pytest -q
```

134 offline tests cover the API flows, website serving, matching, confidence, safety rules, triage, the Gemma client (with faked backends) and audio decoding. Set `RUN_LIVE=1` to also call Gemma for real.

## Data

`data/medicines.csv.gz` is built from [junioralive/Indian-Medicine-Dataset](https://github.com/junioralive/Indian-Medicine-Dataset) (MIT). To rebuild it, download `DATA/updated_indian_medicine_data.csv` from that repository and run:

```bash
.venv/bin/python scripts/build_data.py path/to/updated_indian_medicine_data.csv
```

Jan Aushadhi prices in `data/jan_aushadhi.json` are indicative.
