// Config — change this to your deployed backend URL
const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : "";  // same-origin when served from FastAPI

let conversationHistory = [];
let isLoading = false;

const chatContainer = document.getElementById("chat-container");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const emergencyBanner = document.getElementById("emergency-banner");
const emergencyText = document.getElementById("emergency-text");

userInput.addEventListener("input", () => {
  userInput.style.height = "auto";
  userInput.style.height = Math.min(userInput.scrollHeight, 140) + "px";
});

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

function suggest(el) {
  userInput.value = el.textContent;
  userInput.dispatchEvent(new Event("input"));
  sendMessage();
}

function removeWelcome() {
  const welcome = document.getElementById("welcome");
  if (welcome) welcome.remove();
}

function appendMessage(role, text, toolCalls = []) {
  removeWelcome();
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "👤" : "🩺";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  // shows the badge for which tool is being used
  if (toolCalls.length > 0) {
    const badges = document.createElement("div");
    toolCalls.forEach(tool => {
      const badge = document.createElement("span");
      badge.className = "tool-badge";
      const icons = {
        lookup_drug: "💊",
        search_condition: "🔍",
        flag_emergency: "🚨",
      };
      badge.textContent = `${icons[tool] || "🔧"} ${tool.replace(/_/g, " ")}`;
      badges.appendChild(badge);
    });
    bubble.appendChild(badges);
  }

  // render text
  const formatted = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
  const textNode = document.createElement("p");
  textNode.innerHTML = formatted;
  bubble.appendChild(textNode);

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatContainer.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function appendTypingIndicator() {
  removeWelcome();
  const wrapper = document.createElement("div");
  wrapper.className = "message assistant";
  wrapper.id = "typing-indicator";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "🩺";

  const bubble = document.createElement("div");
  bubble.className = "typing-bubble";
  bubble.innerHTML = `<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>`;

  wrapper.appendChild(avatar);
  wrapper.appendChild(bubble);
  chatContainer.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showEmergency(reason) {
  emergencyText.textContent = `🚨 ${reason} — Call 112 (India) / 911 (US) or go to the nearest emergency room immediately.`;
  emergencyBanner.classList.add("visible");
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text || isLoading) return;

  // clearing input
  userInput.value = "";
  userInput.style.height = "auto";

  // show user message
  appendMessage("user", text);

  // set loading state
  isLoading = true;
  sendBtn.disabled = true;
  const typingEl = appendTypingIndicator();

  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: conversationHistory,
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${response.status}`);
    }

    const data = await response.json();

    // update history
    conversationHistory = data.updated_history;

    // remove typing, show reply
    removeTypingIndicator();
    appendMessage("assistant", data.reply, data.tool_calls_made || []);

    // handle emergency
    if (data.emergency) {
      showEmergency(data.emergency_reason || "Potentially life-threatening symptoms detected");
    }

  } catch (error) {
    removeTypingIndicator();
    appendMessage("assistant", `Sorry, something went wrong: ${error.message}. Please try again or refresh the page.`);
    console.error("Chat error:", error);
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    userInput.focus();
  }
}
