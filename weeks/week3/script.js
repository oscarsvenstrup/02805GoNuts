"use strict";

const graphUrl = "../../data/week3/graph.json";
const svgNamespace = "http://www.w3.org/2000/svg";
const svg = document.getElementById("ego-graph");
const nodeSelect = document.getElementById("node-select");
const sourceSelect = document.getElementById("path-source");
const targetSelect = document.getElementById("path-target");
const pathButton = document.getElementById("path-button");
const pathResult = document.getElementById("path-result");
const spiderInput = document.getElementById("spider-input");
const spiderOptions = document.getElementById("spider-character-options");
const spiderButton = document.getElementById("spider-button");
const spiderResult = document.getElementById("spider-result");

let graph;
let nodesById;
let adjacency;

const displayName = (name) => name.replaceAll("_", " ").replace(/\s*\([^)]*\)$/, "");
const formatNumber = (value, digits = 3) => Number(value).toFixed(digits);

function addSvg(tag, attributes, parent = svg) {
  const element = document.createElementNS(svgNamespace, tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  parent.appendChild(element);
  return element;
}

function optionFor(node) {
  const option = document.createElement("option");
  option.value = node.id;
  option.textContent = displayName(node.character);
  return option;
}

function populateControls() {
  const sorted = [...graph.nodes].sort((a, b) => a.character.localeCompare(b.character));
  for (const node of sorted) {
    nodeSelect.appendChild(optionFor(node));
    sourceSelect.appendChild(optionFor(node));
    targetSelect.appendChild(optionFor(node));
  }
  const rockman = sorted.find((node) => node.character === "Rockman_(character)");
  const spiderMan = sorted.find((node) => node.character === "Spider-Man");
  nodeSelect.value = rockman?.id ?? sorted[0].id;
  sourceSelect.value = rockman?.id ?? sorted[0].id;
  targetSelect.value = spiderMan?.id ?? sorted[1].id;
  for (const node of sorted) {
    const option = document.createElement("option");
    option.value = displayName(node.character);
    spiderOptions.appendChild(option);
  }
}

function localEdges(ids) {
  const visible = new Set(ids);
  return graph.edges.filter((edge) => visible.has(String(edge.source)) && visible.has(String(edge.target)));
}

function drawNetwork(ids, pathIds = []) {
  svg.replaceChildren();
  const pathSet = new Set(pathIds);
  const focusId = String(nodeSelect.value);
  const visibleNodes = ids.map((id) => nodesById.get(String(id))).filter(Boolean);
  const positions = new Map();
  const center = visibleNodes.find((node) => String(node.id) === focusId);
  const others = visibleNodes.filter((node) => node !== center);
  if (center) positions.set(String(center.id), { x: 500, y: 280 });
  const radius = Math.min(220, 80 + others.length * 8);
  others.forEach((node, index) => {
    const angle = (index / Math.max(others.length, 1)) * Math.PI * 2 - Math.PI / 2;
    positions.set(String(node.id), { x: 500 + Math.cos(angle) * radius, y: 280 + Math.sin(angle) * radius });
  });
  for (const edge of localEdges(ids)) {
    const source = positions.get(String(edge.source));
    const target = positions.get(String(edge.target));
    if (source && target) {
      const isPath = pathSet.has(String(edge.source)) && pathSet.has(String(edge.target));
      addSvg("line", { x1: source.x, y1: source.y, x2: target.x, y2: target.y, class: `graph-edge${isPath ? " path" : ""}` });
    }
  }
  for (const node of visibleNodes) {
    const position = positions.get(String(node.id));
    const isFocus = String(node.id) === focusId;
    const className = isFocus ? "graph-node focus" : node.z >= 2 ? "graph-node positive" : node.z <= -2 ? "graph-node negative" : "graph-node";
    const circle = addSvg("circle", { cx: position.x, cy: position.y, r: isFocus ? 14 : 9, class: className, tabindex: "0", role: "button", "aria-label": displayName(node.character) });
    circle.addEventListener("click", () => {
      nodeSelect.value = node.id;
      renderSelected();
    });
    circle.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        nodeSelect.value = node.id;
        renderSelected();
      }
    });
    addSvg("text", { x: position.x, y: position.y - (isFocus ? 21 : 14), class: "graph-label" }).textContent = displayName(node.character);
  }
}

function renderSelected() {
  const node = nodesById.get(String(nodeSelect.value));
  if (!node) return;
  const neighborIds = adjacency.get(String(node.id)) || [];
  const visibleIds = [String(node.id), ...neighborIds.slice(0, 30)];
  document.getElementById("node-degree").textContent = node.degree;
  document.getElementById("node-z").textContent = `${node.z >= 0 ? "+" : ""}${formatNumber(node.z, 2)}`;
  document.getElementById("node-null").textContent = formatNumber(node.null_mean, 4);
  const direction = node.z >= 2 ? "above" : node.z <= -2 ? "below" : "close to";
  document.getElementById("node-explanation").textContent = `${displayName(node.character)} has ${node.degree} links and sits ${direction} the degree-preserving expectation. Click a neighbor to inspect it.`;
  drawNetwork(visibleIds);
}

function shortestPath(sourceId, targetId) {
  const queue = [String(sourceId)];
  const previous = new Map([[String(sourceId), null]]);
  while (queue.length) {
    const current = queue.shift();
    if (current === String(targetId)) break;
    for (const neighbor of adjacency.get(current) || []) {
      if (!previous.has(neighbor)) {
        previous.set(neighbor, current);
        queue.push(neighbor);
      }
    }
  }
  if (!previous.has(String(targetId))) return [];
  const path = [];
  for (let current = String(targetId); current !== null; current = previous.get(current)) path.unshift(current);
  return path;
}

function showPath() {
  const path = shortestPath(sourceSelect.value, targetSelect.value);
  if (!path.length) {
    pathResult.textContent = "No path found in the giant component.";
    return;
  }
  nodeSelect.value = path[0];
  drawNetwork(path, path);
  const names = path.map((id) => displayName(nodesById.get(id).character));
  pathResult.textContent = `${path.length - 1} links: ${names.join("  ->  ")}`;
}

function showSpiderPath() {
  const query = spiderInput.value.trim().toLowerCase();
  const start = graph.nodes.find((node) => displayName(node.character).toLowerCase() === query || node.character.toLowerCase() === query || displayName(node.character).toLowerCase().startsWith(query));
  const spider = graph.nodes.find((node) => node.character === "Spider-Man");
  if (!start || !spider) {
    spiderResult.textContent = "Choose a character from the suggestions.";
    return;
  }
  const path = shortestPath(start.id, spider.id);
  if (!path.length) {
    spiderResult.textContent = "No path found to Spider-Man in the giant component.";
    return;
  }
  spiderResult.textContent = `${path.length - 1} links: ${path.map((id) => displayName(nodesById.get(id).character)).join("  ->  ")}`;
  nodeSelect.value = start.id;
  drawNetwork(path, path);
}

async function start() {
  try {
    const response = await fetch(graphUrl);
    if (!response.ok) throw new Error("Graph data unavailable");
    graph = await response.json();
    nodesById = new Map(graph.nodes.map((node) => [String(node.id), node]));
    adjacency = new Map(graph.nodes.map((node) => [String(node.id), []]));
    for (const edge of graph.edges) {
      adjacency.get(String(edge.source)).push(String(edge.target));
      adjacency.get(String(edge.target)).push(String(edge.source));
    }
    populateControls();
    nodeSelect.addEventListener("change", renderSelected);
    pathButton.addEventListener("click", showPath);
    spiderButton.addEventListener("click", showSpiderPath);
    spiderInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") showSpiderPath();
    });
    renderSelected();
  } catch (error) {
    pathResult.textContent = "The explorer could not load its graph data. The analysis and article remain available below.";
    console.warn(error.message);
  }
}

start();
