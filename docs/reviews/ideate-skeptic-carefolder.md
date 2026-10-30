# Skeptic review: Idea C, CareFolder

2026-10-30 · about 3.4h left (about 2h of real build time) · Verdict: SERIOUS

## Steelman
CareFolder covers both problem statements (PS-2 lab jargon, PS-3 dose mix-ups) with one caregiver story: "I have a bag of papers and a doctor's appointment tomorrow." The idea is defensible because of its split of responsibilities. Gemma 4 reads the images and decides which tool to call. Deterministic code then checks lab values against reference ranges and compares the prescription with the strip, so the model never claims a number is safe. The output is a single printable page for the doctor, which shows clearly on screen. It uses the features Google promotes (multimodal input, function calling, multiple images) and matches the past winning pattern of an accessibility or health assistant.

## Objections (ranked, most damaging first)

### 1. It is two products plus a router plus a document generator, in about 2 hours of build. Severity: Serious (Fatal if built as described)
- Evidence: the deadline is 14:00 IST and it is now 10:33. The video, README, Devpost page and model naming need 45–60 minutes, which leaves about 2h of build time. The card requires: (a) classifying 4 document types, (b) a lab extractor and a range table, (c) a prescription OCR step, (d) a strip OCR step and a matcher, (e) a function-calling loop, (f) merging everything into a brief, (g) a printable layout. Structured JSON output is unconfirmed (REPORT.md line 19: "Unconfirmed. Test it first"), and both extractors depend on parsing value, unit and range reliably. A small team with an unknown headcount cannot absorb one integration surprise.
- Why it costs points: Technical execution (20%) and Presentation (10%). A half-working router plus two half-working tools scores lower than one tool that works.
- What would resolve it: fix the scope at 3 known photo types (lab report, handwritten prescription, medicine strip) and drop "any health photo" and discharge summaries. Use Gemma function-declaration schemas as the structured-output path, so JSON mode isn't needed. Render the brief as HTML with a print stylesheet (browser Ctrl+P) instead of using a PDF library. Write the range table by hand for about 12 common analytes (CBC, HbA1c, lipids, TSH, creatinine). Hard timebox: if the round trip from one photo to a tool call isn't working by 11:30, cut the router and use a document-type dropdown.

### 2. It already exists, and judges have heard of the biggest version. Severity: Serious
- Evidence:
  - ChatGPT Health (launched 7 Jan 2026) already lets users upload lab results and visit summaries for explanation: [Tom's Guide](https://www.tomsguide.com/ai/chatgpt/openai-launches-chatgpt-health-bringing-medical-records-and-wellness-data-into-chatgpt), [MobiHealthNews](https://www.mobihealthnews.com/news/openai-launches-chatgpt-health-partners-bwell). A judge will know about it.
  - [Health Visit App](https://healthvisit-app.pages.dev/) matches the card almost exactly: a "one-page AI brief" for doctor visits, storage for lab PDFs and prescription photos, and caregiver sharing on a $14.99/mo Family tier.
  - [CareLoop](https://getcareloop.pages.dev/) extracts lab values with out-of-range flags and family sharing. [MedReport AI](https://apps.apple.com/app/id6761745488), [Mediqal AI](https://mwm.ai/apps/mediqal-ai/6748867098), [Labio](https://apps.apple.com/app/id6753671707) and [LabLens AI](https://www.producthunt.com/posts/lablens-ai) are lab-explainer apps.
  - Gemma hackathons have built this before: [Mediscribe (Gemma 4 hackathon)](https://huggingface.co/spaces/Fred-Rcky/Mediscribe/blob/main/DEVLOG.md) analyzes lab and prescription images, and [preshack](https://preshack.github.io/presentation/) has Gemma extract drug, dose and frequency from a prescription photo and map it to RxNorm.
- Why it costs points: Innovation (20%). "Upload your lab report, get a summary" is the most common health-AI hackathon project.
- What would resolve it: lead with the part the others don't do, which is verification across documents. The demo moment should be "the strip in the bag doesn't match what the doctor wrote" (for example, a different strength, or a brand vs generic difference that is the same salt). It should not be "jargon becomes plain English." Make the open-weights point explicitly: Gemma can be self-hosted by a clinic or pharmacy, while ChatGPT Health is a consumer cloud product that isn't HIPAA-covered ([The Register](https://www.theregister.com/2026/01/08/chatgpt_health_access_medical_records/)). Put one line in the pitch: "unlike ChatGPT Health, we never interpret; we check documents against each other and against fixed ranges."

### 3. Using function calling to route photos is shallow Gemma use. Severity: Serious
- Evidence: telling a lab report apart from a strip is a single classification prompt, and a judge from the sponsor will see `if doc_type == ...` dressed up as an agent. REPORT.md line 34 says "A plain chat wrapper won't stand out." The card claims "long context," but 4 images plus a short brief isn't long context, and saying so invites a "where?" from the judge.
- Why it costs points: Use of sponsor tech (15%) and Innovation.
- What would resolve it: make Gemma do real argument extraction through tools. It should call `check_lab_value(analyte, value, unit, printed_ref_range)` once per row, and `match_medication(rx_drug, rx_strength, rx_frequency, strip_drug, strip_strength)` for each Rx line. Then show the tool-call trace in a side panel during the demo. Gemma reading a handwritten "Tab Metformin 500 1-0-1" into typed arguments and making several tool calls in one turn is the showcase. Turn on the thinking mode only for the final brief, if latency allows. Drop the "long context" claim.

### 4. Misreading handwriting is the very harm PS-3 describes, so liability goes up. Severity: Serious
- Evidence: PS-3 says misreading causes dose mix-ups. If the matcher reports "MATCH" on a misread handwritten dose, CareFolder causes the error it was built to prevent. "Explains, never diagnoses" doesn't cover a false verification. A judge can test this with one adversarial photo. Nobody has measured how accurately Gemma 4 reads Indian handwritten prescriptions; it has not been checked.
- Why it costs points: Impact and Feasibility, plus a judge's "would you trust this for your mother?" question.
- What would resolve it: the matcher never says "safe" or "match". It says "Looks consistent, confirm with the pharmacist" or "MISMATCH: ask the doctor", and it shows the extracted text next to a crop of the source. Any field Gemma reports with low confidence, or can't read, becomes a "Couldn't read, ask the doctor" line on the brief. The brief's heading is "Questions to ask", not "Findings". Before 11:15, run 5 real photos and record how many fields are read correctly. If fewer than 4 of 5 prescriptions are read correctly, demo with printed (typed) prescriptions and present handwriting as a stretch goal.

### 5. Latency and quota on the live path. Severity: Manageable
- Evidence: one demo run is 4 images, several tool-call turns and a final composition step, which is roughly 6–10 calls to a 31B model. Free-tier Gemma quotas on the Gemini API have historically included a low tokens-per-minute cap. REPORT.md line 42 flags that the real free quotas have not been verified. Images plus a multi-turn tool loop could hit that cap during the recording.
- Why it costs points: Presentation, if the demo stalls or returns a 429 error.
- What would resolve it: at the start of the build, time one full 4-photo run on `gemma-4-26b-a4b-it` (the MoE model, likely faster) and on `gemma-4-31b-it`. Cache the responses for the demo photos to disk, and record the video from a run that has already been completed.

### 6. The business model is weak against free incumbents. Severity: Manageable (it is 10% of the score)
- Evidence: ChatGPT Health is free in the US. Indian e-pharmacies such as 1mg and PharmEasy already ask users to upload prescriptions as part of their workflow. Health Visit App charges $14.99/mo, so a consumer subscription has competition.
- What would resolve it: pitch B2B2C. Diagnostic labs and pharmacy chains would self-host Gemma (open weights, data stays on their servers) and print the brief at the counter. The "why now" is that open multimodal models are good enough to read handwriting and can run on hardware the business owns. One slide covers it.

## Kill criteria
- By 11:30 IST, there is no working round trip from one photo through a Gemma tool call to a correct deterministic check. Drop the router, use a dropdown, and keep only the lab tool or only the matcher.
- On the accuracy test with 5 photos, Gemma misreads more than 1 of 5 handwritten doses. Switch the demo to typed prescriptions and say so honestly.
- A full 4-photo run takes more than 90s, or hits a 429 error. Cache results, cut to 3 photos, and drop the thinking mode.
- At 13:00 IST, freeze features no matter what. Recording and submission start then.

## One pivot that would survive
Reduce the scope to "CareFolder: does the bag match the prescription?" There are 3 photos (one handwritten prescription, two medicine strips, one lab report), and Gemma extracts typed arguments into 2 deterministic tools. The demo moment is a red MISMATCH line on the printed brief ("Prescription says 500 mg, the strip in the bag is 1000 mg. Ask the doctor before giving it"), with lab flags below it as supporting context. This still tells the combined PS-2 and PS-3 caregiver story, shows real function calling with a visible trace, separates the project from ChatGPT Health and the lab-explainer apps, and fits in 2 hours. The single change that helps most is to replace "route any photo" with "Gemma extracts typed arguments into deterministic verification tools, with the cross-document mismatch as the headline."
