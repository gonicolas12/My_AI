/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — VS Code Webview                       */
/* All wire-protocol/E2EE happens in the extension; the */
/* webview just renders messages and posts user intent. */
/* ═══════════════════════════════════════════════════ */

(function () {
  'use strict';
  const vscode = acquireVsCodeApi();

  // ── DOM ──────────────────────────────────────────────
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const connBanner = document.getElementById('connBanner');
  const connectScreen = document.getElementById('connectScreen');
  const connectBtn = document.getElementById('connectBtn');
  const messagesEl = document.getElementById('messages');
  const inputArea = document.getElementById('inputArea');
  const welcomeEl = document.getElementById('welcome');
  const inputEl = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const attachBtn = document.getElementById('attachBtn');
  const attachmentsEl = document.getElementById('attachments');
  const clearBtn = document.getElementById('clearBtn');
  const reconnectBtn = document.getElementById('reconnectBtn');
  const attachToggleBtn = document.getElementById('attachToggleBtn');
  const attachToggleLabel = document.getElementById('attachToggleLabel');

  // ── STATE ────────────────────────────────────────────
  let isConnected = false;
  let isWaiting = false;
  let typingEl = null;
  let lastSentMessageId = null;
  const renderedMessageIds = new Set();
  let pendingAttachments = [];
  let attachmentCounter = 0;
  let streamingMessageId = null;
  let streamingMessageEl = null;
  let userPinnedToBottom = true;
  let autoAttachActive = false;
  // Map call_id → DOM node for the tool card. Used by tool-event handlers
  // to update the card's status and output as the agentic loop progresses.
  const toolCardEls = new Map();

  // Localized strings injected by the extension on startup. The webview
  // renders nothing visible until applyStrings() runs, so the user never
  // sees raw English placeholders if their VS Code is in another language.
  let STR = {};
  function t(key) { return (STR && STR[key]) || key; }

  function applyStrings(strings) {
    STR = strings || {};
    // Static UI elements that never change after init.
    document.getElementById('connBanner').textContent = t('webview.banner.connectionLost');
    document.getElementById('connectTitle').textContent = t('webview.connect.title');
    document.getElementById('connectDescription').textContent = t('webview.connect.description');
    document.getElementById('connectBtn').textContent = t('webview.connect.button');
    document.getElementById('connectHint').textContent = t('webview.connect.hint');
    document.getElementById('welcomeTitle').textContent = t('webview.welcome.title');
    document.getElementById('welcomeText').textContent = t('webview.welcome.text');
    document.getElementById('clearBtn').textContent = t('webview.header.clear');
    document.getElementById('clearBtn').title = t('webview.header.clearTooltip');
    document.getElementById('reconnectBtn').textContent = t('webview.header.reconnect');
    document.getElementById('reconnectBtn').title = t('webview.header.reconnectTooltip');
    document.getElementById('attachToggleBtn').title = t('webview.header.autoAttachTooltip');
    document.getElementById('attachBtn').title = t('webview.input.attachTooltip');
    inputEl.placeholder = t('webview.input.placeholder');
    renderAutoAttachToggle();
  }

  // ── EVENT WIRING ─────────────────────────────────────
  connectBtn.addEventListener('click', () => {
    vscode.postMessage({ type: 'connect-request' });
  });

  sendBtn.addEventListener('click', sendMessage);
  attachBtn.addEventListener('click', () => vscode.postMessage({ type: 'pick-file' }));
  clearBtn.addEventListener('click', clearChat);
  reconnectBtn.addEventListener('click', () =>
    vscode.postMessage({ type: 'connect-request' }),
  );

  attachToggleBtn.addEventListener('click', () => {
    autoAttachActive = !autoAttachActive;
    renderAutoAttachToggle();
    vscode.postMessage({ type: 'set-auto-attach', value: autoAttachActive });
  });

  inputEl.addEventListener('input', () => {
    autoResize();
    updateSendButton();
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  messagesEl.addEventListener('scroll', () => {
    const gap = messagesEl.scrollHeight - (messagesEl.scrollTop + messagesEl.clientHeight);
    userPinnedToBottom = gap < 80;
  }, { passive: true });

  // Capture clicks on injected code-action buttons (event delegation).
  messagesEl.addEventListener('click', (e) => {
    const target = e.target;
    if (!(target instanceof HTMLElement)) return;
    if (target.classList.contains('code-action')) {
      const action = target.dataset.action;
      const wrapper = target.closest('.code-block-wrapper');
      const pre = wrapper && wrapper.querySelector('pre code');
      if (!pre) return;
      const code = pre.textContent || '';
      if (action === 'insert') {
        vscode.postMessage({ type: 'insert-at-cursor', code });
        flashAction(target, t('webview.code.inserted'));
      } else if (action === 'copy') {
        vscode.postMessage({ type: 'copy-to-clipboard', text: code });
        flashAction(target, t('webview.code.copied'));
      }
    }
  });

  function flashAction(btn, label) {
    const orig = btn.textContent;
    btn.textContent = label;
    setTimeout(() => { btn.textContent = orig; }, 1200);
  }

  // ── EXTENSION → WEBVIEW MESSAGES ─────────────────────
  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (!msg || typeof msg !== 'object') return;
    switch (msg.type) {
      case 'init-strings':
        applyStrings(msg.strings);
        break;
      case 'state':
        applyState(msg.state, msg.hasCredentials);
        break;
      case 'history':
        applyHistory(msg.items || []);
        break;
      case 'relay-message':
        applyRelayMessage(msg.payload);
        break;
      case 'attachment-uploading':
        addAttachmentChip(msg.localId, msg.name, msg.isImage, 'uploading');
        break;
      case 'attachment-ready':
        markAttachmentReady(msg.localId, msg.fileId, msg.filename, msg.isImage);
        break;
      case 'attachment-error':
        markAttachmentError(msg.localId, msg.error);
        break;
      case 'cleared-attachments':
        pendingAttachments = [];
        renderAttachments();
        updateSendButton();
        break;
      case 'auto-attach-state':
        autoAttachActive = !!msg.value;
        renderAutoAttachToggle();
        break;
      case 'tool-event':
        applyToolEvent(msg.event);
        break;
    }
  });

  // ── TOOL CARDS (agentic mode) ────────────────────────
  function applyToolEvent(event) {
    if (!event || !event.callId) return;
    if (welcomeEl) welcomeEl.style.display = 'none';
    let card = toolCardEls.get(event.callId);
    if (!card) {
      card = createToolCard(event);
      // Insert above the streaming bubble so cards render inline with
      // the assistant's response.
      if (streamingMessageEl && streamingMessageEl.isConnected) {
        messagesEl.insertBefore(card, streamingMessageEl);
      } else {
        messagesEl.appendChild(card);
      }
      toolCardEls.set(event.callId, card);
      // Drop the typing indicator: the agent is clearly working.
      removeTyping();
    }
    updateToolCard(card, event);
    scrollToBottomStream();
  }

  function createToolCard(event) {
    const card = document.createElement('div');
    card.className = 'tool-card';
    card.dataset.callId = event.callId;
    card.dataset.tool = event.toolName || 'tool';
    card.innerHTML =
      '<div class="tool-card-header" role="button" tabindex="0">' +
        '<span class="tool-card-icon"></span>' +
        '<span class="tool-card-title"></span>' +
        '<span class="tool-card-status"></span>' +
        '<span class="tool-card-chev">▾</span>' +
      '</div>' +
      '<div class="tool-card-body">' +
        '<div class="tool-card-section tool-card-input">' +
          '<div class="tool-card-section-label">Input</div>' +
          '<pre class="tool-card-pre"></pre>' +
        '</div>' +
        '<div class="tool-card-section tool-card-output" style="display:none">' +
          '<div class="tool-card-section-label">Output</div>' +
          '<pre class="tool-card-pre"></pre>' +
        '</div>' +
      '</div>';

    const header = card.querySelector('.tool-card-header');
    const body = card.querySelector('.tool-card-body');
    body.style.display = 'none';
    header.addEventListener('click', () => {
      const open = body.style.display !== 'none';
      body.style.display = open ? 'none' : 'block';
      card.classList.toggle('open', !open);
    });
    header.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        header.click();
      }
    });

    return card;
  }

  function updateToolCard(card, event) {
    const titleEl = card.querySelector('.tool-card-title');
    const iconEl = card.querySelector('.tool-card-icon');
    const statusEl = card.querySelector('.tool-card-status');
    const inputPre = card.querySelector('.tool-card-input .tool-card-pre');
    const outputSection = card.querySelector('.tool-card-output');
    const outputPre = card.querySelector('.tool-card-output .tool-card-pre');

    titleEl.textContent = describeToolTitle(event.toolName, event.input);

    let icon = '';
    let statusLabel = '';
    let cls = '';
    switch (event.kind) {
      case 'requested':
      case 'running':
        icon = '⏳';
        statusLabel = 'en cours';
        cls = 'running';
        break;
      case 'awaiting-approval':
        icon = '🔒';
        statusLabel = 'attente d\'approbation';
        cls = 'awaiting';
        break;
      case 'denied':
        icon = '🚫';
        statusLabel = 'refusé';
        cls = 'denied';
        break;
      case 'completed':
        icon = '✓';
        statusLabel = 'OK';
        cls = 'ok';
        break;
      case 'failed':
        icon = '⚠️';
        statusLabel = 'erreur';
        cls = 'error';
        break;
      default:
        icon = '·';
    }
    iconEl.textContent = icon;
    statusEl.textContent = statusLabel;
    card.classList.remove('running', 'awaiting', 'denied', 'ok', 'error');
    if (cls) card.classList.add(cls);

    inputPre.textContent = formatToolInput(event.input);

    if (event.result || event.error) {
      const text = event.result ? event.result.content : (event.error || '');
      outputPre.textContent = text || '(empty)';
      outputSection.style.display = 'block';
    }
  }

  function describeToolTitle(name, input) {
    name = name || 'tool';
    if (!input || typeof input !== 'object') return name;
    if (typeof input.path === 'string' && input.path) {
      return name + '(' + input.path + ')';
    }
    if (typeof input.command === 'string' && input.command) {
      const c = input.command;
      return name + ': ' + (c.length > 60 ? c.slice(0, 60) + '…' : c);
    }
    if (typeof input.pattern === 'string' && input.pattern) {
      return name + ' /' + input.pattern + '/';
    }
    return name;
  }

  function formatToolInput(input) {
    if (!input || typeof input !== 'object') return '{}';
    try {
      return JSON.stringify(input, null, 2);
    } catch (_e) {
      return String(input);
    }
  }

  function applyState(state, hasCredentials) {
    const kind = state && state.kind;
    if (kind === 'connected') {
      isConnected = true;
      setStatus('connected', t('webview.status.connected'));
      connBanner.classList.remove('visible');
      showConnectedUI();
    } else if (kind === 'connecting') {
      isConnected = false;
      setStatus('connecting', t('webview.status.connecting'));
      showConnectedUI();
    } else if (kind === 'reconnecting') {
      isConnected = false;
      setStatus('connecting', t('webview.status.reconnecting'));
      connBanner.classList.add('visible');
      showConnectedUI();
    } else {
      // idle | disconnected
      isConnected = false;
      const reason = (state && state.reason)
        || (hasCredentials ? t('webview.status.disconnected') : t('webview.status.notConnected'));
      setStatus('offline', reason);
      if (hasCredentials) {
        connBanner.classList.add('visible');
        showConnectedUI();
      } else {
        showConnectScreen();
      }
    }
    updateSendButton();
  }

  function showConnectScreen() {
    connectScreen.style.display = 'flex';
    messagesEl.style.display = 'none';
    inputArea.style.display = 'none';
  }

  function showConnectedUI() {
    connectScreen.style.display = 'none';
    messagesEl.style.display = 'block';
    inputArea.style.display = 'block';
  }

  function applyHistory(items) {
    if (!items.length) return;
    if (welcomeEl) welcomeEl.style.display = 'none';
    items.forEach((m) => {
      if (!m || typeof m.text !== 'string') return;
      const mid = m.message_id || '';
      const key = (m.is_user ? 'user:' : 'ai:') + mid;
      if (mid && renderedMessageIds.has(key)) return;
      if (mid) renderedMessageIds.add(key);
      addMessage(m.text, !!m.is_user, m.timestamp);
    });
    const last = items[items.length - 1];
    if (last && last.is_user && last.message_id) {
      lastSentMessageId = last.message_id;
      isWaiting = true;
      showTyping();
      updateSendButton();
    }
  }

  function applyRelayMessage(data) {
    if (!data || typeof data !== 'object') return;

    if (data.type === 'response') {
      const mid = data.message_id || '';
      if (mid && renderedMessageIds.has('ai:' + mid)) {
        if (streamingMessageId === mid) finalizeStreaming(mid, null, null);
        return;
      }
      if (mid) renderedMessageIds.add('ai:' + mid);
      removeTyping();
      isWaiting = false;
      if (mid && mid === lastSentMessageId) lastSentMessageId = null;
      finalizeStreaming(mid, data.message, data.timestamp);
      updateSendButton();
    } else if (data.type === 'chunk') {
      const cmid = data.message_id || '';
      if (!cmid) return;
      if (renderedMessageIds.has('ai:' + cmid)) return;
      removeTyping();
      updateStreamingBubble(cmid, data.text || '');
    } else if (data.type === 'ack') {
      if (data.message_id) {
        lastSentMessageId = data.message_id;
        renderedMessageIds.add('user:' + data.message_id);
      }
    }
  }

  // ── INPUT/SEND ───────────────────────────────────────
  function sendMessage() {
    const text = inputEl.value.trim();
    const ready = pendingAttachments.filter((a) => a.status === 'ready');
    const hasAttachments = ready.length > 0;
    if ((!text && !hasAttachments) || !isConnected || isWaiting) return;

    const uploading = pendingAttachments.some((a) => a.status === 'uploading');
    if (uploading) return;

    if (welcomeEl) welcomeEl.style.display = 'none';

    let displayText = text;
    if (hasAttachments) {
      const lines = ready.map((a) => (a.isImage ? '🖼️ ' : '📎 ') + a.name).join('\n');
      displayText = displayText ? text + '\n' + lines : lines;
    }

    userPinnedToBottom = true;
    addMessage(displayText, true);

    vscode.postMessage({
      type: 'send-chat',
      text,
      fileIds: ready.map((a) => a.fileId),
    });

    isWaiting = true;
    showTyping();

    inputEl.value = '';
    autoResize();
    pendingAttachments = [];
    renderAttachments();
    updateSendButton();
    scrollToBottom();
  }

  function updateSendButton() {
    const hasText = !!inputEl.value.trim();
    const hasReady = pendingAttachments.some((a) => a.status === 'ready');
    const uploading = pendingAttachments.some((a) => a.status === 'uploading');
    sendBtn.disabled = !isConnected || isWaiting || uploading || (!hasText && !hasReady);
  }

  function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + 'px';
  }

  // ── ATTACHMENT CHIPS ─────────────────────────────────
  function addAttachmentChip(localId, name, isImage, status) {
    pendingAttachments.push({ localId, fileId: null, name, isImage: !!isImage, status, error: null });
    renderAttachments();
    updateSendButton();
  }

  function markAttachmentReady(localId, fileId, filename, isImage) {
    const a = pendingAttachments.find((x) => x.localId === localId);
    if (!a) return;
    a.fileId = fileId;
    a.name = filename || a.name;
    a.isImage = !!isImage;
    a.status = 'ready';
    renderAttachments();
    updateSendButton();
  }

  function markAttachmentError(localId, error) {
    const a = pendingAttachments.find((x) => x.localId === localId);
    if (!a) return;
    a.status = 'error';
    a.error = error || 'Upload failed';
    renderAttachments();
    updateSendButton();
  }

  function removeAttachment(localId) {
    pendingAttachments = pendingAttachments.filter((a) => a.localId !== localId);
    renderAttachments();
    updateSendButton();
    vscode.postMessage({ type: 'remove-attachment', localId });
  }

  function renderAttachments() {
    attachmentsEl.innerHTML = '';
    pendingAttachments.forEach((a) => {
      const chip = document.createElement('div');
      chip.className = 'attachment-chip';
      if (a.status === 'uploading') chip.classList.add('uploading');
      if (a.status === 'error') chip.classList.add('error');

      const icon = document.createElement('span');
      icon.className = 'chip-icon';
      icon.textContent = a.status === 'uploading' ? '⏳'
                       : a.status === 'error' ? '⚠️'
                       : (a.isImage ? '🖼️' : '📎');
      chip.appendChild(icon);

      const name = document.createElement('span');
      name.className = 'chip-name';
      name.textContent = a.status === 'error'
        ? (a.name + ' · ' + (a.error || t('webview.attachment.error')))
        : a.name;
      chip.appendChild(name);

      const rm = document.createElement('button');
      rm.className = 'chip-remove';
      rm.type = 'button';
      rm.textContent = '×';
      rm.setAttribute('aria-label', t('webview.attachment.remove'));
      rm.onclick = () => removeAttachment(a.localId);
      chip.appendChild(rm);

      attachmentsEl.appendChild(chip);
    });
  }

  function renderAutoAttachToggle() {
    attachToggleLabel.textContent = autoAttachActive
      ? t('webview.header.autoAttachOn')
      : t('webview.header.autoAttachOff');
    attachToggleBtn.classList.toggle('active', autoAttachActive);
  }

  // ── MESSAGE RENDERING ────────────────────────────────
  function addMessage(text, isUser, timestamp) {
    if (welcomeEl) welcomeEl.style.display = 'none';
    const msg = document.createElement('div');
    msg.className = 'message ' + (isUser ? 'user' : 'ai');
    const time = formatTime(timestamp ? new Date(timestamp) : new Date());
    if (isUser) {
      msg.innerHTML = '<div class="bubble">' + escapeHtml(text) +
        '<span class="time">' + time + '</span></div>';
    } else {
      msg.innerHTML =
        '<div class="ai-icon">&#x1F916;</div>' +
        '<div class="bubble">' + renderMarkdown(text) +
        '<span class="time">' + time + '</span></div>';
    }
    messagesEl.appendChild(msg);
    enhanceCodeBlocks(msg);
    scrollToBottom();
  }

  function balanceMarkdownForStreaming(text) {
    if (!text) return '';
    const fenceMatches = text.match(/(^|\n)```/g);
    const count = fenceMatches ? fenceMatches.length : 0;
    if (count % 2 === 1) text = text + '\n```';
    return text;
  }

  function ensureStreamingBubble(mid) {
    if (streamingMessageId === mid && streamingMessageEl && streamingMessageEl.isConnected) {
      return streamingMessageEl;
    }
    if (welcomeEl) welcomeEl.style.display = 'none';
    streamingMessageId = mid;
    const msg = document.createElement('div');
    msg.className = 'message ai streaming';
    msg.innerHTML =
      '<div class="ai-icon">&#x1F916;</div>' +
      '<div class="bubble">' +
        '<div class="stream-content"></div>' +
        '<span class="stream-cursor"></span>' +
      '</div>';
    messagesEl.appendChild(msg);
    streamingMessageEl = msg;
    return msg;
  }

  function updateStreamingBubble(mid, text) {
    const bubble = ensureStreamingBubble(mid);
    const content = bubble.querySelector('.stream-content');
    if (content) {
      content.innerHTML = renderMarkdown(balanceMarkdownForStreaming(text));
      enhanceCodeBlocks(content);
    }
    scrollToBottomStream();
  }

  function finalizeStreaming(mid, finalText, timestamp) {
    if (streamingMessageId !== mid || !streamingMessageEl) {
      if (finalText !== null && finalText !== undefined) {
        addMessage(finalText, false, timestamp);
      }
      return;
    }
    if (finalText === null || finalText === undefined) {
      streamingMessageEl.remove();
    } else {
      const time = formatTime(timestamp ? new Date(timestamp) : new Date());
      streamingMessageEl.classList.remove('streaming');
      streamingMessageEl.innerHTML =
        '<div class="ai-icon">&#x1F916;</div>' +
        '<div class="bubble">' + renderMarkdown(finalText) +
        '<span class="time">' + time + '</span></div>';
      enhanceCodeBlocks(streamingMessageEl);
    }
    streamingMessageEl = null;
    streamingMessageId = null;
    scrollToBottom();
  }

  function showTyping() {
    if (typingEl) return;
    typingEl = document.createElement('div');
    typingEl.className = 'message ai';
    typingEl.id = 'typingIndicator';
    typingEl.innerHTML =
      '<div class="ai-icon">&#x1F916;</div>' +
      '<div class="bubble">' +
        '<div class="typing-indicator">' +
          '<div class="typing-dot"></div>' +
          '<div class="typing-dot"></div>' +
          '<div class="typing-dot"></div>' +
        '</div>' +
      '</div>';
    messagesEl.appendChild(typingEl);
    scrollToBottom();
  }

  function removeTyping() {
    if (typingEl) {
      typingEl.remove();
      typingEl = null;
    }
  }

  function clearChat() {
    Array.from(messagesEl.children).forEach((c) => {
      if (c !== welcomeEl) c.remove();
    });
    if (welcomeEl) welcomeEl.style.display = 'flex';
    renderedMessageIds.clear();
    streamingMessageId = null;
    streamingMessageEl = null;
    toolCardEls.clear();
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  function scrollToBottomStream() {
    if (!userPinnedToBottom) return;
    messagesEl.scrollTop = messagesEl.scrollHeight;
    requestAnimationFrame(() => {
      if (!userPinnedToBottom) return;
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
  }

  // ── CODE BLOCK ACTIONS ───────────────────────────────
  function enhanceCodeBlocks(root) {
    root.querySelectorAll('pre').forEach((pre) => {
      if (pre.parentElement && pre.parentElement.classList.contains('code-block-wrapper')) {
        return;
      }
      const wrapper = document.createElement('div');
      wrapper.className = 'code-block-wrapper';
      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(pre);

      const actions = document.createElement('div');
      actions.className = 'code-actions';

      const copyBtn = document.createElement('button');
      copyBtn.className = 'code-action';
      copyBtn.dataset.action = 'copy';
      copyBtn.textContent = t('webview.code.copy');
      actions.appendChild(copyBtn);

      const insertBtn = document.createElement('button');
      insertBtn.className = 'code-action';
      insertBtn.dataset.action = 'insert';
      insertBtn.textContent = t('webview.code.insert');
      actions.appendChild(insertBtn);

      wrapper.appendChild(actions);
    });
  }

  // ── MARKDOWN (light) ─────────────────────────────────
  function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);

    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_, _lang, code) => {
      return '<pre><code>' + code.trim() + '</code></pre>';
    });

    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    html = html.replace(/^(#{1,6}) (.+)$/gm, (_, hashes, content) => {
      const lvl = hashes.length;
      return '<h' + lvl + '>' + content + '</h' + lvl + '>';
    });

    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>');

    html = html.replace(/((?:^\|[^\n]+\n?)+)/gm, (tableBlock) => {
      const lines = tableBlock.trim().split('\n').filter((l) => l.trim());
      if (lines.length < 2) return tableBlock;
      if (!/^\|[\s:\-|]+\|?$/.test(lines[1].trim())) return tableBlock;
      const parseRow = (line) => line.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
      const headers = parseRow(lines[0]);
      let out = '<table><thead><tr>';
      headers.forEach((h) => { out += '<th>' + h + '</th>'; });
      out += '</tr></thead><tbody>';
      for (let i = 2; i < lines.length; i++) {
        const row = lines[i].trim();
        if (!row) continue;
        const cells = parseRow(row);
        out += '<tr>';
        cells.forEach((c) => { out += '<td>' + c + '</td>'; });
        out += '</tr>';
      }
      out += '</tbody></table>';
      return out;
    });

    html = html.replace(/^\s*(\d+)[\.)]\s+(.+)$/gm, '<oli>$2</oli>');
    html = html.replace(/^\s*[\-\*]\s+(.+)$/gm, '<uli>$1</uli>');

    html = html.replace(/(?:<oli>[\s\S]*?<\/oli>\n?)+/g, (block) => {
      const items = block.replace(/<oli>/g, '<li>').replace(/<\/oli>/g, '</li>');
      return '<ol>' + items + '</ol>';
    });

    html = html.replace(/(?:<uli>[\s\S]*?<\/uli>\n?)+/g, (block) => {
      const items = block.replace(/<uli>/g, '<li>').replace(/<\/uli>/g, '</li>');
      return '<ul>' + items + '</ul>';
    });

    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    html = '<p>' + html + '</p>';

    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>(<pre>)/g, '$1');
    html = html.replace(/(<\/pre>)<\/p>/g, '$1');
    html = html.replace(/<p>(<ul>)/g, '$1');
    html = html.replace(/(<\/ul>)<\/p>/g, '$1');
    html = html.replace(/<p>(<ol>)/g, '$1');
    html = html.replace(/(<\/ol>)<\/p>/g, '$1');
    html = html.replace(/<p>(<h[1-6]>)/g, '$1');
    html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<table>)/g, '$1');
    html = html.replace(/(<\/table>)<\/p>/g, '$1');

    html = html.replace(/(<\/li>)<br>(<li>)/g, '$1$2');
    html = html.replace(/<ul><br>/g, '<ul>');
    html = html.replace(/<br><\/ul>/g, '</ul>');
    html = html.replace(/<ol><br>/g, '<ol>');
    html = html.replace(/<br><\/ol>/g, '</ol>');

    return html;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatTime(date) {
    return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  }

  function setStatus(state, label) {
    statusDot.className = 'status-dot ' + (
      state === 'connected' ? '' :
      state === 'connecting' ? 'connecting' : 'offline'
    );
    statusText.textContent = label;
  }

  // Tell the extension we're ready to receive state/history.
  vscode.postMessage({ type: 'webview-ready' });
})();
