from pathlib import Path
import json

import igraph as ig
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


DATA_PATH = Path("data/bt_symmetric.csv")
OUTPUT_DIR = Path("results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SEED = 42

# Baseline modelling choices.
RSSI_MIN = -75
MIN_CONTACTS = 1
LOUVAIN_RESOLUTION = 1.0
BETWEENNESS_SAMPLES = 100
WINDOW_START = None
WINDOW_STOP = None

def clean_bluetooth(path):
    """Read and clean the standard Copenhagen Bluetooth table."""
    raw = pd.read_csv(path, skipinitialspace=True)

    raw.columns = [
        str(column).strip().lstrip("#").strip().lower()
        for column in raw.columns
    ]

    required = ["timestamp", "user_a", "user_b", "rssi"]
    missing = set(required) - set(raw.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}. "
            f"Found: {list(raw.columns)}"
        )

    audit = {"raw_rows": int(len(raw))}
    data = raw[required].apply(pd.to_numeric, errors="coerce")

    # Infer a fixed node roster before filtering observations.
    # Negative IDs are not treated as study participants.
    participants = set()

    for column in ["user_a", "user_b"]:
        values = data[column].dropna()
        valid = (
            np.isfinite(values)
            & (values >= 0)
            & (values % 1 == 0)
        )
        participants.update(values.loc[valid].astype(int).tolist())

    participants = sorted(participants)

    finite = np.isfinite(data.to_numpy()).all(axis=1)
    audit["invalid_numeric_rows"] = int((~finite).sum())
    data = data.loc[finite].copy()

    valid_ids = (
        (data["user_a"] >= 0)
        & (data["user_b"] >= 0)
        & (data["user_a"] % 1 == 0)
        & (data["user_b"] % 1 == 0)
    )

    audit["invalid_id_rows"] = int((~valid_ids).sum())
    data = data.loc[valid_ids].copy()

    data[["user_a", "user_b"]] = data[
        ["user_a", "user_b"]
    ].astype("int64")

    self_loops = data["user_a"].eq(data["user_b"])
    audit["self_loop_rows"] = int(self_loops.sum())
    data = data.loc[~self_loops].copy()

    # Assumption: RSSI is represented as signed dBm.
    valid_rssi = data["rssi"] < 0
    audit["invalid_rssi_rows"] = int((~valid_rssi).sum())
    data = data.loc[valid_rssi].copy()

    # Canonical ordering makes (a, b) and (b, a) the same pair.
    data["source"] = np.minimum(data["user_a"], data["user_b"])
    data["target"] = np.maximum(data["user_a"], data["user_b"])

    # Keep one pair-timestamp observation, using the stronger RSSI.
    observations = (
        data.groupby(
            ["timestamp", "source", "target"],
            as_index=False,
        )["rssi"]
        .max()
        .sort_values(["timestamp", "source", "target"])
        .reset_index(drop=True)
    )

    audit["duplicate_pair_timestamp_rows"] = int(
        len(data) - len(observations)
    )
    audit["clean_observations"] = int(len(observations))
    audit["observed_participant_ids"] = int(len(participants))

    if not participants:
        raise ValueError("No valid participant IDs were found.")

    return observations, participants, audit


def build_network(
    observations,
    participants,
    rssi_min=-75,
    min_contacts=1,
    start=None,
    stop=None,
):
    """Aggregate cleaned observations into a simple weighted graph."""
    if min_contacts < 1:
        raise ValueError("min_contacts must be at least 1.")

    selected = observations

    if start is not None:
        selected = selected.loc[selected["timestamp"] >= start]

    if stop is not None:
        selected = selected.loc[selected["timestamp"] < stop]

    if rssi_min is not None:
        selected = selected.loc[selected["rssi"] >= rssi_min]

    edges = (
        selected.groupby(["source", "target"])
        .size()
        .rename("weight")
        .reset_index()
    )

    edges = edges.loc[edges["weight"] >= min_contacts].copy()

    graph = nx.Graph()
    graph.add_nodes_from(int(node) for node in participants)

    for source, target, weight in edges.itertuples(
        index=False,
        name=None,
    ):
        graph.add_edge(
            int(source),
            int(target),
            weight=int(weight),
        )

    construction = {
        "observations_after_rssi_and_time_filter": int(len(selected)),
        "edges_after_min_contacts_filter": int(len(edges)),
        "rssi_min": rssi_min,
        "min_contacts": int(min_contacts),
        "window_start": start,
        "window_stop": stop,
    }

    return graph, construction


def load_network(
    path,
    rssi_min=-75,
    min_contacts=1,
    start=None,
    stop=None,
):
    """Load, clean, and construct the Bluetooth network."""
    observations, participants, audit = clean_bluetooth(path)

    graph, construction = build_network(
        observations,
        participants,
        rssi_min=rssi_min,
        min_contacts=min_contacts,
        start=start,
        stop=stop,
    )

    audit.update(construction)

    return graph, observations, participants, audit

G, observations, participants, audit = load_network(
    DATA_PATH,
    rssi_min=RSSI_MIN,
    min_contacts=MIN_CONTACTS,
    start=WINDOW_START,
    stop=WINDOW_STOP,
)

print(json.dumps(audit, indent=2))

with open(OUTPUT_DIR / "cleaning_report.json", "w") as file:
    json.dump(audit, file, indent=2)


def to_igraph(graph):
    """Convert a NetworkX graph while preserving node order."""
    nodes = list(graph.nodes())
    index = {node: position for position, node in enumerate(nodes)}
    edges = list(graph.edges(data=True))

    converted = ig.Graph(
        n=len(nodes),
        edges=[
            (index[source], index[target])
            for source, target, _ in edges
        ],
        directed=False,
    )

    converted.vs["name"] = [str(node) for node in nodes]
    converted.es["weight"] = [
        float(attributes.get("weight", 1))
        for _, _, attributes in edges
    ]

    return converted, nodes


def network_statistics(graph):
    """Compute unweighted structural statistics."""
    n = graph.number_of_nodes()
    m = graph.number_of_edges()

    if n == 0:
        raise ValueError("Statistics require at least one node.")

    converted, _ = to_igraph(graph)
    components = converted.connected_components()
    largest = components.giant()

    largest_diameter = int(
        largest.diameter(
            directed=False,
            unconn=False,
            weights=None,
        )
    )

    return {
        "nodes": n,
        "edges": m,
        "density": nx.density(graph),
        "average_degree": 2 * m / n,
        "average_clustering": float(
            converted.transitivity_avglocal_undirected(mode="zero")
        ),
        "global_transitivity": float(
            converted.transitivity_undirected(mode="zero")
        ),
        "components": len(components),
        "isolates": nx.number_of_isolates(graph),
        "largest_component_nodes": largest.vcount(),
        "largest_component_fraction": largest.vcount() / n,
        "diameter_largest_component": largest_diameter,
        "diameter_full_graph": (
            largest_diameter if len(components) == 1 else np.nan
        ),
    }


stats = network_statistics(G)

print(pd.Series(stats).to_string())

pd.DataFrame([stats]).to_csv(
    OUTPUT_DIR / "network_statistics.csv",
    index=False,
)


#Clustering measures

# - Average clustering: average local clustering across all nodes, including zeros for nodes with fewer than two neighbours.

# - Global transitivity: proportion of connected triples that form triangles.

# These are related but not interchangeable. Reporting both is useful. 

def detect_communities(graph, resolution=1.0, seed=42):
    if graph.number_of_edges() == 0:
        communities = [{node} for node in graph.nodes()]
        modularity = np.nan
    else:
        communities = nx.community.louvain_communities(
            graph,
            weight="weight",
            resolution=resolution,
            seed=seed,
        )

        modularity = nx.community.modularity(
            graph,
            communities,
            weight="weight",
            resolution=resolution,
        )

    # Number larger communities first for readable exports.
    communities = sorted(
        communities,
        key=lambda community: (-len(community), min(community)),
    )

    membership = {
        node: community_id
        for community_id, community in enumerate(communities)
        for node in community
    }

    return communities, membership, modularity


communities, membership, modularity = detect_communities(
    G,
    resolution=LOUVAIN_RESOLUTION,
    seed=SEED,
)

print("Number of communities:", len(communities))
print("Weighted modularity:", modularity)

community_sizes = pd.DataFrame(
    {
        "community": range(len(communities)),
        "nodes": [len(community) for community in communities],
    }
)

community_sizes.to_csv(
    OUTPUT_DIR / "community_sizes.csv",
    index=False,
)

pd.DataFrame(
    [
        {
            "communities": len(communities),
            "weighted_modularity": modularity,
            "resolution": LOUVAIN_RESOLUTION,
            "seed": SEED,
        }
    ]
).to_csv(
    OUTPUT_DIR / "community_summary.csv",
    index=False,
)

def calculate_centralities(graph, membership, seed=42):
    nodes = list(graph.nodes())
    n = len(nodes)
    sampled_sources = min(BETWEENNESS_SAMPLES, n)

    degree = dict(graph.degree())
    strength = dict(graph.degree(weight="weight"))
    degree_centrality = nx.degree_centrality(graph)

    closeness = nx.closeness_centrality(
        graph,
        distance=None,
        wf_improved=True,
    )

    betweenness = nx.betweenness_centrality(
        graph,
        k=sampled_sources,
        normalized=True,
        weight=None,
        seed=seed,
    )

    # igraph avoids the SciPy dependency used by NetworkX PageRank.
    converted, igraph_nodes = to_igraph(graph)

    pagerank_values = converted.pagerank(
        directed=False,
        damping=0.85,
        weights="weight",
    )

    pagerank = dict(zip(igraph_nodes, pagerank_values))

    rows = []

    for node in nodes:
        rows.append(
            {
                "node": node,
                "community": membership[node],
                "degree": degree[node],
                "strength": strength[node],
                "degree_centrality": degree_centrality[node],
                "closeness": closeness[node],
                "betweenness": betweenness[node],
                "weighted_pagerank": pagerank[node],
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["betweenness", "degree"],
            ascending=False,
        )
        .reset_index(drop=True)
    )


centralities = calculate_centralities(
    G,
    membership,
    seed=SEED,
)

centralities.to_csv(
    OUTPUT_DIR / "node_centralities.csv",
    index=False,
)

print(centralities.head(10).to_string(index=False))

for record in centralities.to_dict("records"):
    node = int(record.pop("node"))

    for key, value in record.items():
        if key in {"community", "degree", "strength"}:
            G.nodes[node][key] = int(value)
        else:
            G.nodes[node][key] = float(value)

    G.nodes[node]["label"] = str(node)

nx.write_gexf(
    G,
    OUTPUT_DIR / "bluetooth_network.gexf",
)

nx.write_graphml(
    G,
    OUTPUT_DIR / "bluetooth_network.graphml",
)

edge_table = pd.DataFrame(
    [
        {
            "source": source,
            "target": target,
            "weight": attributes["weight"],
        }
        for source, target, attributes in G.edges(data=True)
    ],
    columns=["source", "target", "weight"],
)

edge_table.to_csv(
    OUTPUT_DIR / "network_edges.csv",
    index=False,
)

def plot_degree_ccdf(graphs, output_path):
    fig, ax = plt.subplots(figsize=(7, 5))

    for label, graph in graphs.items():
        degrees = np.array(
            [degree for _, degree in graph.degree()],
            dtype=int,
        )

        positive = degrees[degrees > 0]

        if len(positive) == 0:
            continue

        values, counts = np.unique(
            positive,
            return_counts=True,
        )

        ccdf = np.cumsum(counts[::-1])[::-1] / len(degrees)

        ax.loglog(
            values,
            ccdf,
            marker=".",
            linestyle="-",
            label=label,
        )

    ax.set_xlabel("Degree k")
    ax.set_ylabel("Fraction of nodes with degree >= k")
    ax.set_title("Degree CCDF")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


plot_degree_ccdf(
    {"Bluetooth": G},
    OUTPUT_DIR / "degree_ccdf.png",
)

def plot_network_preview(graph, output_path, max_edges=3000):
    strongest_edges = sorted(
        graph.edges(data=True),
        key=lambda edge: edge[2].get("weight", 1),
        reverse=True,
    )[:max_edges]

    view = nx.Graph()
    view.add_nodes_from(graph.nodes(data=True))
    view.add_edges_from(strongest_edges)

    converted, nodes = to_igraph(view)

    rng = np.random.default_rng(SEED)
    initial_positions = rng.uniform(
        -1,
        1,
        size=(len(nodes), 2),
    )

    layout = converted.layout_fruchterman_reingold(
        niter=500,
        seed=initial_positions.tolist(),
    )

    positions = {
        node: tuple(layout[index])
        for index, node in enumerate(nodes)
    }

    colours = [
        graph.nodes[node]["community"]
        for node in nodes
    ]

    sizes = [
        10 + 4 * np.sqrt(graph.degree(node))
        for node in nodes
    ]

    fig, ax = plt.subplots(figsize=(10, 8))

    nx.draw_networkx_edges(
        view,
        positions,
        ax=ax,
        alpha=0.08,
        width=0.5,
    )

    nx.draw_networkx_nodes(
        view,
        positions,
        nodelist=nodes,
        node_color=colours,
        node_size=sizes,
        cmap=plt.get_cmap("tab20"),
        linewidths=0,
        ax=ax,
    )

    ax.set_title(
        f"Bluetooth network: {view.number_of_edges()} "
        "strongest edges displayed"
    )
    ax.axis("off")

    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)


plot_network_preview(
    G,
    OUTPUT_DIR / "network_preview.png",
)

def run_null_models(graph, runs=10, seed=42):
    n = graph.number_of_nodes()
    m = graph.number_of_edges()

    if n < 2:
        raise ValueError("Null models require at least two nodes.")

    # For NetworkX's default BA initialization, the number of edges
    # is attachment * (n - attachment).
    candidates = range(1, n // 2 + 1)

    attachment = min(
        candidates,
        key=lambda value: abs(value * (n - value) - m),
    )

    ba_edges = attachment * (n - attachment)

    print("Observed edges:", m)
    print("BA attachment parameter:", attachment)
    print("BA edges:", ba_edges)

    if abs(ba_edges - m) / max(m, 1) > 0.05:
        print(
            "Warning: BA differs in edge count by more than 5%. "
            "Interpret density-sensitive comparisons cautiously."
        )

    rows = []
    examples = {}

    for run in range(runs):
        run_seed = seed + run

        models = {
            "ER": nx.gnm_random_graph(
                n,
                m,
                seed=run_seed,
            ),
            "BA": nx.barabasi_albert_graph(
                n,
                attachment,
                seed=run_seed,
            ),
        }

        for model_name, null_graph in models.items():
            row = network_statistics(null_graph)
            row["model"] = model_name
            row["run"] = run
            rows.append(row)

            if run == 0:
                examples[model_name] = null_graph

                nx.write_graphml(
                    null_graph,
                    OUTPUT_DIR / f"null_{model_name.lower()}.graphml",
                )

    return pd.DataFrame(rows), examples


null_results, null_examples = run_null_models(
    G,
    runs=10,
    seed=SEED,
)

null_results.to_csv(
    OUTPUT_DIR / "null_model_statistics.csv",
    index=False,
)

comparison_metrics = [
    "edges",
    "average_degree",
    "average_clustering",
    "global_transitivity",
    "components",
    "diameter_largest_component",
]

null_summary = (
    null_results.groupby("model")[comparison_metrics]
    .agg(["mean", "std"])
)

null_summary.to_csv(
    OUTPUT_DIR / "null_model_summary.csv",
)

print(null_summary.to_string())

plot_degree_ccdf(
    {"Bluetooth": G, **null_examples},
    OUTPUT_DIR / "degree_ccdf_with_null_models.png",
)

sensitivity_rows = []

for rssi_min in [None, -80, -75, -70]:
    for min_contacts in [1, 3, 6]:
        candidate, construction = build_network(
            observations,
            participants,
            rssi_min=rssi_min,
            min_contacts=min_contacts,
            start=WINDOW_START,
            stop=WINDOW_STOP,
        )

        candidate_communities, _, candidate_modularity = (
            detect_communities(
                candidate,
                resolution=LOUVAIN_RESOLUTION,
                seed=SEED,
            )
        )

        row = network_statistics(candidate)
        row.update(construction)
        row["communities"] = len(candidate_communities)
        row["weighted_modularity"] = candidate_modularity

        sensitivity_rows.append(row)

pd.DataFrame(sensitivity_rows).to_csv(
    OUTPUT_DIR / "threshold_sensitivity.csv",
    index=False,
)


#References
    #he supplied Figshare dataset and its metadata.

    # - Sapiezynski et al. (2019), The Copenhagen Networks Study interaction data, Scientific Data.

    # - Blondel et al. (2008), Fast unfolding of communities in large networks.

    # - Erdős and Rényi (1959), On random graphs I.

    # - Barabási and Albert (1999), Emergence of scaling in random networks.

    # - Brandes (2001), A faster algorithm for betweenness centrality.

    # - NetworkX and igraph documentation for the implementations used.