"""Reproduce the Week 4 community-detection comparison: Louvain vs Infomap on Marvel."""
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
from networkx.algorithms.community import louvain_communities, modularity
import sklearn
from sklearn.metrics import normalized_mutual_info_score
import infomap as infomap_module
from infomap import Infomap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/week4"
FIG = ROOT / "weeks/week4"
SEED = 280504
STABILITY_SEEDS = list(range(10))
NULL_RUNS = 20


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
    return component_graph


def faction(description):
    text = description.lower()
    for label, terms in [("X-Men", ["x-men", "x men"]), ("Avengers", ["avenger"]),
                         ("Fantastic Four", ["fantastic four"]), ("Guardians", ["guardians of the galaxy", "guardian of the galaxy"]),
                         ("Spider-Man", ["spider-man", "spider man"]), ("Other", [])]:
        if any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms):
            return label
    return "Other"


def labels_from_communities(graph, communities):
    labels = [None] * len(graph)
    for community_id, members in enumerate(communities):
        for node in members:
            labels[node] = community_id
    return labels


def sort_communities_by_size(communities):
    return sorted((sorted(community) for community in communities), key=len, reverse=True)


def run_infomap(graph):
    infomap = Infomap("--two-level -s 280504 --silent")
    for source, target in graph.edges():
        infomap.add_link(source, target)
    infomap.run()
    modules = {node.node_id: node.module_id for node in infomap.tree if node.is_leaf}
    community_ids = sorted(set(modules.values()))
    remap = {old: new for new, old in enumerate(sorted(community_ids, key=lambda cid: -sum(1 for v in modules.values() if v == cid)))}
    labels = [remap[modules[node]] for node in graph]
    communities = [set() for _ in remap]
    for node, label in enumerate(labels):
        communities[label].add(node)
    return labels, communities, infomap.codelength


def align_by_majority(louvain_communities_sorted, infomap_labels):
    """For each Louvain community, find its majority Infomap module; flag members that disagree."""
    agreement = {}
    matches = []
    for community in louvain_communities_sorted:
        votes = {}
        for node in community:
            votes[infomap_labels[node]] = votes.get(infomap_labels[node], 0) + 1
        majority_module = max(votes, key=votes.get)
        matches.append({"louvain_size": len(community), "majority_infomap_module": majority_module,
                         "majority_count": votes[majority_module], "purity": votes[majority_module] / len(community)})
        for node in community:
            agreement[node] = infomap_labels[node] == majority_module
    return agreement, matches


def null_model_modularity(graph, real_q):
    rng = random.Random(SEED + 1)
    degree = [graph.degree(node) for node in graph]
    q_values = []
    for _ in range(NULL_RUNS):
        shuffled = graph.copy()
        swaps = 10 * shuffled.number_of_edges()
        nx.double_edge_swap(shuffled, nswap=swaps, max_tries=swaps * 100, seed=rng.randrange(2**32))
        assert [shuffled.degree(node) for node in graph] == degree
        communities = louvain_communities(shuffled, seed=SEED)
        q_values.append(modularity(shuffled, communities))
    mean = st.mean(q_values)
    sd = st.stdev(q_values)
    return {"runs": NULL_RUNS, "q_values": q_values, "mean": mean, "sd": sd,
            "z": (real_q - mean) / sd if sd else 0.0}


def stability_analysis(graph):
    runs = []
    partitions = []
    for seed in STABILITY_SEEDS:
        communities = louvain_communities(graph, seed=seed)
        labels = labels_from_communities(graph, communities)
        q = modularity(graph, communities)
        runs.append({"seed": seed, "n_communities": len(communities), "modularity": q})
        partitions.append(labels)
    nmi_matrix = [[normalized_mutual_info_score(partitions[i], partitions[j]) for j in range(len(partitions))] for i in range(len(partitions))]
    off_diagonal = [nmi_matrix[i][j] for i in range(len(partitions)) for j in range(len(partitions)) if i != j]
    return runs, nmi_matrix, {"min": min(off_diagonal), "max": max(off_diagonal), "mean": st.mean(off_diagonal)}


def community_naming(graph, communities_sorted, labels_dict):
    named = []
    for community in communities_sorted:
        ranked = sorted(community, key=lambda node: graph.degree(node), reverse=True)
        top = [{"character": graph.nodes[node]["character"], "degree": graph.degree(node)} for node in ranked[:5]]
        votes = {}
        for node in community:
            label = labels_dict[node]
            votes[label] = votes.get(label, 0) + 1
        dominant_faction, dominant_count = max(votes.items(), key=lambda item: item[1])
        named.append({"size": len(community), "top_members": top, "dominant_faction": dominant_faction,
                       "dominant_faction_share": dominant_count / len(community)})
    return named


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    graph = load()

    canonical_communities = sort_communities_by_size(louvain_communities(graph, seed=SEED))
    canonical_labels = labels_from_communities(graph, canonical_communities)
    canonical_q = modularity(graph, canonical_communities)

    stability_runs, nmi_matrix, nmi_summary = stability_analysis(graph)
    null_result = null_model_modularity(graph, canonical_q)

    infomap_labels, infomap_communities, codelength = run_infomap(graph)
    infomap_q = modularity(graph, infomap_communities)
    infomap_vs_louvain_nmi = normalized_mutual_info_score(canonical_labels, infomap_labels)

    agreement, matches = align_by_majority(canonical_communities, infomap_labels)
    agreement_rate = sum(agreement.values()) / len(agreement)
    disagreeing_nodes = sorted((node for node, agree in agreement.items() if not agree),
                                key=lambda node: graph.degree(node), reverse=True)

    faction_labels = {node: faction(graph.nodes[node]["description"]) for node in graph}
    labeled_nodes = [node for node, label in faction_labels.items() if label != "Other"]
    faction_nmi = None
    if labeled_nodes:
        faction_nmi = normalized_mutual_info_score([canonical_labels[node] for node in labeled_nodes],
                                                      [faction_labels[node] for node in labeled_nodes])

    named_communities = community_naming(graph, canonical_communities, faction_labels)

    layout = nx.spring_layout(graph, seed=SEED, k=1.6 / (len(graph) ** 0.5), iterations=200)

    rows = []
    for node in graph:
        rows.append({
            "node": node, "character": graph.nodes[node]["character"], "degree": graph.degree(node),
            "louvain_community": canonical_labels[node], "infomap_community": infomap_labels[node],
            "agreement": agreement[node], "x": layout[node][0], "y": layout[node][1],
        })
    rows.sort(key=lambda row: row["degree"], reverse=True)

    result = {
        "seed": SEED,
        "n": len(graph),
        "m": graph.number_of_edges(),
        "louvain_canonical": {"n_communities": len(canonical_communities), "modularity": canonical_q,
                                "sizes": [len(c) for c in canonical_communities]},
        "stability": {"runs": stability_runs, "nmi_matrix": nmi_matrix, "nmi_summary": nmi_summary},
        "null_model": null_result,
        "infomap": {"n_communities": len(infomap_communities), "modularity": infomap_q, "codelength": codelength,
                     "sizes": [len(c) for c in infomap_communities]},
        "agreement": {"rate": agreement_rate, "matches": matches,
                       "top_disagreeing_characters": [graph.nodes[node]["character"] for node in disagreeing_nodes[:15]]},
        "nmi_louvain_vs_infomap": infomap_vs_louvain_nmi,
        "faction_nmi": faction_nmi,
        "labeled_nodes": len(labeled_nodes),
        "named_communities": named_communities,
        "source_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "data/week1").glob("*.tsv")},
        "versions": {"python": platform.python_version(), "networkx": nx.__version__, "matplotlib": matplotlib.__version__,
                      "scikit-learn": sklearn.__version__, "infomap": infomap_module.__version__},
        "scope": "Original undirected giant component (277 nodes, 1421 links); Louvain (networkx) and Infomap community detection compared by NMI and by a degree-preserving null on modularity.",
    }
    (OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n")

    with (OUT / "communities.csv").open("w", newline="") as file:
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
                "louvain": row_by_node[node]["louvain_community"],
                "infomap": row_by_node[node]["infomap_community"],
                "agree": row_by_node[node]["agreement"],
                "x": row_by_node[node]["x"],
                "y": row_by_node[node]["y"],
            }
            for node in graph
        ],
        "edges": [{"source": source, "target": target} for source, target in graph.edges()],
        "named_communities": named_communities,
        "agreement_rate": agreement_rate,
        "nmi_louvain_vs_infomap": infomap_vs_louvain_nmi,
    }
    (OUT / "graph.json").write_text(json.dumps(browser_graph, separators=(",", ":")) + "\n")

    # Figure 1: community landscape, force layout coloured by canonical Louvain community.
    palette = ["#dd624b", "#8ccad1", "#c8e85b", "#9a9639", "#527e84", "#20231f", "#f16f54", "#3f6b6f", "#b7a6d6", "#e0a458"]
    figure, axis = plt.subplots(figsize=(11, 9), facecolor="#f6f1e7")
    axis.set_facecolor("#f6f1e7")
    xs = [layout[node][0] for node in graph]
    ys = [layout[node][1] for node in graph]
    for source, target in graph.edges():
        axis.plot([layout[source][0], layout[target][0]], [layout[source][1], layout[target][1]], color="#20231f", alpha=.06, linewidth=.6, zorder=1)
    sizes = [40 + 9 * graph.degree(node) for node in graph]
    colors = [palette[canonical_labels[node] % len(palette)] for node in graph]
    axis.scatter(xs, ys, s=sizes, c=colors, alpha=.88, linewidths=.4, edgecolors="#20231f", zorder=2)
    label_offsets = [(8, 8), (8, -14), (-105, 8), (8, 22), (8, -28), (-115, -14), (8, 36), (-125, 22)]
    for community, offset in zip(canonical_communities[:8], label_offsets):
        hub = max(community, key=lambda node: graph.degree(node))
        axis.annotate(graph.nodes[hub]["character"].replace("_", " ").split(" (")[0], layout[hub], xytext=offset, textcoords="offset points", fontsize=9, fontweight="bold")
    axis.set_title(f"{len(canonical_communities)} Louvain communities, Q = {canonical_q:.3f}", fontsize=15)
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.tight_layout()
    figure.savefig(FIG / "community_landscape.png", dpi=180)
    plt.close(figure)

    # Figure 2: null-model histogram, same visual language as Week 2's shuffle test.
    figure, axis = plt.subplots(figsize=(11, 5.5), facecolor="#f6f1e7")
    axis.set_facecolor("#f6f1e7")
    axis.hist(null_result["q_values"], bins=12, color="#527e84", alpha=.85)
    axis.axvline(canonical_q, color="#dd624b", linewidth=2.5)
    axis.annotate(f"Real Marvel Q = {canonical_q:.3f}", (canonical_q, axis.get_ylim()[1] * .92), xytext=(10, 0), textcoords="offset points", fontsize=11, color="#dd624b")
    axis.set(xlabel="Louvain modularity Q", ylabel="Shuffled networks", title="Modularity of a random network is not zero, but Marvel's is far higher")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    figure.tight_layout()
    figure.savefig(FIG / "null_model_shuffle.png", dpi=180)
    plt.close(figure)

    # Figure 3: Louvain vs Infomap disagreement map.
    figure, axis = plt.subplots(figsize=(11, 9), facecolor="#f6f1e7")
    axis.set_facecolor("#f6f1e7")
    for source, target in graph.edges():
        axis.plot([layout[source][0], layout[target][0]], [layout[source][1], layout[target][1]], color="#20231f", alpha=.06, linewidth=.6, zorder=1)
    agree_xs = [layout[node][0] for node in graph if agreement[node]]
    agree_ys = [layout[node][1] for node in graph if agreement[node]]
    disagree_xs = [layout[node][0] for node in graph if not agreement[node]]
    disagree_ys = [layout[node][1] for node in graph if not agreement[node]]
    axis.scatter(agree_xs, agree_ys, s=32, c="#8ccad1", alpha=.75, zorder=2, label="Same side in both methods")
    axis.scatter(disagree_xs, disagree_ys, s=[40 + 9 * graph.degree(node) for node in graph if not agreement[node]], c="#dd624b", alpha=.92, edgecolors="#20231f", linewidths=.6, zorder=3, label="Louvain and Infomap disagree")
    label_offsets = [(8, 8), (8, -14), (-95, 8), (8, 22), (8, -28), (-105, -14), (8, 36), (-115, 22)]
    for node, offset in zip(disagreeing_nodes[:8], label_offsets):
        axis.annotate(graph.nodes[node]["character"].replace("_", " ").split(" (")[0], layout[node], xytext=offset, textcoords="offset points", fontsize=9, fontweight="bold")
    axis.set_title(f"Where Louvain and Infomap disagree (NMI = {infomap_vs_louvain_nmi:.2f})", fontsize=15, pad=45)
    axis.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.97), fontsize=10)
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)
    figure.tight_layout()
    figure.savefig(FIG / "louvain_vs_infomap.png", dpi=180)
    plt.close(figure)

    print(json.dumps({
        "n_communities": len(canonical_communities), "Q": round(canonical_q, 4),
        "null_mean": round(null_result["mean"], 4), "null_z": round(null_result["z"], 2),
        "nmi_stability_range": [round(nmi_summary["min"], 3), round(nmi_summary["max"], 3)],
        "infomap_n_communities": len(infomap_communities), "infomap_Q": round(infomap_q, 4),
        "nmi_louvain_vs_infomap": round(infomap_vs_louvain_nmi, 3),
        "agreement_rate": round(agreement_rate, 3),
        "faction_nmi": round(faction_nmi, 3) if faction_nmi is not None else None,
    }, indent=2))


if __name__ == "__main__":
    main()
