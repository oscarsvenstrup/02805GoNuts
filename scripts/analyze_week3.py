"""Reproduce the Week 3 degree-preserving centrality comparison."""
from pathlib import Path
import csv
import hashlib
import json
import os
import platform
import random
import statistics as st
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "socialgraphs-matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/week3"
FIG = ROOT / "weeks/week3"
SEED = 280503
RUNS = 200


def load():
    with (ROOT / "data/week1/week1_nodes.tsv").open(encoding="utf-8") as file:
        nodes = list(csv.DictReader((line for line in file if not line.startswith("#")), delimiter="\t"))
    graph = nx.DiGraph()
    graph.add_nodes_from(row["node_id"] for row in nodes)
    with (ROOT / "data/week1/week1_edges.tsv").open(encoding="utf-8") as file:
        graph.add_edges_from(line.strip().split("\t") for line in file if line.strip() and not line.startswith("#"))
    assert (len(graph), graph.number_of_edges()) == (303, 1784)
    simple = graph.to_undirected()
    component = max(nx.connected_components(simple), key=len)
    return nx.convert_node_labels_to_integers(simple.subgraph(sorted(component)).copy(), label_attribute="character")


def centrality(graph):
    return {
        "degree": {node: value for node, value in graph.degree()},
        "betweenness": nx.betweenness_centrality(graph),
        "harmonic": nx.harmonic_centrality(graph),
    }


def z_score(value, values):
    deviation = st.stdev(values)
    return (value - st.mean(values)) / deviation if deviation else 0.0


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    graph = load()
    real = centrality(graph)
    degree = [graph.degree(node) for node in graph]
    rng = random.Random(SEED)
    samples = {measure: {node: [] for node in graph} for measure in ["betweenness", "harmonic"]}
    for run in range(RUNS):
        shuffled = graph.copy()
        swaps = 10 * shuffled.number_of_edges()
        nx.double_edge_swap(shuffled, nswap=swaps, max_tries=swaps * 100, seed=rng.randrange(2**32))
        assert [shuffled.degree(node) for node in graph] == degree
        measured = centrality(shuffled)
        for measure in samples:
            for node in graph:
                samples[measure][node].append(measured[measure][node])

    rows = []
    for node in graph:
        row = {"node": node, "character": graph.nodes[node]["character"], "degree": degree[node]}
        for measure in samples:
            values = samples[measure][node]
            row[f"{measure}_real"] = real[measure][node]
            row[f"{measure}_null_mean"] = st.mean(values)
            row[f"{measure}_null_sd"] = st.stdev(values)
            row[f"{measure}_z"] = z_score(real[measure][node], values)
        rows.append(row)
    rows.sort(key=lambda row: row["betweenness_z"], reverse=True)
    for rank, row in enumerate(rows, 1):
        row["betweenness_surprise_rank"] = rank

    top = rows[:10]
    bottom = sorted(rows, key=lambda row: row["betweenness_z"])[:10]
    neighbors = {}
    for row in top[:5]:
        node = row["node"]
        neighbors[row["character"]] = sorted(graph.nodes[neighbor]["character"] for neighbor in graph.neighbors(node))
    result = {
        "seed": SEED,
        "runs": RUNS,
        "n": len(graph),
        "m": graph.number_of_edges(),
        "real": {measure: {str(node): value for node, value in values.items()} for measure, values in real.items()},
        "top_surprises": top,
        "bottom_surprises": bottom,
        "neighbors": neighbors,
        "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "data/week1").glob("*.tsv")},
        "versions": {"python": platform.python_version(), "networkx": nx.__version__, "matplotlib": matplotlib.__version__},
        "scope": "Original undirected giant component; degree-preserving double-edge swaps; betweenness is the primary selected measure.",
    }
    (OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (OUT / "centralities.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    row_by_node = {row["node"]: row for row in rows}
    browser_graph = {
        "nodes": [
            {
                "id": node,
                "character": graph.nodes[node]["character"],
                "degree": row_by_node[node]["degree"],
                "betweenness": row_by_node[node]["betweenness_real"],
                "null_mean": row_by_node[node]["betweenness_null_mean"],
                "z": row_by_node[node]["betweenness_z"],
            }
            for node in graph
        ],
        "edges": [{"source": source, "target": target} for source, target in graph.edges()],
    }
    (OUT / "graph.json").write_text(json.dumps(browser_graph, separators=(",", ":")) + "\n")

    figure_rows = sorted(rows, key=lambda row: row["degree"])
    figure, axis = plt.subplots(figsize=(11, 6), facecolor="#f6f1e7")
    axis.set_facecolor("#f6f1e7")
    axis.scatter([row["degree"] for row in figure_rows], [row["betweenness_real"] for row in figure_rows], color="#527e84", alpha=.62, s=25)
    for row in top[:5]:
        axis.scatter(row["degree"], row["betweenness_real"], color="#dd624b", s=50, zorder=3)
        axis.annotate(row["character"], (row["degree"], row["betweenness_real"]), xytext=(5, 5), textcoords="offset points", fontsize=8)
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set(xlabel="Degree k", ylabel="Betweenness centrality", title="The bridges degree alone does not predict")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    figure.tight_layout()
    figure.savefig(FIG / "betweenness_surprises.png", dpi=180)
    plt.close(figure)
    print(json.dumps({"top": [(row["character"], round(row["betweenness_z"], 2)) for row in top[:5]], "bottom": [(row["character"], round(row["betweenness_z"], 2)) for row in bottom[:5]]}, indent=2))


if __name__ == "__main__":
    main()