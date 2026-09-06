"""Verify the Week 1 Marvel network stats and plot its in-degree distribution.

Usage: python scripts/verify_week1.py
"""
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
NODES_PATH = ROOT / "data" / "week1" / "week1_nodes.tsv"
EDGES_PATH = ROOT / "data" / "week1" / "week1_edges.tsv"
PLOT_PATH = ROOT / "weeks" / "week1" / "degree_distribution.png"

EXPECTED = {
    "nodes": 303,
    "edges": 1784,
    "undirected_edges": 1434,
    "avg_degree": 9.5,
    "density": 0.031,
    "isolates": 17,
    "giant_component": 277,
    "second_component": 9,
}

# Course log-binning scheme: unit-width bins for k = 1..7, then doubling bins
# (8-15, 16-31, 32-63, 64-127, ...) extended past 128 only if the data needs it.
LOG_BIN_EDGES = [1, 2, 3, 4, 5, 6, 7, 8, 16, 32, 64, 128]


def load_graph():
    nodes = pd.read_csv(NODES_PATH, sep="\t", comment="#", quoting=csv.QUOTE_NONE)
    edges = pd.read_csv(
        EDGES_PATH, sep="\t", comment="#", quoting=csv.QUOTE_NONE, header=None, names=["source", "target"]
    )
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes["node_id"])  # full roster first, so the 17 isolates aren't lost
    graph.add_edges_from(edges[["source", "target"]].itertuples(index=False, name=None))
    return graph


def check(label, actual, expected, tol=0.0):
    ok = abs(actual - expected) <= tol if tol else actual == expected
    print(f"[{'OK' if ok else 'MISMATCH'}] {label}: {actual} (expected {expected})")
    return ok


def log_bin_degrees(degree_values, n_nodes):
    """Bin degree_values (k > 0) on the course's unit/doubling scheme.

    Each bin is normalized by its width and by the total node count, and
    plotted at the geometric mean of its edges.
    """
    degree_values = np.asarray(degree_values)
    degree_values = degree_values[degree_values > 0]
    edges = list(LOG_BIN_EDGES)
    while degree_values.size and edges[-1] < degree_values.max():
        edges.append(edges[-1] * 2)
    edges = np.array(edges, dtype=float)

    counts, _ = np.histogram(degree_values, bins=edges)
    widths = np.diff(edges)
    pk = counts / widths / n_nodes
    centers = np.sqrt(edges[:-1] * edges[1:])

    nonzero = counts > 0
    return centers[nonzero], pk[nonzero]


def plot_degree_distribution(graph, n_nodes):
    in_degrees = np.array([degree for _, degree in graph.in_degree()])
    k_values, counts = np.unique(in_degrees[in_degrees > 0], return_counts=True)
    pk_raw = counts / n_nodes
    bin_centers, pk_binned = log_bin_degrees(in_degrees, n_nodes)

    fig, (ax_linear, ax_loglog) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax_linear.bar(k_values, pk_raw, color="#8ccad1", width=0.8)
    ax_linear.set_title("In-degree distribution (linear)")
    ax_linear.set_xlabel("in-degree k")
    ax_linear.set_ylabel("P(k)")

    ax_loglog.scatter(k_values, pk_raw, s=16, color="#8ccad1", alpha=0.5, label="raw P(k)")
    ax_loglog.plot(bin_centers, pk_binned, "o-", color="#f16f54", label="log-binned")
    ax_loglog.set_xscale("log")
    ax_loglog.set_yscale("log")
    ax_loglog.set_title("In-degree distribution (log-log)")
    ax_loglog.set_xlabel("in-degree k")
    ax_loglog.set_ylabel("P(k)")
    ax_loglog.legend()

    fig.suptitle("Week 1 Marvel network: in-degree distribution")
    fig.tight_layout()
    PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PLOT_PATH, dpi=150)
    plt.close(fig)
    print(f"\nSaved plot to {PLOT_PATH.relative_to(ROOT)}")


def main():
    graph = load_graph()
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()
    undirected = graph.to_undirected()
    m = undirected.number_of_edges()
    avg_degree = 2 * m / n_nodes
    density = nx.density(undirected)
    isolates = list(nx.isolates(graph))
    components = sorted((len(c) for c in nx.connected_components(undirected)), reverse=True)

    checks = [
        check("Total nodes", n_nodes, EXPECTED["nodes"]),
        check("Directed edges", n_edges, EXPECTED["edges"]),
        check("Undirected edges (m)", m, EXPECTED["undirected_edges"]),
        check("Average degree <k>", avg_degree, EXPECTED["avg_degree"], tol=0.05),
        check("Density", density, EXPECTED["density"], tol=0.001),
        check("Isolates", len(isolates), EXPECTED["isolates"]),
        check("Giant component size", components[0], EXPECTED["giant_component"]),
        check("Second component (island) size", components[1], EXPECTED["second_component"]),
    ]

    print("\nTop 5 in-degree characters:")
    for node, degree in sorted(graph.in_degree(), key=lambda item: -item[1])[:5]:
        print(f"  {node}: {degree}")

    print("\nTop 5 out-degree characters:")
    for node, degree in sorted(graph.out_degree(), key=lambda item: -item[1])[:5]:
        print(f"  {node}: {degree}")

    plot_degree_distribution(graph, n_nodes)

    all_ok = all(checks)
    print("\nAll checks passed." if all_ok else "\nSome checks failed - see MISMATCH lines above.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
