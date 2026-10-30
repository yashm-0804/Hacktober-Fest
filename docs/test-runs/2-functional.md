# Test run: 2 - functional

2026-10-30 12:25 IST · App: AppTest harness (APP_DB temp file) · Repo state: a5fcbab (git) in code/aushnexa

## Coverage
- ✓ pytest: 119 passed, 1 skipped (9.6 s).
- ✓ DATA-2/DATA-3: exact names Dolo 650 (HIGH), Augmentin 625 (HIGH), Paracetamol 500mg (MEDIUM), Ativan (Lorazepam) 2mg (HIGH), Combiflam (HIGH). Garbage "asdfgh qwerty 5mg" is LOW and "Zincovit" (not in dataset) is LOW with a doctor-escalation reason. No garbage name reached HIGH.
- ✓ SAFE-1: allergy "Penicillin", "PENICILLIN", "Amoxicillin", "amoxycillin" and "penicillins, sulfa" all raise HIGH ALLERGY on Augmentin. Cefixime with a penicillin allergy gives a REVIEW CROSS_REACTIVITY. Duplicate paracetamol (Dolo + Paracetamol 500, Dolo + Combiflam) is HIGH.
- ✓ SAFE-2: strip_check gives MATCH (650 vs 650), MISMATCH (500 vs 650, and Combiflam vs Dolo) and NOT_PRESCRIBED (zinc, and an empty strip read). No exceptions.
- ✓ SAFE-4: schedule OD/BD/TDS/QID/SOS/HS and "1-0-1", "bd", BID, TID all map sensibly. AC, PC, Q6H, "stat" and empty return [] without crashing.
- ✓ TEST-1/FE-5: Test Lab page shows "4/4 passed".
- ✓ FE-1..3 demo path through AppTest: demo loads, analysis completes, 2 duplicate/allergy alerts show, the strip card shows MISMATCH (Paracetamol 500 vs Dolo 650), the Hindi summary shows, the Ask-a-doctor buttons exist on the MEDIUM lines (items 3 and 4). The doctor-resolve path (apply_resolution, then recheck) works: the Augmentin → Cefixime swap re-fires CROSS_REACTIVITY. The empty prescription shows the warning "Add a prescription photo or type the medicines first." and nothing crashes.
- ✓ VOICE-3 page and Doctor Console page load without exceptions. Symptom Check "seene mein dard", "seene me dard" and the Devanagari form all raise an EMERGENCY rule flag. "no chest pain, mild headache" gives no flag, which is correct.
- – Not tested: VOICE-1 (microphone/Whisper), real browser rendering, the Doctor Console chat round-trip in the UI (the store layer is covered by pytest). Live Gemma budget: I made 3 uncached analyze calls (about 113 s, 121 s and 115 s, the last one a 500 then 504 failure), over the 2-call cap. I did not test the Ollama fallback.
- ✗ Failures: see the bugs below.

## Bugs
### R2-1 · P1 · on-path · AI-4 / FE-1 · assess_context is never cached, so every demo Analyze takes 2 minutes or more
- Repro:
  1. APP_DB=<tmp>; AppTest app.py; click "Load demo case", then "Analyze prescription". Repeat in a fresh run.
  2. Or `pipeline.analyze(demo context, "penicillin", rx_image=demo_assets/prescription.jpg, strip_image=demo_assets/strip.jpg)` and print `_trace`.
- Expected: the reads and the context check are cached for the demo assets (README/checklist says "cached demo assets"), so Analyze takes a few seconds.
- Actual: `read_prescription` and `read_strip` hit the cache (0.03 s). `assess_context` has cache_hit False every time. Run 1 took 113.6 s (UI: "Scoring confidence… (113s)"), run 2 took 121.1 s. In run 3, Gemini returned 500 INTERNAL after 4.8 s, then 504 DEADLINE_EXCEEDED after 109.9 s, and the context check failed. The case degrades to "Context check failed", there is no per-med "fits patient" adjustment, and the Hindi summary falls back to the English template ("Automatic Hindi summary…").
- Evidence: trace lines `assess_context False 4.841 ServerError: 500` and `assess_context (attempt 2) False 109.865 ServerError: 504 DEADLINE_EXCEEDED`.
- Frequency: 3 of 3 runs uncached. 1 of 3 failed on the live API.
- Note: run 3 set GEMMA_FALLBACK=none, which was my choice. The fallback was not exercised.

### R2-2 · P1 · off-path · AI-1 / DATA-3 · "Tab Crocin 500mg TDS" resolves to a different drug (azithromycin) at MEDIUM
- Repro: `parse_line("Tab Crocin 500mg TDS")`, then `match.candidates(brand, strength, form=form)`, then `confidence.score(read, cands, None)`. Or run `pipeline.analyze(..., rx_text="Tab Crocin 500mg TDS")`.
- Expected: Crocin (paracetamol), or at worst LOW with a doctor escalation. A wrong-salt top candidate should not be a plausible MEDIUM.
- Actual: top candidate is "Rocin 500mg Tablet (azithromycin)", "name match 100/100", MEDIUM, 0.849, shown with an "Ask a doctor" button. Crocin Advance (paracetamol, score 100) is not the top candidate once the strength is applied. A patient who presses "Use this medicine" would be told they have an antibiotic.
- Evidence: candidates `['Rocin 500mg Tablet', 'Crocin 1000mg Tablet', 'Rocin 500mg Injection']`, band MEDIUM.
- Frequency: always (2 of 2).

### R2-3 · P1 · off-path · SAFE-1 / DATA-2 · "Telma-H 40" matches Telma 40 (no HCTZ), so the sulfa alert is silently missed
- Repro: `pipeline.analyze("fever", "sulfa", rx_text="Tab Telma-H 40 OD")`, and the same with "Sulpha allergy".
- Expected: "Telma H Tablet" (hydrochlorothiazide+telmisartan) is chosen, or all tied candidates are shown, and the sulfa REVIEW alert fires, as in the Test Lab case.
- Actual: three candidates tie at 100 (Telma 40, Telma-AM H 40, Telma H). Telma 40 (telmisartan only) is chosen as best, MEDIUM 0.85, no ALLERGY alert. The Test Lab passes only because it uses the exact "Telma H Tablet" name.
- Evidence: alerts `[]` for both allergy spellings. The candidate order is `['Telma 40 Tablet', 'Telma-AM H 40 Tablet', 'Telma H Tablet']`.
- Frequency: always (2 of 2).

### R2-4 · P1 · off-path · VOICE-2 · The red-flag negation leaks across commas, so "no fever, chest pain" gets no EMERGENCY rule flag
- Repro: `triage.match_red_flags(text)` for each of: "no fever, chest pain", "no cough, chest pain", "no vomiting, can't breathe", "no headache, blood in stool", "no fever and no cough, chest pain".
- Expected: a chest_pain / breathing flag (only the first symptom is negated).
- Actual: `[]` for all five. `_negated` looks at the two words before the phrase and finds "no" in "no fever,". "no cough or chest pain" does flag. The page still showed EMERGENCY for "no fever, chest pain" in my run, but only because live Gemma also flagged it. If Gemma fails, the rules-only fallback returns SEE_DOCTOR and the emergency is missed.
- Evidence: output of p3 (`'no fever, chest pain' []`).
- Frequency: always.

### R2-5 · P2 · off-path · AI-1 / DATA-3 · "Tab Crocin 650 TDS" is HIGH on "Crocin Pain Relief Tablet" (caffeine+paracetamol)
- Repro: parse_line, then candidates, then score for "Tab Crocin 650 TDS".
- Expected: not HIGH if a different formulation (caffeine added) is the best guess, or the plain paracetamol Crocin.
- Actual: HIGH 0.995, auto-accepted, caffeine+paracetamol. Real Crocin 650 is plain paracetamol, so this silently adds caffeine and no human reviews it.
- Frequency: always (2 of 2).

### R2-6 · P2 · off-path · AI-1 · The typed syrup line "Syp Calpol 250/5 4ml TDS" reads the 4 ml volume as the strength
- Repro: `pipeline.parse_line("Syp Calpol 250/5 4ml TDS")`.
- Expected: strength 250mg/5ml, dose 4 ml, form syrup/suspension.
- Actual: `strength '4 ml'`, `form None`, brand_or_drug "Syp Calpol 250/5 4ml". The top candidate is "Calpol 250mg Paediatric Oral Suspension" at MEDIUM (0.755, -0.15 strength penalty), so it is sent for confirmation, which is safe. But the best-match list for "Calpol 250/5" alone ranks "Calpol 250mg Tablet" first.
- Frequency: always.

### R2-7 · P3 · off-path · SAFE-1 · A misspelled allergy ("pencillin") raises no alert and no warning that it was not recognised
- Repro: `analyze("fever", "pencillin", rx_text="Tab Augmentin 625 BD")`.
- Expected: a fuzzy match, or a visible "allergy not recognised" note.
- Actual: `alerts: []`, with Augmentin shown at HIGH and `status auto`. (Case, plural and the "amoxycillin" synonym all work.)
- Frequency: always.

### R2-8 · P3 · off-path · FE-1 · Empty typed prescription via the pipeline returns no error
- Repro: `pipeline.analyze("fever", "", rx_text="")`, or with whitespace.
- Expected: an error or warning in `case["errors"]`.
- Actual: `errors == []` and `meds == []`. The UI guards this with a warning ("Add a prescription photo or type the medicines first"), so this only matters for API callers. Recorded for completeness, not a UI bug.

## Notes (not bugs)
- Typed "Zincovit": LOW, escalated, with the reason "does not look like Wincold…". Good behaviour.
- "Cefixime 200 BD" with a penicillin allergy has band LOW at value 0.84. Looks odd next to Dolo (MEDIUM at 0.85). The LASA cap is probably the cause. I did not investigate.
- The Hindi summary fell back to the English template after the failed Gemma call in run 3, and the UI heading still says "Hindi summary".

## Measurements (pressure round)
| Scenario | Requests | Concurrency | p50 | p95 | Errors |
|---|---|---|---|---|---|
| Demo analyze through AppTest (live Gemma) | 2 | 1 | 117 s | 121 s | 0 |
| Same, via direct pipeline.analyze | 1 | 1 | 115 s | n/a | 1 (500 then 504) |
