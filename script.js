const messages = {
  A: "Node A is close to 3 other connections.",
  B: "Node B is a bridge between 2 clusters.",
  C: "Node C has the longest path to explore.",
  D: "Node D sits at the edge of the network."
};

document.querySelectorAll(".pick").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelector(".pick.active").classList.remove("active");
    button.classList.add("active");
    document.querySelector(".result").textContent = messages[button.dataset.node];
  });
});
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

const nodes = new Map();
const incoming = new Map();
const outgoing = new Map();
const cleanLines = (text) => text.split("\n").filter((line) => line.trim() && !line.startsWith("#"));

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

function selectCharacter(nodeId) {
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

async function loadNetwork() {
  const [nodesResponse, edgesResponse] = await Promise.all([fetch("week1_nodes.tsv"), fetch("week1_edges.tsv")]);
  const nodeRows = cleanLines(await nodesResponse.text()).slice(1);
  nodeRows.forEach((line) => {
    const [nodeId, name, wikidataId, url, ...description] = line.split("\t");
    nodes.set(nodeId, { nodeId, name, wikidataId, url, description: description.join("\t") });
    incoming.set(nodeId, new Set());
    outgoing.set(nodeId, new Set());
  });
  const edgeRows = cleanLines(await edgesResponse.text()).slice(1);
  const pairs = new Set();
  edgeRows.forEach((line) => {
    const [source, target] = line.split("\t");
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
  selectCharacter([...nodes.keys()].find((nodeId) => displayName(nodeId).toLowerCase().includes("spider-man")) || [...nodes.keys()][0]);
}

searchInput.addEventListener("input", () => showMatches(searchInput.value.trim()));
loadNetwork().catch(() => {
  characterCard.innerHTML = "<span class=\"card-kicker\">Data unavailable</span><h3>Start the site through GitHub Pages</h3><p>The browser blocks local TSV requests when index.html is opened directly. The deployed page loads the official snapshot normally.</p>";
});