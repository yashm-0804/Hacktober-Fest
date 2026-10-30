# Judge review: AushNexa (product + 2-min demo storyline), "Best Use of Gemma 4" track

2026-10-30 12:21 · Rubric: FALLBACK (weights given in the prompt) · Blind: yes (no earlier reviews, iteration logs or test reports opened)

## What a 9 looks like in this track
- **Impact (25%)**: a real, painful, specific Indian problem, shown being solved on realistic input, with the user and the harm clear in 10 seconds.
- **Innovation (20%)**: a pattern judges haven't seen ten times today, not "chat with an LLM about X".
- **Technical execution (20%)**: the demo path runs end to end live, quickly, with tests and graceful failure.
- **Gemma 4 (15%)**: Gemma 4 does something only a multimodal open model can do here (handwriting vision, Hindi, local/offline), the model is named, and the integration is visible on screen.
- **Presentation (10%)**: one tight story, no dead air, every claim visible.
- **Feasibility (10%)**: a credible path to users and money, plus regulatory awareness.

## What I did
- Read README.md (model named: `gemma-4-26b-a4b-it` via Gemini API, `gemma4:e4b` via Ollama).
- `pytest -q`: **119 passed, 1 skipped in 9.5 s**.
- Ran `core.pipeline.analyze()` on `demo_assets/prescription.jpg` + `strip.jpg`, context.txt, allergy "penicillin", twice:
  - Run 1: **158.6 s**. Run 2: **110.9 s**.
  - Both prescription and strip reads were cache hits (0.06 s and 0.03 s).
  - But `assess_context` on Gemini hit **`504 DEADLINE_EXCEEDED` after 109.7 s**, then fell back to the cached local `gemma4:e4b` result.
- Outputs I saw:
  - Dolo 650 and Combiflam both HIGH.
  - Augmentin MEDIUM (needs_confirmation). Calcimax MEDIUM, with LASA rival **"Calcimate-CL Nasal Spray"**.
  - Alerts: DUPLICATE paracetamol "975 mg per combined dose" (HIGH) and ALLERGY penicillin → amoxicillin (HIGH).
  - Strip: **MISMATCH**, 650 mg prescribed vs 500 mg on the strip.
  - Hindi summary present and sensible. Schedule slots correct.
  - Jan Aushadhi savings **₹1,045.21/month**, flagged as indicative.
- Grepped the UI: "Ask a doctor" (app.py:336-339), "Confirmed by doctor" (app.py:40), call 108/112 and the Maps link (pages/1_Symptom_Check.py:15-17), a Test Lab with 4 preset cases, and a per-step trace table in app.py:415.
- I did **not** click through the Doctor Console round-trip, voice/Whisper or the Ollama toggle in a browser.

## Scorecard
| Criterion | Weight | Score /10 | Evidence |
|---|---|---|---|
| Impact and usefulness | 25% | 8 | Real problem with real data: 241,987 Indian brands → salts (MIT dataset). On the demo Rx it caught the duplicate paracetamol across Dolo + Combiflam, the penicillin → amoxicillin allergy and the 650 vs 500 mg strip mismatch. All three are harms that pharmacists actually see. |
| Innovation and originality | 20% | 7 | "Gemma reads → code decides → doctor confirms", plus LASA-aware confidence bands, is a thoughtful split: Gemma's own confidence is ignored, and HIGH needs the written name to match. Strip-vs-Rx cross-check is a nice touch. Duplicate-drug checkers themselves are not new (1mg/Practo-style checkers exist), so this is a 7, not a 9. |
| Technical execution | 20% | 7 | 119 tests pass, and the pipeline produced every promised alert on the demo assets. Retries, a disk cache and an Ollama fallback all exist and worked. Two problems: (1) **Gemini `assess_context` 504'd after ~110 s on both runs**, so a "cached" demo run still takes 110–160 s. (2) Augmentin's *identity* confidence drops to MEDIUM because the *clinical fit* is "no" (allergy), which mixes "did we read it right" with "is it safe". |
| Use of Gemma 4 | 15% | 8 | Gemma 4 vision reads handwriting and the strip label. Text Gemma does fit judgements, the Hindi summary and triage. The local `gemma4:e4b` acts as both a mode and an automatic fallback. The model is named in the README, and the trace table shows model and backend per step. One catch: in my runs the fit and Hindi came from **local Ollama, not the Gemini API**, because the API timed out. Judges who open the trace will see that. |
| Presentation and demo | 10% | 6 | The hook is strong (two brands, one salt). But the 8-beat storyline (including Doctor Console role-play, Ollama toggle, voice, Whisper, 108 and Maps) does not fit in 2 minutes, and there is a 110 s Gemma wait inside it. The README says the look-alike is "Calcimax and Celemax", but the app shows **Calcimate-CL Nasal Spray**, so the claim and the screen disagree. I didn't see a deck or video. |
| Feasibility and business viability | 10% | 6 | Free MIT data, Jan Aushadhi savings and a doctor-in-the-loop give a plausible wedge for pharmacies and telehealth. But there is no stated buyer, pricing or channel. Jan Aushadhi prices cover about 12 salts and are "indicative". There is no CDSCO/SaMD regulatory note. |
| **Weighted** | | **7.20** | 2.00 + 1.40 + 1.40 + 1.20 + 0.60 + 0.60 = 7.20, which is **0.80 below the 8.0 target** |

## What would raise the score (about 50 min left, ranked by points per hour)
1. **Kill the 110 s stall.** The failed Gemini `assess_context` result is never cached, so every run re-waits about 90–110 s before falling back. Two options:
   - Set `GEMMA_TIMEOUT_S`/`GEMMA_BUDGET_S` low for the demo session.
   - Or make a cached fallback result count as a hit for the demo inputs.

   Then confirm the full demo run finishes in under 5 s, and rehearse it once. → Technical execution +0.5, Presentation +1.0 (about **+0.30 weighted**), about 10 min.
2. **Cut the live story to 5 beats:** hook → photo read → duplicate + allergy alerts → Calcimax "Ask a doctor" → doctor confirms → strip MISMATCH. Give voice, Ollama, Test Lab and Hindi a single 10-second closing montage line. → Presentation +1.0 (**+0.10**), about 5 min.
3. **Fix the look-alike story.** Either get Celemax to surface as the rival (cefuroxime vs calcium is a far scarier miss), or change the README and pitch to say what the app actually shows. A nasal spray rival for an oral capsule is weak in front of a domain judge. → Innovation +0.5, Presentation +0.5 (**+0.15**), about 10–15 min.
4. **Add a 5-line "Who pays / path to market" section** to the README and pitch. Cover:
   - Jan Aushadhi Kendras and chain pharmacies as B2B;
   - telehealth as doctor-network revenue;
   - a SaMD/CDSCO "decision support, not diagnosis" note;
   - the 21/21 handwriting result, with the method stated.

   → Feasibility +1.5 (**+0.15**), about 10 min.
5. **Put the Gemma trace on screen during the demo**, using the app.py:415 table: each step with its model, seconds and cache hit, and the fallback labelled honestly ("Gemini API timed out → local Gemma 4 e4b answered"). Robust local fallback then becomes a feature rather than something a judge finds on their own. → Gemma use +0.5 (**+0.08**), about 5 min.

If all five land, the realistic ceiling is about 7.9–8.0. Changes 1–3 matter most.

## Red flags
- **"Their Gemma results are disk-cached, so a run is quick" is false for the full run.** Both of my runs took 110–160 s because the Gemini `assess_context` call times out (504) before the Ollama fallback answers. If Ollama isn't running on the demo machine, the fit step may fail outright. I didn't check that.
- **README claim vs screen:** "Calcimax and Celemax" vs the rival the app actually shows, "Calcimate-CL Nasal Spray".
- **Unverifiable claim:** "21 of 21 medicines on 5 real Indian prescriptions … see the spike notes in the project docs". The notes aren't in the repo, so the claim isn't reproducible from what was submitted.
- **Confidence semantics:** Augmentin is MEDIUM because of an allergy-driven "fit: no". A domain judge will ask why a perfectly read brand is "not confident". Label it as a safety hold, not low confidence.
- **The ₹1,045/month savings headline** rests on about 12 indicative Jan Aushadhi prices. It is labelled, but don't headline the number.
- **Doctor is a teammate:** disclosed in the README (good). Make sure it's said out loud in the demo too.
- **Over-scoped:** voice/Whisper (about a 140 MB first-run download), Maps, 108, the Test Lab and the Ollama toggle in a 6-hour build. I couldn't verify voice or the Doctor Console round-trip without a browser.
- **Hygiene:** `.env` is gitignored, and only `.env.example` is tracked. `cache/` is gitignored, so a fresh clone has no cached demo results and will make live calls (39–210 s each).

## How it compares
- **Typical submission (5–6):** above it. It has real data, real Gemma 4 vision on realistic input, deterministic safety checks with tests, honest "real vs demo" labelling, and alerts I watched fire.
- **Typical track winner (8–8.5):** short of it. The deciding factors are demo reliability and focus, not capability. A winner's 2-minute demo runs in seconds with one clean "wow" (the duplicate salt plus a scary look-alike caught and doctor-confirmed). This build currently risks a 2-minute spinner and a look-alike story that doesn't match the screen.
- Fix changes 1–3 and it is a credible finalist for the Gemma track.
