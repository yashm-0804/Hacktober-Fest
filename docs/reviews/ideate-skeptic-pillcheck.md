# Skeptic review: IDEA B · PillCheck

2026-10-30 · ~3.4h left (~2.5h build) · Verdict: SERIOUS

## Steelman
PillCheck brings a proven hospital safety control, barcode medication administration (the "five rights" check), to the kitchen table. You photograph the prescription and the strips you were given, and it tells you whether they agree. It targets a specific, sympathetic user (older adults and caregivers) in a safety domain, which is the same pattern as the past Gemma winners (AccessLens, the triage co-pilot; REPORT.md line 27-28). The demo moment (Rx says 500 mg, strip says 650 mg, red MISMATCH card) is concrete and easy to remember, and in India it is realistic: paracetamol is sold as both 500 mg and 650 mg (Crocin 500 against Dolo 650).

## Objections (ranked, most damaging first)

### 1. Off-the-shelf vision models read real handwritten prescriptions badly, and a false MATCH is the dangerous failure. Severity: Serious (Fatal if the demo uses a messy real Rx)
- Evidence: In MIRAGE (Indian handwritten prescriptions, annotations from 1,133 doctors), un-fine-tuned **GPT-4o scored ~7.6% F1 and Gemini 1.5 Pro ~5.5% F1** on medication name plus dosage. Only a fine-tuned model reached 82%. https://arxiv.org/html/2410.09729v2 . RxScribe Bench (Indian outpatient Rx) finds even frontier models unstable from run to run on hard fields: https://arxiv.org/pdf/2609.13280 . Trained humans are not perfect either: pharmacists read prescriptions at a median of 75% (cited in MIRAGE). Gemma 4 31B is smaller than those frontier models, and nothing suggests it does better. Google's own "Lens reads doctors' handwriting" was still a research prototype with no launch date (9to5Google, 2022-12-19: https://9to5google.com/2022/12/19/google-lens-will-soon-be-able-to-decipher-prescriptions-from-your-doctors-bad-handwriting).
- Why it costs points: Technical execution (20%) and Impact (25%). A judge who asks "how accurate is it on handwriting?" gets no good answer. If the model misreads "500" as "650" on stage, the demo inverts. The worse error is a misread that produces a reassuring MATCH, which a safety-minded judge will raise.
- What would resolve it: (a) In the first 15 minutes, run Gemma 4 on 5 real prescription photos (a mix of legible and messy) and count the correct name and strength fields. (b) Make abstention the product: require a per-field `confidence` and `legible: bool` from Gemma, and send anything not clearly legible to "UNSURE, ask your pharmacist". (c) For the hero demo use a clearly written or printed/e-prescription, and show a messy one producing UNSURE as a deliberate second beat ("it knows when it can't read").

### 2. In India, the prescription brand and the strip brand often differ, so name matching gives false MISMATCHes unless you resolve brands to salts. Severity: Serious
- Evidence: Indian prescriptions are mostly written by brand, and pharmacies substitute brands with the same salt (Dolo 650 and Calpol 650 are both paracetamol 650). Look-alike and sound-alike brands are a documented Indian hazard. See the Lancet Regional Health SE Asia viewpoint, covered at https://thesouthfirst.com/news/look-alike-sound-alike-medicine-in-indian-market-can-cause-significant-health-threat-lancet , and a Delhi hospital study where identical brand names were the most common error category (https://content.iospress.com/articles/international-journal-of-risk-and-safety-in-medicine/jrs416). If Gemma decides brand-to-salt equivalence from memory, it can hallucinate a composition.
- Why it costs points: Technical execution and Impact. Every legitimate substitution would raise an alarm (alarm fatigue), and a hallucinated salt is a safety bug.
- What would resolve it: Add a small curated `brand_to_salt.json` (about 30 brands covering the demo drugs) exposed as a **function call** `lookup_salt(brand)`. Gemma extracts the text, the table resolves salt and strength, and **deterministic Python** decides MATCH, MISMATCH or UNSURE. Unknown brands go to UNSURE. This also makes the function calling real instead of decorative (see #5).

### 3. The "count" check and multi-strip comparison are too much scope for about 2.5 hours, and latency is a real live risk. Severity: Serious for the schedule
- Evidence: Count means parsing a frequency and duration ("1-0-1 x 5 days", OD/BD/TDS/SOS) and then counting tablets from blister photos. Tablet counting from photos is a separate CV problem. Structured JSON output from Gemma 4 through the API is unconfirmed (REPORT.md line 19). Several images plus thinking mode on a 31B model may take tens of seconds per call, and free-tier quotas are unknown (REPORT.md line 42).
- Why it costs points: Technical execution, and Presentation if the live call stalls.
- What would resolve it: Cut count from the MVP. Check drug (salt) and strength only, and show quantity as "you should have N tablets" computed from the Rx, not from counting the photo. Get structured output through function-call arguments if JSON mode fails (test in the first 10 minutes). Use one Rx image and at most 2 strip images. Cache the demo responses and record the video from a known-good run.

### 4. It exists in parts, and judges may know the parts. Severity: Manageable
- Evidence: Prescription readers already ship. AI Prescription Reader (Dhruvian Labs, Android) reads handwritten Indian prescriptions, including OD/BD/SOS: https://appgoblin.info/apps/com.medisathi.ai.scanner . Aushadhi Vault (vision-AI Rx reading for pharmacist billing) and Aushadhi Mitra (a hackathon project: Rx scan plus price comparison, https://hackquest.io/projects/Meteors). Indian e-pharmacies (Tata 1mg, PharmEasy) already require Rx upload with pharmacist verification (not verified here, but widely known). Hospital BCMA is the established version of this idea. I found **no consumer tool that cross-checks the dispensed strip against the Rx**, so the comparison is the real differentiator.
- Why it costs points: Innovation (20%), if the pitch leads with "reads prescriptions".
- What would resolve it: Pitch it as "the last check after the pharmacy counter, the barcode check hospitals use, for your home". Never lead with "reads handwriting". Name the competitors in the README and say how PillCheck differs.

### 5. Gemma 4 depth: anything here could be "just Gemini Flash". Severity: Manageable
- Evidence: Multi-image extraction is a generic VLM feature. The track asks you to "show the integration" (REPORT.md line 7). Past winners leaned on why an open model matters (offline, privacy).
- Why it costs points: Use of sponsor tech (15%).
- What would resolve it: Show visibly in the UI or demo: a system instruction carrying the safety policy, function calls (`lookup_salt`, `flag_for_pharmacist`, `render_dose_card`) with an on-screen trace, thinking mode on the comparison step, and one slide saying "open weights let a pharmacy run this on-premise, so prescriptions never leave the shop". Be honest that the demo uses the API.

### 6. Liability: a green MATCH is advice, whatever the disclaimer says. Severity: Manageable
- Evidence: "Checks, never advises" does not hold if the screen says "OK" and the patient takes the pill. Issue #1 makes false reassurance plausible.
- Why it costs points: Feasibility/business (10%). Judges in health tracks routinely ask "what if it's wrong?"
- What would resolve it: Never show "safe". Use three states: "Matches what we could read" (neutral), "MISMATCH, show this to your pharmacist", and "UNSURE, ask your pharmacist". Put the source crops beside each extracted field so a human can verify. Store nothing.

### 7. Business model and problem fit are thin. Severity: Manageable
- Evidence: Elderly consumers rarely pay for utility apps, and e-pharmacies already verify the Rx in-house. PS-3 is about *misreading labels at home*, which leads to dose mix-ups. That is mostly a **dose-schedule** problem, which the large-font dose card solves. A dispensing-error check addresses a different, rarer failure.
- Why it costs points: Impact (if judges see a mismatch with PS-3) and Feasibility.
- What would resolve it: Give the dose card equal weight in the demo, since it is the PS-3 answer. Business: B2B2C. Independent chemists or eldercare and home-nursing providers offer it as a "second check", or a caregiver plan in which the dose card is shared with a family member over WhatsApp. One sentence each, no more.

## Kill criteria
- After 15 minutes, Gemma 4 gets fewer than 4 of 5 name+strength fields right on *legible* prescription photos: drop handwriting and switch to printed/e-prescriptions plus strips only.
- One multi-image call takes more than 30s or hits a quota error: cut to one Rx image and one strip, turn off thinking, and pre-record.
- By the 1h45m mark the MATCH/MISMATCH/UNSURE path doesn't work end to end: ship only the dose card from the Rx plus a single-strip strength check.
- Count parsing isn't working at 1h: drop it entirely.

## One pivot that would survive
The single change that most strengthens the idea is **"Gemma reads, code decides, uncertainty escalates."** Gemma 4 extracts fields with per-field confidence through function calls. A curated brand-to-salt table and deterministic Python make the MATCH/MISMATCH/UNSURE call. Anything illegible or unknown goes to "ask your pharmacist". Demo: a legible Rx with a 500 mg vs 650 mg strip gives a red MISMATCH, then a messy Rx gives UNSURE ("it knows what it can't read"), then the large-font dose card. This answers the handwriting-accuracy question, the brand/generic problem and the liability question at once, and it makes the function calling substantive.

## Sources
- [MIRAGE: Indian handwritten prescriptions, arXiv 2410.09729](https://arxiv.org/html/2410.09729v2)
- [RxScribe Bench, arXiv 2609.13280](https://arxiv.org/pdf/2609.13280)
- [AI Prescription Reader (Dhruvian Labs)](https://appgoblin.info/apps/com.medisathi.ai.scanner)
- [Aushadhi Mitra / Meteors, HackQuest](https://hackquest.io/projects/Meteors)
- [9to5Google: Lens prescription prototype](https://9to5google.com/2022/12/19/google-lens-will-soon-be-able-to-decipher-prescriptions-from-your-doctors-bad-handwriting)
- [South First: Lancet on look-alike/sound-alike drugs in India](https://thesouthfirst.com/news/look-alike-sound-alike-medicine-in-indian-market-can-cause-significant-health-threat-lancet)
- [IJRSM: brand-name dispensing errors, Delhi](https://content.iospress.com/articles/international-journal-of-risk-and-safety-in-medicine/jrs416)
