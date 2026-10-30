# TBD (Hacktoberfest 2026): tracker

Last updated: 2026-10-30 12:16 IST by /hack-iterate

## Event

| Field | Value | Source |
|---|---|---|
| Hackathon | Hacktoberfest 2026 (prize categories appear to be a DEV challenge, with an MLH prize) | research/category-open-source-ai-digitalocean.png; URL UNKNOWN |
| Organiser / sponsor | DigitalOcean ("Best Open-Source AI Project"), Google ("Best Use of Gemma 4"), with DEV and MLH prizes | research/category-open-source-ai-digitalocean.png, research/category-gemma-4.png |
| Format | 6-hour hackathon · team (names UNKNOWN) · open innovation within each prize category | User, 2026-10-30 |
| Tracks | 1. Best Open-Source AI Project (DigitalOcean): an original project where open-source or open-weight AI is an important part of how it works, such as an agent skill, an app built on an open-weight LLM or SLM, or an open-source model harness. 2. Best Use of Gemma 4 (Google): build with Gemma 4, a lightweight multimodal open-weights model available through the Gemini API. Suggested directions are a multimodal experience, a focused AI tool, or rapid prototyping. Other categories UNKNOWN | research/category-open-source-ai-digitalocean.png, research/category-gemma-4.png |
| Our track / problem statement | Best Use of Gemma 4 (primary), building on the existing AushNexa project (a prescription safety checker for Indian brand medicines). Gemma 4 is open-weights, so the same project might also qualify for Best Open-Source AI Project if the rules allow entering more than one category | User, 2026-10-30 |
| Submission deadline | 2026-10-30 14:00 IST | User, 2026-10-30 |
| Other dates | UNKNOWN | |
| Prizes | Best Open-Source AI Project: an exclusive Hacktoberfest 2026 Winner DEV badge and an MLH swag bag. Best Use of Gemma 4: a swag bag, keyboard or gift card, depending on region | research/category-open-source-ai-digitalocean.png; https://hacktoberfest-handbook.mlh.com/hack-days-partner-modules/partner-challenge-google-gemma |
| Team | A team (names and roles UNKNOWN) | User, 2026-10-30 |

## Submission requirements

- [ ] Use Gemma through the Gemini API, and show the integration in the code or the demo (source: MLH Gemma partner module)
- [ ] Name the Gemma model (gemma-4-31b-it) in the README (source: MLH Gemma partner module)
- [ ] Public open-source repo with a LICENSE file (expected; not confirmed)
- [ ] UNKNOWN (expected: a write-up post and a demo)

## Judging criteria

Rubric source: FALLBACK (no official rubric found yet)

| Criterion | Weight | What the judges look for |
|---|---|---|
| Impact and usefulness | 25% | |
| Innovation and originality | 20% | |
| Technical execution | 20% | |
| Use of the sponsor's technology | 15% | Gemma 4, especially its multimodal (text and image) abilities |
| Presentation and demo | 10% | |
| Feasibility and business viability | 10% | |

Target weighted score: none (the user set no rating goal on 2026-10-30 12:16; /hack-iterate runs a single iteration)

## Phase status

Hours left at the last update: 2.75 · Ship buffer: 0.75 h (shortened, since the event is under 24 h) · Feature freeze: 2026-10-30 13:15 IST

| # | Phase | Status | Output | Notes |
|---|---|---|---|---|
| 1 | Research | done | research/REPORT.md | Time-boxed pass, no HTML page (under 24 h). The user asked to go straight on to ideas |
| 2 | Ideation | done | docs/IDEAS.md | The user chose to build on the existing AushNexa project instead of the shortlisted ideas |
| 3 | Planning | done | docs/PLAN.md | BUILD_CHECKLIST seeded: 12 MUST, 5 SHOULD |
| 4–6 | Build, test, debug | in progress | docs/ITERATION_LOG.md | core, ai and ui merged at 11:45; 74 tests pass; voice building (due 12:20). App on localhost:8501 |
| 7 | Ship | not started | docs/submission/ | |

Status values: not started · in progress · awaiting review · done

## Settings

- code_repo: code/aushnexa
- commits_allowed: yes (granted by the user 2026-10-30 11:18)
- custom_research_prompt: "TIME-CRITICAL: about 3.5 hours left (deadline 2026-10-30 14:00 IST). Run a minimal pass with no HTML page. Track: Best Use of Gemma 4. Angles: (1) Gemma 4: model sizes, multimodal abilities (image, audio?), context length, Gemini API access (model IDs, free-tier rate limits, SDK quickstart), and on-device options; (2) what has already been built with Gemma, plus past Gemma and DEV challenge winners, so we know what to avoid and what to borrow; (3) whether the DigitalOcean open-source AI category can also be entered (one bullet, low priority). Keep the report short and ideation-ready."

## Artifacts

| What | Local file | URL |
|---|---|---|
| Research report page | | |
| Ideas board page | | |
| Pitch deck | | |

## Decisions log

| Date | Decision | Why | By |
|---|---|---|---|
| 2026-10-30 | Project name is "TBD" | The user chose it | User |
| 2026-10-30 | Primary target is Best Use of Gemma 4 | The user chose it | User |
| 2026-10-30 | Build on the existing AushNexa project (live: https://remix-remix-aushnexa-ai-prescription-safety-medic-9042.ai.studio/). Simplify the cluttered frontend, make it faster, and use Gemma 4 (or another open model) for the AI | It is the team's existing project, and it closely matches the top-scored idea (PillCheck, 7.29) | User |
| 2026-10-30 | Handwriting spike: Gemma 4 26B found 21/21 medicines on 5 real prescriptions (19/21 names right, 0 made up), but took 39–210 s per image with frequent HTTP 500s. Use read → fuzzy-match → confirm, with retries and cached demo results | code/spikes/handwriting/RESULTS.md | Main session |
| 2026-10-30 | Scope: every ⭐ feature, plus a confidence check with doctor-chat escalation and a check of medicines against the patient's condition. Model gemma-4-26b-a4b-it; Ollama gemma4:e4b as an option | The user's request; 26B was more reliable than 31B in the spike | User |
| 2026-10-30 | Demo assets will be synthetic images generated by Claude (labelled as synthetic); the presenter plays the doctor in a second tab | The team needs help with the assets | User |
| 2026-10-30 | Add a voice symptom check (scoped): Whisper STT, Gemma 4 triage with possible causes, code red-flag rules, a Google Maps hospitals link and the doctor chat. SHOULD, cut at 12:50 if shaky | The user's request; it feeds the prescription context | User |
| 2026-10-30 | Beat 5 reworded: Gemma 4 read the ink-blotted Calcimax correctly (robust), so Calcimax goes to MEDIUM via a real different-salt look-alike (Calcimate-CL, calcitonin), and the patient asks a doctor. The 'Celemax' misread is told as a true spike anecdote | Honest demo; Gemma did not misread | Main session |
| 2026-10-30 | 15 real prescriptions tested: the API (26B) reads well but only 9/15 completed (504s); local E4B completed 15/15 in 16–40 s but misreads more. Matcher and confidence were fixed so known-wrong HIGHs went from 4 to 0. GEMMA_FALLBACK=ollama added (API first, local if it fails) | research/test_prescriptions/SCORECARD.md | Main session |
| 2026-10-30 | /hack-iterate: a single iteration only, with no target rating | The user's instruction | User |
| 2026-10-30 | Stack: Python (Streamlit/FastAPI) and/or a browser extension or CLI. Interests: learning and education, accessibility and health | Team strengths | User |

## Open questions

- RULES RISK: AushNexa was built at the MUJ Hypnexis 36-hour hackathon (24–25 Oct 2026, team TRIKΛΛL, research/UQ8W59O1_TRIKΛΛL.pptx). The DEV hf26 rules require a new project built in the window, and MLH events usually expect the work to be done at the event. Does our Hack Day allow building on an existing project?
- Where is the AushNexa source code (AI Studio export or GitHub)? We need it to change anything.

- The user says there is no published URL, rules or rubric, so judging uses the FALLBACK rubric.
- Can one project be entered in more than one category? DEV hf26 says yes; our Hack Day rules are unconfirmed.
- Which rulebook applies to our event (MLH Hack Day module or DEV hf26)?
- Does Gemma 4 support JSON mode through the API, and what are the real free quotas? Test both at the start of the build.
- Who is on the team, and what are their roles?
