# TBD: ideas (Phase 2)

Written 2026-10-30 10:36 IST. About 3.4 h are left (deadline 14:00 IST), so this round used 4 problem statements, 3 ideas and all 3 shortlisted. There is no HTML board, because less than 24 h are left.

## Problem statements
- **PS-1 · Dense pages lock out students with dyslexia** (not chosen)
- **PS-2 · Lab reports nobody can read.** Patients and caregivers get lab reports full of jargon and can't tell what matters before the doctor visit. *(chosen)*
- **PS-3 · Prescriptions and medicine strips for elderly people.** Older adults and caregivers misread labels and handwritten prescriptions, which leads to dose mix-ups. *(chosen)*
- **PS-4 · Charts and diagrams on the web are inaccessible** (not chosen)

## Idea cards
| | A · LabLens | B · PillCheck | C · CareFolder |
|---|---|---|---|
| One-liner | A lab report photo becomes a value table, deterministic out-of-range flags, a plain-language explanation and questions for the doctor (EN/HI) | Photos of the prescription and the medicine strips go through a match check (drug, strength), then a large-font dose card. A mismatch means "confirm with your pharmacist" | Any health photo goes to a Gemma router, then the right tool, then one printable brief for the doctor visit |
| Demo moment | A blurry CBC photo becomes 2 red flags and 3 doctor questions | Prescription 500 mg against strip 650 mg gives a red MISMATCH card | 4 messy photos become 1 doctor brief |
| Gemma 4 use | Image input, function calling, thinking, multilingual output | Comparison of several images, handwriting reading, function calling | Routing through function calling, several images, image input |

## Score matrix
The judge's columns are taken unchanged from docs/reviews/ideate-judge.md (blind, FALLBACK rubric). The feasibility columns are scored by the main session using the skeptic findings. The total is 70% judge and 30% feasibility.

| Idea | Impact 25 | Innov 20 | Tech 20 | Gemma 15 | Demo 10 | Biz 10 | **Judge** | Buildable | Demo str. | Gemma depth | Novelty | **Feas. avg** | **Total** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **B · PillCheck** | 8 | 7 | 6 | 8 | 8 | 6 | **7.20** | 6 | 9 | 8 | 7 | **7.50** | **7.29** |
| A · LabLens | 7 | 5 | 8 | 7 | 7 | 6 | **6.70** | 8 | 6 | 5 | 4 | **5.75** | **6.42** |
| C · CareFolder | 8 | 6 | 4 | 9 | 7 | 6 | **6.65** | 3 | 7 | 8 | 5 | **5.75** | **6.38** |

Feasibility notes:
- **A:** the novelty is low. "LabLens AI" is a live Product Hunt product, and MedAssist, Wizey and the Gemma 4 hackathon builds Doclyst and CureNet do the same thing. The skeptic also says nothing here needs Gemma rather than Gemini.
- **B:** the skeptic found no consumer tool that checks the strips in hand against the prescription. Handwriting is the build risk: the MIRAGE study scored GPT-4o at about 7.6% F1 on Indian handwritten prescriptions.
- **C:** ChatGPT Health, Health Visit App and Mediscribe already exist. C is two products in about 2 h of build time.

## Skeptic verdicts
| Idea | Verdict | Strongest objection | Our answer |
|---|---|---|---|
| B · PillCheck | Serious | Handwriting accuracy is poor (MIRAGE: frontier VLMs score under 8% F1 on Indian handwritten prescriptions), and a wrong MATCH is dangerous | **"Gemma reads, code decides, uncertainty escalates."** Gemma gives each field a confidence or UNSURE, and plain Python decides MATCH, MISMATCH or UNSURE. The tool never says "safe". The main demo uses a clearly written or printed prescription, and a messy one shows UNSURE. |
| B · PillCheck | | Brand vs generic names (Dolo 650 = Calpol 650 = paracetamol 650) cause false alarms | A `brand_to_salt.json` of about 30 common Indian drugs, looked up through a `lookup_salt` function call |
| B · PillCheck | | Too much scope, and JSON output is unconfirmed | Drop the tablet-count check. Use 1 prescription against at most 2 strips. Get structured output through function-call schemas. Pre-record the demo |
| A · LabLens | Serious | It already exists (and the name is taken), and nothing needs Gemma | Not fatal, but no cheap answer within the time box |
| C · CareFolder | Serious | Over-scoped. Its best pitch is the cross-document check, which is B's core | Fold it into B as the story: "step one of a caregiver copilot" |

## Recommendation
**Build B · PillCheck**, scoped down as the skeptics suggest:
- **MUST:** a prescription photo plus 1–2 strip photos, read by `gemma-4-31b-it` (several images in one call). Function calls `lookup_salt` and `record_medication`. A Python matcher gives MATCH, MISMATCH or UNSURE. A red MISMATCH card, a large-font printable dose card, and a visible tool-call trace.
- **Pitch:** hospital barcode checks for the family kitchen table. Open weights mean a pharmacy or clinic could host it themselves.

**Backup: A · LabLens.** It is the fastest to build. Switch to it if the early Gemma test can't read strips or prescriptions reliably.

## Decision
2026-10-30 10:38 IST. The user chose to **build on the existing AushNexa project** (research/UQ8W59O1_TRIKΛΛL.pptx; live app at https://remix-remix-aushnexa-ai-prescription-safety-medic-9042.ai.studio/) rather than start a shortlisted idea. AushNexa already covers PillCheck's core (brand-to-salt mapping, duplicate-ingredient alerts, uncertainty flags), so the skeptic advice for B applies directly: Gemma reads, code decides, uncertainty escalates. The plan is to simplify the frontend, make it faster, and switch the AI to Gemma 4 through the Gemini API.
