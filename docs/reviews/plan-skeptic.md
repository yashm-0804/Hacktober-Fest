# Skeptic review: AushNexa build plan (docs/PLAN.md)

2026-10-30 · 2.8h left (1h50m of build before the 13:15 freeze) · Verdict: SERIOUS

## Steelman

This is a prescription safety checker with Gemma 4 vision at its centre. Gemma reads a messy Indian prescription, deterministic code checks every name against 254k real brands and flags duplicate salts and allergy conflicts, and anything uncertain goes to a human doctor instead of being guessed. The spike showed the read step works (21/21 medicines detected, 0 made up, struck-out drug excluded). The split "the model reads, code decides, a human confirms" is a credible and judge-friendly answer to "LLMs hallucinate in medicine". Sponsor fit is strong: image input is core, not bolted on.

The plan is unlikely to fail on the idea. It is likely to fail on three things: (a) the star beat rests on a misread that the dataset turns into a confident match, (b) the Gemma latency budget is planned as if calls were fast, and (c) too many MUSTs for 110 minutes.

## Objections (ranked, most damaging first)

### 1. The star beat (5) won't produce LOW confidence: "Celemax" is a real brand in the dataset. Severity: Fatal (to the beat as written)
- Evidence: `updated_indian_medicine_data.csv` line 38510 is `Celemax 500mg Tablet, Ajanta Pharma, Cefuroxime (500mg)`. Calcimax only exists as `Calcimax ISO Capsule` (line 34278, calcium carbonate + calcitriol). There is no plain Calcimax, Calcimax P or Calcimax 500. Under the plan's confidence formula, Gemma's "Celemax" scores about 100 against a real row. The gap to the runner-up (Celemix Infusion) is likely over 5 points. Gemma gave it 0.9 and did not flag it unsure (spike RESULTS.md), so there's no unsure penalty. If no strength was read, there's no strength penalty. The total lands at about 0.9–1.0, so the row is **HIGH confidence cefuroxime**, not "Celemax?" LOW.
- Second problem: the spike images are banned from the demo (RESULTS.md line 3), so the team must handwrite its own prescription. Nobody can make Gemma misread a name on cue. If the scrawl reads cleanly, there's no escalation. If it's deliberately illegible, a judge may read it as staged.
- Why it costs points: Presentation (10%) and Technical execution (20%). The one memorable moment either doesn't happen or contradicts the "code catches it" claim live.
- What would resolve it (by 11:45):
  1. Run `candidates("Celemax")` and the team's own handwritten prescription through Gemma once, and write the beat around what actually comes back.
  2. Reframe the beat. It's stronger as written below anyway: "Gemma read *Celemax*. That's a real antibiotic (cefuroxime, a cephalosporin). A naive OCR-then-lookup app would hand you the wrong drug."
  3. Make the escalation trigger deterministic. Add a lookalike rule: if a candidate with a *different salt signature* is within about 20 points (Celemax vs Calcimax), cap the band at LOW. Also add penicillin → cephalosporin "cross-reactivity caution" to `allergy_classes.json`, and allow "Ask a doctor" on any row that has an alert or a band below HIGH.
- Cut: nothing. This is a rewrite of one rule and one beat, not new scope.

### 2. The Gemma latency budget is planned as if calls were fast. The cache-warm window and the post-doctor re-run both break. Severity: Serious
- Evidence:
  - Spike: 39–210 s per image in parallel, 37 s for a single image. HTTP 500s hit about half of the 26B follow-up calls and 4 of 5 parallel 31B calls. Parallelism made it *worse*, but the plan runs 3 vision calls in parallel.
  - 3 of the 4 prompts (strip, report, assess+Hindi) have never been run. At 1–4 minutes per attempt, three iterations each is about 30+ minutes of pure waiting.
  - Cache warming is scheduled for 13:05–13:15. That's 10 minutes for 3 vision calls plus 1 text call at a 50% failure rate, with 3 retries and backoff. The worst case exceeds the window.
  - In beat 5, the doctor's correction changes the medicine list. `assess_context(context, meds)` then has a new cache key, so a **live 40–200 s Gemma call happens in the middle of the star beat**.
  - The cache key includes the image bytes, so any prompt tweak after warming, or using `st.camera_input` (new bytes on every capture), causes a cache miss during recording.
- Why it costs points: Technical execution, and the demo itself. A spinner that runs for minutes in the video, or a 500 error card, is fatal to the 2-minute cut.
- What would resolve it:
  - Warm the cache with the *final* demo photos at about 11:45–12:15, in a background terminal, and freeze the prompts after that.
  - Set a hard per-call timeout (google-genai `HttpOptions(timeout=90_000)`) and a total wall-clock budget of about 120 s, then fall back to typed input.
  - Cap concurrency at 2.
  - After the doctor confirms, re-run only the deterministic checks (duplicates, allergy, strip, schedule) and reuse the existing Hindi summary. Don't call Gemma again.
  - Use `st.file_uploader`, not `camera_input`, in the demo.
  - When replaying from cache, show the original latency ("read in 52 s at 11:58, replayed from cache") rather than "0 ms", which looks like a mock.
- Cut: `read_report` (the report photo) entirely, since a typed condition does the same job. Merge assess and Hindi into the single text call already planned, and don't re-run it.

### 3. 11 MUSTs plus 4 SHOULDs in 110 minutes, and the demo assets aren't on the timeline. Severity: Serious
- Evidence: the MUST list covers a data preprocessing script, `llm.py` with 2 backends, cache and retries, 4 prompts, match, confidence, a 5-function safety engine, 2 hand-curated JSON files (allergy classes, about 30 Jan Aushadhi prices), SQLite chat, and 3 Streamlit pages with about 12 states. The AI agent can type the code quickly. The bottleneck is the real-API verification loop from objection 2, which can't be parallelised. Physical assets aren't scheduled anywhere: a handwritten prescription containing Dolo 650, Combiflam, Augmentin and the Calcimax scrawl, a real **Dolo 500 strip** to photograph for beat 6, and two screens for the doctor. Curating about 30 Jan Aushadhi prices by hand takes about 20 minutes of human time, or else the agent invents them, which is a credibility risk in a medical demo.
- Why it costs points: everything. If M2 slips past 12:45, the plan's own cut order (F3, then C2, then B1) drops things that are barely in the demo, while the expensive items (report photo, Gemma fit scoring, 30-salt price table) survive.
- What would resolve it, using a cut order that saves real time:
  1. The report photo (CTX-1 photo part).
  2. Gemma's fit judgment *changing confidence*. Show it as information only, or drop it. Code already handles the allergy check.
  3. The Test Lab page. Keep pytest and show its terminal output in 3 seconds of video.
  4. The Ollama toggle in the demo. One sentence and the README are enough.
  5. Jan Aushadhi cut to the 3–4 salts in the demo prescription, with prices taken from the official PMBJP product list.
- Add to M0: one person makes the demo assets (prescription and Dolo 500 strip) by 11:40.

### 4. Submission and rules unknowns have no owner, and "ask the organisers before submitting" is too late. Severity: Serious
- Evidence: PLAN.md lists the video format and submission platform as "UNKNOWN; confirm with the organisers". The rules risk (AushNexa was built at MUJ Hypnexis on 24–25 Oct) is mitigated by "Ask the organisers before submitting". HACKATHON.md settings say `code_repo: TBD` and `commits_allowed: no`, but a public repo with a LICENSE is a requirement. The ship buffer (13:15–13:55) has to cover the README, a 2-tab choreographed video, its upload, and the form.
- Why it costs points: disqualification or a missed deadline zeroes the whole score.
- What would resolve it:
  - At 11:20, one human asks the organisers three questions: are prior-hackathon concepts allowed, what video length and format, and where to submit.
  - At M0, create the public GitHub repo with LICENSE (MIT), a README stub naming `gemma-4-26b-a4b-it`, and dataset attribution.
  - Start recording at 13:15 sharp from a written shot list.
  - Note that HACKATHON.md says to name `gemma-4-31b-it`. Name the model actually called, and say 26B in both the README and the trace.

### 5. The confidence formula marks correct reads MEDIUM, and the data columns the plan relies on are mostly empty. Severity: Serious
- Evidence:
  - The dataset has duplicate names: `Dolo 500 Tablet` appears twice (lines 58334 and 60349). Form-word stripping collapses `Combiflam Tablet` and `Combiflam Suspension` (lines 33913 and 33996) into the same `base_name`. In both cases the top-2 gap is 0, so a correct read loses 0.15. A clean Combiflam lands at exactly 0.85, the HIGH/MEDIUM boundary, and Augmentin has several 375/625/1000/Duo variants that will crowd each other the same way. A demo table that's mostly MEDIUM looks broken.
  - Separately, `grep -c ',,,,$'` gives **246,485 of 253,972 rows** with empty `salt_composition`, `medicine_desc`, `side_effects` and `drug_interactions` (for example, the Celemax row). A preprocessor that reads `salt_composition` gets no salts for about 97% of brands, and CTX-1's "fit using `medicine_desc`" has no text for them. The demo drugs (Dolo 650, Combiflam, Augmentin) do have descriptions, so the demo hides the problem but a judge's ad-hoc test won't.
- Why it costs points: Technical execution, and Impact if a judge tries their own brand.
- What would resolve it:
  - Parse salts from `short_composition1` and `short_composition2`, which are populated for Celemax and Calcimax ISO.
  - Collapse candidates with the same salt signature before computing the gap, and only apply the gap penalty when the top-2 candidates differ in salts.
  - Pass the salt list, not the description, to the fit prompt.
  - Assert in a pytest that Dolo 650, Combiflam and Augmentin 625 each come out HIGH when read cleanly.

### 6. Streamlit live polling for the doctor chat. Severity: Manageable
- Evidence: `st.fragment(run_every=...)` is stable in Streamlit 1.37 and later, and two browser tabs reading a shared SQLite file works. The traps:
  - A full-app rerun (any widget click) interrupts a script that is mid-way through a 40–200 s Gemma call.
  - A fragment refresh doesn't redraw the medicine table outside the fragment unless it calls `st.rerun(scope="app")`.
  - If pipeline results aren't stored in `st.session_state`, the rerun recomputes everything (objection 2).
  - SQLite access from multiple sessions needs `check_same_thread=False` and short-lived connections.
- What would resolve it: store all pipeline outputs in session_state. Make the doctor-resolved check inside the fragment call `st.rerun(scope="app")`. Have the manual "Refresh" button ready from the start, so the video can use it if polling misbehaves. Test the two-tab round trip by 12:30.
- Cut: none. Keep it small (no typing indicators, no unread counts).

### 7. rapidfuzz over 254k names. Severity: Manageable
- Evidence: one `process.extract` over about 250k short strings takes on the order of tenths of a second per query on a modern Mac, which is fine for 5–8 medicines. The real risks are reloading the CSV on every Streamlit rerun, and partial-ratio scorers over-rewarding short reads like "DNS", which the spike saw as "DWS".
- What would resolve it: load once with `@st.cache_resource`, pre-lowercase the names, and use `limit=10` with `score_cutoff`. Time one query at M0. If it takes over 1 s, pre-bucket the names by their first 2 letters.

### 8. The storyline is too dense, and parts will look staged. Severity: Manageable
- Evidence: 8 beats in 2 minutes is about 15 s each, but beat 5 (tap, switch screen, doctor reads, types, confirms, patient updates) needs about 35 s on its own. Three parts invite a "this is staged" reading: a "cache hit, 0 ms" trace, a deliberately scrawled name, and a teammate "doctor".
- What would resolve it: merge beats 2 and 3, and cut beat 8 down to a voice-over line. Show the original latency on cached runs. Keep the "Demo: a teammate plays the consultant" label visible in the console header.

## Kill criteria
- **11:45:** the team's own handwritten prescription hasn't been through Gemma once. Make typed input the primary demo path and use the photo only as a cached replay.
- **11:50:** `candidates("Celemax")` returns HIGH under the current formula and the lookalike rule isn't in. Don't build beat 5 around "Celemax?" any more.
- **12:10:** the thin slice doesn't work end to end on typed input. Cut the strip check, the Hindi summary and Jan Aushadhi to template-only.
- **12:30:** the two-tab doctor round trip through SQLite fails. Use the manual Refresh button only. If it's still failing at 12:45, replace it with an in-page "doctor review" panel on one screen.
- **During cache warming:** any call takes over 120 s, or there are 2 consecutive 500s. Stop live calls and demo from cache and typed input only.
- **13:15:** there's no complete cached run of the exact final demo photos. Record the video on the typed-input path. Don't attempt live calls on camera.
- **At any time:** the organisers say concepts from a prior hackathon aren't allowed. Settle the README framing immediately. Don't discover this at 13:55.

## The 3 changes that most raise the chance of shipping on time
1. **Fix the star beat with data, now.** By 11:45, test `candidates("Celemax")` and the team's own handwritten prescription. Rewrite beat 5 as "misread → a real but wrong drug (cefuroxime) → caught". Add a lookalike rule for different salts within about 20 points, and the penicillin → cephalosporin caution, so escalation fires deterministically.
2. **Move cache warming from 13:05 to 11:45–12:15, and remove Gemma from the post-doctor path.** Freeze the prompts, add hard timeouts, cap concurrency at 2, use the file uploader, and run only deterministic checks after the doctor confirms.
3. **Cut the expensive items that don't show in the demo, and give logistics an owner.** Drop the report photo, fit scoring that changes confidence, the Test Lab page and the on-camera Ollama toggle, and cut Jan Aushadhi to the demo salts. At 11:20, one human asks the organisers about rules, video format and platform, creates the public repo with LICENSE and a README naming `gemma-4-26b-a4b-it`, and makes the demo assets.
