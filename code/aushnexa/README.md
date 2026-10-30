# AushNexa

**Explainable prescription safety for Indian brand medicines, built with Gemma 4.**

> **Model:** `gemma-4-26b-a4b-it` (Gemma 4, open weights) via the **Gemini API**. Optional local backend: `gemma4:e4b` on Ollama.

Indian prescriptions are handwritten and full of brand names. Two different brands can hide the same salt: Dolo 650 and Combiflam both contain paracetamol. A smudged letter can turn one real brand into another: in our handwriting test, Gemma once read *Calcimax* (a calcium supplement) as *Celemax*, a real antibiotic. In the demo, Calcimax is flagged because a different-drug look-alike, *Calcimate-CL* (a calcitonin nasal spray), sits right next to it in the brand list.

AushNexa reads the prescription, maps each brand to its active salts, and catches what a hurried eye misses. When it isn't sure, it asks a doctor instead of guessing.

**Gemma reads → code decides → a doctor confirms.**

> ⚠️ Supports medication review only. The absence of an alert does **not** mean a prescription is safe. This is not a substitute for a doctor or pharmacist.

## What it does

| Step | What happens | Who decides |
|---|---|---|
| 1. Patient context | Symptoms, conditions and allergies, typed in | n/a |
| 2. Read | Gemma 4 reads the prescription photo (handwriting included) and the medicine strip photo. Struck-out drugs are ignored, and unreadable items are marked *unsure* | **Gemma 4** (vision) |
| 3. Match | Each reading is fuzzy-matched against **241,987 real Indian brands**, and the top-3 candidates are shown with their salts | Code (rapidfuzz) |
| 4. Fit | One Gemma call judges whether each candidate fits the patient's condition | **Gemma 4** (text) |
| 5. Confidence | A score made of match strength, a look-alike/sound-alike (LASA) penalty, the strength check, Gemma's *unsure* flag and the condition fit. The result is a HIGH / MEDIUM / LOW band, with the reasons shown | Code |
| 6. Escalate | LOW items go to a **doctor chat**. The doctor sees the photo, the candidates and the context, replies, and confirms the medicine | **Human** |
| 7. Safety | Duplicate salts (also inside combinations), allergy class checks (penicillin → amoxicillin), penicillin → cephalosporin cross-reactivity, and a strip-vs-prescription strength mismatch | Code |
| 8. Patient output | Dose schedule, a Hindi summary, Jan Aushadhi generic equivalents and the ₹ saved per month | Gemma 4 + code |

There is also a **Symptom Check** page. You speak or type how you feel. **Whisper** (open source, running locally) transcribes it, and Gemma 4 suggests *possible* causes and an urgency level, never a diagnosis. Code warning-sign rules (chest pain, breathing trouble, stroke signs and so on, in English and Hindi) can only raise the urgency. EMERGENCY shows "call 108 / 112", and a **Hospitals near me** button opens Google Maps. The transcript can feed the prescription check.

There is also a **Safety Test Lab**: preset cases with expected alerts that run as a pass/fail suite, and also as pytest.

## Run it locally

```bash
uv venv --python 3.12 && uv pip install -r requirements.txt   # or: python -m venv .venv && .venv/bin/pip install -r requirements.txt
source .venv/bin/activate       # Windows: .venv\Scripts\activate
cp .env.example .env            # add your GEMINI_API_KEY from aistudio.google.com/apikey
streamlit run app.py            # patient app; the Doctor Console and Test Lab are in the sidebar
```

`data/medicines.csv.gz` is prebuilt. On first use, the Symptom Check downloads the Whisper `base` weights (about 140 MB); set `WHISPER_MODEL=small` for better Hindi. To rebuild it from the source dataset, run `python scripts/build_data.py path/to/updated_indian_medicine_data.csv`.

To use the local open-weights backend, run `ollama pull gemma4:e4b`, then choose "Local Ollama" in the sidebar (or set `LLM_BACKEND=ollama`).

To run the tests (with the venv active): `python -m pytest -q` (121 offline tests; set `RUN_LIVE=1` to also call Gemma).

## How Gemma 4 is used

- **Vision:** prescription and strip photos go to `gemma-4-26b-a4b-it` through `google-genai` (`client.models.generate_content` with an image part plus a prompt). See [core/llm.py](core/llm.py) and [core/prompts.py](core/prompts.py).
- **Reasoning:** one text call judges the condition fit for every (medicine, candidate) pair and writes the Hindi summary.
- **Guardrails:**
  - Gemma never makes a safety decision.
  - Gemma's own confidence is ignored (in our tests it was confidently wrong once).
  - "Never invent a medicine."
- **Latency:** Gemma 4 through the Gemini API took 39–210 s per image in our tests. Calls run in parallel (at most 2 at once), with retries, and responses are cached on disk by image hash. A doctor's correction re-runs only the code checks.

Our handwriting test on 5 real Indian prescriptions found 21 of 21 medicines, got 19 of 21 names right first time, invented none, and correctly skipped a struck-out drug ([evidence](docs/evidence/handwriting-spike-5-prescriptions.md)). A second test on 15 more real prescriptions found the matching bugs that let a wrong brand score HIGH; after the fixes, no known-wrong medicine scores HIGH, and an illegible scribble or a note with no prescription yields no medicines at all ([evidence](docs/evidence/real-prescriptions-15.md)).

## What's real and what's demo

| Part | Status |
|---|---|
| Gemma 4 calls, brand matching, safety checks | Real |
| Brand → salt data | Real: [junioralive/Indian-Medicine-Dataset](https://github.com/junioralive/Indian-Medicine-Dataset) (MIT) |
| Jan Aushadhi prices | **Indicative.** About 12 salts from the original AushNexa reference data. Verify at janaushadhi.gov.in |
| Doctor | A real human in the chat. **In the demo, a teammate plays the consultant** |
| Demo prescription and strip | **Synthetic** images generated by `scripts/make_demo_assets.py` (fictional doctor and patient) |

## Who pays, and the rules it lives under

- **First buyer: pharmacies and pharmacy chains.** A pharmacist already checks every prescription by eye. AushNexa is a second pair of eyes at the counter, with duplicate salts, allergies, strength mismatches and a Jan Aushadhi alternative in one screen. It could be priced as a per-store subscription. Clinics and telehealth apps are the second channel: the same checks run on e-prescriptions before they reach the patient.
- **Patients get the free tier:** the photo check, the Hindi summary and "Ask a doctor". That builds the habit that pharmacies and clinics then pay to support.
- **Regulation:** this is decision *support*, not diagnosis. Software that informs medication decisions may be regulated as a medical device in India (CDSCO's Medical Device Rules, 2017). A production version would need clinical validation, a pharmacist-reviewed drug dataset, and compliance with India's DPDP Act 2023 for patient data. The open-weights Gemma 4 option lets a clinic keep photos on its own machine.
- **Today it is a hackathon prototype.** No regulatory approval or clinical validation is claimed.

## Built with open source

| Component | What we use it for | License |
|---|---|---|
| **Gemma 4** (`gemma-4-26b-a4b-it` via the Gemini API, `gemma4:e4b` locally) | Reading prescriptions and strips, the condition fit, the Hindi summary, symptom triage | Open weights (reported as Apache 2.0) |
| [junioralive/Indian-Medicine-Dataset](https://github.com/junioralive/Indian-Medicine-Dataset) | 241,987 Indian brands → active salts and strengths: the base of every match and safety check | MIT |
| [Ollama](https://ollama.com) | Runs Gemma 4 locally, both as the "open weights" mode and as an automatic fallback when the API fails | MIT |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (OpenAI Whisper weights) | Local speech-to-text for the Symptom Check (English and Hindi) | MIT |
| [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | Fuzzy matching of handwritten readings against 242k brand names | MIT |
| [Streamlit](https://streamlit.io) | Patient app, Doctor Console, Symptom Check, Test Lab | Apache 2.0 |
| pandas, Pillow, google-genai SDK, pytest | Data, images, API client, tests | BSD / MIT-CMU / Apache 2.0 / MIT |
| Google Fonts: Reenie Beanie, Homemade Apple | Synthetic demo prescription | OFL / Apache 2.0 |

**What we add back:** we found no open-source **duplicate-salt checker for Indian brand medicines**. AushNexa's `core/safety.py` is one, and so is `core/match.py`, which matches brand to salt with look-alike/sound-alike detection. Both are MIT-licensed, dependency-light, and covered by tests (`tests/test_safety.py`, `tests/test_match.py`).

For example, Dolo 650 + Combiflam gives "paracetamol in both = 975 mg per combined dose", and Augmentin 625 Duo + Moxikind-CV 625 flags both amoxicillin and clavulanic acid.

Research that shaped the design (ideas, not code): the MIRAGE paper (arXiv 2410.09729) showed that off-the-shelf models read Indian handwritten prescriptions poorly, which is why AushNexa reads → matches → asks a human.

## Project history

The AushNexa concept (a prescription safety checker for Indian brand medicines) comes from team TRIKΛΛL's proposal at the MUJ Hypnexis hackathon (24–25 Oct 2026). **This codebase was written from scratch on 30 Oct 2026** for the Hacktoberfest 2026 "Best Use of Gemma 4" track. No code was reused.

## License

MIT (see [LICENSE](LICENSE)). Dataset: MIT (junioralive). Demo fonts: Reenie Beanie (OFL), Homemade Apple (Apache 2.0).
