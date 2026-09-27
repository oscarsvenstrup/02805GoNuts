"use strict";

const graphUrl = "../../data/week4/graph.json";
const svgNamespace = "http://www.w3.org/2000/svg";
const svg = document.getElementById("community-graph");
const modeButtons = document.querySelectorAll(".mode-toggle button");
const communitySelect = document.getElementById("community-select");
const legendStrip = document.getElementById("legend-strip");
const nodeExplanation = document.getElementById("node-explanation");

const PALETTE = ["#dd624b", "#8ccad1", "#c8e85b", "#9a9639", "#527e84", "#7fb5bb", "#f16f54", "#b7a6d6", "#e0a458", "#6f9e46"];
const LOUVAIN_NAMES = ["Founding Avengers & street heroes", "X-Men", "Cosmic Avengers", "Spider-Verse",
  "Supernatural / Midnight Sons", "Hulk family", "Inhumans & Fantastic Four", "Young cosmic heroes"];

let graph;
let mode = "louvain"; // or "infomap"
let selectedCommunity = "all";
let focusId = null;

const displayName = (name) => name.replaceAll("_", " ").replace(/\s*\([^)]*\)$/, "");

function addSvg(tag, attributes, parent = svg) {
  const element = document.createElementNS(svgNamespace, tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  parent.appendChild(element);
  return element;
}

function communityCount(byMode) {
  return 1 + Math.max(...graph.nodes.map((node) => node[byMode]));
}

function communityLabel(index) {
  if (mode === "louvain") return `${index}. ${LOUVAIN_NAMES[index] ?? "Community " + index}`;
  return `Infomap module ${index}`;
}

function populateCommunitySelect() {
  communitySelect.replaceChildren();
  const allOption = document.createElement("option");
  allOption.value = "all";
  allOption.textContent = "All communities";
  communitySelect.appendChild(allOption);
  const count = communityCount(mode);
  for (let index = 0; index < count; index++) {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = communityLabel(index);
    communitySelect.appendChild(option);
  }
  selectedCommunity = "all";
  communitySelect.value = "all";
}

function computeProjection() {
  const xs = graph.nodes.map((node) => node.x);
  const ys = graph.nodes.map((node) => node.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const width = 1000, height = 600, pad = 45;
  const scale = Math.min((width - 2 * pad) / (maxX - minX || 1), (height - 2 * pad) / (maxY - minY || 1));
  const offsetX = (width - (maxX - minX) * scale) / 2;
  const offsetY = (height - (maxY - minY) * scale) / 2;
  return (node) => ({
    x: offsetX + (node.x - minX) * scale,
    y: offsetY + (node.y - minY) * scale,
  });
}

function renderLegend() {
  legendStrip.replaceChildren();
  const count = communityCount(mode);
  for (let index = 0; index < count; index++) {
    const span = document.createElement("span");
    const swatch = document.createElement("i");
    swatch.style.background = PALETTE[index % PALETTE.length];
    span.appendChild(swatch);
    span.append(mode === "louvain" ? (LOUVAIN_NAMES[index] ?? `Community ${index}`) : `Module ${index}`);
    legendStrip.appendChild(span);
  }
}

function draw() {
  svg.replaceChildren();
  const project = computeProjection();
  const positions = new Map(graph.nodes.map((node) => [String(node.id), project(node)]));
  for (const edge of graph.edges) {
    const source = positions.get(String(edge.source));
    const target = positions.get(String(edge.target));
    if (!source || !target) continue;
    addSvg("line", { x1: source.x, y1: source.y, x2: target.x, y2: target.y, class: "graph-edge" });
  }
  for (const node of graph.nodes) {
    const position = positions.get(String(node.id));
    const communityValue = node[mode];
    const muted = selectedCommunity !== "all" && String(communityValue) !== selectedCommunity;
    const isFocus = focusId !== null && String(node.id) === String(focusId);
    let className = "graph-node";
    if (muted) className += " muted";
    if (isFocus) className += " focus";
    else if (!node.agree) className += " disagree-ring";
    const circle = addSvg("circle", {
      cx: position.x, cy: position.y, r: 4 + Math.sqrt(node.degree),
      fill: PALETTE[communityValue % PALETTE.length],
      class: className, tabindex: "0", role: "button", "aria-label": displayName(node.character),
    });
    circle.addEventListener("click", () => selectNode(node));
    circle.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectNode(node);
      }
    });
  }
  const topByDegree = [...graph.nodes].sort((a, b) => b.degree - a.degree).slice(0, 10);
  for (const node of topByDegree) {
    const position = positions.get(String(node.id));
    addSvg("text", { x: position.x, y: position.y - (7 + Math.sqrt(node.degree)), class: "graph-label" }).textContent = displayName(node.character);
  }
}

function selectNode(node) {
  focusId = node.id;
  const agreeText = node.agree ? "agree" : "disagree";
  nodeExplanation.textContent = `${displayName(node.character)} has ${node.degree} links. Louvain places it in "${LOUVAIN_NAMES[node.louvain] ?? node.louvain}"; Infomap places it in module ${node.infomap}. The two methods ${agreeText} on this character.`;
  draw();
}

function setMode(newMode) {
  mode = newMode;
  for (const button of modeButtons) button.classList.toggle("active", button.dataset.mode === mode);
  populateCommunitySelect();
  renderLegend();
  draw();
}

async function start() {
  try {
    const response = await fetch(graphUrl);
    if (!response.ok) throw new Error("Graph data unavailable");
    graph = await response.json();
    populateCommunitySelect();
    renderLegend();
    for (const button of modeButtons) {
      button.addEventListener("click", () => setMode(button.dataset.mode));
    }
    communitySelect.addEventListener("change", () => {
      selectedCommunity = communitySelect.value;
      draw();
    });
    setMode("louvain");
    nodeExplanation.textContent = `${(graph.agreement_rate * 100).toFixed(1)}% of characters land in the same relative group under both methods (NMI = ${graph.nmi_louvain_vs_infomap.toFixed(2)}). Click a node, or choose a community, to explore.`;
  } catch (error) {
    nodeExplanation.textContent = "The explorer could not load its graph data. The analysis and article remain available below.";
    console.warn(error.message);
  }
}

start();
