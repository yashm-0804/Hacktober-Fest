# Sponsor-tech (Gemma 4): research notes

Hacktoberfest 2026 (Best Use of Gemma 4) · researched 2026-10-30 · by hack-researcher
Time-boxed (~10 min). Several sources are secondary; official Google blog URL guess returned 404. Access date for all: 2026-10-30.

## Key findings
- Model IDs on Gemini API: `gemma-4-31b-it` and `gemma-4-26b-a4b-it` only (E2B/E4B/12B are NOT listed for the API). (source: https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api, undated; page says it is deprecated in favor of gemma.ai) · Med-High
- Release about 2026-04-02 (some say 04-03); Ollama support next day. (source: search aggregation of doolpa.com, dev.to guides, April 2026; no official post fetched) · Med
- Family (official model card): E2B (2.3B eff / 5.1B w/ emb, 128K), E4B (4.5B eff / 8B, 128K), 12B Unified (11.95B, 256K), 26B A4B MoE (25.2B total, 3.8B active, 256K), 31B dense (256K). (source: https://ai.google.dev/gemma/docs/core/model_card_4, undated) · High
- Inputs: text + image on all; audio only on E2B, E4B, 12B (clips up to 30 s); video as frames up to 60 s at 1 fps. Output is text only. (same model card) · High
- Native function calling; configurable thinking mode via `<|think|>` token at start of the system prompt. (same model card) · High
- Gemini API doc page shows: image upload + prompt, system instructions, function calling, multi-turn chat, Google Search grounding, thinking levels "high"/"minimal". So system instructions, images and function calling ARE supported via API. (source: https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api) · Med-High
- Apache 2.0 license (replaces old Gemma terms). (source: aitoolsatlas.ai / doolpa.com summaries, April 2026) · Med
- Ollama: `ollama run gemma4` pulls `gemma4:e4b` (~9.6 GB); also `gemma4:26b`, `gemma4:31b` (31B needs ~24 GB VRAM). Needs Ollama v0.20.0+. (source: dev.to guides, e.g. https://dev.to/emree_demir/gemma-4-lokal-mit-ollama-ausfuhren-eine-vollstandige-anleitung-1h8e, April 2026) · Med

## Answers to the key questions
### 1. Release, sizes, context
See findings: about April 2, 2026; E2B/E4B on-device dense, 12B Unified, 26B A4B MoE, 31B dense; context 128K (E2B/E4B) and 256K (others). (model card URL above) A DataLearner page claimed E4B is 800M params; contradicts official card, ignore.

### 2. Modalities and features
Text/image everywhere, audio on small models + 12B, video via frames; text output only; function calling native; thinking toggle; structured JSON output: NOT confirmed in sources I read (Low; test `response_mime_type="application/json"` early).

### 3. Gemini API access
IDs: `gemma-4-31b-it`, `gemma-4-26b-a4b-it`. Needs a Google AI Studio API key (source: gemma_on_gemini_api page). Rate limits: official rate-limit page (https://ai.google.dev/gemini-api/docs/rate-limits) does not list Gemma 4; says check AI Studio. Official Gemma 3 free tier is 30 RPM / 15,000 TPM / 14,400 RPD (same page, search snippet). A third-party Korean blog (tilnote.io) says Gemma 4 31B free = 15 RPM, unlimited TPM, 1,500 RPD. Confidence Low; verify at aistudio.google.com/rate-limit. Free in AI Studio: plausible but not explicitly confirmed (Low-Med).

### 4. Quickstart (text + image)
Adapted from the standard google-genai SDK; the docs page confirms the pattern (upload image + prompt to generateContent) but I did not capture its verbatim code. UNTESTED; verify.

```python
# pip install google-genai
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_AI_STUDIO_KEY")
with open("photo.jpg", "rb") as f:
    img = f.read()

resp = client.models.generate_content(
    model="gemma-4-31b-it",   # or "gemma-4-26b-a4b-it"
    contents=[
        types.Part.from_bytes(data=img, mime_type="image/jpeg"),
        "Describe this image and suggest three follow-up questions.",
    ],
    config=types.GenerateContentConfig(
        system_instruction="You are a concise tutor.",
    ),
)
print(resp.text)
```

JS equivalent (`npm i @google/genai`): `new GoogleGenAI({apiKey}).models.generateContent({model:"gemma-4-31b-it", contents:[{inlineData:{mimeType:"image/jpeg",data:base64}},{text:"Describe this"}]})`. Untested.

### 5. Other ways to run
- Ollama (`gemma4:e4b`, `:26b`, `:31b`): realistic, best for offline demo if laptop has RAM; e4b easiest (Med).
- Hugging Face, Kaggle, Vertex AI: reported available at launch (doolpa.com, April 2026; Med). Vertex needs GCP setup; skip in 3h.
- Google AI Edge Gallery hosts E2B/E4B on-device (secondhand, Low). LiteRT/MediaPipe browser/Android: not verified; likely too heavy for a short build.
- Recommendation (Inference, Low): Gemini API with `gemma-4-31b-it` is the fastest path; optional Ollama e4b for a "runs locally" angle.

### 6. What Google promotes
Per secondary coverage (not official blog): reasoning, agentic workflows, multimodality, on-device efficiency, built from Gemini 3 research, Apache 2.0, long context (256K). (doolpa.com, aitoolsatlas.ai, April 2026) · Med. Judges likely reward: image+text understanding, function calling/agents, thinking mode, 256K context, audio via E4B locally.

## Things that change how we compete
- API only serves the two large models; audio needs local E2B/E4B/12B (Ollama/HF), not the Gemini API.
- Apache 2.0 + open weights: a "local/private" story is credible.
- Function calling + thinking are native; demoing them beats a plain chat wrapper.

## Conflicts and uncertainties
- Release date April 2 vs 3: trust April 2 (more sources).
- Rate limits: Gemma 3 official numbers vs third-party Gemma 4 numbers; trust neither fully.
- Gemini API doc page is marked deprecated; model IDs could have newer/extra variants on gemma.ai.

## Open questions
- Official launch blog URL and exact date (try blog.google search, gemma.ai).
- Structured JSON output support for Gemma via API.
- Whether 12B / E4B are served by the Gemini API.
- Actual free quotas in AI Studio.

## Sources
1. Gemma on Gemini API, https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api (undated)
2. Gemma 4 model card, https://ai.google.dev/gemma/docs/core/model_card_4 (undated)
3. Gemini API rate limits, https://ai.google.dev/gemini-api/docs/rate-limits (undated)
4. Search roundup of release/sizes (doolpa.com, aitoolsatlas.ai, dev.to Ollama guides), April 2026
5. tilnote.io rate limit post, https://tilnote.io/pages/6a51b3398d9a59d14c1c174c (undated)
