"""Two figures from the epidemic curves in results/bt_time_curves.npz.

figures/bt_time_infected.png is the running total of infections, bt_time_sick.png the
number infectious at the same moment, each with one panel per parameter study. Five values
per study are drawn, evenly spaced through the values that were simulated.

    python bt_time_plots.py
"""
import json
import os

import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
FIGURES = os.path.join(HERE, "figures")
PER_PANEL = 5   # how many of each study's values to draw, evenly spaced


def load_studies(meta):
    """Group the rows of the .npz metadata back into the studies they came from."""
    studies = []
    for i, row in enumerate(meta):
        if not studies or studies[-1]["name"] != row["study"]:
            studies.append({"name": row["study"], "unit": row["unit"], "rows": []})
        studies[-1]["rows"].append(i)
    return studies


def curves_figure(values, studies, meta, days, configs, filename, title, ylabel):
    """One panel per study, each holding a few evenly spaced values of that parameter."""
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for ax, study in zip(axes.flatten(), studies):
        rows = study["rows"]
        picks = sorted(set(int(round(x)) for x in np.linspace(0, len(rows) - 1, PER_PANEL)))
        for k in picks:
            label = "{} {}".format(meta[rows[k]]["label"], study["unit"]).strip()
            ax.plot(days, values[rows[k]], label=label)
        ax.set_xlabel("days since the first case")
        ax.set_ylabel(ylabel)
        ax.set_title(study["name"])
        ax.grid(True)
        ax.legend()
    fig.suptitle("{} (mean of {} runs per value)".format(title, configs))
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, filename), dpi=120)
    plt.close(fig)


def main():
    os.makedirs(FIGURES, exist_ok=True)
    data = np.load(os.path.join(RESULTS, "bt_time_curves.npz"))
    meta = json.loads(str(data["meta"]))
    studies = load_studies(meta)
    days = data["hours"] / 24.0
    configs = int(data["configs"])
    curves_figure(data["mean_total"], studies, meta, days, configs,
                  "bt_time_infected.png", "Infected so far", "% infected")
    curves_figure(data["mean_sick"], studies, meta, days, configs,
                  "bt_time_sick.png", "Infectious at the same time", "% infectious")
    print("wrote figures to", FIGURES)


if __name__ == "__main__":
    main()
