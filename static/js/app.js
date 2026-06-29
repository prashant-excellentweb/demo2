// Configure marked.js with highlight.js for premium visualization
marked.setOptions({
    highlight: function(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value;
        }
        return hljs.highlightAuto(code).value;
    },
    breaks: true,
    gfm: true
});

document.addEventListener("DOMContentLoaded", async () => {
    marked.use({
        breaks: true,
        gfm: true
    });

    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const micBtn = document.getElementById("mic-btn");
    const chatContainer = document.getElementById("chat-container");
    const newChatBtn = document.getElementById("new-chat-btn");
    const newProjectBtn = document.getElementById("new-project-btn");
    const sidebarHistory = document.getElementById("chat-history");
    const projectsList = document.getElementById("projects-list");
    const profileBtn = document.getElementById("profile-btn");
    const logoHome = document.getElementById("logo-home");
    const activeChatTitleDisp = document.getElementById("active-chat-title");
    const attachBtn = document.getElementById("attach-btn");
    const websearchBtn = document.getElementById("websearch-btn");
    const fileInput = document.getElementById("file-input");
    const fileAttachments = document.getElementById("file-attachments");
    const attachmentsList = document.getElementById("attachments-list");
    const clearAttachmentsBtn = document.getElementById("clear-attachments");
    const webSearchResults = document.getElementById("web-search-results");
    const searchResultsList = document.getElementById("search-results-list");
    const clearSearchBtn = document.getElementById("clear-search");

    let chats = [];
    let projects = [];
    let currentChatId = null;
    let currentProjectId = null;
    let lockTimer = null;
    let recognition = null;
    let attachedFiles = [];
    let webSearchData = [];

    // Initialize Speech Recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            micBtn.classList.add("mic-active");
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value += (chatInput.value ? ' ' : '') + transcript;
            chatInput.dispatchEvent(new Event('input'));
        };

        recognition.onerror = () => {
            micBtn.classList.remove("mic-active");
        };

        recognition.onend = () => {
            micBtn.classList.remove("mic-active");
        };
    }

    micBtn.addEventListener("click", () => {
        if (!recognition) {
            alert("Speech recognition not supported in this browser.");
            return;
        }
        if (micBtn.classList.contains("mic-active")) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });

    logoHome.addEventListener("click", startNewChat);

    // Load Projects and Chats on Startup
    await loadProjects();
    await loadChats();

    async function loadProjects() {
        try {
            const resp = await fetch('/api/projects');
            projects = await resp.json();
            renderProjects();
        } catch (e) {
            console.error("Failed to load projects from DB", e);
        }
    }

    async function loadChats() {
        try {
            const resp = await fetch('/api/chats');
            chats = await resp.json();
            renderSidebar();
            if (chats.length > 0) {
                switchChat(chats[0].id);
            } else {
                startNewChat();
            }
        } catch (e) {
            console.error("Failed to load chats from DB", e);
        }
    }

    function renderProjects() {
        projectsList.innerHTML = "";
        projects.forEach(project => {
            const projectDiv = document.createElement("div");
            projectDiv.className = "project-item";
            projectDiv.dataset.projectId = project.id;

            const headerDiv = document.createElement("div");
            headerDiv.className = "project-header";
            if (project.id === currentProjectId) headerDiv.classList.add("active");

            const icon = document.createElement("div");
            icon.className = "project-icon";
            icon.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4c-1.11 0-2 .89-2 2v3h2V6h6V4zM10 19v-1H4v-4H2v5c0 1.11.89 2 2 2h6zm8-15h-6v2h6v3h2V6c0-1.11-.89-2-2-2zm2 13v-5h-2v4h-6v2h6c1.11 0 2-.89 2-2z"/></svg>`;
            headerDiv.appendChild(icon);

            const nameSpan = document.createElement("span");
            nameSpan.className = "project-name";
            nameSpan.textContent = project.name;
            headerDiv.appendChild(nameSpan);

            const actionsDiv = document.createElement("div");
            actionsDiv.className = "project-actions";

            const addChatBtn = document.createElement("button");
            addChatBtn.className = "project-action-btn";
            addChatBtn.title = "New chat in project";
            addChatBtn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>`;
            addChatBtn.onclick = (e) => {
                e.stopPropagation();
                startNewChatInProject(project.id);
            };
            actionsDiv.appendChild(addChatBtn);

            const deleteBtn = document.createElement("button");
            deleteBtn.className = "project-action-btn";
            deleteBtn.title = "Delete project";
            deleteBtn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>`;
            deleteBtn.onclick = (e) => {
                e.stopPropagation();
                deleteProject(project.id);
            };
            actionsDiv.appendChild(deleteBtn);

            headerDiv.appendChild(actionsDiv);
            projectDiv.appendChild(headerDiv);

            const chatsDiv = document.createElement("div");
            chatsDiv.className = "project-chats";
            projectDiv.appendChild(chatsDiv);

            headerDiv.onclick = () => toggleProject(project.id);

            projectsList.appendChild(projectDiv);
        });
    }

    function renderSidebar() {
        // First render project chats
        projects.forEach(project => {
            const projectDiv = document.querySelector(`[data-project-id="${project.id}"]`);
            if (projectDiv) {
                const chatsDiv = projectDiv.querySelector('.project-chats');
                chatsDiv.innerHTML = "";

                const projectChats = chats.filter(chat => chat.project_id === project.id);
                projectChats.forEach(chat => {
                    renderChatItem(chatsDiv, chat);
                });
            }
        });

        // Then render recent chats (those not in any project)
        sidebarHistory.innerHTML = "";
        const recentChats = chats.filter(chat => !chat.project_id);
        recentChats.forEach(chat => {
            renderChatItem(sidebarHistory, chat);
        });
    }

    function renderChatItem(container, chat) {
        const div = document.createElement("div");
        div.className = "history-item";
        if (chat.id === currentChatId) div.classList.add("active");

        const titleSpan = document.createElement("span");
        titleSpan.className = "history-title";
        titleSpan.textContent = chat.title || "New Chat";
        div.appendChild(titleSpan);

        const delBtn = document.createElement("button");
        delBtn.className = "trash-btn";
        delBtn.title = "Delete chat";
        delBtn.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>`;
        delBtn.onclick = (e) => {
            e.stopPropagation();
            deleteChat(chat.id);
        };
        div.appendChild(delBtn);

        div.onclick = () => switchChat(chat.id);
        container.appendChild(div);
    }

    async function deleteChat(id) {
        try {
            const resp = await fetch(`/api/chats/${id}`, { method: 'DELETE' });
            if (resp.ok) {
                chats = chats.filter(c => c.id !== id);
                if (currentChatId === id) {
                    if (chats.length > 0) switchChat(chats[0].id);
                    else startNewChat();
                } else {
                    renderSidebar();
                }
            }
        } catch (e) { console.error("Deletion failed", e); }
    }

    function startNewChat() {
        const chat = getActiveChat();

        // If current chat is already empty and not in temporary mode, don't create a new one
        if (chat && chat.messages.length === 0 && !window.temporaryChatEnabled) {
            return;
        }

        // If the current chat was temporary, remove it from the local list when leaving
        if (window.temporaryChatEnabled) {
            chats = chats.filter(c => c.id !== currentChatId);
        }

        // Always reset temporary mode for new chats
        window.temporaryChatEnabled = false;
        document.body.classList.remove('temporary-mode');

        currentChatId = crypto.randomUUID();
        currentProjectId = null;
        const newChat = {
            id: currentChatId,
            title: "New Chat",
            messages: [],
            total_tokens: 0,
            token_limit: 1000,
            locked_until: 0,
            project_id: null
        };
        chats.unshift(newChat);
        renderSidebar();
        renderCurrentChat();
    }

    function startNewChatInProject(projectId) {
        currentChatId = crypto.randomUUID();
        currentProjectId = projectId;
        const project = projects.find(p => p.id === projectId);
        const newChat = {
            id: currentChatId,
            title: "New Chat",
            messages: [],
            total_tokens: 0,
            token_limit: 1000,
            locked_until: 0,
            project_id: projectId
        };
        chats.unshift(newChat);

        // Expand project if not already expanded
        const projectDiv = document.querySelector(`[data-project-id="${projectId}"]`);
        if (projectDiv && !projectDiv.classList.contains('expanded')) {
            toggleProject(projectId);
        }

        renderSidebar();
        renderCurrentChat();

        // Update project header active state
        document.querySelectorAll('.project-header').forEach(header => {
            header.classList.remove('active');
        });
        const activeHeader = document.querySelector(`[data-project-id="${projectId}"] .project-header`);
        if (activeHeader) activeHeader.classList.add('active');
    }

    function switchChat(id) {
        if (id === currentChatId) return;

        // If the current chat was temporary, remove it from the local list when switching away
        if (window.temporaryChatEnabled) {
            chats = chats.filter(c => c.id !== currentChatId);
        }

        // Reset temporary mode when switching to a saved chat
        window.temporaryChatEnabled = false;
        document.body.classList.remove('temporary-mode');

        currentChatId = id;
        renderSidebar(); // Update active class
        renderCurrentChat();
    }

    function getActiveChat() {
        return chats.find(c => c.id === currentChatId);
    }

    function renderCurrentChat() {
        if (lockTimer) clearInterval(lockTimer);
        const chat = getActiveChat();
        if (!chat) return;

        chatContainer.innerHTML = "";
        if (chat.messages.length === 0) {
            chatContainer.innerHTML = `
                <div class="initial-message-container">
                        <div class="initial-message">What can I help you with today?</div>
                        <div class="initial-submessage">Ask anything, attach files, or enable web research from the + menu.</div>
                    <div class="temp-chat-teaser" id="temp-chat-toggle-initial">
                        <div class="temp-chat-teaser-icon">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                        </div>
                        <div class="temp-chat-teaser-text">
                            <strong>Temporary Chat</strong>
                            <span>Messages won't be saved in history</span>
                        </div>
                        <div class="temp-chat-teaser-switch">
                            <label class="switch">
                                <input type="checkbox" id="temp-chat-checkbox-initial" ${window.temporaryChatEnabled ? 'checked' : ''}>
                                <span class="slider round"></span>
                            </label>
                        </div>
                    </div>
                </div>`;

            const tempCheckbox = document.getElementById("temp-chat-checkbox-initial");
            if (tempCheckbox) {
                tempCheckbox.addEventListener("change", (e) => {
                    window.temporaryChatEnabled = e.target.checked;
                    document.body.classList.toggle('temporary-mode', window.temporaryChatEnabled);
                });
            }
        } else {
            // Hide temp mode indicator if not in temp mode, but keep theme if it was active for this chat session
            // Actually, if a chat has messages, temporaryChatEnabled should probably be false unless we're IN a temp session.
            // But since we don't save temp chats, any chat with messages from DB is NOT temp.
            window.temporaryChatEnabled = false;
            document.body.classList.remove('temporary-mode');

            chat.messages.forEach((m, idx) => {
                const displayText = m.display_text !== undefined ? m.display_text : m.content;
                appendMessage(m.role === 'assistant' ? 'bot' : 'user', displayText, idx, m.attachments);
            });
        }

        updateUIState();
        if (activeChatTitleDisp) activeChatTitleDisp.textContent = chat.title || "New Chat";
    }

    function updateUIState() {
        // Token visuals and locking removed as requested
    }

    function disableInput(unlockTimeMs) {
        // Locked input logic removed
    }

    function enableInput() {
        if (lockTimer) clearInterval(lockTimer);
        chatInput.disabled = false;
        chatInput.placeholder = "Ask anything";
        if (chatInput.value.trim() !== '') sendBtn.disabled = false;
    }

    async function saveChatState(chat) {
        await fetch('/api/chats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: chat.id,
                title: chat.title,
                messages: chat.messages,
                total_tokens: chat.total_tokens,
                token_limit: chat.token_limit,
                locked_until: chat.locked_until,
                project_id: chat.project_id
            })
        });
    }

    window.aiMaxTokens = 4000;
    window.aiTemperature = 0.7;

    newChatBtn.addEventListener("click", startNewChat);
    newProjectBtn.addEventListener("click", createProject);
    attachBtn.addEventListener("click", () => fileInput.click());
    websearchBtn.addEventListener("click", performWebSearch);
    clearAttachmentsBtn.addEventListener("click", clearAllAttachments);
    clearSearchBtn.addEventListener("click", clearWebSearch);
    fileInput.addEventListener("change", handleFileSelect);

    chatInput.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value.trim() !== '') {
            sendBtn.disabled = false;
            sendBtn.classList.add("active");
        } else {
            sendBtn.disabled = true;
            sendBtn.classList.remove("active");
        }
    });

    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!sendBtn.disabled) sendBtn.click();
        }
    });

    sendBtn.addEventListener("click", async () => {
        const message = chatInput.value.trim();
        if (!message && attachedFiles.length === 0 && webSearchData.length === 0) return;

        const chat = getActiveChat();
        if (chat.messages.length === 0) {
            chat.title = message.substring(0, 30) + "...";
            renderSidebar();
        }

        // --- AUTOMATIC WEB SEARCH LOGIC ---
        let autoSearchData = [...webSearchData];
        let searchingIndicatorId = null;

        if (window.webSearchEnabled && message && webSearchData.length === 0) {
            searchingIndicatorId = appendSystemMessage('Searching the web for: ' + message + '...');
            try {
                const searchResp = await fetch('/api/websearch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: message })
                });
                if (searchResp.ok) {
                    const searchData = await searchResp.json();
                    if (searchData.results && searchData.results.length > 0) {
                        autoSearchData = searchData.results;
                        updateSystemMessage(searchingIndicatorId, 'Found ' + autoSearchData.length + ' search results. Generating response...');
                    } else {
                        updateSystemMessage(searchingIndicatorId, 'No search results found. Proceeding with general knowledge...');
                    }
                }
            } catch (e) {
                console.error("Auto search failed", e);
                updateSystemMessage(searchingIndicatorId, 'Search failed. Proceeding with general knowledge...');
            }
        }
        // ----------------------------------

        // Build enhanced message with attachments and web search
        let enhancedMessage = message;
        // Snapshot attachments BEFORE clearing
        const attachmentSnapshot = attachedFiles.map(file => ({
            filename: file.filename,
            name: file.filename,
            size: file.size,
            file_type: file.file_type,
            type: file.file_type,
            content: file.content,
            is_image: file.is_image
        }));

        // Add file information to message sent to AI
        if (attachedFiles.length > 0) {
            const fileText = attachedFiles.map(file => {
                if (file.is_image) {
                    return `[IMAGE: ${file.filename}]\nData: ${file.content}`;
                } else {
                    const content = file.content.length > 2000 ? file.content.substring(0, 2000) + '...' : file.content;
                    return `[FILE: ${file.filename}]\n${content}`;
                }
            }).join('\n\n');

            enhancedMessage = message + '\n\n' + fileText;
        }

        // Add web search results to message
        if (autoSearchData.length > 0) {
            const searchText = autoSearchData.map(result =>
                `[WEB SEARCH: ${result.title}]\n${result.snippet}\nSource: ${result.url}`
            ).join('\n\n');

            enhancedMessage = enhancedMessage + '\n\n' + searchText;
        }

        // Store the user-visible text + attachment snapshot in the message
        chat.messages.push({
            role: "user",
            content: enhancedMessage,
            display_text: message,
            attachments: attachmentSnapshot,
            web_search_results: autoSearchData
        });

        // Render user bubble with original text + snapshotted attachments
        appendMessage('user', message, undefined, attachmentSnapshot);
        chatInput.value = '';
        chatInput.style.height = 'auto';
        sendBtn.disabled = true;
        sendBtn.classList.remove("active");

        // Clear attachments and web search after sending
        clearAllAttachments();
        clearWebSearch();

        // Disable temporary mode after first message (as it's now a persistent session)
        // or rather, keep the theme but remove the toggle
        const tempTeaser = document.getElementById("temp-chat-toggle-initial");
        if (tempTeaser) tempTeaser.remove();

        const typingId = appendTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chat_id: chat.id,
                    messages: chat.messages,
                    title: chat.title,
                    project_id: chat.project_id || null,
                    is_temporary: window.temporaryChatEnabled || false,
                    max_tokens: window.aiMaxTokens || 4000,
                    temperature: window.aiTemperature || 0.7
                })
            });

            const data = await response.json();
            const typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.remove();

            // Remove searching indicator if it exists
            if (searchingIndicatorId) {
                const sEl = document.getElementById(searchingIndicatorId);
                if (sEl) sEl.remove();
            }

            if (response.ok) {
                chat.messages.push({ role: "assistant", content: data.message });
                chat.total_tokens = data.total_tokens;
                chat.token_limit = data.token_limit || chat.token_limit;
                chat.locked_until = data.locked_until || chat.locked_until;

                appendMessage('bot', data.message);
                renderSidebar();
            } else {
                chat.messages.pop();
                appendMessage('bot', 'Error: ' + (data.detail || 'Request failed.'));
            }
            updateUIState();
        } catch (error) {
            chat.messages.pop();
            const typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.remove();
            if (searchingIndicatorId) {
                const sEl = document.getElementById(searchingIndicatorId);
                if (sEl) sEl.remove();
            }
            appendMessage('bot', 'Network error. Please try again.');
        }
    });

    function appendMessage(sender, text, msgIndex, messageAttachments) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-message ${sender}`;

        // Wire up copy button
        if (sender === 'bot') {
            const rawHtml = marked.parse(text);
            contentHtml = typeof DOMPurify !== 'undefined'
                ? DOMPurify.sanitize(rawHtml, { ADD_ATTR: ['target'] })
                : rawHtml;
        } else {
            // For user messages, render plain text + attachments from snapshot
            contentHtml = processUserMessageContent(text, messageAttachments || []);
        }

        let actionsHtml = '';
        if (sender === 'bot') {
            actionsHtml = `<div class="msg-actions">
                <button class="msg-action-btn copy-btn" title="Copy response">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                    <span>Copy</span>
                </button>
            </div>`;
        } else {
            actionsHtml = `<div class="msg-actions">
                <button class="msg-action-btn edit-btn" title="Edit & resend">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                    <span>Edit</span>
                </button>
            </div>`;
        }

        msgDiv.innerHTML = `<div class="message-inner markdown-body">${contentHtml}</div>${actionsHtml}`;
        msgDiv.dataset.rawText = text;
        if (msgIndex !== undefined) msgDiv.dataset.msgIndex = msgIndex;

        if (sender === 'bot' && typeof hljs !== 'undefined') {
            msgDiv.querySelectorAll('pre code').forEach((block) => hljs.highlightElement(block));
        }

        // Remove welcome screen when first message appears
        const initialContainer = document.querySelector(".initial-message-container");
        if (initialContainer) initialContainer.remove();
        const copyBtn = msgDiv.querySelector('.copy-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(text).then(() => {
                    const label = copyBtn.querySelector('span');
                    label.textContent = 'Copied!';
                    setTimeout(() => { label.textContent = 'Copy'; }, 2000);
                });
            });
        }

        // Wire up edit button
        const editBtn = msgDiv.querySelector('.edit-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => {
                const idx = parseInt(msgDiv.dataset.msgIndex);
                const chat = getActiveChat();
                if (!chat || isNaN(idx)) return;

                // Put the original text into the input
                chatInput.value = text;
                chatInput.dispatchEvent(new Event('input'));
                chatInput.focus();

                // Remove this message and everything after it
                chat.messages = chat.messages.slice(0, idx);
                renderCurrentChat();
            });
        }

        chatContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendTypingIndicator() {
        const typingId = 'typing-' + Date.now();
        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-message bot`;
        msgDiv.id = typingId;
        msgDiv.innerHTML = `<div class="message-inner"><div class="typing-indicator"><div class="dots-flow">...</div></div></div>`;
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
        return typingId;
    }

    function scrollToBottom() {
        document.querySelector(".chat-viewport").scrollTop = document.querySelector(".chat-viewport").scrollHeight;
    }

    function appendSystemMessage(text) {
        const id = 'system-' + Date.now();
        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-message system`;
        msgDiv.id = id;
        msgDiv.innerHTML = `<div class="message-inner system-text" style="font-size: 13px; color: var(--text-muted); font-style: italic; opacity: 0.8;">${escapeHtml(text)}</div>`;
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
        return id;
    }

    function updateSystemMessage(id, text) {
        const el = document.getElementById(id);
        if (el) {
            const inner = el.querySelector('.system-text');
            if (inner) inner.textContent = text;
        }
    }

    function escapeHtml(unsafe) {
        if (!unsafe) return "";
        return unsafe.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    // Modal behavior
    const settingsModal = document.getElementById("settings-modal");
    const closeBtnX = document.getElementById("close-modal-x");
    const saveSettingsBtn = document.getElementById("save-settings-btn");
    const settingsMsg = document.getElementById("settings-msg");

    if (profileBtn) {
        profileBtn.addEventListener("click", () => settingsModal.classList.add("active"));
        closeBtnX.addEventListener("click", () => settingsModal.classList.remove("active"));

        saveSettingsBtn.addEventListener("click", async () => {
            const dn = document.getElementById("setting-display-name").value;
            const pwd = document.getElementById("setting-password").value;
            saveSettingsBtn.disabled = true;
            settingsMsg.textContent = "Saving...";

            try {
                const res = await fetch('/api/user/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ display_name: dn, password: pwd || null })
                });
                const data = await res.json();
                if (res.ok) {
                    settingsMsg.style.color = "#10b981";
                    settingsMsg.textContent = "Updated successfully!";
                    setTimeout(() => location.reload(), 1000);
                } else {
                    settingsMsg.style.color = "#ef4444";
                    settingsMsg.textContent = data.detail || "Error";
                }
            } catch (e) { settingsMsg.textContent = "Error"; }
            saveSettingsBtn.disabled = false;
        });
    }

    // Project Management Functions
    function toggleProject(projectId) {
        const projectDiv = document.querySelector(`[data-project-id="${projectId}"]`);
        if (projectDiv) {
            projectDiv.classList.toggle('expanded');
        }
    }

    async function createProject() {
        const name = prompt('Enter project name:');
        if (!name || !name.trim()) return;

        const description = prompt('Enter project description (optional):');

        try {
            const resp = await fetch('/api/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name.trim(),
                    description: description || null
                })
            });

            if (resp.ok) {
                const newProject = await resp.json();
                projects.push(newProject);
                renderProjects();
            } else {
                const data = await resp.json();
                alert('Error creating project: ' + (data.detail || 'Unknown error'));
            }
        } catch (e) {
            console.error('Failed to create project', e);
            alert('Failed to create project. Please try again.');
        }
    }

    async function deleteProject(projectId) {
        if (!confirm('Are you sure you want to delete this project? Chats will be moved to Recent Chats.')) {
            return;
        }

        try {
            const resp = await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
            if (resp.ok) {
                projects = projects.filter(p => p.id !== projectId);
                // Move chats from this project to recent chats
                chats.forEach(chat => {
                    if (chat.project_id === projectId) {
                        chat.project_id = null;
                    }
                });

                if (currentProjectId === projectId) {
                    currentProjectId = null;
                }

                renderProjects();
                renderSidebar();
            } else {
                const data = await resp.json();
                alert('Error deleting project: ' + (data.detail || 'Unknown error'));
            }
        } catch (e) {
            console.error('Failed to delete project', e);
            alert('Failed to delete project. Please try again.');
        }
    }

    // File Upload Functions
    async function handleFileSelect(event) {
        const files = Array.from(event.target.files);

        for (const file of files) {
            if (file.size > 10 * 1024 * 1024) { // 10MB limit
                alert(`File ${file.name} is too large. Maximum size is 10MB.`);
                continue;
            }

            try {
                // Upload file to server
                const formData = new FormData();
                formData.append('file', file);

                console.log(`Uploading file: ${file.name}, size: ${file.size}, type: ${file.type}`);

                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData,
                    credentials: 'include'
                });

                console.log(`Upload response status: ${response.status}`);

                if (!response.ok) {
                    try {
                        const error = await response.json();
                        const errorMessage = error.detail || error.message || 'Unknown error';
                        alert(`Upload failed: ${errorMessage}`);
                    } catch (parseError) {
                        alert(`Upload failed: Server error (${response.status})`);
                    }
                    continue;
                }

                const fileData = await response.json();

                // Add client-side ID for tracking
                fileData.id = Date.now() + Math.random().toString(36);
                attachedFiles.push(fileData);
                renderAttachments();

            } catch (error) {
                console.error('File upload error:', error);
                const errorMessage = error.message || 'Network error occurred';
                alert(`Upload failed for ${file.name}: ${errorMessage}. Please try again.`);
            }
        }

        event.target.value = ''; // Clear input
    }

    function renderAttachments() {
        if (attachedFiles.length === 0) {
            fileAttachments.style.display = 'none';
            return;
        }

        fileAttachments.style.display = 'block';
        attachmentsList.innerHTML = '';
        attachmentsList.className = 'attachments-grid'; // Use grid for better layout

        attachedFiles.forEach(file => {
            const item = document.createElement('div');
            item.className = 'attachment-card';

            if (file.is_image) {
                const imgPreview = document.createElement('div');
                imgPreview.className = 'attachment-image-preview';
                imgPreview.style.backgroundImage = `url(${file.content})`;
                item.appendChild(imgPreview);
            } else {
                const icon = document.createElement('div');
                icon.className = 'attachment-icon-large';
                icon.innerHTML = getFileIcon(file.file_type || file.type);
                item.appendChild(icon);
            }

            const info = document.createElement('div');
            info.className = 'attachment-info';

            const name = document.createElement('div');
            name.className = 'attachment-name-small';
            name.textContent = file.filename || file.name;

            const size = document.createElement('div');
            size.className = 'attachment-size-small';
            size.textContent = formatFileSize(file.size);

            info.appendChild(name);
            info.appendChild(size);
            item.appendChild(info);

            const removeBtn = document.createElement('button');
            removeBtn.className = 'remove-attachment-overlay';
            removeBtn.innerHTML = '×';
            removeBtn.title = "Remove file";
            removeBtn.onclick = (e) => {
                e.stopPropagation();
                removeAttachment(file.id);
            };
            item.appendChild(removeBtn);

            attachmentsList.appendChild(item);
        });
    }

    function removeAttachment(fileId) {
        attachedFiles = attachedFiles.filter(f => f.id !== fileId);
        renderAttachments();
    }

    function clearAllAttachments() {
        attachedFiles = [];
        fileAttachments.style.display = 'none';
        attachmentsList.innerHTML = '';
    }

    function getFileIcon(fileType) {
        if (fileType.startsWith('image/')) {
            return '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M21 19V5c0-1.1-.9-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6V8.5z"/></svg>';
        } else if (fileType.includes('pdf')) {
            return '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-1 8l-3 3v2h3v-2l3-3h-3z"/></svg>';
        } else if (fileType.includes('text')) {
            return '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-2 8l-3 3v2h3v-2l3-3h-3z"/></svg>';
        } else {
            return '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M10 4H4c-1.11 0-2 .89-2 2v12c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-1 8l-3 3v2h3v-2l3-3h-3z"/></svg>';
        }
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Web Search Functions
    async function performWebSearch() {
        const query = prompt('Enter search query:');
        if (!query || !query.trim()) return;

        try {
            const response = await fetch('/api/websearch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query.trim() })
            });

            if (response.ok) {
                const data = await response.json();
                webSearchData = data.results || [];
                renderWebSearchResults();
            } else {
                alert('Web search failed. Please try again.');
            }
        } catch (error) {
            console.error('Web search error:', error);
            alert('Web search failed. Please try again.');
        }
    }

    function renderWebSearchResults() {
        if (webSearchData.length === 0) {
            webSearchResults.style.display = 'none';
            return;
        }

        webSearchResults.style.display = 'block';
        searchResultsList.innerHTML = '';

        webSearchData.forEach(result => {
            const item = document.createElement('div');
            item.className = 'search-result-item';
            item.onclick = () => {
                chatInput.value += `\n\nBased on web search: ${result.title}\n${result.snippet}\nSource: ${result.url}\n\n`;
                chatInput.dispatchEvent(new Event('input'));
            };

            const title = document.createElement('div');
            title.className = 'search-result-title';
            title.textContent = result.title;

            const url = document.createElement('div');
            url.className = 'search-result-url';
            url.textContent = new URL(result.url).hostname;

            const snippet = document.createElement('div');
            snippet.className = 'search-result-snippet';
            snippet.textContent = result.snippet;

            item.appendChild(title);
            item.appendChild(url);
            item.appendChild(snippet);
            searchResultsList.appendChild(item);
        });
    }

    function clearWebSearch() {
        webSearchData = [];
        webSearchResults.style.display = 'none';
        searchResultsList.innerHTML = '';
    }

    function processUserMessageContent(text, attachments) {
        attachments = attachments || [];
        let processedHtml = '';

        // Render image attachments FIRST (requested preview)
        const images = attachments.filter(f => f.is_image);
        if (images.length > 0) {
            processedHtml += '<div class="message-images-grid">';
            images.forEach(file => {
                let imageUrl = file.content;
                if (imageUrl && !imageUrl.startsWith('data:')) {
                    const mimeType = file.file_type || file.type || 'image/png';
                    imageUrl = `data:${mimeType};base64,${imageUrl}`;
                }
                if (imageUrl) {
                    processedHtml += `<div class="message-image-item">
                        <img src="${imageUrl}" alt="${escapeHtml(file.filename || file.name || 'image')}" class="clickable-image" onclick="window.open('${imageUrl}', '_blank')">
                    </div>`;
                }
            });
            processedHtml += '</div>';
        }

        // Render plain text
        if (text && text.trim()) {
            processedHtml += `<div class="user-text">${escapeHtml(text).replace(/\n/g, '<br>')}</div>`;
        }

        // Render non-image file attachments
        const files = attachments.filter(f => !f.is_image);
        if (files.length > 0) {
            processedHtml += '<div class="message-files-list">';
            files.forEach(file => {
                const preview = file.content ? (file.content.length > 200 ? file.content.substring(0, 200) + '...' : file.content) : 'Binary file';
                processedHtml += `<div class="attached-file">
                    <div class="file-header">📄 ${escapeHtml(file.filename || file.name || 'file')}</div>
                    <div class="file-preview">${escapeHtml(preview)}</div>
                </div>`;
            });
            processedHtml += '</div>';
        }

        return processedHtml || '<div class="user-text"><i>Image shared</i></div>';
    }
});
