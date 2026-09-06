# 02805GoNuts

An interactive landing page for the 02805 Social Graphs and Interactions project.

## GitHub Pages

The site is a dependency-free static page. The workflow in `.github/workflows/pages.yml` deploys it automatically whenever changes are pushed to `main`.

## Weekly pages

The landing page in `index.html` lists all eight weeks. Week 1 lives in `weeks/week1/week1.html` (with `script.js` and `styles.css` alongside it) and contains the current project content. Its data files live in `data/week1/`. To add a new weekly page, copy `weeks/week1/` to a new folder such as `weeks/week2/`, replace the post content, add matching data under `data/week2/`, and turn the matching Week 2 card and navigation item into links.

To enable it the first time:

1. Open the repository's **Settings** on GitHub.
2. Go to **Pages** and choose **GitHub Actions** as the source.
3. Push to `main` and open the URL shown under **Pages**.
