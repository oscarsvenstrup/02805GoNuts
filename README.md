# 02805GoNuts

An interactive landing page for the 02805 Social Graphs and Interactions project.

## GitHub Pages

The site is a dependency-free static page. The workflow in `.github/workflows/pages.yml` deploys it automatically whenever changes are pushed to `main`.

## Weekly pages

The page is organized as a project journal. Week 1 contains the current project content, while Week 2 and Week 3 are ready-made placeholders. To add a new weekly page, copy an `upcoming-week` section in `index.html`, give it a new `id` such as `week-4`, and add a matching link in the `week-nav`.

To enable it the first time:

1. Open the repository's **Settings** on GitHub.
2. Go to **Pages** and choose **GitHub Actions** as the source.
3. Push to `main` and open the URL shown under **Pages**.
