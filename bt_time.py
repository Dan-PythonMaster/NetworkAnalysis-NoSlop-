"""Epidemic curves over time for many values of each parameter, six studies at a time.

Where bt_sweep.py keeps only the total size of each outbreak, this keeps the whole curve,
hour by hour, averaged over the configurations. Writes results/bt_time_curves.npz; plot it
with bt_time_plots.py. Slow: six studies of ten-odd values, 300 runs each.

    python bt_time.py
"""
import bisect
import json
import os
import time
from multiprocessing import Pool

import numpy as np

import bt_sweep as sweep

CONFIGS = 300           # configurations averaged per parameter value
SAMPLES = 40            # individual runs kept per value, for drawing single trajectories
HORIZON_DAYS = 21       # curves are cut here, which is inside the four weeks of data
HOURS = HORIZON_DAYS * 24 + 1
DAY = sweep.DAY


def studies():
    """The plan: (name, unit of the x values, baseline value, [(label, parameters), ...])."""
    out = []
    out.append(("infectious period", "days", 3,
                [(d, sweep.variant(period=int(d * DAY))) for d in
                 [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7]]))
    out.append(("immunity", "min of exposure", "60-480",
                [("{}-{}".format(lo, 8 * lo), sweep.variant(imm_lo=lo, imm_hi=8 * lo)) for lo in
                 [15, 20, 30, 40, 50, 60, 80, 100, 120, 160]]))
    out.append(("close-contact threshold", "RSSI dBm", -80,
                [(r, sweep.variant(rssi=r)) for r in [-88, -86, -84, -82, -80, -78, -76, -74, -72]]))
    out.append(("home risk", "", 0.35,
                [(r, sweep.variant(home_risk=r)) for r in [0, 0.1, 0.2, 0.35, 0.5, 0.75, 1, 1.5, 2, 3]]))
    out.append(("vaccinate top contact time", "% of people", 0,
                [(round(100 * c), sweep.variant(strategy="contact time", coverage=c)) for c in
                 [0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.18, 0.22]]))
    out.append(("ring vaccination budget", "% of people", 0,
                [(round(100 * c), sweep.variant(strategy="ring", coverage=c)) for c in
                 [0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30]]))
    return out


def curve(task):
    """One run turned into two hourly curves: infected so far, and infectious right now.

    Times are measured from the moment patient zero was infected, not from the start of the
    study, so that curves from different configurations can be averaged.
    """
    key, p, index = task
    infected, start = sweep.outbreak(p, index, sweep.pick(p["strategy"], p["coverage"], index))
    offsets = sorted(t - start for t in infected.values())
    period = p["period"]
    total = np.empty(HOURS, dtype=np.int16)
    sick = np.empty(HOURS, dtype=np.int16)
    for hour in range(HOURS):
        now = hour * 3600
        total[hour] = bisect.bisect_right(offsets, now)
        sick[hour] = total[hour] - bisect.bisect_right(offsets, now - period)
    return key, index, total, sick


def key_of(p):
    """A hashable key for a parameter set. JSON here, because these keys also go into the
    .npz metadata, where a tuple would not survive."""
    return json.dumps(p, sort_keys=True)


def main():
    clock = time.time()
    rankings, partners, n_blocks = sweep.build_rankings()

    plan = studies()
    unique = {}
    for _, _, _, values in plan:
        for _, p in values:
            unique[key_of(p)] = p
    tasks = [(key, p, index) for key, p in unique.items() for index in range(CONFIGS)]
    print("{} parameter sets, {} simulations".format(len(unique), len(tasks)), flush=True)

    total_sum = {key: np.zeros(HOURS) for key in unique}
    sick_sum = {key: np.zeros(HOURS) for key in unique}
    took_off = {key: 0 for key in unique}
    samples = {key: np.zeros((SAMPLES, HOURS), dtype=np.int16) for key in unique}

    with Pool(sweep.WORKERS, initializer=sweep.setup, initargs=(rankings, partners)) as pool:
        done = 0
        for key, index, total, sick in pool.imap_unordered(curve, tasks, chunksize=4):
            total_sum[key] += total
            sick_sum[key] += sick
            if total[-1] >= sweep.OUTBREAK:
                took_off[key] += 1
            if index < SAMPLES:
                samples[key][index] = total
            done += 1
            if done % 1000 == 0 or done == len(tasks):
                print("  {:>5}/{}  {:.0f}s".format(done, len(tasks), time.time() - clock), flush=True)

    meta = []
    mean_total = []
    mean_sick = []
    sample_curves = []
    for name, unit, baseline, values in plan:
        for label, p in values:
            key = key_of(p)
            meta.append({"study": name, "unit": unit, "baseline": baseline, "label": label,
                         "took_off_pct": 100.0 * took_off[key] / CONFIGS})
            mean_total.append(100.0 * total_sum[key] / CONFIGS / sweep.people)
            mean_sick.append(100.0 * sick_sum[key] / CONFIGS / sweep.people)
            sample_curves.append(100.0 * samples[key] / sweep.people)

    os.makedirs(sweep.RESULTS, exist_ok=True)
    np.savez_compressed(
        os.path.join(sweep.RESULTS, "bt_time_curves.npz"),
        mean_total=np.array(mean_total),
        mean_sick=np.array(mean_sick),
        samples=np.array(sample_curves, dtype=np.float32),
        meta=json.dumps(meta),
        hours=np.arange(HOURS),
        configs=CONFIGS,
    )
    print("saved bt_time_curves.npz to {} in {:.0f}s".format(sweep.RESULTS, time.time() - clock))


if __name__ == "__main__":
    main()
