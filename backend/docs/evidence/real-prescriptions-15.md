# 15 real prescriptions: does Gemma 4 work? (2026-10-30, 11:41–12:07 IST)

Inputs: 15 real handwritten Indian prescriptions shared by a team member. The images, the hand-read answer key and the raw model output are **not** in this repo (patient privacy); only these aggregate findings are.

## Availability and speed
| | Gemini API · gemma-4-26b-a4b-it | Local Ollama · gemma4:e4b |
|---|---|---|
| Completed | **9/15** (6 failed: 504 or timeouts at 285–435 s) | **15/15** |
| Time per prescription | 17–162 s when it worked | **16–40 s** |

## Reading quality (on prescriptions with a reliable answer key)
| Prescription | Gemini API (26B) | Local (E4B) |
|---|---|---|
| rx10 block letters (4 meds) | 4/4 | 4/4 |
| rx14 clean psychiatry (5) | 5/5 | 4/5 (Rivotril → "Rivobit") |
| rx09 clean (4) | 4/4 names (Thyrox strength 50 vs my 75?) | 2/4 ("Thyrox Zomig", "Bplex fair") |
| rx01 messy (5) | 4/5 | 2/5 (Cital syrup → "Citalopram", flagged unsure) |
| rx11 "medical walo batao" (5) | timed out | 0–1/5, but 4 of 5 flagged unsure |
| rx13 messy (4) | timed out | 1/4 |
| rx15 eye drops (3) | timed out | 0/3 exact, 3/3 near-misses (Ajort/Azopt, Combogen/Combigan, Xalton/Xalatan) |
| **rx03 illegible scribble** | **0 medicines, nothing invented ✓** | **0 medicines ✓** |
| **rx08 sick-leave note, no Rx** | **0 medicines ✓** | **0 medicines ✓** |

Takeaways:
- **26B (API) reads well**: it was exact on clean handwriting and near-exact on messy writing. Its problem today was availability.
- **E4B (local) is fast and always available.** It is exact on neat writing but makes letter-level errors on messy writing. It is also overconfident on illegible writing (it rarely sets unsure).
- **Neither model invented medicines** on the scribble or on the note without a prescription.

## Did the safety layer catch the misreads? ("wrong but HIGH" = it skips the doctor)
| Run | Before fixes | After fixes (commits on main, 12:00–12:07) |
|---|---|---|
| API | 11 HIGH, **2 wrong** ("B-plex fort" → B Cillin CV Forte, an antibiotic; "Ravipool-D" → Acio D) | 9 HIGH, **0 known wrong** |
| Local | 9 HIGH, **2–3 wrong** ("pyrena red Ny" → Laxsafe-L; "P. Opor." → J P Flox OZ) | 7 HIGH, **0 known wrong** (Cefix unverified) |

Fixes found by this test:
1. Bracketed generics are ignored ("ATIVAN (Lorazepam)" had matched Tanzepam).
2. The written dosage form is preferred (SYP CALPOL → suspension).
3. The exact brand word is preferred (LEVOLIN, not Levolink).
4. **HIGH needs the name as written to look like the matched brand** (written-name similarity under 65 → LOW, under 80 → MEDIUM).

Everything else lands in MEDIUM (patient confirms from the top 3, or asks a doctor) or LOW (sent to a doctor).

## Dataset gaps seen
Zincovit and B-plex Forte are not in the 242k-brand dataset, so those rows correctly fall to MEDIUM/LOW.
