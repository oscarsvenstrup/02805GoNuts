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