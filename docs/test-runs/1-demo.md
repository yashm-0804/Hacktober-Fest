# Test run: Round 1 (demo path)

2026-10-30 12:24 IST · App: http://localhost:8501 (driven via streamlit.testing AppTest, APP_DB = scratch temp DBs; live app.db untouched) · Repo state: uncommitted (git sha not read)

Scripts and logs: /private/tmp/claude-501/-Users-yashmehta-Desktop-projects-Hacktober-Fest/9c986b07-685e-4f6d-b6d1-0d8f41b39bca/scratchpad/r1/ (demo.py, other.py, run1.log, run2.log, run3.log)
Note: run 1 alone; runs 2 and 3 ran in parallel with each other (shared Gemini quota), so their timings are slightly confounded. Beat 5 in run 1 escalated Augmentin (my script clicked the first Ask button); runs 2 and 3 escalated Calcimax.

## Coverage
- ✓ Beat 2: "Load demo case" fills context, allergies "penicillin", and loads both images (3/3 runs).
- ✓ Beat 3 (partial): Dolo 650 HIGH 1.0, Combiflam HIGH 1.0, Calcimax ISO MEDIUM 0.9 with look-alike reason (Calcimate-CL, 11 points apart). 3/3 runs identical.
- ✗ Beat 3: Augmentin 625 Duo is MEDIUM (0.80), not HIGH. See R1-2.
- ✗ Beat 3 timing: Analyze took 171 s / 117 s / 121 s, not "warm cache" seconds. See R1-1.
- ✓ Beat 4: HIGH DUPLICATE paracetamol (650 + 325 = 975 mg per combined dose) and HIGH ALLERGY penicillin vs Augmentin, 3/3 runs.
- ✓ Beat 5: Ask a doctor on Calcimax opens escalation #1; Doctor Console lists it ("line 4"), shows context, allergies, confidence reasons, candidates table (Calcimax ISO, Calcimate-CL Nasal Spray, Falcimax 50mg); confirming "Calcimax ISO Capsule" flips the patient row to confirmed_by_doctor on the next patient rerun (0.1 s), `rechecked=True`, new trace entries are only "recheck: confidence (no Gemma call)" and the safety step. No Gemma call. 2/2 runs (run 1 did the same for Augmentin).
- ✓ Beat 6: Strip check MISMATCH "Prescribed Dolo 650 Tablet (paracetamol 650mg) but strip is paracetamol 500mg", unchanged after confirmation. 3/3 runs.
- ✓ Beat 7: schedule table (4 rows), Hindi summary in Devanagari (not the English fallback), Jan Aushadhi table with "Indicative prices; verify at janaushadhi.gov.in" caption.
- ✓ Beat 8: Test Lab page "4/4 passed" (1.4 s). Sidebar backend radio "Gemini API / Local Ollama" exists. Trace table has model/backend/seconds/cache hit columns.
- ✓ Symptom Check "chest pain and sweating": red-flag error shown ("Chest pain or pressure can be a heart attack. Call 108 / 112 now.") plus EMERGENCY card "Call 108 (ambulance) / 112 now". The red-flag box renders before the Gemma call (code path run_check). Full Gemma triage took 33 s.
- ✓ No stack traces, raw JSON or "MOCK" text found in any rendered element (checked markdown/caption/error/warning/exception across 3 runs).
- – "Hospitals near me" link: present in code (pages/1_Symptom_Check.py line 139-162, prominent when red flags) but not asserted in rendered output (AppTest link_button not inspected). Not confirmed visually.
- – Photo shown in Doctor Console: image_path is saved in the DB (cache/uploads/<sha>.jpg) and the page calls st.image, but my AppTest could not count images. Unverified, not a bug.
- – Sidebar toggle to Local Ollama and the Gemini-live-app browser rendering: no browser available.
- – Hook (beat 1): no feature.

## Bugs
### R1-1 · P0 · on-path · Analyze takes 2-3 minutes with a "warm" cache because the assess_context call is never cached under the Gemini key
- Repro:
  1. `APP_DB=<temp> ` AppTest of app.py; click "Load demo case"; click "Analyze prescription" (rx and strip reads are cache hits at 0.03 s).
  2. Read `case["_trace"]`.
- Expected: Analyze is a few seconds with a warm cache (read_prescription, read_strip, assess_context all cache hits).
- Actual: `assess_context` goes live to Gemini every time. It got 500 INTERNAL, then 504 DEADLINE_EXCEEDED / ReadTimeout (~105-110 s), then falls back to local Ollama. Total 170.9 s, 117.1 s, 120.6 s. Run 2's local-fallback was a cache hit (0.007 s) and it still took 117 s, because the Gemini attempt is tried first and a successful fallback result is only stored under the ollama key, never the gemini key. So this will not warm up by repeating the demo while Gemini is erroring.
- Evidence (run1.log): `('assess_context','gemma-4-26b-a4b-it','gemini',1.119,False,"ServerError: 500 INTERNAL...")`, `('assess_context (attempt 2)', ..., 110.054, False, 'ReadTimeout: The read operation timed out')`, `('assess_context (local fallback)','gemma4:e4b','ollama',55.293,False,None)`. Run 2: `... (attempt 2) 109.213 ... 504 DEADLINE_EXCEEDED`, `(local fallback) 0.007 True`. Run 3: three Gemini failures (3.1 s, 6.0 s, 102.8 s) before the fallback.
- Frequency: 3/3 runs. (Gemini 500s/504s are external, but the demo has no protection: no pre-warmed Gemini-key cache for assess_context, per-attempt timeout ~110 s.)
- Note for debug: either pre-warm the assess_context cache for the demo case under the active backend, or on fallback also write the result under the primary key, and lower the per-attempt timeout.

### R1-2 · P1 · on-path · Augmentin 625 Duo shows MEDIUM (needs confirmation), not HIGH
- Repro: run the demo case (above); look at medicine 3.
- Expected: Dolo HIGH, Combiflam HIGH, Augmentin HIGH (storyline), Calcimax MEDIUM.
- Actual: Augmentin MEDIUM 0.80, status needs_confirmation, reason "Does not fit the patient's condition (−0.20)". Two "Ask a doctor" buttons appear (Augmentin and Calcimax), so the demo's "Ask a doctor on Calcimax" row is not the only one, and a judge sees a name match of 100/100 labelled MEDIUM. The penalty comes from the Gemma fit answer "no / Patient is allergic to penicillin" (the allergy is already the HIGH ALLERGY alert). Same result 3/3 runs, so it is deterministic given the fallback model's output.
- Evidence: `2 Tab. Augmentin 625 Duo ... -> Augmentin 625 Duo Tablet MEDIUM 0.8 needs_confirmation ['Best match: ... name match 100/100', "Does not fit the patient's condition (−0.20)"]`
- Frequency: 3/3 runs. May differ if Gemini answers (fit value came from the Ollama fallback in all three runs), so the HIGH in the storyline may have been seen only when Gemini was healthy.

### R1-3 · P3 · on-path · "Save about ₹1045/month" counts a drug the patient is allergic to and an SOS drug
- Repro: demo case; read the metric under the Jan Aushadhi table.
- Expected: a plausible, clearly indicative saving.
- Actual: `Save about ₹1045/month` includes Augmentin (HIGH allergy alert, "Do not take it") and Combiflam taken only SOS. The metric is labelled "Estimated savings" and the caption says indicative, but the figure is large and contradicts the allergy alert. Calcimax shows no generic ("not in our list" fallback).
- Evidence: `JA [...] 1045.21` in run1.log.
- Frequency: always.

### R1-4 · P3 · on-path · Hindi summary tells the patient what Augmentin is for and gives no allergy warning
- Actual: "Augmentin बैक्टीरिया के संक्रमण के लिए एंटीबायोटिक है।" with no mention of the penicillin allergy or the Dolo/Combiflam duplicate. Reads like an endorsement next to a HIGH allergy alert. Also names "Calcimax" as the final drug while it is still awaiting confirmation (before beat 5).
- Evidence: HINDI line in run1.log. Frequency: 3/3.

### R1-5 · P3 · on-path · Symptom Check Gemma triage 33 s
- "chest pain and sweating" -> red-flag text and EMERGENCY card immediately (code), but the status stays "Checking your symptoms with Gemma 4… Ns elapsed" for 33.0 s (trace `triage ... 33.04s`). Acceptable since the emergency shows first, but the status is still spinning during a live demo. Frequency: 1/1.

## Measurements
| Beat | Time |
|---|---|
| Initial page load (AppTest) | 0.5 s |
| Load demo case | <0.5 s |
| Analyze (run 1 / 2 / 3) | 170.9 s / 117.1 s / 120.6 s (see R1-1) |
| Ask a doctor click | <0.5 s |
| Doctor confirm -> patient card flips (rerun) | 0.1 s, no Gemma call |
| Test Lab 4 cases | 1.4 s |
| Symptom Check, red flag visible | immediate (code); full triage 33 s |

Side effects: AppTests wrote cache/uploads/<sha>.jpg (1 file, same hash each run) and may have added cache/llm entries for the fallback; the live app.db was not touched.
