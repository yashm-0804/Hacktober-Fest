# TBD: research report (Hacktoberfest 2026 · Best Use of Gemma 4)

Researched 2026-10-30, about 10:25 IST. This is a time-boxed pass of about 10 minutes, with the deadline at 14:00 IST. The raw notes are research/notes/sponsor-tech.md and research/notes/prior-art.md.

## What the hackathon is
- A 6-hour Hacktoberfest 2026 event that is probably an MLH Hack Day. The "Best Use of Gemma 4" card matches the MLH Hack Day partner module. (sources: [2], [3]) · Med
- **Gemma 4 track rules:** Use a Gemma model **through the Gemini API**, **name the model in the README**, and show the integration in the code or the demo. The prize is a swag bag, keyboard or gift card, depending on region. (source: [2]) · High
- The related DEV challenge series (dev.to/challenges/hf26) lets one submission enter several categories, and DEV judging weights the write-up most. Our event may run on the MLH Hack Day rules instead. (source: [1]) · Med
- No official rubric has been found for our event, so the FALLBACK rubric applies.

## Gemma 4: what we can use
| Fact | Detail | Confidence |
|---|---|---|
| Model IDs on the Gemini API | `gemma-4-31b-it` (dense) and `gemma-4-26b-a4b-it` (MoE, 3.8B active) | Med-High [4] |
| Inputs | Text and images. Video as frames (up to 60 s). **Audio is not available through the API**; only the local E2B, E4B and 12B models take it | High [5] |
| Output | Text only | High [5] |
| Features through the API | System instructions, function calling, multi-turn chat, Google Search grounding, thinking levels | Med-High [4] |
| Context | 256K for the API models | High [5] |
| Structured JSON output | Unconfirmed. **Test it first** (`response_mime_type="application/json"`) | Low |
| Free-tier limits | Unconfirmed, possibly about 15 RPM and 1,500 RPD for 31B. Check aistudio.google.com/rate-limit | Low [6] |
| Run locally | Ollama `gemma4:e4b` (about 9.6 GB, needs v0.20+). Optional "runs privately" story | Med |
| License | Apache 2.0, open weights | Med |

The quickstart snippet (Python, google-genai, text plus an image) is in research/notes/sponsor-tech.md.

## What has won before
DEV Gemma 4 Challenge winners (2026-06-18) were LIKAS (offline disaster companion), **AccessLens (visual interpreter for blind users)**, p2p-ai, Genie (offline phone agent), and a privacy-first triage co-pilot. The Gemma 3n winner was **Gemma Vision**, an assistant for blind users. (sources: [7], [8])
- **Winning pattern:** a specific user, accessibility or a regulated domain, privacy, and real-world use. None of the winners is a generic chatbot.
- **Already covered:** visual assistants for blind users (twice) and offline disaster apps. Avoid copying these.
- **Likely saturated** (inference, Low): generic chatbots, PDF Q&A, recipe-from-fridge photo apps, plant disease detectors.

## Link to our project
- **Must have:** a visible Gemini API call to `gemma-4-31b-it`, the model named in the README, and **image input at the centre of the demo**, since images are the multimodal input the API actually supports.
- **Show off what Google promotes:** multimodality, function calling or agentic steps, the thinking mode, and long context. A plain chat wrapper won't stand out.
- **Team fit:** Python (Streamlit or FastAPI) and/or a browser extension or CLI, in learning and education or accessibility and health.
- **Gaps that fit us** (inference): accessibility beyond blindness (dyslexia, cognitive load, low literacy), study tools that start from photos of real material, and privacy-sensitive health paperwork.
- **The write-up and README matter.** DEV weights writing most, and MLH checks the README for the model name.
- **DigitalOcean:** optional. Any Gemma 4 project satisfies "open-weight", and hosting on DigitalOcean is suggested, not required. Only do it if it's trivial.

## Open questions
- Which rulebook applies to our event (MLH Hack Day or DEV)? Is there any judging rubric?
- Does Gemma 4 support JSON mode through the API, and what are the real free quotas? Test both at the start of the build.

## Sources
1. DEV Hacktoberfest 2026 hub, https://dev.to/challenges/hf26 (2026, accessed 2026-10-30)
2. MLH Hacktoberfest Handbook, Google Gemma partner challenge, https://hacktoberfest-handbook.mlh.com/hack-days-partner-modules/partner-challenge-google-gemma (undated, accessed 2026-10-30)
3. Internshala, Hacktoberfest HackDay Meerut 2026, https://internshala.com/competitions/?p=12806 (2026, search snippet)
4. Gemma on Gemini API, https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api (undated, accessed 2026-10-30)
5. Gemma 4 model card, https://ai.google.dev/gemma/docs/core/model_card_4 (undated, accessed 2026-10-30)
6. Gemini API rate limits, https://ai.google.dev/gemini-api/docs/rate-limits, and tilnote.io (undated)
7. DEV, Congrats to the Gemma 4 Challenge Winners, https://dev.to/devteam/congrats-to-the-gemma-4-challenge-winners-4fgc (2026-06-18)
8. Hawkdive, Gemma 3n: Developers Transform Lives Uniquely, https://www.hawkdive.com/gemma-3n-developers-transform-lives-uniquely/ (2025-12-10)
