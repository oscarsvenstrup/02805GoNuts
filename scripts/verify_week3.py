"""Check Week 3 results, provenance and local page links."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads((ROOT / "data/week3/results.json").read_text(encoding="utf-8"))
rows = list(csv.DictReader((ROOT / "data/week3/centralities.csv").open(encoding="utf-8")))
browser_graph = json.loads((ROOT / "data/week3/graph.json").read_text(encoding="utf-8"))
direction_rows = list(csv.DictReader((ROOT / "data/week3/direction_rankings.csv").open(encoding="utf-8")))
removal_curves = json.loads((ROOT / "data/week3/removal_curves.json").read_text(encoding="utf-8"))
assert len(rows) == 277
assert (result["n"], result["m"], result["runs"]) == (277, 1421, 200)
assert len(browser_graph["nodes"]) == 277
assert len(browser_graph["edges"]) == 1421
assert {node["character"] for node in browser_graph["nodes"]} == {row["character"] for row in rows}
assert len(direction_rows) == 303
assert len(removal_curves["degree"]) == len(removal_curves["betweenness"]) == len(removal_curves["random"]) == 278
assert result["removal"]["top"][0]["character"] == "Spider-Man"
assert result["removal"]["highest_betweenness"] == "Spider-Man"
assert result["spider_man_paths"]["longest_distance"] == 3
assert result["cliques_homophily"]["largest_size"] == 8
assert result["cliques_homophily"]["real_assortativity"] > result["cliques_homophily"]["null_mean"]
assert result["top_surprises"][0]["character"] == "Rockman_(character)"
assert result["top_surprises"][0]["betweenness_z"] > 6
assert result["bottom_surprises"][0]["character"] == "Black_Cat_(Marvel_Comics)"
assert result["bottom_surprises"][0]["betweenness_z"] < -2
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


for relative in ["index.html", "weeks/week3/week3.html"]:
    path = ROOT / relative
    parser = Links(path)
    parser.feed(path.read_text(encoding="utf-8"))
    assert all(fragment in parser.ids for fragment in parser.fragments)

page = (ROOT / "weeks/week3/week3.html").read_text(encoding="utf-8")
for required in ["removal_fragments.png", "Shamrock", "Spider-Man", "cliques", "homophily", "spider-input"]:
    assert required in page, required

print("PASS: all five Week 3 question families, result files, figures, source hashes and local links.")