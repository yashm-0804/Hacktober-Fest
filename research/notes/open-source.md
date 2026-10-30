# Open-source and open data: research notes

Hacktoberfest 2026 (MLH Hack Day, Best Use of Gemma 4) · researched 2026-10-30 · by hack-researcher

Time-boxed (~8 min). Many items are UNVERIFIED (flagged). Verify license on the page before shipping.

## Key findings
- Best dataset: junioralive/Indian-Medicine-Dataset on GitHub, 253,973 medicines, CSV+JSON, MIT. Columns: id, name, price(INR), Is_discontinued, manufacturer_name, type, pack_size_label, short_composition1, short_composition2 (source [1], page undated; third-party mirror says created 2023-11-26, last push Dec 2024 [2]) · Confidence: High on columns/license/size, Med on dates. Its data origin is not stated, so the MIT license may not clear the underlying scraped data (Inference, Low).
- Composition is split into 2 columns (short_composition1/2), with strength embedded in the string like "Paracetamol (650mg)". Only two salts per row, so 3+ ingredient combos may be truncated (Inference from columns, Low) [1].
- Kaggle "A-Z Medicine Dataset of India" page NOT found by search; a Kaggle mirror "Indian Medicine Data" (mohneesh7) has 195,605 rows with sub_category, product_name, salt_composition, product_price, product_manufactured, medicine_desc, side_effects, drug_interactions; license not shown [3]. The side_effects/drug_interactions text columns are useful for LLM explanation but are unvetted scraped text · Confidence: Med.
- Jan Aushadhi: no CSV or GitHub mirror found. Official data is PDF price/drug-code lists on pmbi.co.in; basket is 2,047 medicines per a 2026 parliamentary answer [4]. Plan: hand-curate or parse the PDF into ~50-100 rows for the demo salts · Confidence: Med.
- NIH RxNav Drug-Drug Interaction API was retired ~2 Jan 2024 per the official RxNav news page [5]; RxNorm name normalization remains (third-party claim, not confirmed officially) [6]. Do not rely on it · Confidence: High.
- DDInter: data under CC BY-NC-SA 4.0 per the official terms page; one third-party site says CC-BY, ignore it [7]. Non-commercial hackathon use is fine with attribution; ShareAlike applies to derived data · Confidence: High.
- MedGemma: latest found is MedGemma 1.5 4B multimodal (Jan 2026) and MedGemma 1 (4B, 27B text, 27B multimodal), all "built on Gemma 3"; terms are Health AI Developer Foundations terms (not Apache) [8][9]. No Gemma 4-based MedGemma found, and no MedGemma 2 found [8]. Distribution: Hugging Face and Vertex [8]; Gemini API availability not documented, so assume NOT reachable via Gemini API. For the Gemma 4 track, use gemma-4-31b-it only; MedGemma would not count · Confidence: Med.
- MIRAGE paper (arXiv 2410.09729): fine-tuned LLaVA 1.6/Idefics2, ~82% on medicine name+dosage extraction from simulated Indian handwritten prescriptions; 743,118 records, 21,075 unique brand names, only 100 labeled records released [10]. Use the idea (brand-name vocabulary + fuzzy match), not the data/models · Confidence: Med.

## Answers to the key questions

### 1. Indian brand/composition datasets
| Dataset | URL | License | Size/format | Date | How we'd use |
|---|---|---|---|---|---|
| Indian-Medicine-Dataset (junioralive), 90 stars | https://www.github.com/junioralive/Indian-Medicine-Dataset [1] | MIT | 253,973 rows, CSV/JSON | pushed Dec 2024 (mirror [2]) | Load into SQLite; brand to salts+strength; price for savings; fuzzy match OCR output |
| Kaggle "Indian Medicine Data" mirror (mohneesh7) | https://baselight.app/u/kaggle/dataset/mohneesh7_indian_medicine_data [3] | not shown (unknown) | 195,605 rows x 8 cols | undated | Backup; has drug_interactions and side_effects text |
| Kaggle "A-Z Medicine Dataset of India" | not found | unknown | ~250k (per user) | n/a | Likely the same family as above; verify on kaggle.com |
| CDSCO lists | not researched | unknown | n/a | n/a | Skipped for time |
Answer to columns: brand, composition, manufacturer, price all present in [1]; strength is inside the composition string [1].

### 2. Jan Aushadhi / PMBJP
Official: PMBI price/drug-code PDFs (e.g. https://www.pmbi.co.in/old-data/PriceListDec2014.pdf, old, 2014, do not use for prices) [11]; the 2,047-medicine basket figure is from a 2026 parliamentary answer [4]. No official CSV or GitHub mirror found. License unknown (government publication; do not assume). Use: curate a small salt to (generic name, pack, MRP) table from the current PMBI list; match on salt+strength. Confidence: Med. Open: find the current PDF at janaushadhi.gov.in / pmbi.co.in.

### 3. Drug-drug interaction data
- RxNav interaction API: discontinued ~2024-01-02 [5]. High.
- DDInter: CC BY-NC-SA 4.0 [7]; has a downloadable CSV by ATC category (Inference from the paper/site, not fetched; Low); ID: https://ddinter.scbdd.com ; biothings wrapper https://github.com/biothings/DDInter [7].
- TWOSIDES/OFFSIDES, DrugBank open subset, openFDA label API terms: NOT verified (search returned nothing). openFDA rate limits per third-party docs: 240/min, 1,000/day per IP without a key, 120,000/day with one [12]; license field points to https://open.fda.gov/license/ [12]. Do not state these licenses in the submission without checking.
- Offline small JSON: Inference only, nothing found ready-made. Recommended: hand-write ~20-30 high-impact interaction pairs (e.g. warfarin+NSAID, ibuprofen+aspirin, ACE-i+NSAID) plus duplicate-salt and allergy-class rules (penicillin class: amoxicillin, ampicillin, piperacillin) in a rules JSON. For a hackathon, deterministic rules for the demo cases beat a big DB. Low confidence.

### 4. Open-source projects
- amjd/GenMed: SMS bot for generic alternatives and prices, MIT, 2 stars; powered by TrueMD.in API, so little to borrow [13].
- Adit31/Medicine-Search: alternatives by chemical composition using medicine_dataset.json; license/stars not checked [14]. Idea: same-composition match.
- coderarham/PharmaVision: Flask app exploring Indian pharma data; license/stars not checked [14].
- Indian Medicines MCP server (mcp.so listing): fuzzy name match, composition analysis, alternatives with savings; repo not found [14].
- MIRAGE (paper, not repo): see key findings [10].
- upchaar-aayog (ajaynegi45), listed on goodfirstissue.org, unverified content [14].
No duplicate-salt checker or prescription-reconciliation repo was found in the time available. Best project to borrow ideas from: Adit31/Medicine-Search (composition-based alternatives), but the code is small; value is the approach. Confidence: Low-Med.

### 5. Open models
- MedGemma 1.5 4B (multimodal) and MedGemma 1 (4B, 27B text, 27B multimodal): built on Gemma 3; HAI-DEF terms; HF/Vertex [8][9]. Not on the Gemini API per docs [8] (not stated either way; Low). Gemma 4 sizes per Google docs: E2B, E4B, 31B, 26B A4B (one page mentions 12B; conflict unresolved) [15]. MedASR released with MedGemma 1.5 [9]. FunctionGemma is Gemma 3 270M [16].
- No Indian-medicine or prescription-specific open model found; MIRAGE models not released (only 100 records) [10].

### 6. Game-changer ideas
1. Strip/box photo to salt + Jan Aushadhi price: Gemma 4 vision reads the label; brand fuzzy-match against Indian-Medicine-Dataset [1]; price from curated PMBI table [4].
2. "Duplicate salt radar": union of salts across all brands plus combos (short_composition1/2) [1]; deterministic count by normalized salt name, so no LLM risk.
3. Allergy class expansion: penicillin to amoxicillin/ampicillin/co-amoxiclav via a small hand-built class map (own data; Inference).
4. Interaction layer from DDInter pairs for top 100 salts (CC BY-NC-SA, attribute) [7], with the LLM only explaining.
5. Savings meter: total monthly cost brand vs Jan Aushadhi, using price columns [1][4]. Bonus for open-source category: publish the pipeline MIT/Apache and cite datasets.

## Things that change how we compete
- MedGemma is Gemma 3-based and not on the Gemini API, so it is neither needed nor eligible for the Gemma 4 track; frame "deterministic safety + Gemma 4 explain" as the story.
- Jan Aushadhi data is the scarce asset; a small clean curated table is a differentiator.
- Dataset origin of [1] is undocumented (likely scraped); disclose it as a demo dataset, not clinical.

## Conflicts and uncertainties
- DDInter license: official CC BY-NC-SA 4.0 [7] vs third-party "CC-BY-4.0" claim; trust official.
- Gemma 4 sizes: 4 sizes vs a mention of 12B [15]; irrelevant since we use 31B.
- Dataset counts: ~250k (user), 253,973 [1], 195,605 [3]; different datasets or versions.

## Open questions
- Kaggle A-Z dataset URL and license; CDSCO lists (not searched).
- Current PMBI product list URL and format.
- TWOSIDES, DrugBank open subset, openFDA licenses (not verified).
- Whether any Gemma 4 MedGemma exists (none found as of search).
- Stars/licenses of Medicine-Search, PharmaVision.

## Sources
1. Indian Medicine Dataset (junioralive), https://www.github.com/junioralive/Indian-Medicine-Dataset (undated, accessed 2026-10-30)
2. Related listing, https://awesome.ecosyste.ms/projects/github.com%2Fjunioralive%2Findian-medicine-dataset (undated, accessed 2026-10-30; via search snippet)
3. Baselight mirror of Kaggle mohneesh7 dataset, https://baselight.app/u/kaggle/dataset/mohneesh7_indian_medicine_data (undated, accessed 2026-10-30; search snippet)
4. Indian Pharma Post / parliamentary answer (2026), https://www.indianpharmapost.com/policy/lite/govt-targets-25000-jan-aushadhi-kendras-by-march-2027-21058 and https://eparlib.sansad.in/bitstream/123456789/2973987/1/AU56.pdf (2026, accessed 2026-10-30; via search snippet, not fetched)
5. RxNav news, https://www.lhncbc.nlm.nih.gov/RxNav/news/news.html (notice 2023-07-03, accessed 2026-10-30; snippet)
6. DEV Community post, https://dev.to/ben_feeney_f0074083491ec6/the-nlm-drug-interaction-api-is-gone-heres-what-to-use-instead-2ac7 (undated; author promotes own product)
7. DDInter terms, https://ddinter.scbdd.com/terms/ and https://github.com/biothings/DDInter (undated, accessed 2026-10-30; snippet)
8. MedGemma, Google HAI-DEF, https://developers.google.com/health-ai-developer-foundations/medgemma (updated 2026-01-13, accessed 2026-10-30)
9. Digital Health News on MedGemma 1.5/MedASR, https://www.digitalhealthnews.com/google-launches-medgemma-1-5-medasr-to-broaden-healthcare-ai-capabilities (Jan 2026; snippet)
10. MIRAGE, https://arxiv.org/abs/2410.09729 (Oct 2024, accessed 2026-10-30; snippet)
11. PMBI price list, https://www.pmbi.co.in/old-data/PriceListDec2014.pdf (2014)
12. openFDA third-party docs, https://cdn.jsdelivr.net/npm/@saibolla/ada@0.1.3/skills/fda-database/references/api_basics.md (undated; unofficial)
13. GenMed, https://github.com/amjd/GenMed (undated, accessed 2026-10-30)
14. Search listing, results for Medicine-Search https://www.github.com/Adit31/Medicine-Search, PharmaVision https://github.com/coderarham/PharmaVision, MCP https://mcp.so/ja/servers/indian_medicine_mcp_server (undated; snippets only)
15. Gemma 4 model card, https://ai.google.dev/gemma/docs/core/model_card_4 (snippet only)
16. BioSpectrum India, https://biospectrumindia.com/news/16/27196/google-announces-new-additions-to-gemma-open-model-family-to-advance-ai-in-healthcare-in-india.html (2026-01-19)
