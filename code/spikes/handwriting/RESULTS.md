# Spike: Gemma 4 reading handwritten Indian prescriptions (2026-10-30, 10:50–11:02 IST)

- **Setup:** 5 real prescription photos from huggingface.co/datasets/tavishm/100-handwritten-medical-records. No license is stated, so they are for internal testing only and **must not be used in the demo**. The images were resized to 1600 px. The prompt is in run_test.py, and the ground truth (hand-read) is in ground_truth.json.
- **Raw output:** results_gemma-4-26b-a4b-it.json, results_gemma-4-31b-it.json, log_26b.txt, log_31b.txt.

## Accuracy (gemma-4-26b-a4b-it, 1 run each)
| Image | Type | Medicines found | Names right | Dose/frequency issues |
|---|---|---|---|---|
| 2nPPipXy | Printed + 1 handwritten line | 8/8 (+1 nebuliser from the instructions, a valid extra) | 8/8 | Handwritten Montair LC "5 ml" read as "1 ml", **flagged unsure** |
| 0waC2LqO | Messy, outpatient | 3/3 | 2/3: **Calcimax → "Celemax" (conf 0.9, wrong but confident)**. The 31B model read it right. The 1000 px run read "Calcinax" | OK |
| 62qlxpSw | Messy, inpatient IV, one drug struck out | 6/6, and **the struck-out Oflox was correctly excluded** | 6/6 (DNS written as "DWS") | OK |
| 4J7Jyojz | Messy, newborn | 4/4 | 3/4: raw "Visyneral" correct, but the name field said "Vitamin D" (**flagged unsure**, conf 0.4) | Evion "5 drops OD" read as "500" |
| 0fmQCjuf | Notes, **no medicines** | 0, so **no made-up medicines** | n/a | n/a |

**Totals:** 21/21 medicines detected. 19/21 names right first time, and the other 2 are fixable by fuzzy-matching against a brand list ("Celemax" and "Calcinax" are close to Calcimax). There were 3 dose errors, 2 of them flagged unsure. There were 0 made-up medicines, and the struck-out drug was handled correctly.

## Speed and reliability (the real problem)
- 26B: **39–210 s per image** when run in parallel. A single 1000 px image still took 37 s for 333 output tokens.
- 31B: 97–175 s, and **HTTP 500 on 4 of 5 parallel calls**. 26B also returned 500s on about half of the follow-up calls.
- Thinking is not the cause: `thoughts_token_count` was None, and `thinking_level` is rejected for 26B ("not supported for this model").
- Conclusion: the Gemini API's Gemma 4 serving was slow and flaky during this test.

## Implications for the build
1. Reading works well enough for a **"read → fuzzy-match → confirm"** flow. The model's confidence is not trustworthy (Celemax 0.9), so match every name against the brand dataset.
2. Latency and 500 errors put the live demo at risk. We need: retry with backoff, progress UI or streaming, **cached results for the demo images**, a typed-text input fallback, and a smaller output (ask for fewer fields).
3. Consider testing local Ollama `gemma4:e4b` speed as a backup (the open-weights story too).
