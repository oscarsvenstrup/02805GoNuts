"""Check published numbers, data provenance, notebook outputs and local links."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import csv
import hashlib
import json
import math
import statistics

ROOT = Path(__file__).resolve().parents[1]
result = json.loads((ROOT / "data/week2/results.json").read_text())
rows = list(csv.DictReader((ROOT / "data/week2/samples.csv").open()))
assert len(rows) == 630
assert (result["n"], result["m"]) == (277, 1421)
official_hashes = {
    "week1_edges.tsv": "87be017a35e8f27a1f1bc0912ebb5723c0084e460cb2dbd0d2abd0e83fc644b2",
    "week1_nodes.tsv": "a10ec309ac60ea8b72bcc1a18aba801414896676dac172619def0435e585391e",
}
assert result["source_sha256"] == official_hashes
for filename, expected in official_hashes.items():
    assert hashlib.sha256((ROOT / "data/week1" / filename).read_bytes()).hexdigest() == expected
for name, model in result["models"].items():
    subset = [r for r in rows if r["model"] == name]
    vals = [float(r["clustering"]) for r in subset]
    assert len(vals) == model["runs"] == (30 if name == "long_swapped" else 200)
    assert vals == model["clustering_values"]
    assert math.isclose(statistics.mean(vals), model["mean"])
    assert math.isclose(statistics.stdev(vals), model["sd"])
    assert all(0 <= x <= 1 for x in vals)
    assert model["exceedances"] == sum(x >= result["real"]["clustering"] for x in vals)
    assert model["p_upper"] == (1 + model["exceedances"]) / (1 + len(vals))
    if "swapped" in name:
        assert all(int(r["edges"]) == 1421 and int(r["edges_lost"]) == 0 and int(r["hub_degree"]) == 106 for r in subset)

page = (ROOT / "weeks/week2/week2.html").read_text()
for name in ["random", "swapped", "configuration"]:
    assert f"{result['models'][name]['mean']:.5f}" in page
    assert f"{result['models'][name]['sd']:.5f}" in page
assert f"{result['real']['clustering']:.5f}" in page


class Links(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.ids = set()
        self.fragments = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if "id" in attr:
            assert attr["id"] not in self.ids, f"Duplicate ID: {attr['id']}"
            self.ids.add(attr["id"])
        if tag == "img":
            assert attr.get("alt"), "Missing image description"
        for key in ("href", "src"):
            if key not in attr:
                continue
            link = urlsplit(attr[key])
            if link.scheme or link.netloc:
                continue
            if link.path:
                target = (self.path.parent / unquote(link.path)).resolve()
                assert target.is_relative_to(ROOT), f"Link outside repository: {target}"
                assert target.exists(), f"Broken local link: {target}"
            elif link.fragment:
                self.fragments.append(link.fragment)


for relative in ["index.html", "weeks/week1/week1.html", "weeks/week2/week2.html"]:
    path = ROOT / relative
    parser = Links(path)
    parser.feed(path.read_text())
    assert all(fragment in parser.ids for fragment in parser.fragments)

notebook = json.loads((ROOT / "weeks/week2/week2_analysis.ipynb").read_text())
code = [c for c in notebook["cells"] if c["cell_type"] == "code"]
assert all(c["execution_count"] is not None for c in code), "Notebook has not been executed"
assert all(o["output_type"] != "error" for c in code for o in c["outputs"])
assert any("image/png" in o.get("data", {}) for c in code for o in c["outputs"])
print("PASS: 630 simulations, published table, official input hashes, executed notebook, image descriptions and local links.")
