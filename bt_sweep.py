"""Outbreak simulator and parameter sweep on the Copenhagen Bluetooth proximity data.

This module is the core of the project; the other scripts import it. It holds

  * the contact data, loaded once at import time (``edges``, ``people``),
  * the simulator (``outbreak``, ``simulate``),
  * the eight vaccination strategies (``build_rankings``, ``pick``),
  * the one-at-a-time parameter sweep that ``main`` runs.

Running the module executes the full sweep (about eight minutes on eight cores) and
writes results/bt_sweep_runs.csv and results/bt_sweep_summary.csv.

    python bt_sweep.py
"""
import bisect
import csv
import math
import os
import random
import statistics
import time
from array import array
from multiprocessing import Pool

import graph_tool.all as gt

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

DAY = 86400             # every timestamp in the data is a whole second from the study start
SEED_WINDOW = 7 * DAY   # patient zero is infected at a random moment in the first week
HOME_HOUR = 22          # the nightly home exposure is resolved at 22:00
DOSE = 5                # minutes of exposure charged for one close-contact scan
OUTBREAK = 50           # a run counts as having "taken off" once this many people are infected
CONFIGS = 400           # starting configurations simulated per parameter set
WORKERS = 8             # worker processes

# The baseline disease and intervention. Every row of the sweep is this dictionary with one
# or two values changed (see variant), and covid_params.COVID overrides it with the
# COVID-like values. Exposure is bookkept in minutes: a contact charges the susceptible
# person some minutes, and they are infected once their personal budget runs out.
BASE = {
    "rssi": -80,            # close contact: a Bluetooth scan at or above this strength (dBm)
    "imm_lo": 60,           # resistance is uniform on [imm_lo, imm_hi] minutes of exposure
    "imm_hi": 480,
    "period": 3 * DAY,      # how long an infected person keeps spreading, then drops out
    "home_risk": 0.35,      # nightly chance of exposure at home, scaled by prevalence
    "home_dose": 60,        # minutes charged for a night at home with an exposure
    "room_rssi": -90,       # same room: a scan at or above this strength (dBm)
    "room_dose": 0,         # minutes charged per five-minute slot spent in a room with a case
    "strategy": "none",     # "none" or one of STRATEGIES
    "coverage": 0.0,        # share of the students who get a dose
    "ring_delay": DAY,      # how long after infection a case is traced (ring strategy only)
    "ring_per_case": 10,    # contacts vaccinated per traced case (ring strategy only)
}

STRATEGIES = [
    "random",
    "acquaintance",
    "week-1 degree",
    "ring",
    "degree",
    "contact time",
    "betweenness",
    "community bridges",
]

# Loaded at import time rather than inside main(): a Pool worker imports this module in a
# fresh process, and the simulations it runs there need the contacts too.
_graph = gt.collection.ns["copenhagen/bt"]
people = _graph.num_vertices()
edges = _graph.get_edges(eprops=[_graph.ep["timestamp"], _graph.ep["rssi"]]).astype("int32")
edges = edges[edges[:, 2].argsort(kind="stable")]   # columns: person a, person b, time, signal
del _graph

CLOSE_CACHE = {}    # signal threshold -> (a, b, time) of every contact at or above it
SIGNAL_CACHE = {}   # signal threshold -> the same, plus the signal strength itself

# Filled by setup() in each worker process. The rankings are expensive, so they are built
# once in the parent and handed to the workers instead of recomputed per simulation.
RANKINGS = {}
PARTNERS = {}
PARTNERED = []


def contacts_for(rssi):
    """The contacts at or above a signal strength, in time order, as three parallel arrays.

    array("i", ...) rather than NumPy arrays, because the element-by-element walk in
    outbreak() is several times faster over them, and that loop is the whole cost.
    """
    if rssi not in CLOSE_CACHE:
        keep = edges[:, 3] >= rssi
        CLOSE_CACHE[rssi] = (
            array("i", edges[keep, 0].tolist()),
            array("i", edges[keep, 1].tolist()),
            array("i", edges[keep, 2].tolist()),
        )
    return CLOSE_CACHE[rssi]


def contacts_with_signal(rssi):
    """As contacts_for, plus the signal strength, so one pass can serve rooms and contacts."""
    if rssi not in SIGNAL_CACHE:
        keep = edges[:, 3] >= rssi
        SIGNAL_CACHE[rssi] = (
            array("i", edges[keep, 0].tolist()),
            array("i", edges[keep, 1].tolist()),
            array("i", edges[keep, 2].tolist()),
            array("i", edges[keep, 3].tolist()),
        )
    return SIGNAL_CACHE[rssi]


def setup(rankings, partners):
    """Pool initializer: publish the rankings built in the parent to this worker."""
    RANKINGS.update(rankings)
    PARTNERS.update(partners)
    PARTNERED[:] = sorted(partners)


def build_rankings():
    """Rank everybody by each targeting criterion, once, over the whole four weeks.

    Returns (rankings, partners, communities): the orderings pick() draws from, who each
    person met at close range, and how many blocks the block model found.
    """
    a_arr, b_arr, t_arr = contacts_for(BASE["rssi"])
    partners = {}
    week = {}
    strength = [0] * people
    for a, b, t in zip(a_arr, b_arr, t_arr):
        partners.setdefault(a, set()).add(b)
        partners.setdefault(b, set()).add(a)
        strength[a] += 1
        strength[b] += 1
        if t < 7 * DAY:
            week.setdefault(a, set()).add(b)
            week.setdefault(b, set()).add(a)

    pairs = set()
    for a, b in zip(a_arr, b_arr):
        pairs.add((min(a, b), max(a, b)))
    pairs = sorted(pairs)

    close = gt.Graph(directed=False)
    close.add_vertex(people)
    close.add_edge_list(pairs)
    between = list(gt.betweenness(close)[0].a)
    blocks = list(gt.minimize_blockmodel_dl(close).get_blocks().a)

    bridging = [0] * people
    for a, b in pairs:
        if blocks[a] != blocks[b]:
            bridging[a] += 1
            bridging[b] += 1

    def ranked(score):
        return sorted(range(people), key=lambda person: (-score[person], person))

    rankings = {
        "degree": ranked([len(partners.get(p, ())) for p in range(people)]),
        "contact time": ranked(strength),
        "betweenness": ranked(between),
        "community bridges": ranked(bridging),
        "week-1 degree": ranked([len(week.get(p, ())) for p in range(people)]),
    }
    return rankings, partners, len(set(blocks))


def pick(strategy, coverage, index):
    """Who gets a dose before the outbreak starts, for one strategy and configuration.

    Returns an empty set for "none" and for "ring", which instead spends its budget during
    the outbreak (see outbreak()). The two random strategies are seeded from the
    configuration index so that configuration 7 always vaccinates the same people.
    """
    doses = int(round(coverage * people))
    if strategy in ("none", "ring") or doses == 0:
        return set()
    if strategy == "random":
        return set(random.Random(7000 + index).sample(range(people), doses))
    if strategy == "acquaintance":
        # Vaccinate a random contact of a random person. No ranking needed, yet it lands on
        # well-connected people more often than chance, because they are somebody's contact
        # more often ("a friend of a random friend").
        rng = random.Random(7000 + index)
        chosen = set()
        while len(chosen) < doses:
            person = rng.randrange(people)
            if person in PARTNERS:
                chosen.add(rng.choice(sorted(PARTNERS[person])))
        return chosen
    return set(RANKINGS[strategy][:doses])


def outbreak(p, index, static_vaccinated, details=False):
    """Run one outbreak over the real contacts and return who was infected, and when.

    ``p`` is a parameter dictionary (see BASE), ``index`` selects the starting
    configuration, and ``static_vaccinated`` is the set from pick(). With details=True the
    extra bookkeeping the animation needs comes back as well.

    Everything random that does not depend on the strategy is drawn from seeds fixed by
    ``index`` alone, so that the same configuration gives the same patient zero, the same
    resistances and the same nightly home draws under every strategy. That pairing is what
    makes the strategy comparison in covid_strategies.py meaningful.
    """
    rooms_on = p["room_dose"] > 0
    close_cut = p["rssi"]
    if rooms_on:
        a_arr, b_arr, t_arr, r_arr = contacts_with_signal(p["room_rssi"])
    else:
        a_arr, b_arr, t_arr = contacts_for(close_cut)
        r_arr = None

    # Draw the strategy-independent randomness first, and always in the same order, so that
    # the stream does not shift when a strategy changes who is vaccinated. Resistances come
    # in whole multiples of five minutes, the size of one close-contact dose.
    rng = random.Random(index)
    steps = (p["imm_hi"] - p["imm_lo"]) // 5 + 1
    immunity = [p["imm_lo"] + 5 * int(rng.random() * steps) for _ in range(people)]
    patient_zero = PARTNERED[int(rng.random() * len(PARTNERED))]
    start = int(rng.random() * SEED_WINDOW)

    period = p["period"]
    room_dose = p["room_dose"]
    home_risk = p["home_risk"]
    home_dose = p["home_dose"]
    home = random.Random(90000 + index)
    ring = p["strategy"] == "ring"
    budget = int(round(p["coverage"] * people)) if ring else 0
    delay = p["ring_delay"]
    per_case = p["ring_per_case"]

    # Patient zero is the same person in this configuration whatever the strategy, even when
    # the strategy happened to vaccinate them: dropping them instead would change which
    # outbreak we are comparing. They keep the dose in `dosed` (it was spent) but not the
    # protection in `vaccinated`.
    vaccinated = set(static_vaccinated)
    vaccinated.discard(patient_zero)
    dosed = set(static_vaccinated)
    infected = {patient_zero: start}
    until = {patient_zero: start + period}
    horizon = until[patient_zero]
    detections = [(start + delay, patient_zero)] if ring else []
    next_detection = 0
    detected = set()
    seen = {}

    night = start - start % DAY + HOME_HOUR * 3600
    if night < start:
        night += DAY

    def catch(person, when):
        """Infect somebody: note the time, when they drop out, and queue them for tracing."""
        nonlocal horizon
        infected[person] = when
        until[person] = when + period
        horizon = max(horizon, until[person])
        if ring:
            detections.append((when + delay, person))

    def share_room(edges, when):
        """Charge room exposure for one five-minute slot.

        Everybody detected in the slot is merged into rooms with a union-find, so that A-B
        and B-C put all three in one room. A room with at least one infectious person in it
        charges room_dose to every susceptible member, once, however many cases it holds.
        """
        parent = {}

        def find(x):
            root = x
            while parent[root] != root:
                root = parent[root]
            while parent[x] != root:
                parent[x], x = root, parent[x]
            return root

        for a, b in edges:
            parent.setdefault(a, a)
            parent.setdefault(b, b)
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
        groups = {}
        for person in parent:
            groups.setdefault(find(person), []).append(person)
        for members in groups.values():
            spreading = False
            for person in members:
                when_caught = infected.get(person)
                if when_caught is not None and when_caught <= when <= until[person]:
                    spreading = True
                    break
            if not spreading:
                continue
            for person in members:
                if person in infected or person in vaccinated:
                    continue
                immunity[person] -= room_dose
                if immunity[person] <= 0:
                    catch(person, when)

    # Walk the contacts in time order from the moment patient zero is infected. `horizon` is
    # the last moment anybody now infected can still spread, so passing it means nobody is
    # infectious any more and nothing further can happen: most runs stop here within days.
    slot_time = -1
    slot_edges = []
    first = bisect.bisect_left(t_arr, start)
    for i in range(first, len(t_arr)):
        t = t_arr[i]
        if t > horizon:
            break

        # Resolve every night that has passed since the previous contact.
        while t >= night:
            if home_risk > 0:
                spreading = 0
                for person, when in infected.items():
                    if when <= night <= until[person]:
                        spreading += 1
                chance = home_risk * spreading / people
                # Draw for everybody, including the infected and the vaccinated whose draw
                # cannot matter, to keep this stream identical across strategies.
                for person in range(people):
                    draw = home.random()
                    if draw < chance and person not in infected and person not in vaccinated:
                        immunity[person] -= home_dose
                        if immunity[person] <= 0:
                            catch(person, night)
            night += DAY

        if rooms_on and t != slot_time:
            if slot_time >= 0:
                share_room(slot_edges, slot_time)
            slot_time = t
            slot_edges = []

        # Ring vaccination: a case traced ring_delay after being infected spends doses on its
        # most frequent contacts so far. `dosed` keeps a dose from being spent twice.
        if ring:
            while next_detection < len(detections) and detections[next_detection][0] <= t:
                case = detections[next_detection][1]
                next_detection += 1
                detected.add(case)
                given = 0
                ranked = sorted(seen.get(case, {}).items(), key=lambda item: -item[1])
                for contact, _ in ranked:
                    if budget <= 0 or given >= per_case:
                        break
                    if contact in dosed or contact in detected:
                        continue
                    budget -= 1
                    given += 1
                    dosed.add(contact)
                    if contact not in infected:
                        vaccinated.add(contact)

        a = a_arr[i]
        b = b_arr[i]
        if rooms_on:
            # With rooms on we walk the weaker room threshold, so every detection feeds the
            # room for this slot and only the strong ones go on to count as close contact.
            slot_edges.append((a, b))
            if r_arr[i] < close_cut:
                continue

        if ring:
            row = seen.setdefault(a, {})
            row[b] = row.get(b, 0) + 1
            row = seen.setdefault(b, {})
            row[a] = row.get(a, 0) + 1

        # Close contact. One of the pair must be infectious and the other never infected;
        # a vaccinated person neither catches it nor passes it on.
        if a in vaccinated or b in vaccinated:
            continue
        ta = infected.get(a)
        tb = infected.get(b)
        if ta is not None:
            if tb is None and t <= until[a]:
                immunity[b] -= DOSE
                if immunity[b] <= 0:
                    catch(b, t)
        elif tb is not None and t <= until[b]:
            immunity[a] -= DOSE
            if immunity[a] <= 0:
                catch(a, t)

    if rooms_on and slot_time >= 0:
        share_room(slot_edges, slot_time)

    if details:
        return infected, start, until, dosed, vaccinated
    return infected, start


def simulate(p, index, static_vaccinated):
    """One run reduced to the two numbers the sweep stores: total infected and peak.

    The peak is the largest number of people infectious at the same moment, found by
    sliding a window of one infectious period over the infection times.
    """
    infected, start = outbreak(p, index, static_vaccinated)
    period = p["period"]
    times = sorted(infected.values())
    peak = 0
    j = 0
    for i, when in enumerate(times):
        while times[j] < when - period:
            j += 1
        peak = max(peak, i - j + 1)
    return len(infected), peak


def run(task):
    """One unit of work for the Pool: (parameter-set key, parameters, configuration)."""
    key, p, index = task
    size, peak = simulate(p, index, pick(p["strategy"], p["coverage"], index))
    return key, index, size, peak


def variant(**changes):
    """BASE with some values replaced, which is how every parameter set here is built."""
    p = dict(BASE)
    p.update(changes)
    return p


def build_studies():
    """The sweep plan: (study name, x value, strategy, coverage, parameters) per row.

    One parameter is changed at a time from BASE, except for the last study, which crosses
    the strategies with the infectious period to see whether the ranking holds.
    """
    studies = []
    for days in [0.5, 1, 2, 3, 5, 7]:
        studies.append(("infectious period (days)", days, "none", 0.0, variant(period=int(days * DAY))))
    for lo, hi in [(15, 120), (30, 240), (60, 480), (120, 960), (240, 1920)]:
        studies.append(("immunity (minutes of exposure)", "{}-{}".format(lo, hi), "none", 0.0,
                        variant(imm_lo=lo, imm_hi=hi)))
    for rssi in [-85, -80, -75, -70]:
        studies.append(("close-contact threshold (RSSI dBm)", rssi, "none", 0.0, variant(rssi=rssi)))
    for risk in [0, 0.1, 0.35, 1, 3]:
        studies.append(("home risk", risk, "none", 0.0, variant(home_risk=risk)))
    for dose in [15, 60, 240]:
        studies.append(("home dose (minutes)", dose, "none", 0.0, variant(home_dose=dose)))

    studies.append(("vaccination coverage", 0.0, "none", 0.0, variant()))
    for strategy in STRATEGIES:
        for coverage in [0.025, 0.05, 0.10, 0.20, 0.30]:
            studies.append(("vaccination coverage", coverage, strategy, coverage,
                            variant(strategy=strategy, coverage=coverage)))

    for days in [1, 3, 7]:
        studies.append(("strategy x infectious period", days, "none", 0.0, variant(period=days * DAY)))
        for strategy in STRATEGIES:
            studies.append(("strategy x infectious period", days, strategy, 0.10,
                            variant(strategy=strategy, coverage=0.10, period=days * DAY)))
    return studies


def key_of(p):
    """A hashable key for a parameter set, so that rows sharing one are simulated once."""
    return tuple(sorted(p.items()))


def summarise(rows):
    """Average one parameter set's runs. `rows` is a list of (size, peak) pairs."""
    sizes = [size for size, peak in rows]
    big = [size for size in sizes if size >= OUTBREAK]
    mean = statistics.mean(sizes)
    std = statistics.stdev(sizes)
    ci = 1.96 * std / math.sqrt(len(sizes))
    return {
        "runs": len(sizes),
        "mean": mean,
        "std": std,
        "ci95": ci,
        "mean_pct": 100.0 * mean / people,
        "ci95_pct": 100.0 * ci / people,
        "took_off_pct": 100.0 * len(big) / len(sizes),
        "median": statistics.median(sizes),
        "peak_mean": statistics.mean(peak for size, peak in rows),
        # Mean size of the runs that took off, which separates "how often does it spread"
        # from "how big does it get once it does".
        "mean_if_outbreak_pct": 100.0 * statistics.mean(big) / people if big else 0.0,
    }


def write_runs(path, unique, results):
    """Every single simulation, one row each: the parameters, the configuration, the result."""
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(BASE.keys()) + ["config", "size", "peak"])
        for key, p in unique.items():
            for index, (size, peak) in enumerate(results[key]):
                writer.writerow([p[name] for name in BASE] + [index, size, peak])


def write_summary(path, studies, results):
    """One row per study row, averaged over the configurations, printed as it is written."""
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["study", "x", "strategy", "coverage", "runs", "mean", "std", "ci95",
                         "mean_pct", "ci95_pct", "outbreak_pct", "median", "peak_mean",
                         "mean_if_outbreak_pct"])
        current = None
        for study, x, strategy, coverage, p in studies:
            s = summarise(results[key_of(p)])
            writer.writerow([study, x, strategy, coverage, s["runs"],
                             round(s["mean"], 2), round(s["std"], 2), round(s["ci95"], 2),
                             round(s["mean_pct"], 2), round(s["ci95_pct"], 2),
                             round(s["took_off_pct"], 1), s["median"],
                             round(s["peak_mean"], 2), round(s["mean_if_outbreak_pct"], 2)])
            if study != current:
                current = study
                print()
                print(study)
                print("  {:<20}{:>10}{:>8}{:>8}{:>9}{:>10}{:>12}{:>8}".format(
                    "strategy", "x", "mean", "std", "mean %", "outbreak%", "if outbreak", "peak"))
            print("  {:<20}{:>10}{:>8.1f}{:>8.1f}{:>9.1f}{:>10.1f}{:>11.1f}%{:>8.1f}".format(
                strategy, str(x), s["mean"], s["std"], s["mean_pct"], s["took_off_pct"],
                s["mean_if_outbreak_pct"], s["peak_mean"]))


def main():
    clock = time.time()
    rankings, partners, n_blocks = build_rankings()
    print("people {}   communities {}   rankings ready in {:.0f}s".format(
        people, n_blocks, time.time() - clock), flush=True)

    # Different study rows often share a parameter set (every study repeats the untouched
    # baseline, for one), so simulate each distinct set once and look it up per row.
    studies = build_studies()
    unique = {}
    for study in studies:
        unique[key_of(study[4])] = study[4]
    tasks = [(key, p, index) for key, p in unique.items() for index in range(CONFIGS)]
    print("{} study rows, {} unique parameter sets, {} simulations".format(
        len(studies), len(unique), len(tasks)), flush=True)

    results = {key: [None] * CONFIGS for key in unique}
    with Pool(WORKERS, initializer=setup, initargs=(rankings, partners)) as pool:
        done = 0
        for key, index, size, peak in pool.imap_unordered(run, tasks, chunksize=4):
            results[key][index] = (size, peak)
            done += 1
            if done % 250 == 0 or done == len(tasks):
                print("  {:>5}/{}  {:.0f}s".format(done, len(tasks), time.time() - clock), flush=True)

    os.makedirs(RESULTS, exist_ok=True)
    write_runs(os.path.join(RESULTS, "bt_sweep_runs.csv"), unique, results)
    write_summary(os.path.join(RESULTS, "bt_sweep_summary.csv"), studies, results)
    print()
    print("wrote bt_sweep_runs.csv and bt_sweep_summary.csv to", RESULTS)
    print("finished in {:.0f}s".format(time.time() - clock))


if __name__ == "__main__":
    main()
