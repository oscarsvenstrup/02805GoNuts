# 02805GoNuts

An interactive landing page for the 02805 Social Graphs and Interactions project.

## GitHub Pages

The site is a dependency-free static page. The workflow in `.github/workflows/pages.yml` deploys it automatically whenever changes are pushed to `main`.

## Weekly pages

The landing page in `index.html` lists all eight weeks. Week 1 lives in `week1.html` and contains the current project content. To add a new weekly page, copy `week1.html` to a new file such as `week2.html`, replace the post content, and turn the matching Week 2 card and navigation item into links.

To enable it the first time:

1. Open the repository's **Settings** on GitHub.
2. Go to **Pages** and choose **GitHub Actions** as the source.
3. Push to `main` and open the URL shown under **Pages**.
