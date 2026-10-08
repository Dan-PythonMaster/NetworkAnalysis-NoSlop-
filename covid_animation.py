"""Animates one outbreak over the proximity network, five simulated minutes per frame.

Pass the scenarios to render as arguments; both run the same outbreak (same patient zero,
same resistances), so the two videos can be compared frame by frame:

    python covid_animation.py "contact time"        # the best strategy
    python covid_animation.py none                  # no vaccination
    python covid_animation.py none "contact time"   # both

The layout is stationary. Students who spend a lot of time in the same room are grouped
into class cohorts by a block model, each cohort is drawn as a packed disc, and the discs
are pushed apart; see class_layout. Nothing moves during the video except the colours, the
room crosses and the contact lines, which is what makes it readable.

Writes figures/stationary_graph.png (the layout, drawn before the slow part starts) and one
mp4 per scenario. Needs ffmpeg on PATH.
"""
import os
import statistics
import subprocess
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.lines import Line2D

import graph_tool.all as gt

import bt_sweep as sweep
from covid_params import COVID

HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.join(HERE, "figures")

# strategy -> (caption, coverage, output file)
SCENARIOS = {
    "none": ("no vaccination", 0.0, "covid_no_vaccination.mp4"),
    "contact time": ("vaccinate the 10% with the most contact time", 0.10, "covid_best_strategy.mp4"),
}
WINDOW = 5 * 60         # simulated seconds per frame, the interval the phones scan at
FPS = 30
PICK_FROM = 200         # configurations tried when looking for one worth watching
MAX_MEGABYTES = 7.2     # the video is re-encoded to fit under this

CLASS_CUT = 60          # five-minute slots two students must share to count as classmates
CLASS_MIN = 4           # smaller blocks are not treated as a cohort
CLASS_SEAT = 0.85       # disc radius per sqrt(cohort size)
CLASS_GAP = 1.25        # how far apart the discs are pushed, as a share of their radii

ROOM_MIN = 3            # people needed before a group of detections counts as a room
ROOM_HOLD = 3           # frames a room must persist before it is drawn, which kills the flicker
ROOM_MEMORY = 12        # frames a vanished room is remembered, so it keeps its colour
ROOM_GRACE = 6          # frames a settled room stays drawn while nobody is detected in it
ROOM_COLORS = plt.cm.tab10.colors

POPULAR_PERCENTILES = [75, 95]  # patient zero is picked from this band of close-contact degree
DAY = sweep.DAY


def close_degree():
    """How many distinct people each student met at close range over the four weeks."""
    a_arr, b_arr, t_arr = sweep.contacts_for(COVID["rssi"])
    a = np.asarray(a_arr)
    b = np.asarray(b_arr)
    pairs = np.unique(np.minimum(a, b) * sweep.people + np.maximum(a, b))
    return np.bincount(np.concatenate([pairs // sweep.people, pairs % sweep.people]),
                       minlength=sweep.people)


def choose_config():
    """Find a starting configuration worth watching, and return its index.

    An average video is a dull one: most configurations fizzle out in a few days. This asks
    for an outbreak that took off, started from a student of unremarkable popularity, and
    ended up closest to the median size among the candidates.
    """
    params = sweep.variant(**COVID)
    degree = close_degree()
    low, high = np.percentile(degree, POPULAR_PERCENTILES)
    vaccinated = sweep.pick("contact time", SCENARIOS["contact time"][1], 0)
    candidates = []
    for index in range(PICK_FROM):
        infected, start = sweep.outbreak(params, index, set())
        zero = min(infected, key=infected.get)
        if low <= degree[zero] <= high and zero not in vaccinated and len(infected) >= sweep.OUTBREAK:
            candidates.append((len(infected), index, zero))
    if not candidates:
        raise SystemExit("no configuration out of {} both took off and started from a "
                         "student in the {}th-{}th percentile of contacts; widen "
                         "POPULAR_PERCENTILES or raise PICK_FROM".format(
                             PICK_FROM, POPULAR_PERCENTILES[0], POPULAR_PERCENTILES[1]))
    middle = statistics.median(size for size, index, zero in candidates)
    size, index, zero = min(candidates, key=lambda c: abs(c[0] - middle))
    print("config {}: patient zero {} with {} close contacts, {} infected without vaccination".format(
        index, zero, degree[zero], size))
    return index


def sunflower(count, radius):
    """Pack points evenly in a disc (the sunflower spiral), for seating one cohort."""
    index = np.arange(count) + 0.5
    reach = radius * np.sqrt(index / count)
    angle = np.pi * (1 + 5 ** 0.5) * index
    return np.stack([reach * np.cos(angle), reach * np.sin(angle)], axis=1)


def class_groups():
    """Split the students into class cohorts.

    Two students are classmates if they were detected in the same five-minute slot at least
    CLASS_CUT times over the four weeks, which is about five hours together. A block model
    on that graph gives the cohorts. Returns (cohorts, students without one, classmate pairs).
    """
    people = sweep.people
    a_arr, b_arr, t_arr, r_arr = sweep.contacts_with_signal(COVID["room_rssi"])
    a = np.asarray(a_arr)
    b = np.asarray(b_arr)
    keys, counts = np.unique(np.minimum(a, b) * people + np.maximum(a, b), return_counts=True)
    keep = counts >= CLASS_CUT
    pairs = np.stack([keys[keep] // people, keys[keep] % people], axis=1)

    graph = gt.Graph(directed=False)
    graph.add_vertex(people)
    graph.add_edge_list(pairs.tolist())
    blocks = np.asarray(gt.minimize_blockmodel_dl(graph).get_blocks().a)

    members = {}
    for person, block in enumerate(blocks.tolist()):
        members.setdefault(block, []).append(person)
    classes = [sorted(group) for group in members.values() if len(group) >= CLASS_MIN]
    classes.sort(key=len, reverse=True)
    placed = {person for group in classes for person in group}
    loose = [person for person in range(people) if person not in placed]
    return classes, loose, pairs


def class_layout():
    """Place every student once, and for good: the fixed layout the whole video uses.

    The cohorts are laid out by a small spring relaxation of their centres only: discs push
    each other apart until they no longer overlap, cohorts that share classmates pull
    together, and a weak pull towards the origin keeps the picture compact. Students inside
    a cohort are seated by sunflower packing, and those without a cohort sit on an outer ring.
    """
    classes, loose, pairs = class_groups()
    home = {person: index for index, group in enumerate(classes) for person in group}
    count = len(classes)

    links = np.zeros((count, count))
    for one, two in pairs.tolist():
        first, second = home.get(one), home.get(two)
        if first is not None and second is not None and first != second:
            links[first, second] += 1
            links[second, first] += 1

    sizes = np.array([len(group) for group in classes], dtype=float)
    radii = CLASS_SEAT * np.sqrt(sizes)
    rng = np.random.default_rng(5)
    angle = rng.random(count) * 2 * np.pi
    centres = np.stack([np.cos(angle), np.sin(angle)], axis=1) * (radii.sum() * 0.35)

    weight = links / (links.max() + 1e-9)
    for step in range(600):      # plain gradient steps; 600 is well past settling
        gap = centres[:, None, :] - centres[None, :, :]
        distance = np.sqrt((gap ** 2).sum(-1)) + np.eye(count)
        want = (radii[:, None] + radii[None, :]) * CLASS_GAP
        push = np.clip(want - distance, 0, None) / distance
        np.fill_diagonal(push, 0)
        move = (gap * push[:, :, None]).sum(axis=1)
        pull = -(gap / distance[:, :, None]) * (weight * np.clip(distance - want, 0, None))[:, :, None]
        move += 0.05 * pull.sum(axis=1)
        move -= 0.004 * centres
        centres += 0.35 * move

    pos = np.zeros((sweep.people, 2))
    for index, group in enumerate(classes):
        pos[group] = centres[index] + sunflower(len(group), radii[index] * 0.9)

    if loose:
        far = np.abs(centres).max() + radii.max() * 1.6
        ring = np.linspace(0, 2 * np.pi, len(loose), endpoint=False)
        pos[loose] = np.stack([far * np.cos(ring), far * np.sin(ring)], axis=1)
    return pos, classes, loose


def group_rooms(a_list, b_list):
    """Merge one frame's detections into rooms with a union-find, as the simulator does.

    A and B detecting each other and B and C detecting each other puts all three in one
    room. Groups smaller than ROOM_MIN are dropped as noise.
    """
    parent = {}

    def find(x):
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for a, b in zip(a_list, b_list):
        parent.setdefault(a, a)
        parent.setdefault(b, b)
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for person in parent:
        groups.setdefault(find(person), set()).add(person)
    return [members for members in groups.values() if len(members) >= ROOM_MIN]


class RoomTracker:
    """Gives rooms an identity across frames, so a room keeps one colour while it lasts.

    Each frame's groups are matched to the rooms already known by Jaccard overlap of their
    members. A room is only drawn once it has persisted ROOM_HOLD frames, which removes the
    flicker of groups that appear for a single scan, and it survives ROOM_GRACE frames of
    nobody being detected, which bridges the gaps when phones miss a scan.
    """

    def __init__(self):
        self.rooms = {}
        self.next_id = 0

    def follow(self, groups):
        """Take this frame's groups and return the rooms settled enough to draw."""
        for room in self.rooms.values():
            room["missing"] += 1
        matched = set()
        for members in groups:
            best, score = None, 0.0
            for room_id, room in self.rooms.items():
                if room_id in matched:
                    continue
                shared = len(members & room["members"]) / len(members | room["members"])
                if shared > score:
                    best, score = room_id, shared
            if best is None or score < 0.3:
                best = self.next_id
                self.next_id += 1
                self.rooms[best] = {"members": members, "age": 0, "missing": 0}
            room = self.rooms[best]
            room["members"] = members
            room["age"] += 1
            room["missing"] = 0
            matched.add(best)
        for room_id in [key for key, room in self.rooms.items() if room["missing"] > ROOM_MEMORY]:
            del self.rooms[room_id]
        settled = []
        for room_id, room in self.rooms.items():
            if room["age"] >= ROOM_HOLD and room["missing"] <= ROOM_GRACE:
                settled.append((room_id, sorted(room["members"])))
        return settled


def compress(source, target, seconds, tag):
    """Re-encode to a target size with ffmpeg, two passes, and delete the raw file.

    matplotlib's own mp4 runs to tens of megabytes, which is awkward in a repository and
    over the limit on most chat clients; a bitrate computed from the duration fixes the size.
    """
    kbps = int(MAX_MEGABYTES * 8 * 1024 / seconds)
    log = os.path.join(HERE, "ffmpeg2pass_" + tag)
    common = ["ffmpeg", "-y", "-v", "error", "-i", source, "-c:v", "libx264", "-preset", "slow",
              "-b:v", "{}k".format(kbps), "-pix_fmt", "yuv420p", "-passlogfile", log, "-an"]
    subprocess.run(common + ["-pass", "1", "-f", "mp4", os.devnull], check=True)
    subprocess.run(common + ["-pass", "2", target], check=True)
    for name in os.listdir(HERE):
        if name.startswith(os.path.basename(log)):
            os.remove(os.path.join(HERE, name))
    os.remove(source)


def preview(pos, classes, loose, filename="stationary_graph.png"):
    """Draw the bare layout, so it can be checked before spending minutes on a video."""
    os.makedirs(FIGURES, exist_ok=True)
    filename = os.path.join(FIGURES, filename)
    plt.figure(figsize=(8, 8))
    for group in classes:
        plt.plot(pos[group, 0], pos[group, 1], "o", markersize=4)
    if loose:
        plt.plot(pos[loose, 0], pos[loose, 1], "o", markersize=4, color="gray")
    plt.gca().set_aspect("equal")
    plt.axis("off")
    plt.title("{} class cohorts, {} students without one".format(len(classes), len(loose)))
    plt.savefig(filename, dpi=120)
    plt.close()
    print("wrote", filename)


def render(strategy, config, pos):
    """Simulate one scenario and write the video for it.

    The outbreak is simulated in full first, so that the figure can be set up knowing how
    far the curves will reach; each frame then only looks up who was infected by then.
    """
    title, coverage, filename = SCENARIOS[strategy]
    filename = os.path.join(HERE, filename)
    params = sweep.variant(**COVID, strategy=strategy, coverage=coverage)
    static = sweep.pick(strategy, coverage, config)
    infected, start, until, dosed, vaccinated = sweep.outbreak(params, config, static, details=True)

    people = sweep.people
    caught = np.full(people, np.inf)
    gone = np.full(people, np.inf)
    for person, when in infected.items():
        caught[person] = when
        gone[person] = until[person]

    # One frame per five-minute scan, from midnight of patient zero's day to the end of
    # the four weeks of data.
    times = np.arange(int(start // DAY) * DAY, 28 * DAY, WINDOW)
    n_caught = np.searchsorted(np.sort(caught), times, side="right")
    n_gone = np.searchsorted(np.sort(gone), times, side="right")
    circulating = 100.0 * (n_caught - n_gone) / people
    dropped = 100.0 * n_gone / people
    days = times / DAY + 1

    # Which contacts fall in which frame, found once by binary search over the time column:
    # frame f draws the contacts from starts[f] to ends[f].
    a_arr, b_arr, t_arr = sweep.contacts_for(COVID["rssi"])
    slot = np.asarray(t_arr) // WINDOW
    a_np = np.asarray(a_arr)
    b_np = np.asarray(b_arr)
    starts = np.searchsorted(slot, times // WINDOW, side="left")
    ends = np.searchsorted(slot, times // WINDOW, side="right")

    ra_arr, rb_arr, rt_arr, _ = sweep.contacts_with_signal(COVID["room_rssi"])
    room_slot = np.asarray(rt_arr) // WINDOW
    room_a = np.asarray(ra_arr)
    room_b = np.asarray(rb_arr)
    room_starts = np.searchsorted(room_slot, times // WINDOW, side="left")
    room_ends = np.searchsorted(room_slot, times // WINDOW, side="right")
    tracker = RoomTracker()

    fig, (net, plot) = plt.subplots(1, 2, figsize=(14, 7), gridspec_kw={"width_ratios": [2, 1]})
    net.set_aspect("equal")
    net.axis("off")
    net.set_xlim(pos[:, 0].min() - 1, pos[:, 0].max() + 1)
    net.set_ylim(pos[:, 1].min() - 1, pos[:, 1].max() + 1)

    contacts, = net.plot([], [], color="gray", linewidth=0.5)
    spreading, = net.plot([], [], color="tab:orange", linewidth=1)
    shots = sorted(dosed)
    if dosed:
        net.scatter(pos[shots, 0], pos[shots, 1], s=50, facecolors="none", edgecolors="black")
    dots = net.scatter(pos[:, 0], pos[:, 1], s=8, color="tab:blue")
    crosses = net.scatter([], [], marker="x", s=25)

    keys = [Line2D([], [], marker="o", linestyle="", color="tab:blue", label="not infected"),
            Line2D([], [], marker="o", linestyle="", color="tab:orange", label="infected"),
            Line2D([], [], marker="o", linestyle="", color="tab:red", label="dropped out"),
            Line2D([], [], marker="x", linestyle="", color="black", label="in a room"),
            Line2D([], [], color="gray", label="contact"),
            Line2D([], [], color="tab:orange", label="contact with infected")]
    if dosed:
        keys.insert(3, Line2D([], [], marker="o", linestyle="", markerfacecolor="none",
                              markeredgecolor="black", label="vaccinated"))
    net.legend(handles=keys, loc="upper right", fontsize=8)

    circ_line, = plot.plot([], [], color="tab:orange", label="infected")
    drop_line, = plot.plot([], [], color="tab:red", label="dropped out")
    plot.set_xlim(days[0], days[-1])
    plot.set_ylim(0, max(circulating.max(), dropped.max()) * 1.1 + 1)
    plot.set_xlabel("day of study")
    plot.set_ylabel("% of students")
    plot.legend(loc="upper left")
    plot.grid(True)
    # A full-width placeholder title, so that tight_layout leaves room for the real ones.
    net.set_title("day 28  00:00   " + title)
    fig.tight_layout()

    def update(frame):
        """Draw one five-minute window. Everything here is a lookup, not a simulation."""
        now = times[frame]
        settled = tracker.follow(group_rooms(room_a[room_starts[frame]:room_ends[frame]],
                                             room_b[room_starts[frame]:room_ends[frame]]))

        is_circ = (caught <= now) & (now < gone)
        is_gone = gone <= now
        colors = np.where(is_gone, "tab:red", np.where(is_circ, "tab:orange", "tab:blue"))
        dots.set_color(colors)

        marked, tints = [], []
        for room_id, members in settled:
            tint = ROOM_COLORS[room_id % len(ROOM_COLORS)]
            for person in members:
                marked.append(person)
                tints.append(tint)
        crosses.set_offsets(pos[marked] if marked else np.empty((0, 2)))
        crosses.set_color(tints if tints else "none")

        # Both sets of contact lines are drawn as one Line2D each, with None between the
        # segments to lift the pen: hundreds of separate line objects per frame would be
        # far slower.
        a = a_np[starts[frame]:ends[frame]]
        b = b_np[starts[frame]:ends[frame]]
        hot = is_circ[a] | is_circ[b]
        for line, pick in ((contacts, ~hot), (spreading, hot)):
            xs, ys = [], []
            for one, two in zip(a[pick], b[pick]):
                xs += [pos[one, 0], pos[two, 0], None]
                ys += [pos[one, 1], pos[two, 1], None]
            line.set_data(xs, ys)

        net.set_title("day {}  {:02d}:{:02d}   {}".format(
            int(now // DAY) + 1, int(now % DAY) // 3600, int(now % 3600) // 60, title))
        circ_line.set_data(days[:frame + 1], circulating[:frame + 1])
        drop_line.set_data(days[:frame + 1], dropped[:frame + 1])
        return dots, crosses, contacts, spreading, circ_line, drop_line

    print("{}: config {}, {} infected, {} frames".format(strategy, config, len(infected), len(times)))
    ani = FuncAnimation(fig, update, frames=len(times), interval=1000 / FPS)
    raw = os.path.join(HERE, "_raw_" + os.path.basename(filename))
    ani.save(raw, fps=FPS, dpi=100)
    plt.close(fig)
    compress(raw, filename, len(times) / FPS, strategy.replace(" ", "_"))
    print("saved", filename)


def main(argv):
    wanted = argv or ["contact time"]
    unknown = [name for name in wanted if name not in SCENARIOS]
    if unknown:
        raise SystemExit("unknown scenario {}; choose from {}".format(
            ", ".join(repr(name) for name in unknown),
            ", ".join(repr(name) for name in SCENARIOS)))

    rankings, partners, n_blocks = sweep.build_rankings()
    sweep.setup(rankings, partners)
    config = choose_config()
    pos, classes, loose = class_layout()
    preview(pos, classes, loose)
    for strategy in wanted:
        render(strategy, config, pos)


if __name__ == "__main__":
    main(sys.argv[1:])
