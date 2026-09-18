"""Reproduce the Week 3 degree-preserving centrality comparison."""
from pathlib import Path
import csv
import hashlib
import json
import os
import platform
import random
import re
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
    graph.add_nodes_from((row["node_id"], {"description": row["description"], "name": row["name"], "url": row["url"]}) for row in nodes)
    with (ROOT / "data/week1/week1_edges.tsv").open(encoding="utf-8") as file:
        graph.add_edges_from(line.strip().split("\t") for line in file if line.strip() and not line.startswith("#"))
    assert (len(graph), graph.number_of_edges()) == (303, 1784)
    simple = graph.to_undirected()
    component = max(nx.connected_components(simple), key=len)
    component_graph = nx.convert_node_labels_to_integers(simple.subgraph(sorted(component)).copy(), label_attribute="character")
    return component_graph, graph


def centrality(graph):
    return {
        "degree": {node: value for node, value in graph.degree()},
        "betweenness": nx.betweenness_centrality(graph),
        "harmonic": nx.harmonic_centrality(graph),
    }


def z_score(value, values):
    deviation = st.stdev(values)
    return (value - st.mean(values)) / deviation if deviation else 0.0


def component_size(graph):
    return len(max(nx.connected_components(graph), key=len)) if graph else 0


def removal_analysis(graph, betweenness):
    impacts = []
    for node in graph:
        remaining = graph.copy()
        remaining.remove_node(node)
        impacts.append({"character": graph.nodes[node]["character"], "node": node, "degree": graph.degree(node),
                        "betweenness": betweenness[node], "giant_after": component_size(remaining),
                        "lost_from_giant": len(graph) - component_size(remaining)})
    impacts.sort(key=lambda row: (row["lost_from_giant"], row["betweenness"]), reverse=True)

    def curve(order):
        remaining = graph.copy()
        values = [component_size(remaining)]
        for node in order:
            remaining.remove_node(node)
            values.append(component_size(remaining))
        return values

    orders = {
        "betweenness": sorted(graph, key=lambda node: betweenness[node], reverse=True),
        "degree": sorted(graph, key=lambda node: graph.degree(node), reverse=True),
        "random": list(graph),
    }
    random.Random(SEED + 1).shuffle(orders["random"])
    return impacts, {name: curve(order) for name, order in orders.items()}


def directed_analysis(directed):
    nodes = list(directed.nodes)
    in_rank = {node: rank for rank, (node, _) in enumerate(sorted(directed.in_degree, key=lambda item: item[1], reverse=True), 1)}
    out_rank = {node: rank for rank, (node, _) in enumerate(sorted(directed.out_degree, key=lambda item: item[1], reverse=True), 1)}
    rows = []
    for node in nodes:
        rows.append({"character": node, "name": directed.nodes[node]["name"], "url": directed.nodes[node]["url"], "in_degree": directed.in_degree(node),
                     "out_degree": directed.out_degree(node), "in_rank": in_rank[node], "out_rank": out_rank[node],
                     "rank_gap": abs(in_rank[node] - out_rank[node])})
    rows.sort(key=lambda row: row["rank_gap"], reverse=True)
    return rows


def spider_man_paths(graph):
    spider = next(node for node in graph if graph.nodes[node]["character"] == "Spider-Man")
    distances = nx.single_source_shortest_path_length(graph, spider)
    longest_distance = max(distances.values())
    longest_nodes = [node for node, distance in distances.items() if distance == longest_distance]
    longest_node = sorted(longest_nodes, key=lambda node: graph.nodes[node]["character"])[0]
    path = nx.shortest_path(graph, longest_node, spider)
    return {"target": "Spider-Man", "longest_distance": longest_distance,
            "longest_characters": [graph.nodes[node]["character"] for node in longest_nodes],
            "example_start": graph.nodes[longest_node]["character"],
            "example_path": [graph.nodes[node]["character"] for node in path],
            "distances": {graph.nodes[node]["character"]: distance for node, distance in distances.items()}}


def faction(description):
    text = description.lower()
    for label, terms in [("X-Men", ["x-men", "x men"]), ("Avengers", ["avenger"]),
                         ("Fantastic Four", ["fantastic four"]), ("Guardians", ["guardians of the galaxy", "guardian of the galaxy"]),
                         ("Spider-Man", ["spider-man", "spider man"]), ("Other", [])]:
        if any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms):
            return label
    return "Other"


def clique_and_homophily(graph):
    cliques = sorted((sorted(graph.nodes[node]["character"] for node in clique) for clique in nx.find_cliques(graph)), key=lambda clique: (-len(clique), clique))
    labels = {node: faction(graph.nodes[node]["description"]) for node in graph}
    labeled_nodes = [node for node, label in labels.items() if label != "Other"]
    labeled_graph = graph.subgraph(labeled_nodes).copy()
    nx.set_node_attributes(labeled_graph, labels, "faction")
    real = nx.attribute_assortativity_coefficient(labeled_graph, "faction") if labeled_graph.number_of_edges() else 0.0
    rng = random.Random(SEED + 2)
    label_values = [labels[node] for node in labeled_graph]
    null_values = []
    for _ in range(RUNS):
        shuffled = label_values[:]
        rng.shuffle(shuffled)
        nx.set_node_attributes(labeled_graph, dict(zip(labeled_graph, shuffled)), "faction")
        null_values.append(nx.attribute_assortativity_coefficient(labeled_graph, "faction"))
    mean = st.mean(null_values)
    sd = st.stdev(null_values)
    return {"largest_size": len(cliques[0]), "largest_cliques": cliques[:10], "all_cliques": len(cliques),
            "labels": {graph.nodes[node]["character"]: labels[node] for node in graph}, "labeled_nodes": len(labeled_nodes),
            "real_assortativity": real, "null_mean": mean, "null_sd": sd, "z": (real - mean) / sd if sd else 0.0,
            "null_values": null_values}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    graph, directed = load()
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
    removal_rows, removal_curves = removal_analysis(graph, real["betweenness"])
    directed_rows = directed_analysis(directed)
    spider_paths = spider_man_paths(graph)
    clique_results = clique_and_homophily(graph)
    result = {
        "seed": SEED,
        "runs": RUNS,
        "n": len(graph),
        "m": graph.number_of_edges(),
        "real": {measure: {str(node): value for node, value in values.items()} for measure, values in real.items()},
        "top_surprises": top,
        "bottom_surprises": bottom,
        "neighbors": neighbors,
        "removal": {"top": removal_rows[:10], "curves": removal_curves,
                     "highest_betweenness": graph.nodes[max(graph, key=real["betweenness"].get)]["character"]},
        "direction": {"largest_rank_gaps": directed_rows[:20], "out_high_in_low": sorted(directed_rows, key=lambda row: (row["in_rank"] - row["out_rank"], -row["out_degree"]), reverse=True)[:10]},
        "spider_man_paths": spider_paths,
        "cliques_homophily": clique_results,
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
        "analysis": {"spider_man_paths": spider_paths, "removal": {"top": removal_rows[:10], "curves": removal_curves},
                      "direction": {"largest_rank_gaps": directed_rows[:20], "out_high_in_low": sorted(directed_rows, key=lambda row: (row["in_rank"] - row["out_rank"], -row["out_degree"]), reverse=True)[:10]},
                      "cliques_homophily": {key: value for key, value in clique_results.items() if key not in ["labels", "null_values"]}},
    }
    (OUT / "graph.json").write_text(json.dumps(browser_graph, separators=(",", ":")) + "\n")

    with (OUT / "direction_rankings.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=directed_rows[0].keys())
        writer.writeheader()
        writer.writerows(directed_rows)
    (OUT / "removal_curves.json").write_text(json.dumps(removal_curves) + "\n")

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
    figure, axis = plt.subplots(figsize=(11, 5.5), facecolor="#f6f1e7")
    axis.set_facecolor("#f6f1e7")
    x_values = range(len(removal_curves["degree"]))
    for name, color in [("degree", "#527e84"), ("betweenness", "#dd624b"), ("random", "#9a9639")]:
        axis.plot(x_values, removal_curves[name], label=name.title(), color=color, linewidth=2)
    axis.set(xlabel="Characters removed", ylabel="Largest connected component", title="Which removal order breaks Marvel fastest?")
    axis.legend(frameon=False)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    figure.tight_layout()
    figure.savefig(FIG / "removal_fragments.png", dpi=180)
    plt.close(figure)
    print(json.dumps({"top": [(row["character"], round(row["betweenness_z"], 2)) for row in top[:5]], "bottom": [(row["character"], round(row["betweenness_z"], 2)) for row in bottom[:5]]}, indent=2))


if __name__ == "__main__":
    main()