const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000" : "";

let conversationHistory = [];
let patientContext = {};
let isLoading = false;

let sessionId = localStorage.getItem("sessionId");
if (!sessionId) {
  sessionId = "session_" + Math.random().toString(36).substr(2, 9);
  localStorage.setItem("sessionId", sessionId);
}

let userCountry = localStorage.getItem("userCountry") || null;

const EMERGENCY_NUMBERS = {
  "india": [{ label: "112", href: "tel:112" }, { label: "1066 Ambulance", href: "tel:1066" }],
  "usa": [{ label: "911", href: "tel:911" }],
  "uk": [{ label: "999", href: "tel:999" }, { label: "112", href: "tel:112" }],
  "australia": [{ label: "000", href: "tel:000" }],
  "canada": [{ label: "911", href: "tel:911" }],
  "default": [{ label: "112 (Intl)", href: "tel:112" }, { label: "911 (US)", href: "tel:911" }],
};

const TOOL_SOURCES = {
  lookup_drug: { label: "OpenFDA", url: "https://open.fda.gov" },
  search_condition: { label: "MedlinePlus · NIH", url: "https://medlineplus.gov" },
};

function getFeed() { return document.getElementById("feed"); }
function getUserInput() { return document.getElementById("user-input"); }
function getSendBtn() { return document.getElementById("send-btn"); }

function getNumbers() {
  if (!userCountry) return EMERGENCY_NUMBERS["default"];
  return EMERGENCY_NUMBERS[userCountry.toLowerCase().trim()] || EMERGENCY_NUMBERS["default"];
}

function toggleLoc() {
  document.getElementById("loc-popup").classList.toggle("open");
  if (document.getElementById("loc-popup").classList.contains("open"))
    document.getElementById("loc-input").focus();
}

function saveLoc() {
  const val = document.getElementById("loc-input").value.trim();
  if (!val) return;
  userCountry = val;
  localStorage.setItem("userCountry", val);
  document.getElementById("loc-label").textContent = `📍 ${val}`;
  document.getElementById("loc-popup").classList.remove("open");
}

function removeWelcome() {
  const w = document.getElementById("welcome");
  if (w) w.remove();
}

function suggest(el) {
  getUserInput().value = el.textContent;
  autoResize();
  sendMessage();
}

function autoResize() {
  const input = getUserInput();
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 120) + "px";
}

function appendMsg(role, text, toolCalls = []) {
  removeWelcome();
  const feed = getFeed();
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const av = document.createElement("div");
  av.className = "av";
  av.textContent = role === "user" ? "U" : "";
  wrap.appendChild(av);

  const bub = document.createElement("div");
  bub.className = "bub";

  if (toolCalls.length > 0) {
    const badges = document.createElement("div");
    badges.className = "badges";
    const icons = { lookup_drug: "💊", search_condition: "🔍", flag_emergency: "🚨" };
    toolCalls.forEach(t => {
      const b = document.createElement("span");
      b.className = "badge";
      b.textContent = `${icons[t] || "⚙"} ${t.replace(/_/g, " ")}`;
      badges.appendChild(b);
    });
    bub.appendChild(badges);
  }

  const p = document.createElement("p");
  p.innerHTML = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
  bub.appendChild(p);

  if (toolCalls.length > 0) {
    const srcs = toolCalls.filter(t => TOOL_SOURCES[t]).map(t => TOOL_SOURCES[t]);
    if (srcs.length > 0) {
      const src = document.createElement("div");
      src.className = "source";
      src.innerHTML = "Sources: " + srcs.map(s =>
        `<span class="source-pill">${s.label}</span> <a href="${s.url}" target="_blank" rel="noopener">↗ ${s.url.replace("https://", "")}</a>`
      ).join(" · ");
      bub.appendChild(src);
    }
  }

  wrap.appendChild(bub);
  feed.appendChild(wrap);
  feed.scrollTop = feed.scrollHeight;
}

function appendTyping() {
  removeWelcome();
  const feed = getFeed();
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";
  wrap.id = "typing";

  const av = document.createElement("div");
  av.className = "av";

  const bub = document.createElement("div");
  bub.className = "typing-bub";
  bub.innerHTML = `<div class="tdot"></div><div class="tdot"></div><div class="tdot"></div>`;

  wrap.appendChild(av);
  wrap.appendChild(bub);
  feed.appendChild(wrap);
  feed.scrollTop = feed.scrollHeight;
}

function removeTyping() {
  const el = document.getElementById("typing");
  if (el) el.remove();
}

function showEmergency(reason) {
  document.getElementById("em-text").textContent = reason || "Potentially life-threatening symptoms detected.";
  const nums = document.getElementById("em-nums");
  nums.innerHTML = "";
  getNumbers().forEach(n => {
    const a = document.createElement("a");
    a.className = "em-num";
    a.href = n.href;
    a.textContent = `📞 ${n.label}`;
    nums.appendChild(a);
  });
  const banner = document.getElementById("em-banner");
  banner.classList.add("on");
  banner.scrollIntoView({ behavior: "smooth" });
}

function dismissEm() {
  document.getElementById("em-banner").classList.remove("on");
}

async function loadSession() {
  try {
    const res = await fetch(`${API_BASE}/session/${sessionId}`);
    const data = await res.json();
    if (data.patient_context) patientContext = data.patient_context;
    if (data.history && data.history.length > 0) {
      conversationHistory = data.history;
      data.history.forEach(m => appendMsg(m.role === "assistant" ? "assistant" : "user", m.content));
    }
  } catch (e) {
    console.error("Session load failed:", e);
  }
}

async function sendMessage() {
  const userInput = getUserInput();
  const sendBtn = getSendBtn();
  const text = userInput.value.trim();
  if (!text || isLoading) return;

  userInput.value = "";
  userInput.style.height = "auto";
  appendMsg("user", text);
  isLoading = true;
  sendBtn.disabled = true;
  appendTyping();

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: sessionId,
        history: conversationHistory,
        patient_context: patientContext,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      let msg = "Something went wrong. Please try again.";
      if (typeof err.detail === "string") {
        msg = err.detail;
      } else if (Array.isArray(err.detail)) {
        msg = err.detail.map(e => e.msg).join(", ");
      }
      removeTyping();
      appendMsg("assistant", msg);
      isLoading = false;
      sendBtn.disabled = false;
      getUserInput().focus();
      return;
    }

    const data = await res.json();
    conversationHistory = data.updated_history;
    patientContext = data.patient_context || {};
    removeTyping();
    appendMsg("assistant", data.reply, data.tool_calls_made || []);
    if (data.emergency) showEmergency(data.emergency_reason);

  } catch (err) {
    removeTyping();
    appendMsg("assistant", `Something went wrong: ${err.message}.`);
    console.error(err);
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    getUserInput().focus();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (userCountry) document.getElementById("loc-label").textContent = `📍 ${userCountry}`;

  getUserInput().addEventListener("input", autoResize);
  getUserInput().addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  loadSession();
});
