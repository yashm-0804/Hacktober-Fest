# Prior art + event: research notes

Hacktoberfest 2026 (Best Use of Gemma 4) · researched 2026-10-30 · by hack-researcher
Time-boxed (~10 min). Saturation evidence (Q3) and gaps (Q4) are mostly inference; no entry counts were gathered.

## Key findings
- A Hacktoberfest 2026 DEV challenge series exists (MLH + DEV, presenting partner DigitalOcean). Prompt: build a NEW project with open-source AI at its core, and write it up on DEV. (source [1], 2026) · High
- Judging order on the DEV page: writing quality weighted most, then relevance, creativity, technical execution, then optional partner-tech use. (source [1]) · High
- One submission can enter several categories. Each submission is automatically entered for the overall prize and every partner category it qualifies for. (source [1]) · High
- The "Best Use of Gemma 4" card matches the MLH Hacktoberfest Hack Day partner module (Gemma through the Gemini API). The winner must use a Gemma model through the Gemini API, name the model in the README, and show the integration in code or a demo. Prize: a swag bag, keyboard or gift card, depending on region. (source [2]) · High
- The same track appears at local Hack Days (e.g. Meerut, 27 Oct 2026, "Track 1 – Best Use of Gemma 4"). Our 6-hour event is probably a Hack Day, so the DEV-page rules are likely not ours. Check the organizers' rules. (source [3]) · Med
- Winners of the May 2026 DEV Gemma 4 Challenge, "Build with Gemma 4" (announced 2026-06-18; $500 each): LIKAS (offline disaster companion, Philippines, Gemma 4 E2B on-device), AccessLens (on-device visual interpreter for blind users), p2p-ai (peer-to-peer inference network), Genie (offline phone-control agent), a local Postgres triage co-pilot (HIPAA-driven privacy). (source [4]) · High
- Pattern across winners: on-device or offline, privacy by design (the data cannot go to the cloud), accessibility, a specific local or regulated user. None of the five is a generic chatbot. (source [4]) · High
- Gemma 3n Impact Challenge: only one winner is named in what I found. Gemma Vision is a chest-worn camera and controller assistant for blind users, built by someone whose brother is blind. The article is from Dec 2025. (source [5]) · Med
- The Kaggle MedGemma Impact Challenge drew 850+ teams (secondary source) and shows health is a heavily contested niche. (source [6]) · Low

## Answers to the key questions
### 1. Event
- DEV hub: dev.to/challenges/hf26 [1]. It has five challenges (Weekend 2–5 Oct, then Weeks 1–4, with Week 4 running 26–31 Oct). The rules are one submission per challenge, a new project built in the window, no PRs to existing projects, and one win per challenge. [1]
- Submission requirements: a published DEV write-up explaining why open innovation matters for the project. Embedding a DevRelay agent session is optional. [1]
- Prizes: overall $250 + DEV++ + badge. Featured partner categories $200 (Render, TabPFN, Tinker, Qualcomm). Other partner categories $100. All winners get a badge, and everyone with a valid submission gets a completion badge. [1]
- The Gemma 4 prize appears in the MLH Hack Day module [2], not in the part of the DEV page I read. The DEV page was truncated (194k characters unread), so a Gemma 4 category could be in the unread part. The last-week page is https://dev.to/challenges/hacktoberfest-week4-2026-10-26. [1]
- The Gemma-specific DEV Gemma 4 Challenge (May 2026) is closed. Prize pool $3,000 for 10 winners; its separate "Write About Gemma 4" track also paid $100 each. [4]

### 2. Past winners
See key findings. The winning patterns are offline, on-device, privacy-driven, accessibility (blind and low-vision users), disaster resilience and a regulated profession. The Write-About winners (not the build track) leaned on explainers and practical benchmarks, such as variant selection, soft tokens, Android speed tips and tests on real low-end phones in Freetown. [4] Given DEV's writing-first weighting, the write-up matters as much as the build. [1]
I did not find the Google AI Studio or Gemini API Developer Competition winners. Open: kaggle.com/competitions/google-gemma-3n-hackathon.

### 3. Saturated ideas
Inference only, Low confidence; I gathered no entry counts. Generic chatbots, PDF Q&A, recipe-from-fridge photo apps and plant disease detectors are the likely crowd. Evidence in favour: the winners list [4] contains none of these, and the DEV Gemma 4 Challenge was the "most participated-in" DEV challenge to date, so volume of entries is high. [4]

### 4. Gaps (Inference, Low-Med; chosen to match the winning pattern in [4])
- Offline field tools for low-connectivity communities (health workers, farmers, disaster responders). Who: people with unreliable networks. Close to LIKAS, so pick a different vertical.
- Accessibility beyond blindness (deaf or hard-of-hearing captions of sounds, dyslexia, cognitive load). Who: users underserved relative to the visual-assistance crowd (AccessLens and Gemma Vision already cover blind users).
- Privacy-bound professionals (lawyers, clinicians, finance, HR) who cannot paste data into cloud AI. Who: regulated workers, as in the HIPAA Postgres winner.
- Local-language or low-resource-language education on cheap phones. Who: students in regions where [4] notes phones are modest.
- Screenshot or photo-to-structured-data tools for small local businesses (handwritten ledgers, forms), run on-device. Who: small shops.

### 5. DigitalOcean category
The DEV page lists "Best Use of DigitalOcean" ($200), not "Best Open-Source AI Project". Hosting on DigitalOcean (GPU Droplet with 1-Click Models, or an agent on the Gradient AI Platform) is suggested, not required, by the open-AI prompt. [7] A Gemma 4 project would satisfy the open-weights requirement. But the Gemma track requires Gemma via the Gemini API [2], so a DO deployment is optional extra effort. Given only 6 hours, I would host the frontend on DO only if it is trivial. Confidence: Med.

## Things that change how we compete
- The DEV judging weights writing most heavily [1]. Plan time for a strong write-up and README naming the model.
- Verification needs a visible Gemma call through the Gemini API, with the model named in the README. [2]
- Running Gemma locally conflicts with "via Gemini API" verification. Inference: do both (an API path plus a local option), and say so in the README.

## Conflicts and uncertainties
- DEV page (open-source AI prompt, no Gemma category visible) vs MLH module (Gemma 4 track): the MLH module is the more likely source of our track. Which rulebook applies to our event is unconfirmed.
- Category name "Best Open-Source AI Project" was not found; DigitalOcean's listed category is "Best Use of DigitalOcean". [7]

## Open questions
- Full DEV page (offset 100000+) for a Gemma category and the partner list.
- Official Gemma 3n and Gemini API competition winners (Kaggle, Google blog).
- Entry counts for saturation evidence.

## Sources
1. DEV Hacktoberfest 2026 hub, https://dev.to/challenges/hf26 (2026, accessed 2026-10-30)
2. MLH Hacktoberfest Handbook, Google Gemma partner challenge, https://hacktoberfest-handbook.mlh.com/hack-days-partner-modules/partner-challenge-google-gemma (undated, accessed 2026-10-30)
3. Internshala, Hacktoberfest HackDay Meerut 2026, https://internshala.com/competitions/?p=12806 (2026, via search snippet only)
4. DEV, Congrats to the Gemma 4 Challenge Winners, https://dev.to/devteam/congrats-to-the-gemma-4-challenge-winners-4fgc (2026-06-18, accessed 2026-10-30)
5. Hawkdive, Gemma 3n: Developers Transform Lives Uniquely, https://www.hawkdive.com/gemma-3n-developers-transform-lives-uniquely/ (2025-12-10, accessed 2026-10-30)
6. CalcSnippets on MedGemma Impact Challenge, https://calcsnippets-web.pages.dev/blog/medgemma-drawing-850-plus-teams-and-160-plus-guidelines-into-real-healthcare-demos-is-the-kind-of-open-medical-ai-signal-the-market-should-not-ignore.html (undated, search snippet only)
7. DEV Hacktoberfest Week 1 page, https://dev.to/challenges/hacktoberfest-week1-2026-10-05 (2026, via search summary)
