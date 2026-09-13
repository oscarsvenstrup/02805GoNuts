"""Reproduce Week 2 from the unchanged Week 1 snapshot.

Run from any directory: python scripts/analyze_week2.py
Dependencies are pinned in requirements-week2.txt. Outputs are generated artifacts.
"""
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
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/week2"
FIG = ROOT / "weeks/week2"
SEED = 280502
RUNS = 200


def load():
    with (ROOT / "data/week1/week1_nodes.tsv").open() as f:
        nodes = list(csv.DictReader((line for line in f if not line.startswith("#")), delimiter="\t"))
    graph = nx.DiGraph()
    graph.add_nodes_from(row["node_id"] for row in nodes)
    with (ROOT / "data/week1/week1_edges.tsv").open() as f:
        graph.add_edges_from(line.strip().split("\t") for line in f if line.strip() and not line.startswith("#"))
    assert (len(graph), graph.number_of_edges(), len(list(nx.isolates(graph)))) == (303, 1784, 17)
    simple = graph.to_undirected()
    assert simple.number_of_edges() == 1434
    component = max(nx.connected_components(simple), key=len)
    g = nx.convert_node_labels_to_integers(simple.subgraph(sorted(component)).copy(), label_attribute="character")
    assert len(g) == 277 and nx.number_of_selfloops(g) == 0
    return g


def measure(g):
    return {"clustering": nx.average_clustering(g), "transitivity": nx.transitivity(g),
            "triangles": sum(nx.triangles(g).values()) // 3,
            "edges": g.number_of_edges(), "max_degree": max(dict(g.degree()).values()),
            "components": nx.number_connected_components(g)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    g = load()
    n, m = len(g), g.number_of_edges()
    degree = [g.degree(i) for i in range(n)]
    real = measure(g)
    rng = random.Random(SEED)
    rows = []
    for model in ["random", "swapped", "configuration", "long_swapped"]:
        count = 30 if model == "long_swapped" else RUNS
        for run in range(count):
            seed = rng.randrange(2**32)
            if model == "random":
                h = nx.gnm_random_graph(n, m, seed=seed)
            elif "swapped" in model:
                h = g.copy()
                swaps = (50 if model == "long_swapped" else 10) * m
                nx.double_edge_swap(h, nswap=swaps, max_tries=swaps * 100, seed=seed)
                assert [h.degree(i) for i in range(n)] == degree
                assert h.number_of_edges() == m and nx.number_of_selfloops(h) == 0
            else:
                multi = nx.configuration_model(degree, seed=seed)
                assert [multi.degree(i) for i in range(n)] == degree
                h = nx.Graph(multi)
                h.remove_edges_from(nx.selfloop_edges(h))
            stats = measure(h)
            assert len(h) == n
            rows.append({"model": model, "run": run + 1, "seed": seed, **stats,
                         "edges_lost": m - h.number_of_edges(),
                         "hub_degree": h.degree(int(np.argmax(degree)))})
        print(f"Completed {model}: {count} networks", flush=True)
    summaries = {}
    for model in ["random", "swapped", "configuration", "long_swapped"]:
        subset = [r for r in rows if r["model"] == model]
        vals = [r["clustering"] for r in subset]
        exceed = sum(x >= real["clustering"] for x in vals)
        mean, sd = st.mean(vals), st.stdev(vals)
        summaries[model] = {"runs": len(vals), "mean": mean, "sd": sd,
                            "z": (real["clustering"] - mean) / sd,
                            "exceedances": exceed, "p_upper": (1 + exceed) / (1 + len(vals)),
                            "mean_edges_lost": st.mean(r["edges_lost"] for r in subset),
                            "mean_hub_degree": st.mean(r["hub_degree"] for r in subset),
                            "mean_transitivity": st.mean(r["transitivity"] for r in subset),
                            "clustering_values": vals}
    result = {"seed": SEED, "n": n, "m": m, "real": real, "models": summaries,
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "data/week1").glob("*.tsv")},
              "versions": {"python": platform.python_version(), "networkx": nx.__version__, "numpy": np.__version__, "matplotlib": matplotlib.__version__},
              "scope": "Fixed original undirected giant component, all its 277 nodes retained in every null; no connectivity constraint.",
              "test": "Prespecified one-sided average clustering test, H1: real > null. p=(1+exceedances)/(1+runs). z is descriptive, not a Gaussian-tail p-value."}
    (OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (OUT / "samples.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(11, 5.3), facecolor="#f6f1e7")
    ax.set_facecolor("#f6f1e7")
    bins = np.linspace(0, max(.36, real["clustering"] + .03), 55)
    for model, label, color in [("random", "Random links · same n, m", "#527e84"), ("configuration", "Configuration · simplified", "#9a9639"), ("swapped", "Edge swaps · same degrees", "#dd624b")]:
        ax.hist(summaries[model]["clustering_values"], bins=bins, label=label, color=color, alpha=.65)
    ax.axvline(real["clustering"], color="#20231f", linewidth=2, label=f"Real Marvel · C = {real['clustering']:.3f}")
    ax.set(xlabel="Average local clustering C", ylabel="Number of simulated networks", title="Hubs survive. Clustering falls.")
    ax.legend(frameon=False, fontsize=10, loc="upper center", bbox_to_anchor=(.55, 1))
    fig.tight_layout()
    fig.savefig(FIG / "clustering_nulls.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"n": n, "m": m, "real": real, "models": {k: {a: b for a, b in v.items() if a != "clustering_values"} for k, v in summaries.items()}}, indent=2))


if __name__ == "__main__":
    main()
