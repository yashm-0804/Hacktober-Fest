# AushNexa: feature inventory

Written 2026-10-30, about 10:42 IST. Sources: **App** means the live app's JS bundle (https://remix-remix-aushnexa-ai-prescription-safety-medic-9042.ai.studio/), and **PPT** means research/UQ8W59O1_TRIKΛΛL.pptx. We are rebuilding from scratch (we don't have the source), so every row has to earn its build time.

⭐ = a game changer for the Gemma 4 judges · Suggestion = my default (the user decides). Cross a row out with ~~strikethrough~~, or reply with the IDs to cut.

## A. Core prescription safety (the heart of the product)
| ID | Feature | Source | Suggestion |
|---|---|---|---|
| A1 | Prescription input as typed text | PPT, App | Keep |
| A2 | ⭐ Prescription input as a **photo** (printed or handwritten Rx), read by Gemma 4 | App ("Upload & Scan", camera capture) | Keep. This is the main multimodal moment |
| A3 | Patient context: allergies and conditions | PPT, App | Keep, as a minimal form |
| A4 | Brand → active salt + strength + form resolution, with a match confidence | PPT, App | Keep (deterministic lookup) |
| A5 | ⭐ Duplicate active-ingredient detection across brands and inside combination drugs (Dolo 650 + Combiflam = paracetamol twice, 975 mg per dose) | PPT, App | Keep. This is the hero alert |
| A6 | ⭐ Allergy cross-check (penicillin allergy against amoxicillin in Augmentin; sulfa allergy against HCTZ) | App | Keep |
| A7 | Dosing abbreviation decoding (OD, BD, TDS, SOS, HS, AC) | PPT, App | Keep |
| A8 | Drug–drug and drug–food interaction notes (Allegra + fruit juice; aspirin + glimepiride) | App | Keep a small curated set |
| A9 | Prioritised alert cards (HIGH, REVIEW, INFO), with severity kept separate from match confidence (to fight alert fatigue) | PPT, App | Keep |
| A10 | ⭐ Uncertainty handling: flag unknown or unclear items as UNSURE instead of guessing | PPT | Keep. Judges love "it knows what it doesn't know" |
| A11 | Evidence and explanation panel for each alert (why, and which rule) | PPT, App | Keep, short |
| A12 | Daily dose limit warnings ("do not exceed 1950 mg in 24 h") | App | Nice to have |

## B. Patient-facing outputs
| ID | Feature | Source | Suggestion |
|---|---|---|---|
| B1 | Dosage schedule (morning, afternoon, night, with before or after food) | App | Keep |
| B2 | ⭐ Jan Aushadhi generic alternative, with price saved (₹34 → ₹14) | App | Keep. A strong India impact story |
| B3 | ⭐ Hindi / English toggle, including a Hindi patient summary | App | Keep the Hindi summary from Gemma. Cut the full-UI translation |
| B4 | Medicine lookup (search one brand and see its salt, class, uses and generic) | App | Optional, since the same data powers it |
| B5 | Rx Assistant chat with suggested questions ("Can I switch to Jan Aushadhi generics?") | App | Optional. It's Gemma chat grounded on the report |
| B6 | Print Rx sheet / printable large-font dose card | App | Keep as a simple print view |
| B7 | Questions to ask your doctor (generated per prescription) | App | Cheap win, fold it into the report |

## C. Professional / clinical extras
| ID | Feature | Source | Suggestion |
|---|---|---|---|
| C1 | Duplicate-ingredient relationship diagram (brand → salt graph) | PPT | ⭐ if time allows. Very visual |
| C2 | ⭐ Safety test laboratory: preset cases with expected outcomes, run as a test suite | PPT | Keep 3–4 preset demo cases (the app has 3: fever polypharmacy, sinusitis with penicillin allergy, a cardio-metabolic regimen) |
| C3 | Clinician portal / clinician mode | App | Cut |
| C4 | Clinical safety audit log | App | Cut |
| C5 | Patient registry | App | Cut |
| C6 | Telehealth queue | App | Cut |
| C7 | Versioned rules and medicine data (JSON / SQLite) | PPT | Keep (it's just our data file) |

## D. Commerce and telehealth (the "hodgepodge")
| ID | Feature | Source | Suggestion |
|---|---|---|---|
| D1 | Doctor consult with 6 doctor profiles and time slots | App | Cut |
| D2 | Medicine delivery / Pharmacy Express ordering ("from ₹129") | App | Cut |
| D3 | Live GPS delivery tracking (Google Maps) | App | Cut |
| D4 | Pharmacy order management and prescription verification queue | App | Cut |

## E. App shell
| ID | Feature | Source | Suggestion |
|---|---|---|---|
| E1 | Login with patient and clinician portals and 1-click demo access | App | Cut. No login |
| E2 | Side navigation drawer plus taskbar plus "sections overview" modal | App | Cut. One page with 3 steps |
| E3 | Light / dark theme toggle | App | Optional (cheap) |
| E4 | Accessible design: readable type, high contrast, a text label beside each severity colour | PPT | Keep |
| E5 | "Supports review, does not replace a professional" disclaimer, in a consistent place | PPT, App | Keep |

## F. New game changers (not in the app)
| ID | Feature | Why it wins |
|---|---|---|
| F1 | ⭐ **Strip / box photo → salt + Jan Aushadhi price.** Photograph the medicine you were given and check it against the prescription (500 mg prescribed, 650 mg given = MISMATCH) | This is PillCheck's core. It needs several images at once, a strong use of Gemma 4 |
| F2 | ⭐ **Visible Gemma tool-call trace.** Show Gemma calling `lookup_salt`, `check_allergy`, `find_generic`, with plain code making the decision | Shows real function calling and makes the safety design visible: "Gemma reads, code decides" |
| F3 | ⭐ **Runs with open weights.** The same pipeline also works on local Gemma 4 E4B through Ollama, for privacy | Qualifies for the open-source category too, and gives a privacy story for clinics |
| F4 | Read-aloud of the Hindi summary for elderly or low-literacy users (browser speech) | Cheap accessibility win |

| F5 | ⭐ **Real brand coverage from open data.** Load the junioralive/Indian-Medicine-Dataset (about 254k Indian brands with compositions, MIT license) so that *any* brand resolves, not just 12 hard-coded ones | "Try any medicine in your cabinet" makes for a credible live demo |
| F6 | Monthly savings meter: the total ₹ saved by switching every item to its Jan Aushadhi generic | A single impact number for the pitch |
| F7 | Allergy class expansion (penicillin allergy → every beta-lactam salt) | A deterministic rule that is cheap and impressive |

Open-source findings (research/notes/open-source.md):
- **Brand → salt data:** junioralive/Indian-Medicine-Dataset, 253,973 rows, MIT. Use a filtered slice of the top brands to keep it fast.
- **Jan Aushadhi prices:** only official PDFs exist (pmbi.co.in), so hand-curate about 30 salt → price rows.
- **Interactions:** the RxNav API was discontinued in Jan 2024. DDInter is CC BY-NC-SA 4.0. Hand-write 20–30 pairs, citing DDInter.
- **MedGemma** is built on Gemma 3 and is not on the Gemini API, so it doesn't help the Gemma 4 track.
- No open-source duplicate-salt checker exists, which makes this an open-source gap we can fill.
