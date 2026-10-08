"""Builds the project presentation as a PDF, from the committed results.

Reads results/covid_strategies.csv and the figures in figures/, and writes
presentation/outbreak_presentation.pdf. Three slides are deliberately left blank, as a
title over an empty body, for the deep dives the group still has to choose; every other
slide carries numbers straight from the Monte Carlo output.

Runs from anywhere and needs neither graph-tool nor a rerun of the simulations.

    python presentation/build_deck.py
"""
import csv
import os
import subprocess

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGURES = os.path.join(ROOT, "figures")
RESULTS = os.path.join(ROOT, "results")
OUT = os.path.join(HERE, "outbreak_presentation.pdf")

# Must match covid_strategies.py, which produced the CSV this deck reads.
CONFIGS = 400
COVERAGE = 0.10

WIDE = (13.333, 7.5)    # 16:9 in inches, like the example decks
TITLE_SIZE = 30
BODY_SIZE = 17
NOTE_SIZE = 11
FRAME_AT = 150          # seconds into the video to grab the still from


def read_strategies():
    """The strategy table, numeric columns parsed."""
    path = os.path.join(RESULTS, "covid_strategies.csv")
    with open(path, newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        for name in ["mean", "std", "mean_pct", "took_off_pct", "saved", "saved_ci95"]:
            row[name] = float(row[name])
    return rows


def strategy_figure(rows):
    """Bar chart of people saved per strategy, with the 95% interval of the paired difference."""
    rows = [r for r in rows if r["strategy"] != "none"]
    rows = sorted(rows, key=lambda r: r["saved"])
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh([r["strategy"] for r in rows], [r["saved"] for r in rows],
            xerr=[r["saved_ci95"] for r in rows], capsize=4)
    ax.set_xlabel("students spared compared with no vaccination "
                  "(mean of {} paired runs)".format(CONFIGS))
    ax.set_title("Vaccinating {:.0f}% of students".format(100 * COVERAGE))
    ax.grid(True, axis="x")
    fig.tight_layout()
    os.makedirs(FIGURES, exist_ok=True)
    path = os.path.join(FIGURES, "covid_strategies.png")
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def animation_frame():
    """Grab a still from whichever video is around, or None if there is none (or no ffmpeg).

    The videos are not committed, so this has to cope with their absence: the slide is
    simply built without the picture.
    """
    os.makedirs(FIGURES, exist_ok=True)
    target = os.path.join(FIGURES, "animation_frame.png")
    options = [os.path.join(folder, name)
               for folder in (ROOT, os.path.dirname(ROOT))
               for name in ("covid_best_strategy.mp4", "covid_no_vaccination.mp4")]
    source = next((name for name in options if os.path.exists(name)), None)
    if source is None:
        return None
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(FRAME_AT), "-i", source,
                    "-frames:v", "1", target], check=False)
    return target if os.path.exists(target) else None


def slide(pdf, title, lines=(), image=None, number=None, note=None, blank=False):
    """Append one slide.

    title    headline, newlines allowed
    lines    body text, one entry per line, "" for a gap
    image    path to a PNG, placed beside the text or filling the slide if there is none
    number   the one figure worth saying out loud, in bold across the bottom
    note     a source or caveat, small and grey
    blank    stamp it "to be decided", for the slides the group still has to fill in
    """
    fig = plt.figure(figsize=WIDE)
    fig.text(0.06, 0.90, title, fontsize=TITLE_SIZE, va="top")
    y = 0.78
    for line in lines:
        fig.text(0.06, y, line, fontsize=BODY_SIZE, va="top")
        y -= 0.065
    if image and os.path.exists(image):
        box = fig.add_axes([0.30, 0.08, 0.66, 0.70] if lines else [0.12, 0.08, 0.80, 0.74])
        box.imshow(plt.imread(image))
        box.axis("off")
    if number:
        fig.text(0.5, 0.045, number, fontsize=22, ha="center", fontweight="bold")
    if note:
        fig.text(0.06, 0.04, note, fontsize=NOTE_SIZE, color="gray")
    if blank:
        fig.text(0.5, 0.5, "TO BE DECIDED BY THE AUTHORS", fontsize=16, color="gray",
                 ha="center", va="center")
    pdf.savefig(fig)
    plt.close(fig)


def build():
    strategies = read_strategies()
    chart = strategy_figure(strategies)
    frame = animation_frame()
    best = max(strategies, key=lambda r: r["saved"])
    unvaccinated = [r for r in strategies if r["strategy"] == "none"]
    baseline = unvaccinated[0] if unvaccinated else None
    table = sorted((r for r in strategies if r["strategy"] != "none"),
                   key=lambda r: -r["saved"])[:4]

    with PdfPages(OUT) as pdf:
        slide(pdf, "Vaccination strategies on a\nproximity network",
              ["An agent-based outbreak on the Copenhagen Networks Study",
               "", "Group __ · names · course code",
               "Data: Sapiezynski et al., Scientific Data 6, 315 (2019)"])

        slide(pdf, "Contents",
              ["1.  The network", "2.  Network statistics", "3.  Research question",
               "4.  The model", "5.  Monte Carlo experiments", "6.  Results",
               "7.  Deep dives", "8.  Limitations and conclusion"])

        slide(pdf, "The network",
              ["Copenhagen Networks Study: ~700 first-year students, 4 weeks",
               "Every phone scans for nearby phones every 5 minutes",
               "692 nodes, 2,426,279 Bluetooth scans",
               "Signal strength stands in for distance (RSSI)",
               "Close contact = at least -75 dBm, about 1.5 m"],
              note="Accessed through Netzschleuder: networks.skewed.de/net/copenhagen")

        slide(pdf, "Network statistics",
              ["Close-contact ties (4 weeks aggregated):  23,670",
               "Mean degree 68.4   ·   median 65   ·   max 214",
               "Density 0.099   ·   giant component 673 of 692",
               "Average shortest path 2.02   ·   diameter 5",
               "Clustering 0.28, against 0.18 when rewired",
               "Degree assortativity +0.08   ·   deepest core: 49-core, 337 students"],
              number="two thirds of ties are under 30 minutes in total")

        slide(pdf, "Class cohorts", [],
              image=os.path.join(FIGURES, "stationary_graph.png"),
              number="23 cohorts of 4+ students, largest 104; 58 students without one")

        slide(pdf, "Research question",
              ["With doses for a tenth of the students, whom should we vaccinate?",
               "", "Does targeting by contact time beat targeting by number of contacts?",
               "Does the ranking survive a change in how the disease spreads?"])

        slide(pdf, "The model",
              ["Walks the real contacts in time order, five minutes at a time",
               "Close contact costs the other person 5 minutes of immunity",
               "Sharing a room costs 0.8 minutes",
               "Immunity drawn per person: 2.5 to 30 hours of exposure",
               "Infectious for 5 days, then drops out",
               "Each night a chance of exposure at home"],
              note="No latent period, no symptoms, no variation in infectiousness between people")

        slide(pdf, "The eight strategies",
              ["Random  ·  Acquaintance (a random contact of a random person)",
               "Degree  ·  Contact time  ·  Betweenness  ·  Community bridges",
               "Week-1 degree (only past data)  ·  Ring (reacts to detected cases)",
               "", "Budget: {:.0f}% of students, vaccinated before the outbreak".format(100 * COVERAGE),
               "except ring, which spends the same budget during it"])

        slide(pdf, "Monte Carlo design",
              ["A starting configuration fixes patient zero, the start time,",
               "every person's immunity and the nightly home draws",
               "Every strategy runs on the same 400 configurations",
               "Reported: mean infected, share that took off (50+), and",
               "'saved' = people spared versus no vaccination, same configuration"],
              number="{} simulations behind the table on the next slide".format(
                  len(strategies) * CONFIGS))

        slide(pdf, "Which strategy saves most", [], image=chart,
              number="{} saves {:.0f} ± {:.0f} students; random saves {:.0f}".format(
                  best["strategy"],
                  best["saved"], best["saved_ci95"],
                  [r["saved"] for r in strategies if r["strategy"] == "random"][0]))

        slide(pdf, "Results table",
              ["strategy                mean infected     took off      saved"] +
              ["{:<22} {:>8.1f}%    {:>8.1f}%   {:>7.1f}".format(
                  r["strategy"], r["mean_pct"], r["took_off_pct"], r["saved"]) for r in table] +
              ([""] + ["{:<22} {:>8.1f}%    {:>8.1f}%".format(
                  "no vaccination", baseline["mean_pct"], baseline["took_off_pct"])] if baseline else []),
              note="{} paired configurations, {:.0f}% coverage, current parameters".format(
                  CONFIGS, 100 * COVERAGE))

        slide(pdf, "What the disease parameters do", [],
              image=os.path.join(FIGURES, "bt_sweep_disease.png"),
              number="30,000 runs; thresholds dominate, not smooth trends",
              note="Sweeps use the simpler baseline disease, not the COVID-like parameters")

        slide(pdf, "Strategies against coverage", [],
              image=os.path.join(FIGURES, "bt_sweep_vaccination.png"),
              number="between 10% and 20% coverage, targeted strategies stop the outbreak")

        slide(pdf, "Epidemic curves", [],
              image=os.path.join(FIGURES, "bt_time_sick.png"),
              number="18,000 runs; the peak, not the total, is what strategies flatten")

        slide(pdf, "The outbreak, frame by frame", [], image=frame,
              number="same first case, with and without vaccination",
              note="Video: covid_best_strategy.mp4 and covid_no_vaccination.mp4")

        slide(pdf, "Deep dive 1", blank=True)
        slide(pdf, "Deep dive 2", blank=True)
        slide(pdf, "Sensitivity and robustness", blank=True)

        slide(pdf, "Limitations",
              ["Bluetooth is a noisy proxy for distance; the threshold changes everything",
               "Contacts with people outside the study were removed from the data",
               "Four weeks caps how far an outbreak can run",
               "No latent period, no symptoms, no superspreading",
               "Vaccines here are complete and immediate"])

        slide(pdf, "Conclusion",
              ["Targeting the students with the most contact time saves the most people",
               "One week of past contacts is nearly as good as four",
               "Reactive (ring) vaccination depends on how fast the disease moves",
               "", "Open question for the deep dives: does the ranking hold when",
               "the disease, the contact threshold or the budget change?"])

        slide(pdf, "References",
              ["[1]  Sapiezynski, Stopczynski, Lassen, Lehmann (2019).",
               "      Interaction data from the Copenhagen Networks Study. Scientific Data 6, 315.",
               "[2]  Sekara, Lehmann (2014). The strength of friendship ties in",
               "      proximity sensor data. PLoS ONE.",
               "[3]  Netzschleuder network catalogue, networks.skewed.de",
               "", "Python, NumPy, matplotlib, graph-tool"])

    print("wrote", OUT)


if __name__ == "__main__":
    build()
