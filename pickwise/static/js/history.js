// Simple conversation history management using localStorage.
// Each conversation: { id, title, messages: [{ role, content, ts }] }

const STORAGE_KEY = "pickwise_conversations_v1";
const MAX_CONVERSATIONS = 20;

let conversations = [];
let currentConversationId = null;

function loadConversations() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        conversations = raw ? JSON.parse(raw) : [];
    } catch {
        conversations = [];
    }
}

function persistConversations() {
    try {
        const trimmed =
            conversations.length > MAX_CONVERSATIONS
                ? conversations.slice(conversations.length - MAX_CONVERSATIONS)
                : conversations;
        localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {
        // Ignore quota errors
    }
}

function createConversation(firstUserMessage) {
    const id = String(Date.now());
    const title =
        (firstUserMessage || "New chat").trim().slice(0, 40) ||
        "New chat";
    const conv = { id, title, messages: [] };
    conversations.push(conv);
    currentConversationId = id;
    persistConversations();
    renderConversationList();
    return conv;
}

function getCurrentConversation(createIfMissing = false, firstMessage = "") {
    let conv = conversations.find((c) => c.id === currentConversationId);
    if (!conv && createIfMissing) {
        conv = createConversation(firstMessage);
    }
    return conv || null;
}

function addMessageToCurrent(role, content) {
    if (!currentConversationId) {
        createConversation(role === "user" ? content : "New chat");
    }
    const conv = getCurrentConversation(true, content);
    conv.messages.push({
        role,
        content,
        ts: new Date().toISOString(),
    });
    persistConversations();
}

function setCurrentConversation(id) {
    currentConversationId = id;
    renderConversationList();
}

function deleteConversation(id) {
    const idx = conversations.findIndex((c) => c.id === id);
    if (idx === -1) return;
    const wasCurrent = id === currentConversationId;
    conversations.splice(idx, 1);
    persistConversations();
    if (wasCurrent) {
        startNewConversation();
    } else {
        renderConversationList();
    }
}

function handleDeleteConversation(id, itemEl) {
    if (!confirm("Are you sure you want to delete this conversation?")) return;
    itemEl.classList.add("deleting");
    itemEl.addEventListener(
        "animationend",
        () => {
            deleteConversation(id);
        },
        { once: true }
    );
}

function renderConversationList() {
    const listEl = document.getElementById("chat-list");
    if (!listEl) return;
    listEl.innerHTML = "";

    conversations
        .slice()
        .reverse()
        .forEach((conv) => {
            const item = document.createElement("div");
            item.className =
                "chat-list-item" +
                (conv.id === currentConversationId ? " active" : "");
            item.dataset.id = conv.id;

            const content = document.createElement("div");
            content.className = "chat-list-item-content";

            const title = document.createElement("div");
            title.className = "chat-list-item-title";
            title.textContent = conv.title || "Untitled chat";
            content.appendChild(title);

            const deleteBtn = document.createElement("button");
            deleteBtn.className = "chat-list-item-delete";
            deleteBtn.type = "button";
            deleteBtn.setAttribute("aria-label", "Delete conversation");
            deleteBtn.innerHTML =
                '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14z"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>';
            deleteBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                handleDeleteConversation(conv.id, item);
            });

            content.appendChild(deleteBtn);
            item.appendChild(content);

            item.addEventListener("click", (e) => {
                if (e.target.closest(".chat-list-item-delete")) return;
                currentConversationId = conv.id;
                renderConversationList();
                if (window.loadConversationIntoView) {
                    window.loadConversationIntoView(conv);
                }
            });

            listEl.appendChild(item);
        });
}

function startNewConversation() {
    currentConversationId = null;
    const log = document.getElementById("chat-log");
    if (log) {
        log.innerHTML = "";
    }
    renderConversationList();
}

// Initialize on load
window.addEventListener("DOMContentLoaded", () => {
    loadConversations();
    renderConversationList();
});

// Expose minimal API to other scripts
window.PickWiseHistory = {
    getCurrentConversation,
    addMessageToCurrent,
    setCurrentConversation,
    startNewConversation,
    deleteConversation,
    conversations,
};

