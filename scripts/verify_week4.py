"""Check Week 4 results, provenance and local page links."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads((ROOT / "data/week4/results.json").read_text(encoding="utf-8"))
rows = list(csv.DictReader((ROOT / "data/week4/communities.csv").open(encoding="utf-8")))
browser_graph = json.loads((ROOT / "data/week4/graph.json").read_text(encoding="utf-8"))

assert len(rows) == 277
assert (result["n"], result["m"]) == (277, 1421)
assert len(browser_graph["nodes"]) == 277
assert len(browser_graph["edges"]) == 1421
assert {node["character"] for node in browser_graph["nodes"]} == {row["character"] for row in rows}

assert result["louvain_canonical"]["n_communities"] == 8
assert 0.38 < result["louvain_canonical"]["modularity"] < 0.40
assert sum(result["louvain_canonical"]["sizes"]) == 277

assert result["null_model"]["runs"] == 20
assert result["null_model"]["z"] > 30, "Real modularity should be far above the degree-preserving null"
assert result["null_model"]["mean"] < result["louvain_canonical"]["modularity"]

assert len(result["stability"]["runs"]) == 10
assert all(run["n_communities"] in (7, 8, 9) for run in result["stability"]["runs"])
assert 0 < result["stability"]["nmi_summary"]["min"] < result["stability"]["nmi_summary"]["max"] < 1

assert result["infomap"]["n_communities"] > result["louvain_canonical"]["n_communities"]
assert sum(result["infomap"]["sizes"]) == 277
assert 0 < result["nmi_louvain_vs_infomap"] < 1
assert 0 < result["agreement"]["rate"] < 1
assert "Hulk" in " ".join(result["agreement"]["top_disagreeing_characters"])

for filename, expected in result["source_sha256"].items():
    assert hashlib.sha256((ROOT / "data/week1" / filename).read_bytes()).hexdigest() == expected


class Links(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.ids = set()
        self.fragments = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            assert attributes["id"] not in self.ids
            self.ids.add(attributes["id"])
        if tag == "img":
            assert attributes.get("alt")
        for key in ("href", "src"):
            if key not in attributes:
                continue
            link = urlsplit(attributes[key])
            if link.scheme or link.netloc:
                continue
            if link.path:
                target = (self.path.parent / unquote(link.path)).resolve()
                assert target.is_relative_to(ROOT), target
                assert target.exists(), target
            elif link.fragment:
                self.fragments.append(link.fragment)


for relative in ["index.html", "weeks/week4/week4.html"]:
    path = ROOT / relative
    parser = Links(path)
    parser.feed(path.read_text(encoding="utf-8"))
    assert all(fragment in parser.ids for fragment in parser.fragments)

page = (ROOT / "weeks/week4/week4.html").read_text(encoding="utf-8")
for required in ["Louvain", "Infomap", "community_landscape.png", "null_model_shuffle.png", "louvain_vs_infomap.png", "community-graph"]:
    assert required in page, required

print("PASS: Week 4 Louvain/Infomap comparison, null model, stability, result files, figures and local links.")
