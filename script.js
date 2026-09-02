const nodeCount = document.querySelector("#node-count");
const edgeCount = document.querySelector("#edge-count");
const isolateCount = document.querySelector("#isolate-count");
const pairCount = document.querySelector("#pair-count");
const density = document.querySelector("#density");
const searchInput = document.querySelector("#character-search");
const searchResults = document.querySelector("#search-results");
const incomingList = document.querySelector("#incoming-list");
const outgoingList = document.querySelector("#outgoing-list");
const incomingCount = document.querySelector("#incoming-count");
const outgoingCount = document.querySelector("#outgoing-count");
const characterCard = document.querySelector("#character-card");
const graph = document.querySelector("#network-graph");
const graphFrame = document.querySelector(".network-frame");
const graphTooltip = document.querySelector("#graph-tooltip");

const nodes = new Map();
const incoming = new Map();
const outgoing = new Map();
const edgeRefs = [];
const positions = new Map();
const cleanLines = (text) => text.split("\n").filter((line) => line.trim() && !line.startsWith("#"));
const svgElement = (tag, attributes) => {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
};

function displayName(nodeId) {
  return nodes.get(nodeId)?.name || nodeId.replaceAll("_", " ");
}

function renderList(list, values, emptyText) {
  list.replaceChildren();
  if (!values.length) {
    const item = document.createElement("li");
    item.textContent = emptyText;
    list.append(item);
    return;
  }
  values.sort((a, b) => displayName(a).localeCompare(displayName(b))).forEach((nodeId) => {
    const item = document.createElement("li");
    item.textContent = displayName(nodeId);
    list.append(item);
  });
}

function updateGraphSelection(nodeId) {
  const neighbors = new Set([...(incoming.get(nodeId) || []), ...(outgoing.get(nodeId) || [])]);
  graph.querySelectorAll(".network-node").forEach((node) => {
    const isSelected = node.dataset.nodeId === nodeId;
    node.classList.toggle("selected", isSelected);
    node.classList.toggle("neighbor", neighbors.has(node.dataset.nodeId));
    node.classList.toggle("muted", !isSelected && !neighbors.has(node.dataset.nodeId));
  });
  edgeRefs.forEach(({ element, source, target }) => {
    const highlighted = source === nodeId || target === nodeId;
    element.classList.toggle("highlight", highlighted);
    element.classList.toggle("muted", !highlighted);
  });
}

function showTooltip(nodeId, event) {
  const selected = nodes.get(nodeId);
  const frameBounds = graphFrame.getBoundingClientRect();
  graphTooltip.innerHTML = `<strong>${selected.name}</strong><span>${incoming.get(nodeId).size} in · ${outgoing.get(nodeId).size} out</span>`;
  graphTooltip.hidden = false;
  graphTooltip.style.left = `${Math.min(event.clientX - frameBounds.left + 12, frameBounds.width - 235)}px`;
  graphTooltip.style.top = `${Math.max(event.clientY - frameBounds.top - 58, 10)}px`;
}

function selectCharacter(nodeId, event) {
  const selected = nodes.get(nodeId);
  if (!selected) return;
  const incomingNodes = [...(incoming.get(nodeId) || [])];
  const outgoingNodes = [...(outgoing.get(nodeId) || [])];
  characterCard.innerHTML = `<span class="card-kicker">Selected node</span><h3>${selected.name}</h3><p>${selected.description || "A Marvel character in the shared Week 1 snapshot."}</p>`;
  incomingCount.textContent = incomingNodes.length;
  outgoingCount.textContent = outgoingNodes.length;
  renderList(incomingList, incomingNodes, "No incoming links.");
  renderList(outgoingList, outgoingNodes, "No outgoing links.");
  searchResults.replaceChildren();
  searchInput.value = selected.name;
  updateGraphSelection(nodeId);
  if (event) showTooltip(nodeId, event);
}

function showMatches(query) {
  searchResults.replaceChildren();
  if (!query) return;
  [...nodes.values()].filter((node) => node.name.toLowerCase().includes(query.toLowerCase())).slice(0, 8).forEach((node) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = node.name;
    button.addEventListener("click", () => selectCharacter(node.nodeId));
    searchResults.append(button);
  });
}

function renderGraph(edgeRows) {
  const graphWidth = 1000;
  const graphHeight = 600;
  const centerX = graphWidth / 2;
  const centerY = graphHeight / 2;
  const radiusX = 445;
  const radiusY = 255;
  const nodeIds = [...nodes.keys()];
  const degrees = new Map(nodeIds.map((nodeId) => [nodeId, incoming.get(nodeId).size + outgoing.get(nodeId).size]));
  const maxDegree = Math.max(...degrees.values());
  nodeIds.forEach((nodeId, index) => {
    const angle = (index / nodeIds.length) * Math.PI * 2 - Math.PI / 2;
    positions.set(nodeId, { x: centerX + Math.cos(angle) * radiusX, y: centerY + Math.sin(angle) * radiusY });
  });
  const defs = svgElement("defs", {});
  const marker = svgElement("marker", { id: "arrow", markerWidth: "5", markerHeight: "5", refX: "5", refY: "2.5", orient: "auto" });
  marker.append(svgElement("path", { d: "M0,0 L5,2.5 L0,5 z", fill: "#f6f1e7" }));
  defs.append(marker);
  graph.append(defs);
  edgeRows.forEach(([source, target]) => {
    const sourcePosition = positions.get(source);
    const targetPosition = positions.get(target);
    if (!sourcePosition || !targetPosition) return;
    const line = svgElement("line", { x1: sourcePosition.x, y1: sourcePosition.y, x2: targetPosition.x, y2: targetPosition.y, class: "network-edge", "marker-end": "url(#arrow)" });
    graph.append(line);
    edgeRefs.push({ element: line, source, target });
  });
  nodeIds.forEach((nodeId) => {
    const position = positions.get(nodeId);
    const node = svgElement("circle", { cx: position.x, cy: position.y, r: 3 + (degrees.get(nodeId) / maxDegree) * 8, class: degrees.get(nodeId) > maxDegree * .45 ? "network-node hub" : "network-node", tabindex: "0", "aria-label": displayName(nodeId) });
    node.dataset.nodeId = nodeId;
    node.addEventListener("click", (event) => selectCharacter(nodeId, event));
    node.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") selectCharacter(nodeId, event); });
    graph.append(node);
  });
}

async function loadNetwork() {
  const [nodesResponse, edgesResponse] = await Promise.all([fetch("week1_nodes.tsv"), fetch("week1_edges.tsv")]);
  const nodeRows = cleanLines(await nodesResponse.text()).slice(1);
  nodeRows.forEach((line) => {
    const [nodeId, name, wikidataId, url, ...description] = line.split("\t");
    nodes.set(nodeId, { nodeId, name, wikidataId, url, description: description.join("\t") });
    incoming.set(nodeId, new Set());
    outgoing.set(nodeId, new Set());
  });
  const edgeRows = cleanLines(await edgesResponse.text()).slice(1).map((line) => line.split("\t"));
  const pairs = new Set();
  edgeRows.forEach(([source, target]) => {
    if (!source || !target) return;
    outgoing.get(source)?.add(target);
    incoming.get(target)?.add(source);
    pairs.add([source, target].sort().join("\0"));
  });
  const isolates = [...nodes.keys()].filter((nodeId) => !incoming.get(nodeId).size && !outgoing.get(nodeId).size).length;
  nodeCount.textContent = nodes.size;
  edgeCount.textContent = edgeRows.length.toLocaleString();
  isolateCount.textContent = isolates;
  pairCount.textContent = pairs.size.toLocaleString();
  density.textContent = `${(pairs.size / (nodes.size * (nodes.size - 1) / 2) * 100).toFixed(1)}%`;
  renderGraph(edgeRows);
  selectCharacter([...nodes.keys()].find((nodeId) => displayName(nodeId).toLowerCase().includes("spider-man")) || [...nodes.keys()][0]);
}

searchInput.addEventListener("input", () => showMatches(searchInput.value.trim()));
loadNetwork().catch(() => {
  characterCard.innerHTML = "<span class=\"card-kicker\">Data unavailable</span><h3>Start the site through GitHub Pages</h3><p>The browser blocks local TSV requests when index.html is opened directly. The deployed page loads the official snapshot normally.</p>";
});
