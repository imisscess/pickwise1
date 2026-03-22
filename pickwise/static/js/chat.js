const chatLogEl = document.getElementById("chat-log");
const inputEl = document.getElementById("chat-input");
const sendBtnEl = document.getElementById("send-btn");
const newChatBtnEl = document.getElementById("new-chat-btn");
const sidebarToggleEl = document.getElementById("sidebar-toggle");
const sidebarEl = document.getElementById("sidebar");
const chatMenuBtnEl = document.getElementById("chat-menu-btn");
const sidebarOverlayEl = document.getElementById("sidebar-overlay");
const themeToggleEl = document.getElementById("theme-toggle");

const THEME_STORAGE_KEY = "pickwise_theme";

const INPUT_MIN_ROWS = 1;
const INPUT_MAX_HEIGHT = 200;

function scrollToBottom() {
    if (chatLogEl) {
        chatLogEl.scrollTop = chatLogEl.scrollHeight;
    }
}

function wrapInContainer(el) {
    const container = document.createElement("div");
    container.className = "message-container";
    container.appendChild(el);
    return container;
}

function renderMessage(role, content, ts) {
    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${role}`;
    bubble.textContent = content;
    row.appendChild(bubble);

    if (ts) {
        const meta = document.createElement("div");
        meta.className = "message-meta";
        const date = new Date(ts);
        meta.textContent = date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
        });
        row.appendChild(meta);
    }

    chatLogEl.appendChild(wrapInContainer(row));
    scrollToBottom();
}

function showTypingIndicator() {
    if (document.getElementById("typing-indicator")) return;
    const row = document.createElement("div");
    row.className = "message-row bot";
    const span = document.createElement("div");
    span.id = "typing-indicator";
    span.className = "typing-indicator";
    span.textContent = "PickWise is generating a response…";
    row.appendChild(span);
    chatLogEl.appendChild(wrapInContainer(row));
    scrollToBottom();
}

function hideTypingIndicator() {
    const el = document.getElementById("typing-indicator");
    if (el) {
        const container = el.closest(".message-container");
        if (container) container.remove();
    }
}

function autoExpandInput() {
    if (!inputEl) return;
    inputEl.style.height = "auto";
    const newHeight = Math.min(Math.max(inputEl.scrollHeight, 24), INPUT_MAX_HEIGHT);
    inputEl.style.height = newHeight + "px";
}

function resetInputHeight() {
    if (inputEl) {
        inputEl.style.height = "auto";
        inputEl.style.height = "24px";
    }
}

async function sendMessage() {
    const text = (inputEl.value || "").trim();
    if (!text) return;

    inputEl.value = "";
    resetInputHeight();
    renderMessage("user", text);
    if (window.PickWiseHistory) {
        window.PickWiseHistory.addMessageToCurrent("user", text);
    }

    sendBtnEl.disabled = true;
    showTypingIndicator();

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text }),
        });
        const data = await res.json();
        hideTypingIndicator();
        const answer =
            data && data.answer
                ? data.answer
                : "I was unable to generate a response for that request.";
        renderMessage("bot", answer);
        if (window.PickWiseHistory) {
            window.PickWiseHistory.addMessageToCurrent("bot", answer);
        }
    } catch (err) {
        hideTypingIndicator();
        const msg =
            "There was an error communicating with the PickWise server. Please try again in a moment.";
        renderMessage("bot", msg);
        if (window.PickWiseHistory) {
            window.PickWiseHistory.addMessageToCurrent("bot", msg);
        }
    } finally {
        sendBtnEl.disabled = false;
        inputEl.focus();
    }
}

// Load a conversation from history into the view
window.loadConversationIntoView = function (conversation) {
    if (!chatLogEl) return;
    chatLogEl.innerHTML = "";
    (conversation.messages || []).forEach((m) => {
        renderMessage(m.role, m.content, m.ts);
    });
};

function closeSidebarMobile() {
    if (sidebarEl) sidebarEl.classList.remove("open");
    if (sidebarOverlayEl) sidebarOverlayEl.classList.remove("visible");
}

function openSidebarMobile() {
    if (sidebarEl) sidebarEl.classList.add("open");
    if (sidebarOverlayEl) sidebarOverlayEl.classList.add("visible");
}

// Events
if (sendBtnEl) {
    sendBtnEl.addEventListener("click", sendMessage);
}

if (inputEl) {
    inputEl.addEventListener("input", autoExpandInput);
    inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

if (newChatBtnEl) {
    newChatBtnEl.addEventListener("click", () => {
        if (window.PickWiseHistory) {
            window.PickWiseHistory.startNewConversation();
        }
        closeSidebarMobile();
    });
}

if (sidebarToggleEl && sidebarEl) {
    sidebarToggleEl.addEventListener("click", () => {
        const isCollapsed = sidebarEl.classList.toggle("collapsed");
        sidebarToggleEl.setAttribute("aria-label", isCollapsed ? "Expand sidebar" : "Collapse sidebar");
    });
}

if (chatMenuBtnEl) {
    chatMenuBtnEl.addEventListener("click", openSidebarMobile);
}

if (sidebarOverlayEl) {
    sidebarOverlayEl.addEventListener("click", closeSidebarMobile);
}

function applyTheme(theme) {
    const body = document.body;
    if (!body) return;
    body.classList.remove("theme-light", "theme-dark");
    if (theme === "light") {
        body.classList.add("theme-light");
    } else {
        body.classList.add("theme-dark");
    }
    if (themeToggleEl) {
        const icon = theme === "light" ? "☀️" : "🌙";
        themeToggleEl.querySelector(".theme-icon").textContent = icon;
        themeToggleEl.setAttribute(
            "aria-label",
            theme === "light" ? "Switch to dark mode" : "Switch to light mode"
        );
    }
}

function loadThemePreference() {
    try {
        const stored = localStorage.getItem(THEME_STORAGE_KEY);
        if (stored === "light" || stored === "dark") {
            applyTheme(stored);
            return;
        }
    } catch {
        // ignore
    }
    // Fallback to system preference
    const prefersLight = window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: light)").matches;
    applyTheme(prefersLight ? "light" : "dark");
}

if (themeToggleEl) {
    themeToggleEl.addEventListener("click", () => {
        const body = document.body;
        const isLight = body.classList.contains("theme-light");
        const nextTheme = isLight ? "dark" : "light";
        applyTheme(nextTheme);
        try {
            localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
        } catch {
            // ignore
        }
    });
}

window.addEventListener("DOMContentLoaded", loadThemePreference);
