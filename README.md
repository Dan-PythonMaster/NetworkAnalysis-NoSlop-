# Outbreak simulation on the Copenhagen Networks Study

An agent-based epidemic simulator that runs on the real Bluetooth proximity data of 692
university students (Copenhagen Networks Study, four weeks, a scan every five minutes),
together with the Monte Carlo experiments and the animation built on top of it.

The question it answers: **given doses for a tenth of the students, whom should we
vaccinate?** Eight targeting strategies are compared on identical outbreaks.

The data is fetched from [Netzschleuder](https://networks.skewed.de/net/copenhagen) through
`graph-tool` and cached there, so no data is stored in this repository.

## Quick start

```bash
pip install -r requirements.txt
conda install -c conda-forge graph-tool    # not on PyPI; Linux/macOS only

python bt_sweep_plots.py        # redraw the sweep figures from the committed results
python bt_time_plots.py         # redraw the epidemic-curve figures
python presentation/build_deck.py
```

Those three read the committed files in `results/` and need neither `graph-tool` nor a
rerun, so they work anywhere and finish in seconds. The simulations themselves are plain
Python and NumPy; only the data loading and a few graph routines use `graph-tool`.

Every script can be run from any directory — paths are resolved relative to the file, not
to the working directory.

## The model

Every contact in the data is a timed edge, and the simulation walks them in time order.
Exposure is bookkept in minutes: each contact charges a susceptible person some minutes, and
they are infected the moment their personal budget runs out.

| mechanism | what it does |
|---|---|
| **close contact** | a Bluetooth scan at or above `rssi` (−75 dBm ≈ 1.5 m) charges the susceptible person 5 minutes |
| **rooms** | everyone detected at or above `room_rssi` (−90 dBm) in the same five-minute slot forms a room; if anyone in it is infectious, every susceptible member is charged `room_dose` |
| **immunity** | each person draws a personal resistance in minutes of exposure, uniform on `[imm_lo, imm_hi]`; at zero they are infected |
| **dropping out** | `period` after being infected a person stops spreading, and cannot be reinfected |
| **home** | each night at 22:00 every susceptible person risks exposure at home with probability `home_risk × prevalence`, charging `home_dose` |
| **vaccination** | a vaccinated person neither catches it nor passes it on; eight strategies, below |

Deliberately *not* modelled: latent period, symptoms, asymptomatic cases, variation in
infectiousness between people (so no superspreaders), partial or delayed vaccine protection,
behaviour change during the outbreak, and contacts with anyone outside the study.

The baseline values live in `BASE` in `bt_sweep.py`; `covid_params.py` overrides them with
COVID-like ones and documents the source behind each number.

### The eight strategies

Four need the full four-week contact log — **degree**, **contact time**, **betweenness**,
**community bridges** — and four need little or no data: **random**, **acquaintance** (a
random contact of a random person), **week-1 degree** (only the first week, so only the
past), and **ring** (reactive: a case is traced `ring_delay` after infection and its most
frequent contacts are vaccinated). All but ring spend their doses before the outbreak starts.

## Repository layout

| file | purpose |
|---|---|
| `bt_sweep.py` | the simulator (`outbreak`, `simulate`), the strategies (`build_rankings`, `pick`) and the one-at-a-time parameter sweep |
| `covid_params.py` | the COVID-like parameter set, with the source behind each value |
| `covid_strategies.py` | Monte Carlo comparison of the eight strategies under those parameters |
| `covid_animation.py` | the animation: stationary class-cohort layout, coloured crosses for rooms, live contacts |
| `bt_time.py` | epidemic curves over time for many parameter values |
| `bt_sweep_plots.py`, `bt_time_plots.py` | the figures, drawn from the committed results |
| `presentation/build_deck.py` | builds the slide deck PDF from those results |
| `results/` | committed simulation output, so the figures can be redrawn without rerunning |
| `figures/` | PNGs written by the plot scripts and by the animation |

Videos are not committed (`*.mp4` is in `.gitignore`); rerun `covid_animation.py` for them.

## Reproducing the results

```bash
python covid_strategies.py                 # the strategy table      (~20 min) -> results/covid_strategies.csv
python bt_sweep.py                         # the parameter sweep     (~8 min)  -> results/bt_sweep_*.csv
python bt_time.py                          # the epidemic curves     (slow)    -> results/bt_time_curves.npz
python covid_animation.py "contact time"   # the animation           (~10 min) -> covid_best_strategy.mp4
python covid_animation.py none             # the same outbreak, unvaccinated
```

All of them write straight into `results/`. `bt_sweep.py` also writes
`bt_sweep_runs.csv`, every individual run, which is too large to commit. The animation needs
`ffmpeg` on `PATH`. `WORKERS` in `bt_sweep.py` sets how many cores everything uses.

## Monte Carlo design

* A **starting configuration** fixes everything random that does not depend on the strategy:
  patient zero, their infection time, every person's resistance, and the nightly home draws.
* Every strategy is tested on the **same** configurations (common random numbers), so a
  difference between two strategies comes only from who was vaccinated. The simulator draws
  that shared randomness first and always in the same order to keep the streams aligned —
  which is why, for instance, the nightly loop draws for people whose draw cannot matter.
* Reported per setting: mean infected, share of runs that **took off** (≥ 50 infected), and
  **saved** — the mean over paired configurations of how many people a strategy spared
  compared with no vaccination. Pairing makes that far less noisy than a difference of means.
* A run stops as soon as nobody is infectious, which makes the many runs that fizzle almost
  free.

## Results

`results/covid_strategies.csv` — 400 paired configurations, COVID-like parameters, 10 % of
the 692 students vaccinated:

| strategy | mean infected | took off | saved (95 % CI) |
|---|---|---|---|
| contact time | 17.3 % | 36.5 % | 223.4 ± 24.4 |
| degree | 22.7 % | 40.5 % | 186.1 ± 22.0 |
| week-1 degree | 24.1 % | 42.3 % | 176.8 ± 21.5 |
| betweenness | 24.5 % | 42.3 % | 173.6 ± 21.1 |
| ring | 27.1 % | 43.0 % | 155.6 ± 20.0 |
| acquaintance | 29.9 % | 46.3 % | 136.6 ± 18.5 |
| random | 33.9 % | 49.0 % | 108.4 ± 15.8 |
| community bridges | 36.3 % | 50.3 % | 92.4 ± 14.2 |
| no vaccination | 49.6 % | 58.8 % | — |

Three things worth noticing: targeting the students with the most *contact time* beats
targeting the ones with the most *contacts*; one week of past data (`week-1 degree`) is
nearly as good as all four weeks, which matters because a real campaign cannot see the
future; and `community bridges` is the worst of the lot, so the people who connect groups
are not the ones to protect here.

`results/bt_sweep_summary.csv` — 91 study rows over 75 distinct parameter sets, 400 runs
each (30,000 runs), one parameter changed at a time. Columns: study, x, strategy, coverage,
runs, mean, std, ci95, mean_pct, ci95_pct, outbreak_pct, median, peak_mean,
mean_if_outbreak_pct.

`results/bt_time_curves.npz` — for each of six parameter studies, the mean "infected so far"
and "infectious now" curves (% of students, hourly over 21 days, 300 runs per value), 40
sample runs per value, and JSON metadata (`meta`, `hours`, `configs`).

`results/covid_strategies_log.txt` — the console output of the run that produced the table
above, kept as a record of when and with what it was made.

## The animation

`covid_animation.py` draws a **stationary** layout, which is what makes it readable: students
who share at least five hours of room time over the four weeks are grouped into class
cohorts by a block model, each cohort is drawn as a sunflower-packed disc, the discs are
pushed apart by a short spring relaxation, and the students without a steady cohort sit on an
outer ring (`figures/stationary_graph.png`).

Over that fixed layout: blue dots for uninfected, orange for infected, red for dropped out, a
ring around the vaccinated, a coloured cross on anyone currently in a room (one colour per
room, held for as long as the room lasts), and lines for the close contacts in that
five-minute window, orange when someone infectious is involved. A second panel tracks the
curves as they happen. Nothing moves except those; no node ever changes position.

Both scenarios use the same starting configuration, so the two videos can be compared frame
by frame. All figures are plain matplotlib with default styling.

## Caveats

* Bluetooth signal strength is a noisy proxy for distance, and the close-contact threshold
  changes the outcome more than most of the disease parameters do.
* Contacts with people outside the study were removed from the data; the nightly home route
  is a crude stand-in for them.
* The four weeks of data cap how far an outbreak can run.
* The sweep in `bt_sweep.py` uses the simpler baseline disease, not the COVID-like
  parameters, so its figures show mechanism rather than a forecast.

## Data and references

1. Sapiezynski, Stopczynski, Lassen, Lehmann (2019). *Interaction data from the Copenhagen
   Networks Study.* Scientific Data 6, 315.
2. Sekara, Lehmann (2014). *The strength of friendship ties in proximity sensor data.*
   PLoS ONE — the −75 dBm close-contact threshold.
3. Cevik et al. (2021), Lancet Microbe — the infectious period.
4. Madewell et al. (2022), JAMA Network Open — the household attack rate the resistance
   range was tuned against.
5. Kretzschmar et al. (2020), Lancet Public Health — the contact-tracing delay.
