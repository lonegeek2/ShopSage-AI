const API = "";
const $ = (id) => document.getElementById(id);
let sessionId = localStorage.getItem("shopsage_session") || null;
let busy = false;
let toastTimer;

const categoryEmoji = {
  Laptop: "💻", Smartphone: "📱", Headphones: "🎧",
  Smartwatch: "⌚", Backpack: "🎒", Furniture: "🪑",
  Clothing: "👕", Shoes: "👟"
};

function showToast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[ch]));
}

// Lightweight Markdown formatting for model answers; HTML is escaped first.
function formatAnswer(text) {
  let safe = escapeHtml(text);
  safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
  const lines = safe.split(/\r?\n/);
  let html = "", inList = false;
  for (const line of lines) {
    const trimmed = line.trim();
    const match = trimmed.match(/^[-*]\s+(.+)/);
    const numbered = trimmed.match(/^\d+[.)]\s+(.+)/);
    if (match || numbered) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${(match || numbered)[1]}</li>`;
    } else {
      if (inList) { html += "</ul>"; inList = false; }
      if (trimmed) html += `<p>${trimmed}</p>`;
    }
  }
  if (inList) html += "</ul>";
  return html;
}

function addMessage(role, text, typing = false) {
  const container = $("chatMessages");
  const welcome = container.querySelector(".welcome-message");
  if (welcome) welcome.remove();
  const row = document.createElement("div");
  row.className = `message ${role}`;
  const avatar = role === "assistant" ? "✳" : "●";
  row.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-body">${typing
      ? '<div class="typing"><span></span><span></span><span></span></div>'
      : formatAnswer(text)}</div>`;
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
  return row;
}

async function sendMessage(rawText) {
  const message = rawText.trim();
  if (!message || busy) return;
  busy = true;
  $("sendButton").disabled = true;
  $("agentStatus").textContent = "Thinking through your request";
  addMessage("user", message);
  $("chatInput").value = "";
  $("chatInput").style.height = "auto";
  const typing = addMessage("assistant", "", true);

  try {
    const response = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({message, session_id: sessionId})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "The assistant could not respond.");
    sessionId = data.session_id;
    localStorage.setItem("shopsage_session", sessionId);
    typing.remove();
    addMessage("assistant", data.answer || "I couldn't find an answer for that.");
    $("agentStatus").textContent = "Assistant ready";
  } catch (error) {
    typing.remove();
    addMessage("assistant", `I couldn't connect to the shopping agent. ${error.message} Check that the local server and Ollama are running.`);
    $("agentStatus").textContent = "Connection needs attention";
    showToast("Could not reach ShopSage");
  } finally {
    busy = false;
    $("sendButton").disabled = false;
    $("chatInput").focus();
  }
}

async function newConversation() {
  if (sessionId) {
    try { await fetch(`${API}/api/session/${encodeURIComponent(sessionId)}`, {method:"DELETE"}); } catch {}
  }
  sessionId = null;
  localStorage.removeItem("shopsage_session");
  $("chatMessages").innerHTML = `
    <div class="welcome-message">
      <div class="welcome-icon">✳</div>
      <h3>Let's find your <em>perfect pick.</em></h3>
      <p>Share a product, a budget, or a feature that matters to you.</p>
    </div>`;
  $("agentStatus").textContent = "Assistant ready";
}

function productCard(p) {
  const stock = Number(p.stock_quantity) > 0;
  const emoji = categoryEmoji[p.category] || "✦";
  return `
    <article class="product-card">
      <div class="product-visual">
        <span class="product-tag">${escapeHtml(p.category)}</span>
        <span class="product-rating">★ ${Number(p.rating || 0).toFixed(1)}</span>
        <span class="product-emoji">${emoji}</span>
      </div>
      <div class="product-name">${escapeHtml(p.name)}</div>
      <div class="product-brand">${escapeHtml(p.brand)}</div>
      <div class="product-card-bottom">
        <div class="product-price">₹${Number(p.price).toLocaleString("en-IN")}</div>
        <div class="product-stock ${stock ? "available" : "unavailable"}">${stock ? "● In stock" : "○ Sold out"}</div>
      </div>
    </article>`;
}

async function loadProducts() {
  const params = new URLSearchParams();
  const q = $("productSearch").value.trim();
  const category = $("categoryFilter").value;
  const maxPrice = Number($("maxPrice").value || 0);
  const sort = $("sortFilter").value;
  if (q) params.set("q", q);
  if (category) params.set("category", category);
  if (maxPrice > 0) params.set("max_price", maxPrice);
  if ($("inStock").checked) params.set("in_stock", "true");
  params.set("sort", sort);

  const grid = $("productGrid");
  grid.innerHTML = '<div class="loading-card">Finding your products…</div>';
  try {
    const response = await fetch(`${API}/api/products?${params.toString()}`);
    if (!response.ok) throw new Error("Catalog request failed");
    const data = await response.json();
    $("productCount").textContent = data.total;
    $("catalogFooterCount").textContent = `${data.total} MATCHING PRODUCTS`;
    grid.innerHTML = data.products.length
      ? data.products.map(productCard).join("")
      : '<div class="empty-state">No products match those filters.<br>Try a different search or a wider budget.</div>';
  } catch (error) {
    grid.innerHTML = '<div class="empty-state">Could not load the catalog. Check that the ShopSage server is running.</div>';
  }
}

async function init() {
  try {
    const health = await fetch(`${API}/api/health`);
    if (!health.ok) throw new Error("Offline");
    $("connectionState").className = "online";
    $("connectionState").innerHTML = "<i></i> Connected to your local shopping engine";
    const cats = await fetch(`${API}/api/categories`).then(r => r.json());
    for (const category of cats.categories || []) {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      $("categoryFilter").appendChild(option);
    }
  } catch {
    $("connectionState").className = "offline";
    $("connectionState").innerHTML = "<i></i> Local server is not connected";
  }
  await loadProducts();
}

$("sendButton").addEventListener("click", () => sendMessage($("chatInput").value));
$("chatInput").addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage($("chatInput").value);
  }
});
$("chatInput").addEventListener("input", event => {
  event.target.style.height = "auto";
  event.target.style.height = `${Math.min(event.target.scrollHeight, 100)}px`;
});
document.querySelectorAll("[data-prompt]").forEach(button => {
  button.addEventListener("click", () => sendMessage(button.dataset.prompt));
});
$("newChat").addEventListener("click", newConversation);
$("newChatTop").addEventListener("click", newConversation);

let searchDebounce;
$("productSearch").addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadProducts, 250);
});
["categoryFilter", "sortFilter", "maxPrice", "inStock"].forEach(id => {
  $(id).addEventListener("change", loadProducts);
});
$("maxPrice").addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(loadProducts, 350);
});

init();
