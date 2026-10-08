# Style notes: Network Analysis (ITU) student project decks

Sources studied: Christian_Wiktor_NA_project.pdf (20 slides, "Chicago road network", missile-strike robustness),
MaleneNAExamPowerPoint.pdf (22 slides, "Anybeat Social Network", link prediction),
Giulia_NA_Project.pptx (17 slides, "HIV Transmission Network", SIR / SIR+ simulation).
All three were inspected as rendered images plus extracted text; Giulia's deck also via slide XML and embedded media.
Giulia's deck is the closest in kind to our project (simulation on a network with protection/vaccination).

## 1. Deck anatomy

Slide counts: 17, 20, 22 (main body ~13-15 plus "Extra Slides"/appendix). Aim for ~15-18 main slides.
All decks are 16:9 (960x540 pt, 720x405 pt, and 13.333x7.5 in).

### Christian & Wiktor (20 slides)
1 Title ("Network Analysis Project", Group 11, names + ITU emails) / 2 Contents of the Presentation (6 icon+label items) /
3 Network Description / 4 Network Statistics / 5 Visualization / 6 Degree Distribution /
7 Simulation of missile strikes in Chicago (research question + 4 bullets) /
8 Chicago simulation comparison: Random Attacks VS. Strategic Attacks / 9 Chicago Strategic Bombardment Visualization /
10 Constructing a random planar graph / 11 Main issues when implementing a planar graph /
12 Parallel computing of betweenness centrality / 13 Random network simulation comparison /
14 Results & Conclusion / 15 Further Research / 16 Extra Slides (divider) / 17 Motivation /
18 Appendix A: Code snippets / 19 Random PA network simulation comparison / 20 References.
Note the unusual choice to put Motivation in the appendix, and References last (after the divider).

### Malene's group (22 slides)
1 Title (course code BSNEANA1KU, "Anybeat Social Network", Group 21, names) / 2 Project outline (6 numbered coloured circles) /
3 "1. Network description" / 4 "2. Problem statement and Research Question" / 5 "3. Network statistics" /
6 Social Dynamics of Centrality / 7 Centrality Node Table / 8 Degree Distribution of the network /
9 "4. The Heuristics" (pipeline diagram) / 10 Common Neighbour (CN) / 11 Adamic Adar (AA) / 12 Resource Allocation (RA) /
13 Jaccard coefficient / 14 Preferential Attachment / 15 "5. Improvements" (meme image) / 16-17 Community detection (x2) /
18 Leiden communities / 19 Results / 20 "6. Conclusions" (summary table) / 21 Extra Slides / 22 Resources.
Section numbers in titles mirror the outline slide ("1. ... 6.").

### Giulia's group (17 slides)
1 Title "HIV TRANSMISSION NETWORK" + 4 names (no emails) / 2 Contents (9 items) / 3 Network Introduction /
4 Our Network (Largest Connected Component) / 5 Other Centrality Measures / 6 Communities / 7 Degree Distributions /
8 Power-Law? / 9 Research Question / 10 SIR Model / 11 "SIR... SPWPSPIWPIIM Model...?" / 12 SIR Model (first 30 cycles) /
13 SIR+ Model / 14 SIR+ Model (heatmaps) / 15 Interpretation & Conclusion / 16 Future work / 17 Thank you for your attention! (+ references line).

### Common running order
Title -> Contents/outline -> Network description (type, what nodes/edges are, source) -> Network statistics (table/tiles) ->
Network picture -> Degree distribution -> (centralities / communities / power-law) -> Research question -> Method or model ->
Results (plots) -> Conclusion -> Further research/Future work -> Extra Slides divider -> appendix (code, extra plots) -> References/Resources.
Research question comes either right after the description (Malene, Giulia) or just before the simulation (Christian). References are always last or on the last slide, never in the main flow. No separate "Limitations" slide in any deck: limitations appear inside Conclusion or Future work.

## 2. Slide density

- Very sparse. Typically 2-5 text items per slide; most slides are one figure plus 1-4 short lines.
- Bullets: 3-6 per slide max (Christian "Further Research": 5; "Missile strikes": 4 but long, up to ~25 words, the densest slide). Typical bullet 4-12 words, fragments, no full stops (Giulia: "Initial Infected: 10", "Average degree: 7.91"). Malene's explanation slides use 1-2 sentence paragraphs (20-40 words) in smaller text; these are the weakest slides.
- Key/value lines ("Label: number") are the dominant pattern for statistics.
- Titles: 1-6 words, 12-45 characters, Title Case or sentence case, no trailing punctuation (except "?" in "Power-Law?"). Giulia: "Network Introduction", "Our Network (Largest Connected Component)". Malene prefixes section numbers ("3. Network statistics"). Subtitles/parentheticals used for qualifiers ("(first 30 cycles)", "(Ridiculogram)").
- Big-number tiles for headline stats (Christian: Nodes 12,979, Edges 39,018, Avg degree 3.01, Diameter 106 in four boxes).
- Speaker narration clearly carries the argument; slides are prompts, not documents.

## 3. Figures

- 1-2 figures per slide; side-by-side pairs are the norm (Giulia degree distributions, SIR without vs with protection; Christian random vs strategic attack curves; Malene two Leiden plots). Never 3+ plots except Giulia's 3-panel heatmap strip, which is one image.
- Almost all plots are matplotlib/seaborn screenshots pasted as PNG (white background, default fonts, default blue/orange/green/red line colours, in-plot titles like "SIR Model Spread", grid on). Axis labels, legends and in-plot titles are visible but small; they are often hard to read when scaled (Christian's attack curves; Giulia's heatmaps have tiny tick labels). Avoid this: make fonts large.
- Network pictures are tool output, not drawn: Giulia's are Gephi-style dark-background force layouts (orange nodes on black; one coloured by community), Christian's is a geographic node-link plot of the road graph with green/red edge colouring and a legend in text beside it. Malene has no real network drawing; she uses decorative node-and-edge clip art in the corners and hand-built circle diagrams.
- Captions: essentially absent. Instead the figure title lives in the slide title or in the plot's own title; Christian puts the key result number as a label under each plot (4080.72, 199). Worth copying: a single bold number under each curve.
- Pairs of before/after panels are labelled with header text above ("Without Protection" / "With Protection") plus the parameter list below each (Initial Infected: 10, Infection spread chance: 0.1 ...).
- Decorative stock imagery is used heavily by Christian (Chicago skyline, missile, aerial photo, clock, bridge) and Giulia (virus renders, AI-generated lab scene), memes by Malene (cats). Good for tone, not necessary; do not copy memes.
- Animation: Giulia embeds a 13 MB animated GIF of the SIR run on slide 12 ("first 30 cycles"). That is the precedent for our animation slide.

## 4. Visual style

- Page: 16:9 landscape, white (or near-white, Malene's is off-white cream) background on content slides. Christian mixes dark photo/black full-bleed slides for title, stats, and section dividers; Giulia is pure white with the default Office theme (Calibri / Calibri Light, title 44 pt, body 20-28 pt, labels 17-18 pt, confirmed in XML).
- Fonts: Giulia Calibri / Calibri Light / Arial; Christian a clean Office-default-looking sans (titles ~28-32 pt at 960 pt width, body ~12-14 pt); Malene a sans (title ~20 pt at 720 width, body 8-10 pt). Take Calibri titles 36-44 pt, body 20-28 pt.
- Colours: Christian uses an orange and dark green pair for panels and a thin orange rule under the title; Malene uses a four-colour pastel set (red, yellow, green, cyan circles, numbered 1-4) with dotted network clip art in corners; Giulia is monochrome with photos providing colour. Accent colours are used for numbered bullet circles, table header fill (orange header, light-peach banded rows in Christian; pale yellow table in Malene) and highlight rows.
- Titles sit top-left, left-aligned in all three decks (Christian a few centred). Christian adds a thin orange horizontal rule under titles on ~8 slides; that is the only recurring ruling device.
- Boxes: coloured rectangles for Q&A pairs (Christian "Network Description", "Motivation"); light-grey card rows with an icon each for problem/solution lists (Christian slide 12).
- Slide numbers/footers: none in any deck. Only Malene has the course code on the title slide.
- Contents slide: icon in a coloured circle + 2-word label, 6 items in a 3x2 grid (Christian) or numbered coloured circles in a 2x3 grid (Malene).

## 5. Network-analysis conventions

Metrics reported (union): nodes, edges, directed/undirected, unipartite/unweighted, density, average and median degree, diameter,
average path length, global clustering coefficient, degree distribution (histogram, log-log scatter, CCDF), centralities
(degree, closeness, betweenness, eigenvector), largest connected component, communities with number of communities, size range and modularity,
power-law fit vs log-normal vs exponential (log-likelihood ratio R, p, KS D), link-prediction AUC and average precision, robustness (attacks needed to collapse the giant component).
Assortativity is NOT reported by any deck; do not pad with it unless used.

- Network introduction: type of network (undirected/unipartite/...), what a node and an edge are, data collection period and source (Giulia: "gathered between 1988-2001", three datasets, 121028 original edges) before any numbers.
- Reduce to the Largest Connected Component and state it (Giulia: 5743 nodes, 22710 edges, avg degree 7.91, median 6, avg path length 6.89, diameter 21, clustering 0.407; communities ~95, modularity 0.87).
- Tables: small, 3-5 columns, 4-8 rows; header row coloured; numbers to 2-4 decimals; top-5 node lists written as `'283': 0.036, 204 (degree)` (node id, centrality, raw degree). Malene's centrality table maps metric -> "academic focus" (Popularity/Visibility, Information Brokerage, Access Efficiency, Network Prestige) -> top node -> score: a good reading aid to copy.
- Network picture: single layout plot with a colour legend written as text beside it, plus 1-2 numbered assumptions/interpretations. Giulia colours by community.
- Degree distribution: shown twice in Giulia (largest component vs entire network, log-log count vs degree, orange dots), followed by a formal power-law test slide listing R, p, D. Comparing fits is standard.
- Simulation results: time-series of compartment counts vs time step (Susceptible/Infected/Removed/Protected, one line per compartment, 100 steps), then a parameter sweep as heatmaps (3 panels, one per infection spread rate, axes protection spread rate vs protection strength, colour = final count). Conclusions are stated as rules ("Protection spread rate is key", "Even minimal protection is useful").
- Parameter listing beside each run: initial infected, infection spread chance, initial protected, protection spread chance. There are no repeats or confidence bands in Giulia's deck, a weakness; we have Monte Carlo and should show mean plus a band.
- Dataset citation: just a bare URL ("https://networks.skewed.de/net/anybeat") on a final Resources slide, grouped as Data / Libraries / Other. Christian cites papers in numbered [1][2][3] style with author, year, title, doi. Giulia only points to a GitHub repo. Nobody cites inline on content slides. We should add a small footnote-style source line on the dataset slide.
- Code: appears only in the appendix, as dark-theme code screenshots (Christian) or one snippet slide (Giulia, the SIRModel call). Keep it out of the main flow.

## 6. Distinctive things to copy / avoid

Copy:
- Title -> Contents -> Description -> Stats -> Picture -> Distribution -> RQ -> Method -> Results -> Conclusion -> Further work -> Extra Slides -> References. This is the expected ordering.
- Headline numbers as large tiles; one number labelled under each result plot.
- Explicit research question slide (Giulia gives two questions, each one sentence).
- Before/after side-by-side with parameter lists beneath.
- Heatmap parameter sweep and an "Interpretation & Conclusion" slide with two groups ("For low infection spread rate ..." / "For high ...") and 3 short rules each.
- "Extra Slides" divider so the main talk stays tight; a "Future work" slide of 5-6 fragments.
- Pipeline/flow diagram for methodology (Malene slide 9: five small coloured boxes top-to-bottom).
- Humour is tolerated but keep it to at most one slide.

Avoid:
- Tiny, unreadable plot tick labels and 8-9 pt body text (Malene), and cramped paragraphs.
- Default matplotlib legends and unlabeled colours; plots with no axis labels.
- No slide numbers anywhere in the examples, so the contents slide cannot be referred back to; add small ones bottom-right.
- Stock/AI imagery that carries no information; memes; a Motivation slide hidden in the appendix; a single-run result with no replication; raw URLs as the only dataset citation; code walls in the main talk; text laid over busy photos (low contrast).
- Missing limitations slide: none of the decks has one; include one.

## RECOMMENDED DECK FOR THIS PROJECT

Topic: agent-based epidemic simulation on the Copenhagen Networks Study (CNS) Bluetooth proximity network, Monte Carlo vaccination-strategy experiments, animation.
Style: 16:9, white background, Calibri titles 36-40 pt top-left, body 20-24 pt, 3-5 fragment bullets max, one neutral dark accent plus one highlight colour, slide numbers bottom-right, no stripe/rule decorations, plots with large fonts and axis labels, one bold number under every result plot.
Legend: [FILL] = content to be written by us; [BLANK] = leave the slide as a title only (title text + empty body, with a small grey "TO BE DECIDED BY AUTHORS" note) so the authors can decide what to dig into.

1. Title: "Vaccination Strategies on a Proximity Network" - subtitle (agent-based epidemic on the Copenhagen Networks Study), group number, names, ITU emails, course code. [FILL]
2. Contents: 6-7 items in a 2x3 / 3x3 grid (Network, Statistics, Research Question, Model, Experiments, Results, Conclusion). [FILL]
3. Network Introduction: Copenhagen Networks Study, Bluetooth proximity between ~700 students, scans every 5 min over 4 weeks; nodes = participants, edges = proximity encounters; source citation (Sapiezynski et al. 2019, Scientific Data) as a footnote. [FILL]
4. Our Network (aggregated / largest component): headline tiles - nodes, edges, density, average degree, avg path length, diameter, clustering; state aggregation window and any signal-strength threshold. [FILL]
5. Network Picture: single layout plot (Gephi-style or networkx), coloured by community or degree, legend and 1-2 observations. [FILL]
6. Degree and Strength Distributions: log-log degree distribution (and weighted strength if used), plus the fit-comparison summary line. [FILL]
7. Centralities and Communities: top-5 table (node id, degree, betweenness, closeness) and communities (count, size range, modularity). [FILL]
8. Research Question: one or two single-sentence questions on which vaccination strategy (random, degree, betweenness/acquaintance, community-based) best reduces outbreak size. [FILL]
9. Model: agent-based SIR/SEIR on the temporal or aggregated contact network; state diagram of compartments, transmission and recovery parameters listed as "Label: value" lines. [FILL]
10. Vaccination Strategies: the compared strategies as 4-5 short fragments or small cards, plus the vaccination budget. [FILL]
11. Monte Carlo Setup: number of runs, seeds, vaccination fractions swept, outcome metrics (final attack rate, peak infected, time to peak), how confidence bands are formed. [FILL]
12. Animation of the Outbreak: embedded GIF/video (repo has bt_epidemic.mp4, covid_no_vaccination.mp4, covid_best_strategy.mp4), side by side without and with vaccination, "first N steps" in the title. [FILL]
13. Epidemic Curves: S/I/R vs time per strategy, mean with band across runs, one bold number (final attack rate) under each panel. [FILL]
14. Strategy Comparison Across Budgets: heatmap or line chart of outcome vs vaccinated fraction per strategy, with a compact results table. [FILL]
15. Interpretation & Conclusion: two groups of 3 short rules (e.g., low vs high transmissibility) and the answer to the research question. [FILL]
16. [BLANK] "Deep Dive 1" - title only; authors decide what to dig into (e.g., temporal vs aggregated network).
17. [BLANK] "Deep Dive 2" - title only; authors decide (e.g., community structure effect).
18. [BLANK] "Sensitivity / Robustness" - title only; authors decide.
19. Limitations and Future Work: 4-5 fragments (proximity is not contact, sampling bias in a student population, parameter calibration, no behaviour change) plus future work. [FILL]
20. Thank you / Questions: contact line. [FILL, minimal]
21. Extra Slides (divider). [FILL]
22. Appendix: Code Snippets (simulation loop, strategy selection) and extra parameters/plots. [FILL, or BLANK if time is short]
23. References: data (CNS dataset DOI/URL), numbered paper citations in [1][2] style with author, year, title, DOI, and libraries (networkx, numpy, matplotlib, etc.). [FILL]
