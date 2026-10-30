# Iteration log

A controlled improvement loop: a baseline, then one batch with verification and a blind re-score. Changes that don't clearly improve quality are reverted. Only the reviewer's scores appear in the scorecards.

Rubric: FALLBACK from HACKATHON.md · Target: none (the user set no rating goal; a single iteration was requested at 12:16)

---

## Baseline · 2026-10-30 12:20 IST

### What it currently does

AushNexa is one Streamlit app with four pages: Patient, Symptom Check, Doctor Console and Test Lab. The full demo path runs on real Gemma 4 output:
- prescription photo → Gemma 4 read → match against 241,987 Indian brands → HIGH/MEDIUM/LOW bands;
- duplicate-paracetamol and penicillin-allergy alerts, and a strip MISMATCH (650 vs 500 mg);
- doctor-chat escalation, dose schedule, Hindi summary and Jan Aushadhi savings.

There are 119 offline tests and all pass. A fresh clone installs and runs from the README (round 6).

A "cached" full demo run still took **111–158 s**: the Gemini `assess_context` call returned 504 after about 110 s before the local Gemma fallback answered. The doctor in the demo is a teammate, and the demo prescription and strip are synthetic; both are labelled.

### Strengths

- **Safety decisions are pure code, with Gemma as the reader.** Round 4 confirmed it: Gemma only feeds the fits and the Hindi text. The judge rated the split "thoughtful".
- **Real data at scale.** 241,987 brands (MIT); the judge's Impact score is 8.
- **Tested on real prescriptions.** 15 real ones exposed 4 wrong-HIGH matches, which are now fixed to 0 (docs/evidence).
- **Clean security and reproducibility.** No secrets or patient data in the repo or its history; parameterised SQL; pip-audit clean; the fresh clone runs.
- **Open-weights resilience.** An automatic local Gemma 4 fallback is verified (40 s prescription read, 9 s strip read).

### Weaknesses

| # | Weakness, and why it costs points | Severity |
|---|---|---|
| W1 | A full demo run stalls 110–160 s on the Gemini `assess_context` 504 before the fallback. That is a 2-minute spinner inside a 2-minute demo (Presentation, Technical) | Critical |
| W2 | The 8-beat storyline doesn't fit in 2 minutes (Presentation 6) | High |
| W3 | The README says "Calcimax vs Celemax" but the screen shows Calcimate-CL; the claim and the screen disagree (Presentation) | High |
| W4 | Gemma's condition fit counts the allergy, so Augmentin's *reading* confidence drops to MEDIUM, mixing identity with safety (Technical) | High |
| W5 | No buyer, pricing, channel or regulatory note (Feasibility 6) | Med |
| W6 | The README never activates the venv, so `streamlit run` fails as written (R6-1) | Med |
| W7 | Chat, context and Gemma text are rendered as markdown, so an image link makes the doctor's browser fetch a URL and fake "Doctor:" lines are possible (R4-1) | Med |
| W8 | The "21/21" handwriting claim has no evidence in the repo (R6-3) | Low |

### Baseline scorecard (blind, docs/reviews/1-test-judge.md)

| Criterion | Weight | Score |
|---|---|---|
| Impact and usefulness | 25% | 8 |
| Innovation and originality | 20% | 7 |
| Technical execution | 20% | 7 |
| Use of Gemma 4 | 15% | 8 |
| Presentation and demo | 10% | 6 |
| Feasibility and business viability | 10% | 6 |
| **Weighted** | | **7.20** |

---

## Iteration 1 · 2026-10-30 12:20 IST · 1.7 h left (freeze 13:15)

**Batch:**

| Item | Expected effect |
|---|---|
| W1 | Reuse a cached local-Gemma answer instead of waiting out another API timeout, and re-warm the demo, so a demo run takes seconds (Technical, Presentation) |
| W4 | The fit prompt ignores allergies, and a "fits" answer can't promote a reading to HIGH (Technical; also closes R4-2) |
| W3 + W8 | Accurate look-alike story in the README; the evidence files are shipped in the repo (Presentation) |
| W5 | A "Who pays / regulation" README section (Feasibility) |
| W6 | The README venv step (Technical/reproducibility) |
| W7 | Escape user and Gemma text before rendering it as markdown (security) |
| W2 | Not code: the 2-minute storyline is trimmed in /hack-ship (pitch and video script) |

**What changed:** 6a495cd (W1, W4, W3, W8, W6, numpy in requirements); the W5 and W7 commits follow below.
- 6a495cd: W1 (reuse a cached local-Gemma answer instead of waiting out another API timeout); W4 (the fit prompt ignores allergies; a "fits" answer can't promote to HIGH); W3/W8 (accurate look-alike story; evidence files in docs/evidence); W6 (README venv step); numpy listed
- 442b409: W7 (core/safe_md.py escapes chat, context, Hindi and triage text); W5 (README: who pays and regulation)
- 8a77810: R2-4, negation stops at clause breaks ("no fever, chest pain" now flags EMERGENCY)
- 4ff9d23: R2-3, matcher ranks the written brand word and written suffix words first ("Telma-H 40" → Telma H with HCTZ, not Telma 40); scores untouched, so the Calcimax look-alike is preserved

Measured after the batch: demo Analyze took 146.6 s on a cold cache (Gemini 504 at 110 s → local Gemma 36 s), then **0.7 s** on the second run (cached local answer reused). Augmentin is now HIGH. Tests: 119 → 125 passed.

**Bugs:**
- Fixed: R1-1 (P0 stall) = R2-1; R1-2 (P1 Augmentin MEDIUM); R2-3 (P1 Telma-H); R2-4 (P1 negation); R4-1/R4-2 (P2); R6-1, R6-3, R6-4.
- Still open: R2-2 (P1, off-path: "Crocin 500" → Rocin 500 at MEDIUM, because no Crocin 500 product is in the top fuzzy hits); R2-5/R2-6 (P2); R1-3/R1-4/R1-5, R2-7, R2-8, R4-3..6 (P3); Pan-D shown as Pan HD (identical salts).
