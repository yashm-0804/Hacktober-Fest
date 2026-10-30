# Skeptic review: LabLens (PS-2, photo of lab report to flags, explanations and doctor questions)

2026-10-30 · ~3.4h left (~2.5h of build) · Verdict: SERIOUS

## Steelman
Lab reports are the most common medical document an Indian family handles, and most families read them alone, in English, days before the doctor visit. LabLens fits Gemma 4's API surface well: image in, a tool call to deterministic Python for the range check (so the model never decides what is abnormal), and output in Hindi. It is buildable in Streamlit in an afternoon, the "safety by design" story is clear, and the demo is a single before/after: a blurry photo becomes 2 red flags and 3 questions.

## Objections (ranked, most damaging first)

### 1. This is one of the most-built AI health apps, and the name is already taken. Severity: Serious
- Evidence: there is a live consumer product called **LabLens AI** on Product Hunt (https://www.producthunt.com/products/lablens-ai) that "explains what values generally mean ... rather than diagnosing", which is our exact pitch. App Store apps do the same photo-to-explanation flow: MedAssist (https://apps.apple.com/app/id6741788102), Wizey, which color-codes attention markers and has a follow-up chat (https://apps.apple.com/us/app/-/id6744994210), Infolens Med, which highlights out-of-range values (https://apps.apple.com/us/app/-/id6743679217), LabSimplify and MedReport AI. Hackathon builds include Doclyst on Devpost (https://kelaenderkoe.pages.dev/java/docs/reference/google-https-devpost.com/software/doclyst), HealthAlzer, which is Gemini plus blood reports, Dr.Parser (FastAPI + EasyOCR + Gemini), MurffyLab, a multilingual lab-report reader (https://dev.to/akansha_kumari/murffylab-ai-that-reads-your-lab-report-in-your-language-a1m), and CureNet, which says Gemma 4 analyzes lab reports directly (https://dev.to/labishbardiya/curenet-ai-decentralized-health-intelligence-for-india-powered-by-gemma-4-and-abha-standardization-4po9).
- Why it costs points: Innovation (20%). A judge who has seen even one of these will score it as "a ChatGPT wrapper for lab reports". The out-of-range flagging, plain-language explanation and doctor-questions features are all in shipping apps. Hindi is the only partial differentiator, and MurffyLab already claims regional languages.
- What would resolve it: rename now, because a Product Hunt collision looks careless in a judged demo. Then pick one differentiator that none of the above shows and make it the demo moment. My recommendation is in "Single change" below. Saying "we use Gemma" is not a differentiator.

### 2. The demo moment rests on the weakest link: reading numbers off a blurry photo. Severity: Serious
- Evidence: the deterministic range check is only as good as the numbers the model extracts. A vision LLM that misreads Hb "12.1" as "1.21", drops the decimal in a platelet count, or confuses units produces a confident false red flag. Python then "verifies" it as out of range, so the safety story turns into false authority. Indian CBC reports mix units (lakhs/cumm vs 10^3/uL vs /cumm for platelets, TLC in /cumm), and reference ranges vary by lab, age and sex. Not yet tested: Gemma 4 31B's digit accuracy on a deliberately blurry photo. Structured JSON output is also unconfirmed (REPORT.md line 19), so parsing the table may need regex fallbacks.
- Why it costs points: Technical execution (20%) and Impact (25%). If any health-literate judge spots a wrong flag on screen, the project loses all credibility.
- What would resolve it: (a) In the first 20 minutes, run 3 real report photos (one blurry) through gemma-4-31b-it and compare every extracted value by hand. If more than 1 in 20 values is wrong, drop "blurry" from the pitch. (b) Have the model extract the printed reference range from the same report and compare against that, rather than a hard-coded table. (c) Add a plausibility guard in Python (for example Hb outside 2-25 g/dL means "possible misread, please confirm" rather than a red flag). (d) Show each extracted value next to its source text, with a confirm/edit step before the flags are computed.

### 3. Gemma 4 is used as a generic vision LLM. "Why Gemma and not Gemini Flash?" has no answer. Severity: Serious
- Evidence: every feature listed (image input, function calling, thinking, Hindi) is also available, and arguably better, in Gemini 2.5 Flash through the same API. The function call for the range check is a one-line comparison that Python could run after the model without any tool call, so a technical judge may see the tool use as staged. Past Gemma winners (per the brief: an offline disaster app and a privacy-first triage co-pilot) won on the open-weights story, meaning private, local and deployable at the edge. LabLens sends photos of medical documents to a cloud API, which works against that story.
- Why it costs points: Use of sponsor tech (15%) and Innovation.
- What would resolve it: (a) Pitch the deployment, not the demo. Because the weights are open, the same model can run on a diagnostic lab's own server, so patient reports never leave the premises, which matters under India's DPDP Act 2023. The hackathon build uses the API only because the rules require it. Say this explicitly in the README and the video. (b) Make the tool loop do real work. Give the model 2-3 tools it must choose between, for example `get_reference_range(test, age, sex)`, `check_value(...)` and `flag_possible_misread(field)`, and show the tool-call trace in a UI expander so the integration is visible. (c) Name the exact model ID in the README and on screen.

### 4. Latency and quota could break the live demo. Severity: Manageable
- Evidence: a 31B model handling a full-page image, with thinking mode and a tool round-trip, plus a second call for Hindi, could take tens of seconds per report. Free-tier quotas for Gemma on the Gemini API are unverified (REPORT.md line 42). Neither has been measured.
- Why it costs points: Presentation (10%). Dead air in a short video, or a 429 error mid-demo.
- What would resolve it: time one full run in the first 30 minutes. If it takes more than 20 seconds, turn thinking off for extraction and keep it for the explanation step, or try gemma-4-26b-a4b-it. Cache one known-good response as a demo fallback, and record the video from a real run rather than a live one.

### 5. Scope will not fit in about 2.5 hours as listed. Severity: Manageable
- Evidence: the feature list covers extraction, a table, flags, explanations, questions, a Hindi toggle, a confirm/edit step, a tool trace, disclaimers, a README and a video. The ship phase (README, video, Devpost) realistically takes 45-60 minutes, which leaves about 1.5-2 hours of build.
- What would resolve it: cut in this order: the Hindi toggle becomes a single prompt parameter (keep it, it is cheap), the edit step becomes a read-only "source text" column, then the explanations shrink to flagged values only. Do not cut the 2 flags + 3 questions moment or the visible tool trace.

### 6. Medical liability: "explains, never diagnoses" is a slogan, not a mechanism. Severity: Manageable
- Evidence: a red flag plus "ask your doctor whether this means X" is clinical triage in practice. The competing apps all carry "not a diagnosis" disclaimers (see the search results), so a disclaimer is table stakes, not a safeguard. Thinking-mode explanations can drift into naming diseases.
- What would resolve it: in the system instruction, forbid naming any condition as the patient's diagnosis, and phrase questions as "What could cause my low X?". Add a hard rule that critical values (for example K+ above 6.0, or platelets below 20k) produce "contact your doctor today" and nothing else. That rule is a 10-line Python feature that judges will remember.

### 7. Nobody obviously pays, and the incumbents already ship smart reports. Severity: Manageable
- Evidence: free consumer apps saturate the B2C market (objection 1). Large Indian diagnostic chains may already issue color-coded "smart reports". This is unverified, so check one Thyrocare/Healthians/1mg sample report before claiming the gap.
- Why it costs points: Feasibility/business (10%), which is low weight.
- What would resolve it: frame it as B2B. Tier-2/3 standalone pathology labs that cannot build smart reports would print a Hindi QR summary on each report, running a self-hosted Gemma (which ties back to objection 3).

## Kill criteria
- After 20 minutes: more than 1 misread number in 20 on real photos, with no fix from cropping or a re-prompt. Drop "blurry photo", demo a clean scan, and lead with the verification UI.
- Gemma 4 function calling through the API fails or is flaky after 2 attempts. Do the range check in plain Python, say so honestly, and do not fake a tool trace.
- One end-to-end run takes more than 40 seconds, or you hit a 429 error. Switch to 26b-a4b, turn thinking off for extraction, and pre-record.
- At T-75 minutes (12:45 IST) with no end-to-end run on a real photo: freeze features and move to the ship phase.

## Single change that most strengthens the idea
Make "trust" the product, not "explanation". Every flagged value appears next to the source text Gemma read from the photo and the report's own printed reference range. Python plausibility rules catch likely misreads ("we may have misread this, please confirm") and critical values ("contact your doctor today"). Show this in the demo by catching a deliberate misread. No competitor listed above shows it, it directly defuses the OCR-accuracy and liability objections, and it gives the Gemma function-calling trace a real job. Pair it with a rename and the on-prem open-weights pitch.

## Sources
- [LabLens AI (Product Hunt)](https://www.producthunt.com/products/lablens-ai)
- [MedAssist](https://apps.apple.com/app/id6741788102) · [Wizey](https://apps.apple.com/us/app/-/id6744994210) · [Infolens Med](https://apps.apple.com/us/app/-/id6743679217) · [LabSimplify](https://apps.apple.com/bz/app/labsimplify-lab-test-reader/id6747992138) · [MedReport AI](https://apps.apple.com/app/id6761745488)
- [Doclyst (Devpost mirror)](https://kelaenderkoe.pages.dev/java/docs/reference/google-https-devpost.com/software/doclyst) · [HealthAlzer (Devpost mirror)](https://kelaenderkoe.pages.dev/Function-https-devpost.com/software/healthalzer) · [Dr.Parser](https://awesome.ecosyste.ms/api/v1/projects/github.com%2Fgyanvir%2Fdrparser)
- [MurffyLab (DEV)](https://dev.to/akansha_kumari/murffylab-ai-that-reads-your-lab-report-in-your-language-a1m) · [CureNet, Gemma 4 (DEV)](https://dev.to/labishbardiya/curenet-ai-decentralized-health-intelligence-for-india-powered-by-gemma-4-and-abha-standardization-4po9)
- /Users/yashmehta/Desktop/projects/Hacktober Fest/research/REPORT.md (lines 9, 19, 42)
