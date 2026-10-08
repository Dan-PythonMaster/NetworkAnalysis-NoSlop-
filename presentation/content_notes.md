# Content sheet: outbreak simulation on the Copenhagen Networks Study

Purpose: inventory of everything a slide deck could show. Every number is copied from a file in the repo; the source tag in [brackets] says which.
Source tags: [README] outbreak-sim/README.md; [params] covid_params.py; [strat.csv] results/covid_strategies.csv; [sweep.csv] results/bt_sweep_summary.csv; [sweep.py] bt_sweep.py; [strat.py] covid_strategies.py; [anim.py] covid_animation.py (read only); [ch02] [ch04] [ch05] [ch06] [ch07] [ch08] [ch09] [ch11] [ch12] [ch13] [ch14] [ch15] = book/chapters/NN-*.md.

One-line pitch: an agent-based epidemic simulator that replays the real timed Bluetooth contacts of ~692 students, with Monte Carlo experiments on which 10% of students to vaccinate. [README]

---------------------------------------------------------------------
## 1. Dataset facts

| fact | value | source |
|---|---|---|
| Study | Copenhagen Networks Study, first-year students at the Technical University of Denmark (DTU), 2013; four-week extract published in Scientific Data 2019 (Sapiezynski, Stopczynski, Lassen, Lehmann) | [ch02], [ch15] |
| Access | Netzschleuder `copenhagen/bt` via graph-tool; nothing stored in the repo | [README], [ch02] |
| Participants (bt layer) | 692 | [ch02] |
| Duration | 28 days (timestamps 0 to ~2,419,000 s). Calendar dates removed for privacy. Day 1 inferred to be a Sunday from the weekly rhythm | [ch02] |
| Scan interval | every 5 minutes, strict grid (every timestamp is a multiple of 300 s) | [ch02] |
| Scans (timed edges) in bt layer | 2,426,279 | [ch02] |
| What RSSI is | Received Signal Strength Indicator in dBm, a negative number; about -50 = strong, about -100 = barely in range. Falls with distance but noisily (walls, bodies, pockets, phone model) | [ch02] |
| Median RSSI of all scans | -86 dBm (so most detections are "same room, not next to each other") | [ch04] |
| Close contact definition | a scan with RSSI >= -75 dBm, calibrated by Sekara & Lehmann 2014 to about 1.5 m; one scan counts as 5 minutes of exposure | [ch02], [README], [params] |
| Scans counted as close | 438,547 (about 18%; 18.1% in ch04) at -75 dBm; 731,495 (about 30%) at -80 dBm | [ch02], [ch04] |
| Room definition | all detections >= -90 dBm in the same 5-min slot, grouped into connected components. Median room 4 people, max 68 | [README], [ch13] |
| Contact episodes | consecutive scans of one pair; 175,885 episodes; median episode is one scan, 60% are single scans, only 2.6% last an hour or more | [ch04] |
| Burstiness | median burstiness coefficient 0.40 over 3,962 pairs with >=10 episodes (0 = Poisson, 1 = extreme bursts) | [ch04] |
| Weekly rhythm | average weekday 19,416 close scans vs weekend day 6,278 (about a third). About 525 phones log an encounter on a weekday, about 352 on a weekend day | [ch04] |
| Daily rhythm | weekday peak at 10:00 (about 2,000 scans/h), lunch dip to about 1,300 at 12:00, 1,900 at 13:00, collapse after 16:00; still about 240 close scans/h at 03:00-06:00 (phones of people sleeping near each other) | [ch04] |

The four layers (Netzschleuder `copenhagen/*`) [ch02]:

| layer | edge means | nodes | edges | directed |
|---|---|---|---|---|
| bt | one Bluetooth scan where two phones saw each other | 692 | 2,426,279 | no |
| sms | one text message | 568 | 24,333 | yes |
| calls | one phone call | 536 | 3,600 | yes |
| fb_friends | a Facebook friendship (static, no timestamps) | 800 | 6,429 | no |

Only the bt layer drives the simulation. Side facts on layers: 89% of texting pairs and 90% of calling pairs were also physically close at least once [ch08]. Text messages drop only about 28% on weekends vs about 68% for close contacts, so layers partly substitute [ch04]. Node numbering differs per layer; match on the `id` property [ch02].

What is missing from the data [ch02], [README], [ch15]:
- People outside the study: scans with non-participants were removed (partners, family, housemates outside the cohort are invisible).
- Gender: the `female` property is False for every node, so no analysis uses it. No age, programme or housing data either.
- Phones that were off or left behind (cannot be separated from people being alone).
- Context: ventilation, masks, walls, indoor/outdoor, talking.
- Real dates (removed).

---------------------------------------------------------------------
## 2. Network structure findings (the "network" slide)

Aggregated close-contact network (any pair within about 1.5 m at least once in the 4 weeks) [ch05] unless noted:

| measure | value |
|---|---|
| Nodes / edges | 692 / 23,670; density 0.099 (about 1 in 10 pairs ever met closely) |
| Isolated students | 17 (never had a close contact) |
| Degree | mean 68.4, median 65, max about 214. Broader than the Poisson/Erdos-Renyi expectation (nearly nobody <50 or >90), but not scale-free: the tail bends down near 200 |
| Tie weights (total minutes close) | median 10 min over the month; 67% of ties under 30 min; only 2.6% of ties 10 h or more |
| Time per student | mean 6,337 min (about 106 h), median 4,838 min; top 10% of students hold 29% of all contact minutes |
| Giant component | 673 students (97.3%); one extra component of 2 students; 17 isolated |
| Distances | average shortest path 2.02, diameter 5 (small world) |
| Weight percolation | keeping only ties >= 2 h: mean degree 9.5, 92% still in one component; >= 4 h: 84%; >= 8 h: mean degree 2.4, 59%; between 8 h and 16 h the giant component collapses to 5% |
| Clustering | global 0.28, average local 0.31. Null model (degree-preserving rewiring, configuration model, 10 randomisations): 0.18. So real clustering is far above null: triadic closure from shared lectures/groups/flats |
| Shortest path vs null | 2.02 real vs 1.97 null: short distances are explained by degrees alone |
| Degree assortativity | +0.08 real vs -0.04 in the rewired null (small but clearly different) |
| k-core | deepest core is the 49-core with 337 students (nearly half the cohort) |
| Friendship paradox | mean degree of a student 70.1 vs mean degree of a contact 93.8 (a third higher) [ch06] |
| Centrality overlap | degree, closeness, eigenvector rank correlations 0.97-0.98; betweenness-degree 0.90; contact time-degree only 0.71. Top-69 by degree and top-69 by contact time share only 24 students; degree vs betweenness share 50 [ch06] |
| Stability over time | only 22-26% of ties repeat between weeks (32% for ties >= 1 h/week), but degree rank correlation is 0.72 (week 2 vs 3) and 0.56 (week 1 vs 4): who is popular persists, whom they meet does not [ch06] |
| Timing vs structure | perfect contagion (instant, certain) median reach after 1 day: 0.4% with real timing, 94% with shuffled timestamps; after 3 days 62%, after 7 days 89% (static graph says 97%) [ch07] |

How communities / class cohorts were found [anim.py lines 70-90; README]:
- Count room-level co-presence (detections >= -90 dBm) per pair; keep pairs with at least 60 scans = 5 hours of shared room time over four weeks (CLASS_CUT = 60).
- Run graph-tool's stochastic block model (`minimize_blockmodel_dl`) on that graph; keep blocks with at least 4 people (CLASS_MIN = 4).
- Result: 23 class cohorts, the largest 104 students; 58 students with no steady cohort, drawn on an outer ring. [README; figures/stationary_graph.png title "23 class cohorts, 58 students without one"]
- Caution: the "community bridges" vaccination strategy in bt_sweep.py also uses `minimize_blockmodel_dl` on the close-contact graph [sweep.py build_rankings]. The book (ch12, ch15) says label propagation was used as a stand-in because graph-tool was unavailable on Windows. The number of blocks in that partition is not recorded in any file I read. Treat community-bridges results as unverified (see section 7).

---------------------------------------------------------------------
## 3. The model

Agent-based, event-driven SIR. Every contact is a timed edge; the simulation walks them in time order. No latent stage. Random patient zero (a person with at least one recorded contact) is infected at a random moment in the first 7 days (SEED_WINDOW). [README, ch09, sweep.py]

Mechanisms, one line each [README table; ch09]:
- Close contact: a scan at or above `rssi` (-75 dBm, about 1.5 m) costs the susceptible person 5 minutes of immunity if the other person is infectious.
- Room dose: everyone detected at or above `room_rssi` (-90 dBm) in the same 5-minute slot forms a room; if anyone in it is infectious, everyone else loses `room_dose` minutes.
- Immunity: each person draws a personal resistance (minutes of exposure), uniform on [imm_lo, imm_hi]; reaching zero means infected. Dose-response, deterministic once drawn.
- Dropping out: after `period` an infected person stops spreading and cannot be reinfected (the "red" people in the animation).
- Home exposure: each night at 22:00 every susceptible person is exposed with probability home_risk x (share currently infectious), costing home_dose minutes. Stand-in for invisible housemates/family.
- Vaccination: vaccinated people cannot be infected or spread (complete, instant protection). Eight strategies (below).
- Early stopping: a run ends when nobody is infectious, so fizzles are almost free.
- Not modelled: latent period, symptoms, asymptomatic cases, per-person infectiousness variation, partial or delayed vaccine protection. [README]

Eight vaccination strategies [ch12, sweep.py]:
- Needing the full contact log: degree (most distinct close contacts), contact time (most total close minutes), betweenness, community bridges (most contacts outside own block).
- Needing little data: random; acquaintance (random contact of a random person, uses the friendship paradox); week-1 degree (degree from the first week only); ring (reactive: when a case is detected, vaccinate its most frequent contacts so far, up to ring_per_case = 10, until the budget is used).

Current parameter set [params = covid_params.py `COVID`], with justification from `SOURCES` in the same file and ch13:

| parameter | value | justification |
|---|---|---|
| rssi (close contact) | -75 dBm | about 1.5 m; Sekara & Lehmann, PLoS ONE 2014; CDC close-contact distance |
| room_rssi | -90 dBm | the bulk of Bluetooth detections |
| room_dose | 0.8 min per 5-min slot | "sharing a room counts 0.8 of the 5 minutes a close contact counts" (0.8/5 = 0.16, the file's "a sixth"). No direct measurement behind it; a judgement |
| imm_lo / imm_hi | 150 / 1800 min (2.5 to 30 h) | tuned so two nights of household exposure infect about half, in the range of the 42.7% household attack rate (Madewell et al., JAMA Netw Open 2022), and so outbreaks neither always fizzle nor always reach everyone |
| period | 5 days | about 2 days before symptoms + about 3 after; Cevik et al., Lancet Microbe 2021 (ch13 also cites Wu 2022) |
| home_risk | 1.0 | about one housemate at current prevalence [ch13] |
| home_dose | 500 min | a night of shared air with a housemate [ch13 describes 600; code says 500] |
| ring_delay | 3 days | contact-tracing lag; Kretzschmar et al., Lancet Public Health 2020 |
| ring_per_case | 10 | ring vaccination budget per detected case |

Baseline parameters for the older sweeps [sweep.py BASE; ch11]: rssi -80, imm 60-480 min, period 3 days, home_risk 0.35, home_dose 60 min, room_dose 0 (rooms off), ring_delay 1 day, coverage 0. Describe it as "a didactic baseline chosen before the COVID calibration".

PARAMETER DRIFT WARNING: ch13 (written earlier) lists imm 180-2160, home_dose 600, room_dose 0.5. The strategy CSV was produced with those older values [README]. The current covid_params.py has imm 150-1800, home_dose 500, room_dose 0.8, i.e. more transmissible.

---------------------------------------------------------------------
## 4. Monte Carlo design

- Starting configuration = everything random that does not depend on the strategy: patient zero, their infection time, every person's resistance, and the nightly home draws. [README; sweep.py seeds each configuration with `random.Random(index)` and home draws with `Random(90000+index)`]
- Paired comparison / common random numbers: every strategy is run on the same configurations, so a difference between strategies comes only from who was vaccinated. (Random and acquaintance vaccine draws are seeded per configuration: `Random(7000+index)`.) [README, sweep.py]
- Number of runs: 400 configurations per setting [strat.py CONFIGS = 400; sweep.py CONFIGS = 400]. Coverage 10% = 69 of 692 students for the strategy comparison [strat.py COVERAGE = 0.10; ch06 "top 69"].
- Sweep scale: 91 study rows, 30,000 runs over 75 distinct parameter sets, one parameter changed at a time [README].
- Time-curve data: 6 parameter studies, 300 runs per value, hourly over 21 days, 40 sample runs per value [README, results/bt_time_curves.npz].
- Run time: strategy comparison about 20 min; full sweep about 8 min [README] (8 worker processes [sweep.py]).
- Metrics reported:
  - mean infected (count and % of 692);
  - took off = share of runs reaching at least 50 infected (OUTBREAK = 50);
  - saved = mean over paired configurations of (infected with no vaccination) minus (infected with the strategy), with a 95% CI = 1.96 x std / sqrt(400);
  - the sweep CSV also gives std, ci95, median, peak_mean (peak simultaneous infectious), mean_if_outbreak_pct (size when it took off).
- Key concept for slides: outcomes are bimodal (most runs fizzle, some infect most of the cohort), so "took off" and "size if took off" are separate questions [ch09, ch11].

---------------------------------------------------------------------
## 5. Headline results

### 5a. Strategy comparison (results/covid_strategies.csv)

CAVEAT TO PRINT ON THE SLIDE: these numbers were produced with an earlier, less transmissible parameter set (imm_lo 180, imm_hi 2160, room_dose 0.5, home_dose 600). The current covid_params.py (imm 150-1800, room_dose 0.8, home_dose 500) spreads more easily, so the table must be re-run (`python covid_strategies.py`) to match it. [README]

Setup: 400 paired configurations, 10% of students vaccinated (69 people), COVID-like parameters. Values rounded from the CSV.

| strategy | mean infected (count) | mean infected (%) | took off | saved (95% CI) |
|---|---|---|---|---|
| contact time | 45.5 | 6.6% | 19.8% | 148.6 +/- 21.0 |
| degree | 60.6 | 8.8% | 24.8% | 133.5 +/- 19.0 |
| betweenness | 63.2 | 9.1% | 26.8% | 130.9 +/- 18.9 |
| week-1 degree | 68.9 | 10.0% | 25.2% | 125.2 +/- 17.9 |
| ring | 82.0 | 11.9% | 29.0% | 112.1 +/- 16.7 |
| acquaintance | 87.7 | 12.7% | 30.8% | 106.4 +/- 16.3 |
| random | 103.9 | 15.0% | 32.2% | 90.2 +/- 14.3 |
| community bridges | 117.7 | 17.0% | 35.5% | 76.4 +/- 12.6 |
| no vaccination | 194.1 | 28.0% | 44.0% | - |

Other CSV columns: median outbreak is 4 for every vaccinated strategy (3.5 for acquaintance) and 11 with no vaccination; std ranges from 99.6 (contact time) to 262.5 (none).
Takeaways stated in ch13: contact-time targeting saves about 149 of 692 students vs about 90 for random with the same doses; 10% vaccination cuts take-off probability from 44% to about 20% with contact-time targeting; ring sits mid-table; the ranking matches the earlier baseline disease (ch12), suggesting it comes from network structure.
Caveat: the CIs on "saved" overlap between neighbouring strategies (e.g. degree 133.5 +/- 19.0 vs betweenness 130.9 +/- 18.9), so only broad tiers are clearly separated: contact time on top; community bridges and random at the bottom; no vaccination far worse than all. Avoid claiming a strict ordering in the middle. (Because runs are paired, differences between strategies are tighter than these CIs against baseline suggest, but no pairwise strategy-vs-strategy CI is computed in the files.)

### 5b. Parameter-sweep highlights (results/bt_sweep_summary.csv)

All sweeps use the OLD didactic baseline (rssi -80, immunity 60-480 min, 3-day infectious period, home risk 0.35, home dose 60 min, rooms off), 400 runs per row. Baseline row: 24.43% mean infected, 30.8% took off, 78.84% size if took off.

Disease parameters, no vaccination:

| study | value | mean infected % | took off % | size if took off % |
|---|---|---|---|---|
| infectious period (days) | 0.5 | 0.18 | 0.0 | 0.0 (no run took off) |
| | 1 | 0.38 | 0.8 | 12.3 |
| | 2 | 8.2 | 11.5 | 68.9 |
| | 3 (baseline) | 24.43 | 30.8 | 78.8 |
| | 5 | 50.47 | 58.0 | 86.9 |
| | 7 | 64.56 | 71.8 | 89.9 |
| immunity (min of exposure) | 15-120 | 77.25 | 83.2 | 92.8 |
| | 30-240 | 55.97 | 63.8 | 87.7 |
| | 60-480 (baseline) | 24.43 | 30.8 | 78.8 |
| | 120-960 | 1.51 | 2.8 | 42.6 |
| | 240-1920 | 0.17 | 0.0 | 0.0 (no run took off) |
| close-contact threshold (RSSI dBm) | -85 | 40.15 | 47.2 | 84.7 |
| | -80 (baseline) | 24.43 | 30.8 | 78.8 |
| | -75 | 5.45 | 9.8 | 52.8 |
| | -70 | 0.27 | 0.0 | 0.0 (no run took off) |
| home risk | 0 | 22.66 | 30.0 | 74.9 |
| | 0.35 (baseline) | 24.43 | 30.8 | 78.8 |
| | 3 | 35.44 | 36.2 | 97.4 |
| home dose (min) | 15 | 22.9 | 30.0 | 75.7 |
| | 60 (baseline) | 24.43 | 30.8 | 78.8 |
| | 240 | 46.97 | 53.0 | 88.4 |

(In the CSV, mean_if_outbreak_pct is 0.0 where no run reached 50 infected; it means "no taken-off runs", not "zero".) The 95% CI on mean infected is about +/-3 to 4.6 percentage points for the mid-range rows.
Messages [ch11]: (1) thresholds dominate: resistance, infectious period and contact definition show sharp transitions; (2) most parameters change the probability of take-off, not the size of a taken-off outbreak; home risk/dose is the exception (raises size, not probability, because it scales with prevalence); (3) the contact threshold, a measurement choice, matters as much as any disease parameter.

Vaccination coverage sweep: mean infected % (took off %) by strategy, same baseline disease, no vaccination = 24.43 (30.8):

| coverage | random | acquaintance | week-1 degree | ring | degree | contact time | betweenness | community bridges |
|---|---|---|---|---|---|---|---|---|
| 2.5% | 22.26 (29.0) | 21.97 (28.8) | 19.15 (25.2) | 14.20 (18.2) | 20.15 (26.5) | 19.85 (26.2) | 20.47 (27.0) | 23.31 (30.0) |
| 5% | 20.74 (28.0) | 20.38 (27.8) | 16.03 (22.5) | 12.37 (16.2) | 15.36 (22.0) | 13.67 (19.5) | 15.78 (22.0) | 21.98 (29.2) |
| 10% | 17.61 (25.5) | 15.88 (23.8) | 9.06 (14.5) | 10.27 (14.0) | 9.54 (18.0) | 6.74 (12.0) | 10.50 (17.5) | 19.28 (27.5) |
| 20% | 12.38 (21.2) | 9.18 (18.0) | 0.97 (2.2) | 6.93 (10.5) | 0.83 (2.2) | 0.39 (0.5) | 1.60 (6.8) | 12.96 (22.0) |
| 30% | 7.76 (16.8) | 2.86 (8.2) | 0.32 (0.2) | 5.21 (8.8) | 0.40 (0.0) | 0.25 (0.0) | 0.37 (0.0) | 6.54 (15.0) |

Highlights: contact time is best among static strategies from 5% to 30% coverage; ring is best at 2.5-5% coverage (14.2 and 12.4% vs about 19-20 for the others) but flattens out; at 20% coverage degree, contact time and week-1 degree stop the outbreak almost completely (<1%) and betweenness nearly (1.6%) while random still leaves 12.4% (a percolation-like tipping point from targeted immunization, [ch12]). Community bridges is worse than random (19.28% vs 17.61% at 10%).

Strategy x infectious period at 10% coverage (mean infected %): [sweep.csv "strategy x infectious period"; figure bt_sweep_strategy_period.png]

| infectious period | none | random | acquaintance | week-1 degree | ring | degree | contact time | betweenness | community bridges |
|---|---|---|---|---|---|---|---|---|---|
| 1 day | 0.38 | 0.33 | 0.28 | 0.22 | 0.32 | 0.23 | 0.19 | 0.24 | 0.32 |
| 3 days | 24.43 | 17.61 | 15.88 | 9.06 | 10.27 | 9.54 | 6.74 | 10.50 | 19.28 |
| 7 days | 64.56 | 54.29 | 54.32 | 49.41 | 41.36 | 48.87 | 50.65 | 48.60 | 54.94 |

Message: the best strategy depends on the disease. At 3 days contact time wins; at 7 days ring vaccination is best (41.4%) because a long infectious window lets reactive doses land before contacts are infected. [ch12]

Epidemic-curve findings [ch11; figures bt_time_*.png; results/bt_time_curves.npz]: S-shaped cumulative curves; low-resistance prevalence peaks at about 45% of students around day 5 vs a baseline of about 7% around day 9; a 7-day infectious period gives about 40% infectious at once around day 14. Means over runs are smoother and lower than any single taken-off outbreak (many runs fizzle).

---------------------------------------------------------------------
## 6. Figure inventory (outbreak-sim/figures/; all six viewed)

| file | what it shows | suits slide |
|---|---|---|
| stationary_graph.png | The animation's fixed layout, titled "23 class cohorts, 58 students without one". Each cohort is a packed disc of coloured dots (largest cluster, blue, centre-left), cohorts spread apart, and 58 grey dots on an outer ring for students with no steady cohort. No edges drawn. | "The network / who sits where"; also the key to read the animation |
| bt_sweep_disease.png | 5 small panels (infectious period, immunity range, close-contact RSSI threshold, home risk, home dose). Each has three lines: mean infected (blue), share of runs that took off (orange), size if took off (green), vs the parameter, no vaccination, 400 runs per point. Sharp thresholds for infectious period, immunity and RSSI; home risk/dose moves size more than take-off. | "What the disease parameters do" / sensitivity |
| bt_sweep_vaccination.png | 2x2 grid. Left column "needs the full contact log" (degree, contact time, betweenness, community bridges), right column "needs little contact data" (random, acquaintance, week-1 degree, ring). Top row: mean infected % vs % vaccinated (0-30); bottom row: runs that took off %. Dashed line = no vaccination (24.4% / 30.8%). Contact time lowest on the left; ring best at low coverage and week-1 degree best at high coverage on the right; community bridges worst. | Core "Whom to vaccinate" slide (baseline disease; pairs with the coverage table in 5b) |
| bt_sweep_strategy_period.png | One line chart: mean infected % vs infectious period (1, 3, 7 days) at 10% coverage, one line per strategy plus "none". Lines coincide at 1 day; contact time lowest at 3 days; ring lowest at 7 days (about 41%). | "The best strategy depends on the disease" |
| bt_time_infected.png | 2x3 panels, "Infected so far (mean of 300 runs per value)" vs days since the first case: infectious period, immunity, close-contact threshold, home risk, "vaccinate top contact time" (0, 4, 8, 15, 22% of people), "ring vaccination budget" (0, 2, 5, 15, 30%). S-shaped curves; vaccination flattens and delays them. Note: the legend values here (e.g. -88/-84/-80/-76/-72 dBm, 50-400 min) differ from the sweep CSV values. | "Outbreak over time" / how vaccination bends the curve |
| bt_time_sick.png | Same 2x3 layout, "Infectious at the same time (mean of 300 runs per value)": prevalence curves. Peaks: immunity 15-120 min about 45% around day 5; 7-day period about 40% around day 14; -80 dBm about 7.5%; contact-time vaccination of 22% flattens it to near zero. | "Flatten the curve" slide |

Figures mentioned in the book but NOT in outbreak-sim/figures/ (they live with the book, I did not open them): fig01_activity (daily activity), fig02_daily_cycle, fig03_rssi, fig05_durations, fig04_degree_weights, fig07_percolation, fig06_null_model, fig10_centrality, fig08_stability, fig11_reachability, covid_frame. Also the animation output covid_best_strategy.mp4 (from covid_animation.py, currently being rewritten by another agent; describe generally).

Animation legend [README]: blue dot = uninfected, orange = infected, red = dropped out, blue ring = vaccinated, coloured cross = person currently in a room (one colour per room, held across frames), lines = close contacts in the current 5-minute window (orange if someone infectious is involved), second panel tracks the infected and dropped-out curves over time. Per ch13 the example run: no vaccination reaches 543 students, contact-time vaccination 106 (same starting configuration; patient zero well connected, 75th-95th percentile of contacts); ch14 notes a quiet start (about two days to a second case, eleven days to ten, still more than three quarters infected). These come from the older parameter set and the video is being re-rendered.

---------------------------------------------------------------------
## 7. Limitations (slide candidates) and open questions

Limitations worth a slide [README caveats, ch15, ch02]:
1. Bluetooth RSSI is a noisy proxy for distance; the close-contact threshold changes outcomes more than most disease parameters (mean infected 40.2% at -85 dBm vs 0.3% at -70 dBm in the sweep).
2. Contacts outside the study were removed; the home route is a crude scalar stand-in, not real housemates.
3. Only 4 weeks: outbreaks are cut off at day 28.
4. Simplified model: no latent period, no symptoms or asymptomatic cases, identical infectiousness for everyone, complete and instant vaccine protection (flatters all strategies, ring most of all), uniform resistance has no long tail.
5. Calibration is partly judgement (immunity range, room dose); absolute numbers would move with other choices; the ranking of strategies is expected to be more stable (ch15) but this has not been tested.
6. Silent phones look like isolated people, so weekends may look safer than they were; one cohort, one university, 2013.
7. Community-based results unverified: the book says a label-propagation stand-in was used, the current bt_sweep.py calls the stochastic block model. Check which produced the committed numbers.
8. The strategy table is stale relative to the current parameters (section 5a), and the sweeps use the old didactic baseline, not the COVID parameter set.

Open questions / "what we are digging into next" candidates (from ch15 "What would strengthen the conclusions" and the README; phrase as intentions, not results):
1. Refresh the strategy comparison under the current, more transmissible covid_params.py and check whether contact time still ranks first and where ring lands.
2. Robustness of the ranking: repeat across plausible calibrations and contact thresholds, report how often each strategy ranks first.
3. Superspreading: add random infectiousness per case and test whether targeted vaccination stays best.
4. Fix community detection and re-evaluate "community bridges", which currently does worse than random.
5. Separate structure from timing: run the epidemic on time-shuffled contacts and degree-preserving rewired networks to attribute outbreak size to structure vs timing vs volume. (Further candidates: use the sms layer for social closeness; partial/delayed vaccine protection; longer horizons.)

---------------------------------------------------------------------
## 8. Inconsistencies the slide-maker should know about

- room_dose: code 0.8 (about a sixth of a close contact's 5 min); ch13 says 0.5 and "a tenth" (older set). Use 0.8 for the current set.
- home_dose: code 500; ch13 says 600. Immunity range: code 150-1800 (2.5-30 h); ch13 says 180-2160 (3-36 h).
- ring_delay: covid_params.py 3 days; BASE in bt_sweep.py 1 day (the old sweep results use 1 day).
- Close-contact threshold: sweeps use -80 dBm, the COVID set uses -75 dBm.
- "Saved" counts are per paired configuration out of 692 students.
- README states "75 distinct parameter sets" and "30,000 runs"; I did not recount, quote as README figures.
