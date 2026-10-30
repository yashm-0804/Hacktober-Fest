# Test run: 6 fresh-clone

2026-10-30 12:16 IST · App: http://localhost:8611 (stopped after the run) · Repo state: a5fcbab "README: Built with open source section" (clean clone, `git status` clean)

Clone: /private/tmp/claude-501/-Users-yashmehta-Desktop-projects-Hacktober-Fest/9c986b07-685e-4f6d-b6d1-0d8f41b39bca/scratchpad/fresh-clone

## Coverage
- ✓ `git clone`: 0.1 s, 44 tracked files.
- ✓ `uv venv --python 3.12 && uv pip install -r requirements.txt`: 1.1 s with a warm uv cache. A second install into a fresh venv with `--no-cache` took 5.5 s. No resolver errors. `import faster_whisper, rapidfuzz, google.genai, streamlit` works (streamlit 1.66.1). A real cold download on a judge's machine was not measured, and the Whisper weights download was not tested.
- ✓ `cp .env.example .env` plus the key copied in (key length 53, not the placeholder; never printed).
- ✓ `streamlit run app.py --server.port 8611 --server.headless true`: the server was listening in under 6 s. `/_stcore/health` returns `ok`. `/`, `/Symptom_Check`, `/Doctor_Console` and `/Test_Lab` all return HTTP 200. No Traceback or Error in the server log.
- ✓ AppTest (`run(timeout=120)`, `APP_DB` set to a temp file) on app.py and the 3 pages: 0 exceptions, 0 errors, each ran in 0.3 s or less. Titles render. Test Lab with the button clicked shows "4/4 passed".
- ✓ `python -m pytest -q`: 119 passed, 1 skipped, in 15.5 s on the first run and 9.7 s on the second. The skip is the live Gemma test (`set RUN_LIVE=1`). 120 tests collected.
- ✓ README files and links exist: core/llm.py, core/prompts.py, scripts/build_data.py, scripts/make_demo_assets.py, data/medicines.csv.gz, demo_assets/ (with the 2 fonts), LICENSE (MIT, matches the README), core/safety.py, core/match.py, tests/test_safety.py, tests/test_match.py. `.env.example` has every variable the README mentions (`LLM_BACKEND`, `WHISPER_MODEL`, `GEMMA_FALLBACK`).
- ✓ Model name: the default in core/llm.py:72 is `gemma-4-26b-a4b-it` and the local one is `gemma4:e4b`. Both match the README and `.env.example`.
- ✓ Brand count: `data/medicines.csv.gz` has exactly 241,987 data rows, matching the README's "241,987" (in two places). "242k" elsewhere is a fair rounding.
- ✓ "Built with open source" against requirements.txt. Every listed dependency is present: faster-whisper, rapidfuzz, streamlit, pandas, pillow, google-genai, pytest. Ollama is a runtime tool, not a pip dependency, and `requests` is used for it in llm.py:218. "At most 2 Gemma calls at once" is true (`threading.Semaphore(2)` in core/llm.py and `max_workers=2` in pipeline.py).
- ✓ No `/Users/` paths anywhere in the repo.
- – Not tested: real Gemma calls (RUN_LIVE), the Whisper download and transcription, the Ollama fallback, and the image upload flow. Out of scope and over the time limit.

Timings: clone 0.1 s · install 1.1 s (warm) / 5.5 s (`--no-cache`) · server up under 6 s · pytest 10–16 s · AppTest of all 4 pages under 1 s.

## Bugs
### R6-1 · P2 · on-path · README "Run it locally" never activates the venv
- Repro:
  1. Follow the README: `uv venv --python 3.12 && uv pip install -r requirements.txt`.
  2. Run the next steps as written: `streamlit run app.py` and `python -m pytest -q`.
- Expected: the README tells the judge how to reach the venv (`source .venv/bin/activate`, or `uv run streamlit run app.py`).
- Actual: `uv venv` only creates `.venv` and does not activate it. A judge without a global streamlit gets `command not found: streamlit`, or runs against the wrong Python. Neither `source .venv/bin/activate` nor `uv run` appears in the README. I ran everything through `.venv/bin/...`, so the app itself is fine.
- Evidence: README.md lines 34–38. `grep -n "activate\|uv run" README.md` returns nothing.
- Frequency: always, for anyone not already inside an activated venv.

### R6-2 · P3 · off-path · scripts/build_data.py defaults to a path outside the repo
- Repro:
  1. Run `python scripts/build_data.py` with no argument.
- Expected: a clear "source CSV required" message, or a README note that the default is outside the repo.
- Actual: `DEFAULT_SRC = ROOT.parent / "_data_src" / "Indian-Medicine-Dataset" / "DATA" / "updated_indian_medicine_data.csv"` (scripts/build_data.py, line 16) points one directory above the repo. The README does say to pass `path/to/updated_indian_medicine_data.csv` explicitly, so the documented path works. The silent default would fail with a file-not-found error. I did not run the rebuild, since the source CSV is not in the repo.
- Evidence: `grep -rnE "\.\./|_data_src" .` finds only this one hit.
- Frequency: always, for the no-argument case.

### R6-3 · P3 · off-path · README points to documents that are not in the repo
- Repro:
  1. Read README.md "How Gemma 4 is used", the last paragraph: "See the spike notes in the project docs."
- Expected: a link or file that ships with the repo, or no pointer.
- Actual: the cloned repo has no docs/ folder, so the pointer goes nowhere. The claim "21 of 21 medicines found, 19 of 21 names right first time" therefore has no evidence a judge can open. The "MIRAGE paper (arXiv 2410.09729)" reference is external and fine.
- Evidence: `git ls-files` lists 44 files and none are docs.
- Frequency: always.

### R6-4 · P3 · off-path · numpy is imported directly but not declared in requirements.txt
- Repro:
  1. `grep -n numpy core/match.py core/stt.py`.
- Expected: direct imports are declared, or the README says numpy comes in through pandas and faster-whisper.
- Actual: `import numpy as np` appears at core/match.py:14, but requirements.txt has no numpy line. It installs transitively through pandas, so there is no failure today. This is a fragility only.
- Evidence: requirements.txt lists streamlit, google-genai, rapidfuzz, pandas, pillow, requests, pytest and faster-whisper. The fresh install ran without error.
- Frequency: n/a, no failure observed.

### R6-5 · P3 · off-path · README gives no test count
- The README says "Covered by tests" but states no number, so there is nothing to contradict. Observed: 119 passed, 1 skipped (120 collected). If the deck or write-up quotes a test count, use these numbers.

No P0 or P1 bugs. The app runs from the README steps once the venv is reachable (R6-1).
