"""Three figures from the parameter sweep, drawn from results/bt_sweep_summary.csv.

Writes figures/bt_sweep_disease.png (one panel per disease parameter),
figures/bt_sweep_vaccination.png (the strategies against coverage) and
figures/bt_sweep_strategy_period.png (the strategies against the infectious period).
Reads the summary only, so it needs neither graph-tool nor a rerun of the sweep.

    python bt_sweep_plots.py
"""
import csv
import os

import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
FIGURES = os.path.join(HERE, "figures")

# The strategies split in two by how much data they need, which is the interesting contrast:
# the ones below need the full four-week contact log, the ones after them hardly any.
FULL_DATA = ["degree", "contact time", "betweenness", "community bridges"]
LITTLE_DATA = ["random", "acquaintance", "week-1 degree", "ring"]
STUDIES = ["infectious period (days)", "immunity (minutes of exposure)",
           "close-contact threshold (RSSI dBm)", "home risk", "home dose (minutes)"]


def load_rows():
    """The summary CSV with the numeric columns parsed."""
    rows = []
    with open(os.path.join(RESULTS, "bt_sweep_summary.csv"), newline="") as handle:
        for row in csv.DictReader(handle):
            for name in ["coverage", "mean_pct", "ci95_pct", "outbreak_pct", "mean_if_outbreak_pct"]:
                row[name] = float(row[name])
            rows.append(row)
    return rows


def disease_figure(rows):
    """One panel per disease parameter, with no vaccination: how it shifts the three measures."""
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, study in zip(axes.flatten(), STUDIES):
        part = [r for r in rows if r["study"] == study]
        xs = range(len(part))
        ax.plot(xs, [r["mean_pct"] for r in part], "o-", label="mean infected")
        ax.plot(xs, [r["outbreak_pct"] for r in part], "s-", label="took off")
        ax.plot(xs, [r["mean_if_outbreak_pct"] for r in part], "^-", label="size if took off")
        ax.set_xticks(list(xs))
        ax.set_xticklabels([r["x"] for r in part])
        ax.set_ylim(0, 100)
        ax.set_ylabel("% of students")
        ax.set_title(study)
        ax.grid(True)
    axes.flatten()[-1].axis("off")
    axes.flatten()[0].legend()
    fig.suptitle("One parameter changed at a time, no vaccination, 400 runs per point")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "bt_sweep_disease.png"), dpi=120)
    plt.close(fig)


def vaccination_figure(rows):
    """The strategies against coverage, split by how much contact data each one needs.

    Every line starts at the same point, the shared no-vaccination run at 0% coverage.
    """
    part = [r for r in rows if r["study"] == "vaccination coverage"]
    none = [r for r in part if r["strategy"] == "none"][0]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    groups = [("needs the full contact log", FULL_DATA), ("needs little contact data", LITTLE_DATA)]
    metrics = [("mean_pct", "mean infected (%)"), ("outbreak_pct", "runs that took off (%)")]
    for column, (title, names) in enumerate(groups):
        for row_index, (field, label) in enumerate(metrics):
            ax = axes[row_index][column]
            for name in names:
                line = [none] + [r for r in part if r["strategy"] == name]
                ax.plot([100 * r["coverage"] for r in line], [r[field] for r in line], "o-", label=name)
            ax.axhline(none[field], linestyle="--", label="no vaccination")
            ax.set_xlabel("% of students vaccinated")
            ax.set_ylabel(label)
            ax.set_title(title)
            ax.grid(True)
            ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "bt_sweep_vaccination.png"), dpi=120)
    plt.close(fig)


def interaction_figure(rows):
    """Does the ranking of the strategies survive a change in how long people spread it?"""
    part = [r for r in rows if r["study"] == "strategy x infectious period"]
    periods = sorted({r["x"] for r in part}, key=float)
    names = ["none"] + FULL_DATA + LITTLE_DATA
    fig, ax = plt.subplots(figsize=(8, 5))
    for name in names:
        values = [[r["mean_pct"] for r in part
                   if r["strategy"] == name and r["x"] == p][0] for p in periods]
        ax.plot([float(p) for p in periods], values, "o-", label=name)
    ax.set_xlabel("infectious period (days)")
    ax.set_ylabel("mean infected (%)")
    ax.set_title("Strategies at 10% coverage, by infectious period")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "bt_sweep_strategy_period.png"), dpi=120)
    plt.close(fig)


def main():
    os.makedirs(FIGURES, exist_ok=True)
    data = load_rows()
    disease_figure(data)
    vaccination_figure(data)
    interaction_figure(data)
    print("wrote figures to", FIGURES)


if __name__ == "__main__":
    main()
