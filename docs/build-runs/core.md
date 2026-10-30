# Build report: core (build/core)

2026-10-30 11:38 IST · Commits: b1a12f3, e6bc8d3, cfc7656, 160fb10, 4c2a9ee, e57b7cc

All contracts in the stub docstrings were kept exactly (signatures and return shapes). `jan_aushadhi()` adds two extra keys (`source`, `units`) on top of the contract. Full suite: `.venv/bin/python -m pytest -q` → `45 passed in 2.56s`.

## DATA-2 candidates(name, strength=None, k=3) · Status: done
- Used: rapidfuzz 3.14 (`process.cdist` + `fuzz.WRatio`), pandas, numpy. The data is loaded once (`lru_cache`).
- Decisions:
  - The query is normalised with the same FORM_WORDS as `scripts/build_data.py`, and punctuation is flattened on both sides ("glycomet-gp 1" == "glycomet gp 1").
  - **Short-name filter.** Names shorter than len(query)/1.5 are skipped. WRatio otherwise scores them 90 as a free partial match ("om" inside "combiflam", "c" inside "celemax").
  - **Letters-only cap.** The score is capped by WRatio of the letters-only parts. WRatio gives 85.5 to any name that shares one token ("650", "1", "duo"). Without the cap, "Dolo 650" ~ "Spirodin 650" counted as a LASA rival.
  - **Speed.** `cdist(names, [q], workers=-1)` runs WRatio on all cores. It gives the same scores as `process.extract`, about 2x faster. The top 200 hits are kept (the brief said about 60; more headroom after the cap).
  - **Strength handling.** +5 when a number in the strength appears in the name or the salt strengths. Ranking uses the uncapped score and the reported score is capped at 100, so with "Dolo" + "650mg" Dolo 650 Tablet beats Dolo Drops. When the strength number isn't in the name, a second pass searches "name + number".
  - Salt synonyms: amoxycillin→amoxicillin, acetaminophen→paracetamol, cephalexin→cefalexin, and others. Results are de-duplicated by salt_key and ties go to the closer plain edit ratio.
  - Helpers that confidence/safety reuse: `norm_salt`, `salt_key`, `parse_strength`, `same_strength`, `numbers`, `normalise_query`.
- Files: core/match.py
- Verified by: `.venv/bin/python -m pytest -q tests/test_match.py`. It covers Dolo 650→paracetamol, Combiflam→ibuprofen+paracetamol, Augmentin 625 Duo→amoxicillin+clavulanic acid, Telma-H, Glycomet GP 1, de-duplication, the contract keys, and latency < 300 ms.
  - Timings after warm-up: mean 73 ms, max 86 ms. With a separate strength (2 passes) it takes about 180 ms.
  - Actual output:
```
candidates('Celemax')
   90.0  Celemax 500mg Tablet  [cefuroxime]  ['500mg']  Rs260.0 strip of 4 tablets
   85.7  Ceremax Tablet  [piracetam]  ['na']
   85.7  Celemix Infusion  [sorbitol]  ['5% w/v']
candidates('Calcimax')
   90.0  Calcimax ISO Capsule  [calcitriol+calcium carbonate]  ['500mg', '0.25mcg']  Rs380.0 strip of 15 capsules
   84.0  Calcimate-CL Nasal Spray  [calcitonin (salmon)]  ['2200iu']
   80.0  Clinmax Gel  [clindamycin]  ['1% w/w']
candidates('Dolo 650')
  100.0  Dolo 650 Tablet  [paracetamol]  ['650mg']  Rs34.27 strip of 15 tablets
   85.5  Doloral P 100 mg/650 mg Tablet  [aceclofenac+paracetamol]
   85.5  Dolo-MF Junior Oral Suspension  [mefenamic acid+paracetamol]
```
  - **Calcium is not in the top 3 for "Celemax"** (it is for "Calcimax"). WRatio("celemax", "calcimax iso") is only 52.6, and no standard string scorer ranks it above Ceremax or Celemix. The LASA rule still fires for "Celemax", because Ceremax (piracetam) is 4 points behind. With fit=no the band is LOW (see DATA-3), so beat 5 ("real but wrong antibiotic, caught") still lands. The doctor sees the Ceremax and Celemix rivals, though, not Calcimax ISO.

## DATA-3 score(read, cands, fit) · Status: done
- Used: rapidfuzz `fuzz.WRatio` for name-only similarity, plus `core.match` helpers.
- Decisions:
  - The read strength counts as present only if *every* number in it appears in cands[0]'s name or salt strengths.
  - No candidates → value 0, LOW, with a reason.
  - fit is case-insensitive and "unclear" gives no adjustment.
  - **LASA rule, with the coordinator's fix (commit e57b7cc).** A different-salt_key candidate is a rival only if two conditions both hold:
    - (a) its fuzzy candidate score is within 12 of the top;
    - (b) its **name-only** similarity to the read text is within 12 of the top's name-only similarity. Name-only means WRatio after stripping form words, digits and strength units from both the read `brand_or_drug` (falling back to raw_text, then the top's base_name) and the candidate base_name.
    - So "Dolo 650" vs "Spirodin 650" no longer counts as a look-alike because of the shared "650". The penalty is stored in `breakdown["gap_penalty"]`. This replaces PLAN's older "gap < 5" rule, as the Review changes require.
  - match.py also caps each fuzzy score by its letters-only WRatio (commit 160fb10). That removes the same shared-number noise at the source.
- Files: core/confidence.py, tests/test_confidence.py
- Verified by: `pytest tests/test_confidence.py` (15 tests).
  - The coordinator's tests:
    - "Dolo 650" + Spirodin 650 at 92 → no rival, HIGH.
    - Real `candidates("Dolo 650")` → HIGH, no rival.
    - "Celcimax"/"Calcemax" read with [Celemax 500mg Tablet, Calcimax ISO Capsule] → rival = Calcimax ISO, band MEDIUM; with fit=no → LOW.
  - The tests also cover the unsure/strength penalties, fit no, LASA + unsure → LOW, a rival outside the window, clamping and no candidates.
  - **Behaviour change to note for beat 5.** An *exact* read of "Celemax" against real data no longer has a rival. Ceremax is 85.7 name-only vs 100 for Celemax, which is 14 points apart. So:
    - fit=no → `0.70 MEDIUM` (it was LOW before the fix);
    - fit=no plus unsure → `0.50 LOW`.
    - A LASA rival appears only when the read text sits *between* two brands, e.g. "Celcimax" (Celemax 500 vs Calcimax ISO). Real `candidates("Celcimax")` currently returns Clinmax Gel 80, Calcimax ISO 78.8, Acecomax 75. It does not include Celemax.
  - Real bands with no fit after the fix:
    - HIGH 1.0: Dolo 650, Combiflam, Augmentin 625 Duo, Telma H, Atorva 20, Azithral 500.
    - MEDIUM because of a LASA rival: Ecosprin 75 (vs Ecosprin-AV 75), Glycomet-GP 1 (vs Bala GP), Calcimax with fit=yes (vs Calcimate-CL).

## SAFE-1 duplicates / allergy · Status: done
- Used: stdlib. Class data is in data/allergy_classes.json.
- Decisions:
  - **Allergy data and matching.** data/allergy_classes.json holds `classes` (salts, caution_salts, aliases) plus a `cross_reactivity` list. A keyword matches a salt name as a whole word, so "cefuroxime axetil" is caught.
  - **Alert levels.** Every match produces one alert per (med, salt):
    - A directly named salt → HIGH ALLERGY.
    - A salt in an allergic class → HIGH ALLERGY.
    - A caution salt → REVIEW ALLERGY. Hydrochlorothiazide, furosemide, chlorthalidone, indapamide, torsemide, acetazolamide and celecoxib are caution salts under sulfa.
    - A class-mate of a named salt → REVIEW CROSS_REACTIVITY.
    - Penicillin plus a cephalosporin → REVIEW CROSS_REACTIVITY ("about 1–2% cross-reactivity; confirm with doctor").
  - Free text is accepted ("Penicillin", "sulfa drugs", "NSAIDs").
  - Duplicates sum mg only when every strength parses as mg (1 g counts as 1000 mg).
- Files: core/safety.py, data/allergy_classes.json
- Verified by: `pytest tests/test_safety.py`. The duplicate detail is exactly "Paracetamol in Dolo 650 Tablet (650mg) and Combiflam Tablet (325 mg) = 975 mg per combined dose. …". The tests also cover penicillin/amoxicillin → HIGH, penicillin + cefuroxime → REVIEW CROSS_REACTIVITY, sulfa + Telma H → REVIEW ALLERGY, NSAIDs, and no false alerts.

## SAFE-2 strip_check · Status: done
- Decisions:
  - An identical salt set with all strengths equal → MATCH. A missing strength on either side counts as equal.
  - An identical salt set with a strength that differs → MISMATCH.
  - A partial salt overlap → MISMATCH.
  - No shared salt → NOT_PRESCRIBED.
  - When several meds qualify, the best status wins.
- Files: core/safety.py
- Verified by: tests. The detail is exactly "Prescribed Dolo 650 Tablet (paracetamol 650mg) but strip is paracetamol 500mg." "650 mg" matches "650mg".

## SAFE-3 jan_aushadhi / monthly_savings · Status: done
- Decisions:
  - **The 12 entries.** data/jan_aushadhi.json holds exactly the 12 listed entries, keyed `salt_key|strengths` and carrying the given source string.
  - **Matching.** A med matches on salt_key, and on strength when the med has one.
  - **Unit price.** The brand unit price = med price / pack count when both exist. Otherwise it falls back to brand_prices[i]: divided by the pack count when the med has a pack, else taken as a per-unit price. ml packs give no count.
  - **Savings.** Units/day = len(schedule(freq)) or 1, over 30 days, summing only positive differences.
- Files: core/safety.py, data/jan_aushadhi.json
- Verified by: tests. Dolo 650 TDS + Augmentin BD = ₹1030.14/month, which matches the hand calculation (79.62 + 950.52). Celemax gives None and paracetamol 500mg gives None.

## SAFE-4 schedule · Status: done
- Decisions:
  - Matching is case-insensitive on whole words anywhere in the string.
  - The rules are checked in order: QID, TDS/TID, BD/BID, OD/QD, HS, SOS/PRN.
  - It also understands "twice/thrice/once daily" and the Indian "1-0-1" notation.
- Verified by: tests ("1 tab TDS after food" → 3 slots, "take with food" → []).

## TEST-1 pytest + core/testlab.py · Status: done
- Files: tests/test_match.py, tests/test_confidence.py, tests/test_safety.py, core/testlab.py
- Verified by: `run_cases()` → 4/4 passed on real data:
  - Dolo 650 Tablet + Combiflam Tablet → HIGH DUPLICATE paracetamol.
  - Augmentin 625 Duo Tablet + penicillin → HIGH ALLERGY.
  - Telma H Tablet + sulfa → REVIEW ALLERGY "Caution: hydrochlorothiazide with sulfa (sulfonamide) allergy".
  - Atorva 20 + Ecosprin 75 + Glycomet-GP 1 Tablet PR → no alerts.
  - A case that raises an exception is reported as a failure rather than crashing the page.

## FE-5 pages/3_Test_Lab.py · Status: done
- Decisions: the results are kept in session_state. The page shows a "✅ PASS"/"❌ FAIL" column and a summary through st.success/st.error.
- Verified by: `PYTHONPATH=. python -c "AppTest.from_file('pages/3_Test_Lab.py').run(); click"` → title "Safety Test Lab", success "4/4 passed", all four rows ✅ PASS, no exceptions.

## Integration needed
- None required. Callers should note:
  - `jan_aushadhi()` also returns `source` and `units`.
  - `monthly_savings` reads the optional med keys `price` (pack price) and `pack`. Pass the candidate's `price`/`pack` into the resolved med.
  - `run_cases()` loads the 242k-row CSV on first use (about 0.5 s).

## Blockers
- None.

## Suggested items
- **Beat 5 needs a decision (11:50 demo check).** With the name-only LASA rule, an exact "Celemax" read with fit=no is MEDIUM, not LOW. Two options to make it land:
  - (a) make the demo read come out unsure, or slightly off (e.g. "Celcimax"), so the rule fires;
  - (b) add a curated LASA-pair list (celemax↔calcimax) in match.py that injects the paired brand into the candidates and treats it as a rival regardless of score.
- The demo asset for beat 5: "Celemax" does not surface Calcimax ISO in the top 3 (WRatio 52.6). If the demo needs the doctor to see Calcimax as an option, add a small curated LASA-pair list (e.g. celemax↔calcimax) that injects the paired brand into the candidates.
- Glycomet-GP 1 lands at MEDIUM because of a weak rival (Bala GP, 85.5). A per-token rival check could tighten the LASA rule if this shows in the demo.
