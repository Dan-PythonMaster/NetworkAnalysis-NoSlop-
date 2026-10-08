"""Monte Carlo comparison of the eight vaccination strategies under COVID-like parameters.

Every strategy is run on the same 400 starting configurations (see outbreak() in
bt_sweep.py), so "saved" below is a paired difference: for each configuration, how many
people this strategy spared compared with not vaccinating at all. Takes about 20 minutes.
Prints a table and writes results/covid_strategies.csv.

    python covid_strategies.py
"""
import csv
import math
import os
import statistics
import time
from multiprocessing import Pool

import bt_sweep as sweep
from covid_params import COVID

CONFIGS = 400       # paired configurations per strategy
COVERAGE = 0.10     # share of the students who get a dose


def main():
    clock = time.time()
    rankings, partners, n_blocks = sweep.build_rankings()
    names = ["none"] + sweep.STRATEGIES
    params = {}
    for name in names:
        coverage = 0.0 if name == "none" else COVERAGE
        params[name] = sweep.variant(**COVID, strategy=name, coverage=coverage)
    tasks = [(name, params[name], index) for name in names for index in range(CONFIGS)]

    sizes = {name: [0] * CONFIGS for name in names}
    with Pool(sweep.WORKERS, initializer=sweep.setup, initargs=(rankings, partners)) as pool:
        for name, index, size, peak in pool.imap_unordered(sweep.run, tasks, chunksize=8):
            sizes[name][index] = size

    # "saved" is the paired difference against no vaccination on the very same
    # configuration, which is far less noisy than the difference of the two means.
    people = sweep.people
    baseline = sizes["none"]
    table = []
    for name in names:
        values = sizes[name]
        saved = [b - v for b, v in zip(baseline, values)]
        table.append({
            "strategy": name,
            "mean": statistics.mean(values),
            "std": statistics.stdev(values),
            "median": statistics.median(values),
            "mean_pct": 100 * statistics.mean(values) / people,
            "took_off_pct": 100 * sum(1 for v in values if v >= sweep.OUTBREAK) / CONFIGS,
            "saved": statistics.mean(saved),
            "saved_ci95": 1.96 * statistics.stdev(saved) / math.sqrt(CONFIGS),
        })
    table.sort(key=lambda row: row["mean"])

    print("COVID-like parameters, {} configurations, {:.0f}% coverage".format(CONFIGS, 100 * COVERAGE))
    print("{:<20}{:>8}{:>8}{:>8}{:>9}{:>10}{:>16}".format(
        "strategy", "mean", "std", "median", "mean %", "took off", "saved (95% CI)"))
    for row in table:
        print("{:<20}{:>8.1f}{:>8.1f}{:>8.0f}{:>8.1f}%{:>9.1f}%{:>9.1f} +-{:>4.1f}".format(
            row["strategy"], row["mean"], row["std"], row["median"], row["mean_pct"],
            row["took_off_pct"], row["saved"], row["saved_ci95"]))

    os.makedirs(sweep.RESULTS, exist_ok=True)
    with open(os.path.join(sweep.RESULTS, "covid_strategies.csv"), "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(table)
    print("best:", [row["strategy"] for row in table if row["strategy"] != "none"][0])
    print("wrote covid_strategies.csv to", sweep.RESULTS)
    print("finished in {:.0f}s".format(time.time() - clock))


if __name__ == "__main__":
    main()
