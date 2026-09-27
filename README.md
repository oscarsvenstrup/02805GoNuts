# 02805GoNuts

An interactive landing page for the 02805 Social Graphs and Interactions project.

## GitHub Pages

The site is a dependency-free static page. The workflow in `.github/workflows/pages.yml` deploys it automatically whenever changes are pushed to `main`.

## Weekly pages

The landing page in `index.html` lists all eight weeks. Week 1 lives in `weeks/week1/week1.html`; Week 2 lives in `weeks/week2/week2.html`; Week 3 lives in `weeks/week3/week3.html`; Week 4 lives in `weeks/week4/week4.html`. The weekly pages use the frozen Marvel dataset in `data/week1/`. Weeks 2-4's generated results live in `data/week2/`, `data/week3/` and `data/week4/`.

To enable it the first time:

1. Open the repository's **Settings** on GitHub.
2. Go to **Pages** and choose **GitHub Actions** as the source.
3. Push to `main` and open the URL shown under **Pages**.

## Week 2: hubs survive, clustering falls

This post addresses [2026 exercise 2.11](https://sunelehmann.com/socialgraphs2026-web/weeks/week2.html#go-nuts), not the optional explorable exercise 2.10 or every individual Week 2 exercise. It asks whether Marvel's clustering exceeds a degree-preserving null model. It includes the question, method, figure and table, interpretation, surprise, limitations and a small interactive comparison.

The main statistic is average local clustering on the **fixed original undirected giant component** (277 nodes, 1,421 edges). We compare 200 fixed-edge random graphs, 200 exact degree-preserving shuffles and 200 simplified configuration graphs, plus 30 longer-shuffle sensitivity runs. All seeds, input hashes and software versions are saved. The original TSV files match the official course downloads byte for byte, verified 13 September 2026.

### Reproduce

Use Python 3.12 and a virtual environment. From the repository root:

```sh
python -m pip install -r requirements-week2.txt
python scripts/analyze_week2.py
python scripts/verify_week2.py
```

The analysis takes a few minutes and overwrites only generated Week 2 results and the chart. It never modifies the source data. To use the notebook, install `requirements-week2-notebook.txt` in your Jupyter Python environment and run all cells of `weeks/week2/week2_analysis.ipynb`. The committed notebook contains executed outputs. The notebook and script run the same implementation, avoiding two divergent analyses. If you change the experiment, update the page's static table and interpretation as well; the verifier checks the main table against the results.

To preview the static site locally:

```sh
python -m http.server 8000
```

Open `http://localhost:8000/weeks/week2/week2.html`. No JavaScript dependencies or build step are needed. If JavaScript or the result fetch is unavailable, the full article, figure and table still work.

## Week 3: the bridges degree misses

This post addresses exercise 3.12 by asking which characters have unusually high or low betweenness after comparing them with 200 degree-preserving edge-swap networks. The analysis uses the original undirected giant component, saves every character's centrality comparison, and publishes the figure and provenance in `data/week3/`.

Run the analysis and verifier with the same pinned Week 2 environment:

```sh
python scripts/analyze_week3.py
python scripts/verify_week3.py
```

The post is available at `weeks/week3/week3.html`. Its main result is that Rockman has a betweenness z-score of 6.88 despite having only two links; Black Cat is a contrasting high-degree character whose betweenness is below the degree-preserving expectation.

## Week 4: Louvain agrees with itself more than with Infomap

This post addresses exercise 4.13's first suggested opener: run Louvain and Infomap on the same network, compare them by NMI, and show where they disagree. It reuses the frozen giant component from Weeks 2 and 3 (277 nodes, 1,421 links) rather than switching to the philosopher network, since the group already has a Marvel story going.

Louvain (10 seeds) finds 7-9 communities at Q around 0.38; the canonical run (seed 280504) finds 8 communities at Q = 0.390, about 40 standard deviations above 20 degree-preserving shuffles (mean Q = 0.248). Infomap finds 17 modules at Q = 0.371. The two methods agree at NMI = 0.62, and a majority-vote alignment shows 40.4% of characters land in a different relative group depending on which algorithm is asked. Disagreement concentrates on high-degree, cross-team characters (Hulk, Scarlet Witch, Hercules, Black Widow); tight teams like the X-Men (91% agreement) and a supernatural cluster (94%) are stable under both methods.

Run the analysis with its pinned environment:

```sh
python -m pip install -r requirements-week4.txt
python scripts/analyze_week4.py
python scripts/verify_week4.py
```

The post is available at `weeks/week4/week4.html`, with an interactive explorer that toggles between the two methods' colorings on the same fixed layout.
