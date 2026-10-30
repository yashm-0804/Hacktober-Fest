# Judge review: Ideas A (LabLens), B (PillCheck), C (CareFolder), Best Use of Gemma 4 track

2026-10-30 10:35 IST · Rubric: FALLBACK · Blind: yes (no earlier scores were in the prompt; docs/reviews was not read)

Scored as if each idea were built well in the roughly 2.5 hours of build time left. Weights: Impact 25 · Innovation 20 · Technical execution 20 · Use of Gemma 4 15 · Presentation 10 · Feasibility 10.

## What a 9 looks like in this hackathon
- **Impact (25%):** a specific, high-stakes user (an elderly patient, a caregiver in India) with a measurable harm avoided. The panel should *feel* that the problem matters.
- **Innovation (20%):** not "chat with a document". It reframes the problem or borrows a proven pattern from another field.
- **Technical execution (20%):** one end-to-end path that works on real, messy inputs live, with deterministic guardrails where the model is weak. Built and solid within 2.5 h.
- **Use of Gemma 4 (15%):** image input carries the product, and function calling, system instructions and thinking each do real work and are visible in the code or UI. The model ID is in the README.
- **Presentation (10%):** a 10-second "aha" moment on screen that judges remember after 30 other demos.
- **Feasibility (10%):** a believable user and channel, cost advantages from open weights or on-device use, and a sensible handling of liability.

---

## Idea A: LabLens

| Criterion | Weight | Score /10 | Evidence |
|---|---|---|---|
| Impact and usefulness | 25% | 7 | Patients really do struggle with lab reports, and the Hindi output widens reach, but the stakes are "understanding" rather than preventing harm. |
| Innovation and originality | 20% | 5 | "Explain my lab report" is one of the most common health-AI hackathon ideas. Only the deterministic range checks and the doctor-questions list set it apart. |
| Technical execution | 20% | 8 | It is the smallest scope of the three: one image, then a schema, then Python range checks, then explanations. That fits comfortably in 2.5 h with time left to polish. |
| Use of Gemma 4 | 15% | 7 | Uses image input, function calling and thinking well, but it is single-image extraction that any VLM could do. Nothing makes it uniquely Gemma 4. |
| Presentation and demo | 10% | 7 | A blurry photo turning into red flags is clean, but judges have seen this transformation many times. |
| Feasibility and business viability | 10% | 6 | Labs and telehealth apps are plausible channels, but crowded with existing products. Misreading a value is a liability risk. |
| **Weighted** | | **6.70** | |

**Top 2 changes**
1. Add trend or comparison: two reports from different dates go in, and a "Haemoglobin dropped 2.1 since March" line comes out. That uses multi-image input and lifts Innovation (+1) and Use of Gemma 4 (+1), for about +0.35.
2. Show a provenance crop for each flagged value (a bounding box or snippet from the photo next to the extracted number) so judges can see it is not hallucinated. That raises Technical execution and Presentation, for about +0.3.

---

## Idea B: PillCheck

| Criterion | Weight | Score /10 | Evidence |
|---|---|---|---|
| Impact and usefulness | 25% | 8 | Dispensing and strength errors cause real harm, especially for elderly people on several drugs. The user and the harm are concrete. |
| Innovation and originality | 20% | 7 | Bringing hospital barcode medication verification to a phone camera is a fresh reframe that I have rarely seen at hackathons. The large-font dose card is a thoughtful touch. |
| Technical execution | 20% | 6 | Comparing images is well scoped, but reading handwritten Indian prescriptions is unreliable. Brand-versus-generic name matching (Dolo vs paracetamol) needs a lookup table, or it will raise false MISMATCH alerts. |
| Use of Gemma 4 | 15% | 8 | Several images in one call, handwriting OCR, and function calling to a deterministic matcher. Multimodal input is essential here, not decoration. |
| Presentation and demo | 10% | 8 | A red MISMATCH card for 500 mg against 650 mg is visceral, takes 10 seconds, and is easy to remember. |
| Feasibility and business viability | 10% | 6 | Pharmacies, caregivers and insurers are plausible channels. "Checks, never advises" handles liability sensibly, but a false "match" is a serious failure mode. |
| **Weighted** | | **7.20** | |

**Top 2 changes**
1. Add a small brand-to-generic-and-strength table (around 30 common Indian drugs) used by the deterministic matcher, plus an "UNCERTAIN, can't read" state alongside MATCH and MISMATCH. That raises Technical execution +1 and Feasibility +1, for about +0.3, and defuses the panel's biggest question.
2. Use a printed or typed prescription as the main demo, keep handwriting as a bonus, and show the per-field confidence and the thinking trace. That protects Presentation and Technical execution against a live failure, for about +0.2 to 0.3.

---

## Idea C: CareFolder

| Criterion | Weight | Score /10 | Evidence |
|---|---|---|---|
| Impact and usefulness | 25% | 8 | Caregivers juggling paperwork before a doctor visit is a real and broad problem, and a single brief is useful. |
| Innovation and originality | 20% | 6 | The router plus brief is a nice packaging, but it is mostly A and B stitched together. The novelty is in the integration, not the insight. |
| Technical execution | 20% | 4 | Two complete pipelines, a classifier and router, and a combined printable brief in 2.5 h is very likely to end up shallow or half-working. Each tool would be weaker than A or B alone. |
| Use of Gemma 4 | 15% | 9 | Image input, routing via function calling, multi-image input and orchestration across tools show the broadest Gemma 4 usage of the three. ("Long context" is a stretch for four photos.) |
| Presentation and demo | 10% | 7 | "Four photos in, one brief out" sounds good, but a brief is a dense page with no single emotional beat like a red MISMATCH card. |
| Feasibility and business viability | 10% | 6 | A caregiver app is a plausible consumer product, but it is broad, and the go-to-market is unclear. |
| **Weighted** | | **6.65** | |

**Top 2 changes**
1. Cut scope: route between only two types (lab report and prescription plus strip) and build the brief from those, treating everything else as "unsupported type". That raises Technical execution +2, for about +0.4.
2. Give the brief one headline alert at the top (for example "MISMATCH: strip 650 mg vs Rx 500 mg" or "2 values out of range") so the demo has a single visible moment. That raises Presentation +1 and Impact +0.5, for about +0.2.

---

## Ranking

| Rank | Idea | Weighted | Lowest criterion | Why |
|---|---|---|---|---|
| 1 | B · PillCheck | **7.20** | Technical execution and Feasibility (6) | It has the most memorable demo and a fresh framing that borrows from hospital barcode medication verification. Multi-image input is essential. The risk is handwriting and brand-name matching, and it is fixable. |
| 2 | A · LabLens | 6.70 | Innovation (5) | It is the safest build, but judges have seen many lab-report explainers. |
| 3 | C · CareFolder | 6.65 | Technical execution (4) | It has the best Gemma story on paper but is over-scoped for 2.5 h. |

Recommendation: build B, and use one piece of C as a stretch goal. A function-calling router that accepts a lab report and passes it to a minimal range-check would show routing without risking the core.

## Red flags (at the idea stage)
- **C claims "long context".** Four photos do not exercise long context, and a judge from the sponsor will notice. Drop the claim or don't lean on it.
- **B's handwriting reading.** Gemma 4's accuracy on Indian handwritten prescriptions is unproven. Don't make a live demo depend on it without a fallback image.
- **A's Hindi output.** The quality of Gemma's Hindi medical explanations has not been checked. Have a native speaker spot-check before you show it.
- **For all three:** use synthetic or anonymised reports and prescriptions in the demo and the repo, never real patient data. The README must name `gemma-4-31b-it` (or `gemma-4-26b-a4b-it`) and point to the API call.
- **Safety framing must be visible in the UI**, not only stated in the README ("explains, never diagnoses" or "checks, never advises").

## How it compares
A typical submission in a Gemma track is a single-image "explain this" app, which scores about 5.5 to 6.5. LabLens sits at the top of that band. A typical winner has one visceral demo moment, multimodal input that the product could not work without, and a clearly bounded safety story, which scores about 7.5 to 8.5. PillCheck is the only one of the three in reach of that band. It gets there if the matcher is deterministic, an "uncertain" state exists, and the demo runs reliably on a printed prescription.
