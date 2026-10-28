/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — VS Code Webview                       */
/* All wire-protocol/E2EE happens in the extension; the */
/* webview just renders messages and posts user intent. */
/* Replies are drawn by turn.js and markdown.js, the    */
/* same files as the phone page of the Relay: one       */
/* bubble per reply, its tool calls inside.             */
/* ═══════════════════════════════════════════════════ */

(function () {
  'use strict';
  const vscode = acquireVsCodeApi();

  // Logo de My_AI (le robot de l'appli, de la barre d'activité et du Marketplace)
  const ROBOT_SVG =
    '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">' +
    '<circle cx="7" cy="1.5" r="1"/><rect x="6.6" y="2.4" width="0.8" height="2.8" rx="0.4"/>' +
    '<circle cx="17" cy="1.5" r="1"/><rect x="16.6" y="2.4" width="0.8" height="2.8" rx="0.4"/>' +
    '<path fill-rule="evenodd" d="M5 4.5H19A4 4 0 0 1 23 8.5V18A4 4 0 0 1 19 22H5A4 4 0 0 1 1 18V8.5A4 4 0 0 1 5 4.5Z' +
    'M6.25 9.25H8.75A1.25 1.25 0 0 1 10 10.5V12A1.25 1.25 0 0 1 8.75 13.25H6.25A1.25 1.25 0 0 1 5 12V10.5A1.25 1.25 0 0 1 6.25 9.25Z' +
    'M15.25 9.25H17.75A1.25 1.25 0 0 1 19 10.5V12A1.25 1.25 0 0 1 17.75 13.25H15.25A1.25 1.25 0 0 1 14 12V10.5A1.25 1.25 0 0 1 15.25 9.25Z' +
    'M9 15.75H15A1 1 0 0 1 15 17.75H9A1 1 0 0 1 9 15.75Z"/></svg>';

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
  // Réponses closes (reçues en entier, ou arrêtées par Stop) : leurs chunks
  // tardifs sont ignorés. Clear garde cet ensemble, contrairement à
  // renderedMessageIds : l'hôte peut encore envoyer quelques chunks après un
  // Stop, et ils ne doivent pas s'écrire dans le chat vidé.
  const closedMessageIds = new Set();
  // Stop demandé pour la réponse attendue (son id peut n'arriver qu'avec l'ack).
  let stopRequested = false;
  // Clear pendant une génération : la fin de cette réponse n'affiche plus rien.
  let discardingReply = false;
  let pendingAttachments = [];
  // Bibliothèque de prompts (slash commands) + état du menu d'autocomplétion.
  let slashPrompts = [];
  let slashItems = [];
  let slashIndex = 0;
  let slashMenuOpen = false;
  let slashMenuEl = null;
  // Mentions « @ » : attache un fichier ou un dossier du workspace VS Code.
  let mentionItems = [];
  let mentionIndex = 0;
  let mentionMenuOpen = false;
  let mentionMenuEl = null;
  let mentionQuery = null;       // requête « @… » courante (null = menu fermé)
  let mentionDebounce = null;
  // Mode du bouton d'envoi : 'send' (avion) ou 'stop' (carré) pendant la génération.
  let sendBtnMode = 'send';
  let userPinnedToBottom = true;
  let lastScrollTop = 0;
  let autoAttachActive = false;
  // Replies of the conversation, as the host keeps them (relay/code_hub.py):
  // message_id → { status, parts, text, timestamp, duration_ms }. Each one is
  // a bubble (turn.js): the text of every pass of the model and, between two
  // passes, its tool calls, in order.
  const replies = new Map();
  const turns = new Map();
  // Reply in progress: the tool events of this extension belong to it
  let activeId = null;
  // Replies whose text changed since the last frame, drawn at the next one:
  // the host sends a chunk per token, more often than the screen redraws
  let dirtyReplies = [];
  let dirtyFrame = 0;
  // Message typed here, sent, not yet acknowledged by the host: its bubble is
  // already shown (a message sent by a command — selection, active file — is
  // shown when its ack arrives).
  let pendingLocalSend = false;
  // The host shares this conversation with the Code page of My_AI and the phone.
  let sharedConversation = false;
  // Locale of the times (My_AI's language), given with the strings.
  let timeLocale;

  // Localized strings injected by the extension on startup, in My_AI's
  // language. The webview renders nothing visible until applyStrings()
  // runs, so the user never sees raw English placeholders.
  let STR = {};
  function t(key) { return (STR && STR[key]) || key; }

  // Texts of the replies (turn.js), under the keys of the phone page:
  // {target}, {tool}… come from the page; {0}, in the extension's texts, is
  // the first of them
  function turnText(key, params) {
    const text = t(key);
    if (!params) return text;
    const first = Object.keys(params)[0];
    return text.replace(/\{(\w+)\}/g, (match, name) => {
      if (Object.prototype.hasOwnProperty.call(params, name)) return String(params[name]);
      return name === '0' && first !== undefined ? String(params[first]) : match;
    });
  }

  // Bubbles of the replies, the same as on the phone; approvals asked for a
  // message typed on the PC or the phone are answered here too
  const turnOptions = {
    t: turnText,
    approve: (callId, decision) => vscode.postMessage({ type: 'approve-tool', callId, decision }),
    robotSvg: ROBOT_SVG,
    formatTime: formatTime,
    locale: undefined,
    codeActions: [],
  };

  // Language of the page: direction (Arabic is written right to left) and
  // locale of the times. Sent with the strings, again when it changes.
  function applyLanguage(lang, dir, locale) {
    if (lang) document.documentElement.lang = lang;
    document.documentElement.dir = dir === 'rtl' ? 'rtl' : 'ltr';
    timeLocale = locale || undefined;
    turnOptions.locale = timeLocale;
  }

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
    document.getElementById('welcomeShared').textContent = t('webview.welcome.shared');
    document.getElementById('clearBtn').textContent = t('webview.header.clear');
    document.getElementById('clearBtn').title = t('webview.header.clearTooltip');
    document.getElementById('reconnectBtn').textContent = t('webview.header.reconnect');
    document.getElementById('reconnectBtn').title = t('webview.header.reconnectTooltip');
    document.getElementById('attachToggleBtn').title = t('webview.header.autoAttachTooltip');
    document.getElementById('attachBtn').title = t('webview.input.attachTooltip');
    inputEl.placeholder = t('webview.input.placeholder');
    renderAutoAttachToggle();
    if (sendBtnMode === 'stop') sendBtn.title = t('webview.send.stopTooltip');
    // Buttons of the code blocks, then the replies already on screen
    turnOptions.codeActions = [
      { action: 'copy', label: t('webview.code.copy') },
      { action: 'insert', label: t('webview.code.insert') },
    ];
    turns.forEach((turn, id) => {
      const reply = replies.get(id);
      if (reply) turn.refresh(reply);
    });
    messagesEl.querySelectorAll('.origin-label').forEach((label) => {
      label.textContent = originText(label.dataset.origin);
    });
  }

  // ── EVENT WIRING ─────────────────────────────────────
  connectBtn.addEventListener('click', () => {
    vscode.postMessage({ type: 'connect-request' });
  });

  sendBtn.addEventListener('click', () => {
    if (sendBtnMode === 'stop') {
      stopGeneration();
    } else {
      sendMessage();
    }
  });
  attachBtn.addEventListener('click', () => vscode.postMessage({ type: 'pick-file' }));
  // New conversation, also on the Code page of My_AI and on the phone: the view
  // clears when the host says so (code_cleared), or by itself (clear-local)
  clearBtn.addEventListener('click', () => vscode.postMessage({ type: 'clear-chat' }));
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
    updateSlashMenu();
    updateMentionMenu();
  });

  inputEl.addEventListener('blur', () => {
    // Léger délai : laisse le mousedown d'une ligne s'exécuter avant de fermer.
    setTimeout(() => { hideSlashMenu(); hideMentionMenu(); }, 150);
  });

  inputEl.addEventListener('keydown', (e) => {
    if (mentionMenuOpen) {
      if (e.key === 'ArrowDown') { e.preventDefault(); mentionMove(1); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); mentionMove(-1); return; }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (mentionItems[mentionIndex]) mentionAccept(mentionItems[mentionIndex]);
        return;
      }
      if (e.key === 'Escape') { e.preventDefault(); hideMentionMenu(); return; }
    }
    if (slashMenuOpen) {
      if (e.key === 'ArrowDown') { e.preventDefault(); slashMove(1); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); slashMove(-1); return; }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        if (slashItems[slashIndex]) slashAccept(slashItems[slashIndex]);
        return;
      }
      if (e.key === 'Escape') { e.preventDefault(); hideSlashMenu(); return; }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // The view follows the reply as long as the user doesn't scroll up; back at
  // the bottom, it follows it again. Text growing below the view doesn't stop it.
  messagesEl.addEventListener('scroll', () => {
    const top = messagesEl.scrollTop;
    const gap = messagesEl.scrollHeight - (top + messagesEl.clientHeight);
    if (gap < 80) userPinnedToBottom = true;
    else if (top < lastScrollTop) userPinnedToBottom = false;
    lastScrollTop = top;
  }, { passive: true });

  // Buttons of the code blocks (markdown.js): copy, insert at the cursor
  messagesEl.addEventListener('click', (e) => {
    const target = e.target;
    if (!(target instanceof Element)) return;
    const button = target.closest('.md-code-btn');
    const block = button && button.closest('.md-code');
    const pre = block && block.querySelector('pre code');
    if (!pre) return;
    const code = pre.textContent || '';
    if (button.dataset.action === 'insert') {
      vscode.postMessage({ type: 'insert-at-cursor', code });
      flashAction(button, t('webview.code.inserted'));
    } else if (button.dataset.action === 'copy') {
      vscode.postMessage({ type: 'copy-to-clipboard', text: code });
      flashAction(button, t('webview.code.copied'));
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
    // A tool call, the end of a reply… show after the text received before them
    if (!(msg.type === 'relay-message' && msg.payload && msg.payload.type === 'chunk')) {
      flushReplies();
    }
    switch (msg.type) {
      case 'init-strings':
        applyLanguage(msg.lang, msg.dir, msg.locale);
        applyStrings(msg.strings);
        break;
      case 'state':
        sharedConversation = !!msg.shared;
        document.getElementById('welcomeShared').style.display = sharedConversation ? 'block' : 'none';
        applyState(msg.state, msg.hasCredentials);
        break;
      case 'clear-local':
        clearChat();
        break;
      case 'send-failed':
        // Never left VS Code: no reply to wait for
        pendingLocalSend = false;
        isWaiting = false;
        removeTyping();
        updateSendButton();
        break;
      case 'prompts':
        slashPrompts = Array.isArray(msg.items) ? msg.items : [];
        break;
      case 'mention-results':
        applyMentionResults(msg.query, Array.isArray(msg.items) ? msg.items : []);
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

  // ── REPLIES (a bubble each, turn.js) ─────────────────
  const OPEN_TOOL = { requested: true, running: true, 'awaiting-approval': true };

  // Reply on screen: drawn again where it is, or its bubble added at the bottom
  function showReply(reply) {
    if (welcomeEl) welcomeEl.style.display = 'none';
    let turn = turns.get(reply.message_id);
    if (turn) {
      turn.update(reply);
      return;
    }
    turn = window.MyAITurn.create(reply, turnOptions);
    turns.set(reply.message_id, turn);
    messagesEl.appendChild(turn.el);
  }

  // Reply begun (message acknowledged, or typed elsewhere): its bubble shows
  // the typing indicator until the first text or tool call
  function startReply(mid, timestamp) {
    let reply = replies.get(mid);
    if (!reply) {
      reply = { message_id: mid, status: 'streaming', parts: [], text: '', timestamp };
      replies.set(mid, reply);
    }
    activeId = mid;
    removeTyping();
    showReply(reply);
    scrollToBottom();
    return reply;
  }

  function scheduleReply(reply) {
    if (!dirtyReplies.includes(reply)) dirtyReplies.push(reply);
    if (!dirtyFrame) dirtyFrame = requestAnimationFrame(flushReplies);
  }

  // Texts waiting: drawn at the next frame, or before any other event
  function flushReplies() {
    if (dirtyFrame) cancelAnimationFrame(dirtyFrame);
    dirtyFrame = 0;
    const queued = dirtyReplies;
    dirtyReplies = [];
    queued.forEach(showReply);
    if (queued.length) scrollToBottomStream();
  }

  // Text of a pass of the model, whole each time (segment_index: the pass)
  function applyChunk(data) {
    const mid = data.message_id || '';
    if (!mid || discardingReply || closedMessageIds.has(mid)) return;
    if (renderedMessageIds.has('ai:' + mid)) return;
    const reply = replies.get(mid) || startReply(mid, data.timestamp);
    // Hosts from before the passes: a single one
    const segment = typeof data.segment_index === 'number' ? data.segment_index : 0;
    const text = data.text || '';
    let part = reply.parts.find((p) => p.kind === 'text' && p.segment === segment);
    if (!part) {
      // No empty text: a pass that only writes a tool call
      if (!text.trim()) return;
      part = { kind: 'text', segment, text };
      reply.parts.push(part);
    } else {
      part.text = text;
    }
    scheduleReply(reply);
  }

  // Tool call run by this extension (toolDispatcher.ts), for the reply in progress
  function applyToolEvent(event) {
    if (!event || !event.callId || discardingReply) return;
    // The reply begins with its ack; without it, the message still waiting
    const mid = activeId || (isWaiting && lastSentMessageId) || null;
    if (!mid || closedMessageIds.has(mid)) return;
    const reply = replies.get(mid) || startReply(mid);
    if (reply.status !== 'streaming') return;
    let part = reply.parts.find((p) => p.kind === 'tool' && p.call_id === event.callId);
    if (!part) {
      part = { kind: 'tool', call_id: event.callId };
      reply.parts.push(part);
    }
    part.name = event.toolName || part.name || 'tool';
    part.input = event.input || part.input || {};
    part.status = event.kind;
    if (event.result) part.output = event.result.content;
    else if (event.kind === 'failed' && event.error) part.output = event.error;
    if (Array.isArray(event.options)) part.options = event.options;
    else delete part.options;
    showReply(reply);
    scrollToBottomStream();
  }

  // End of a reply: done, stopped or error (hosts from before: done)
  function applyResponse(data) {
    const mid = data.message_id || '';
    if (mid) closedMessageIds.add(mid);
    // Refused by the host (empty id): the message typed here got no reply
    pendingLocalSend = false;
    if (discardingReply) {
      // Fin de la réponse arrêtée par Clear : on rend le bouton d'envoi
      // sans rien afficher dans le chat vidé.
      if (mid) renderedMessageIds.add('ai:' + mid);
      discardingReply = false;
      stopRequested = false;
      isWaiting = false;
      lastSentMessageId = null;
      updateSendButton();
      return;
    }
    if (mid && renderedMessageIds.has('ai:' + mid)) return;
    if (mid) renderedMessageIds.add('ai:' + mid);
    removeTyping();
    isWaiting = false;
    stopRequested = false;
    if (mid && mid === lastSentMessageId) lastSentMessageId = null;
    if (mid && mid === activeId) activeId = null;
    const reply = (mid && replies.get(mid)) || { message_id: mid, parts: [] };
    reply.status = data.status || 'done';
    reply.text = data.message || '';
    reply.timestamp = data.timestamp || reply.timestamp;
    reply.duration_ms = data.duration_ms;
    reply.parts.forEach((part) => {
      if (part.kind === 'tool' && OPEN_TOOL[part.status]) {
        part.status = 'stopped';
        delete part.options;
      }
    });
    if (mid) {
      replies.set(mid, reply);
      showReply(reply);
    } else {
      // Message refused (VS Code busy…): the reason, in a bubble of its own
      if (welcomeEl) welcomeEl.style.display = 'none';
      messagesEl.appendChild(window.MyAITurn.create(reply, turnOptions).el);
    }
    updateSendButton();
    scrollToBottom();
  }

  // Message acknowledged by the host: typed here, or sent by a command
  // (selection, active file); its reply begins
  function applyAck(data) {
    const mid = data.message_id;
    if (!mid) return;
    lastSentMessageId = mid;
    if (!pendingLocalSend && typeof data.text === 'string'
      && !renderedMessageIds.has('user:' + mid)) {
      // Sent by a command (selection, active file), not typed here
      userPinnedToBottom = true;
      addUserMessage(userDisplayText(data.text, data.attachments), data.timestamp);
      isWaiting = true;
      updateSendButton();
    }
    pendingLocalSend = false;
    renderedMessageIds.add('user:' + mid);
    // Stop cliqué avant cet ack : la réponse est déjà arrêtée.
    if (stopRequested) closedMessageIds.add(mid);
    if (!discardingReply && !replies.has(mid)) startReply(mid, data.timestamp);
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

  // ── CODE CONVERSATION (shared with My_AI on the PC and the phone) ──
  // The host's full state (connection, view reloaded): it replaces the view.
  function applySnapshot(messages, state) {
    removeTyping();
    clearView();
    pendingLocalSend = false;
    discardingReply = false;
    const list = Array.isArray(messages) ? messages : [];
    list.forEach(renderStoredMessage);
    if (welcomeEl) welcomeEl.style.display = list.length ? 'none' : 'flex';
    applyCodeState(state);
    scrollToBottom();
  }

  function renderStoredMessage(m) {
    if (!m || !m.message_id) return;
    const mid = m.message_id;
    if (m.role === 'user') {
      renderedMessageIds.add('user:' + mid);
      addUserMessage(userDisplayText(m.text, m.attachments), m.timestamp, m.origin);
      return;
    }
    const reply = {
      message_id: mid,
      status: m.status || 'done',
      text: m.text || '',
      timestamp: m.timestamp,
      duration_ms: m.duration_ms,
      parts: (Array.isArray(m.parts) ? m.parts : []).filter(Boolean).map((part) => Object.assign({}, part)),
    };
    replies.set(mid, reply);
    showReply(reply);
    if (reply.status === 'streaming') {
      // Reply in progress: its next chunks and tool calls continue this bubble
      activeId = mid;
    } else {
      renderedMessageIds.add('ai:' + mid);
      closedMessageIds.add(mid);
    }
  }

  // Messages and replies on screen, gone (the welcome stays)
  function clearView() {
    Array.from(messagesEl.children).forEach((c) => {
      if (c !== welcomeEl) c.remove();
    });
    renderedMessageIds.clear();
    replies.clear();
    turns.clear();
    activeId = null;
    dirtyReplies = [];
  }

  // Reply in progress or not, wherever its message was typed: the send button
  // becomes Stop while My_AI works, here as on the PC and the phone.
  function applyCodeState(state) {
    if (!state || typeof state !== 'object') return;
    if (state.busy) {
      isWaiting = true;
      if (state.message_id) lastSentMessageId = state.message_id;
    } else if (!pendingLocalSend) {
      isWaiting = false;
      stopRequested = false;
      removeTyping();
    }
    updateSendButton();
  }

  // Message typed on the Code page of My_AI or on the phone
  function applyRemoteUser(data) {
    const mid = data.message_id || '';
    if (!mid || renderedMessageIds.has('user:' + mid)) return;
    renderedMessageIds.add('user:' + mid);
    userPinnedToBottom = true;
    addUserMessage(userDisplayText(data.text, data.attachments), data.timestamp, data.origin);
    lastSentMessageId = mid;
    isWaiting = true;
    startReply(mid, data.timestamp);
    updateSendButton();
  }

  // New conversation (Clear here, on the PC or on the phone)
  function resetConversation() {
    removeTyping();
    clearView();
    if (welcomeEl) welcomeEl.style.display = 'flex';
    isWaiting = false;
    stopRequested = false;
    discardingReply = false;
    pendingLocalSend = false;
    lastSentMessageId = null;
    updateSendButton();
  }

  function userDisplayText(text, attachments) {
    const lines = (Array.isArray(attachments) ? attachments : []).map((name) => '📎 ' + name);
    return [text || ''].concat(lines).filter((line) => line).join('\n');
  }

  function originText(origin) {
    return origin === 'desktop' || origin === 'mobile' ? t('webview.origin.' + origin) : '';
  }

  function applyRelayMessage(data) {
    if (!data || typeof data !== 'object') return;
    switch (data.type) {
      case 'code_snapshot': applySnapshot(data.messages, data.state); break;
      case 'code_state': applyCodeState(data); break;
      case 'code_user': applyRemoteUser(data); break;
      case 'code_cleared': resetConversation(); break;
      case 'response': applyResponse(data); break;
      case 'chunk': applyChunk(data); break;
      case 'ack': applyAck(data); break;
      default: break;
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
    addUserMessage(displayText);

    pendingLocalSend = true;
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

  // Icônes du bouton d'envoi : avion en papier (envoi) / carré (stop), identiques
  // au bouton STOP du chat mobile (My_AI Relay).
  const SEND_ICON_HTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
    '<line x1="22" y1="2" x2="11" y2="13"></line>' +
    '<polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
  const STOP_ICON_HTML =
    '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"></rect></svg>';

  function setSendBtnMode(mode) {
    if (sendBtnMode === mode) return;
    sendBtnMode = mode;
    if (mode === 'stop') {
      sendBtn.classList.add('stopmode');
      sendBtn.innerHTML = STOP_ICON_HTML;
      sendBtn.title = t('webview.send.stopTooltip');
    } else {
      sendBtn.classList.remove('stopmode');
      sendBtn.innerHTML = SEND_ICON_HTML;
      sendBtn.title = '';
    }
  }

  // Demande au host d'arrêter la génération en cours (LLM + appels d'outils).
  // Le host annule la tâche agentique et renvoie une réponse « interrompue »,
  // ce qui repasse isWaiting à false (via applyRelayMessage). D'ici là, les
  // chunks encore en route sont ignorés : le texte s'arrête tout de suite.
  function stopGeneration() {
    if (!isWaiting) return;
    stopRequested = true;
    if (lastSentMessageId) closedMessageIds.add(lastSentMessageId);
    vscode.postMessage({ type: 'stop-generation', messageId: lastSentMessageId || '' });
  }

  function updateSendButton() {
    // Pendant la génération, le bouton devient un bouton STOP cliquable
    // (carré noir sur fond blanc), exactement comme sur le chat mobile.
    if (isWaiting) {
      setSendBtnMode('stop');
      sendBtn.disabled = false;
      return;
    }
    setSendBtnMode('send');
    const hasText = !!inputEl.value.trim();
    const hasReady = pendingAttachments.some((a) => a.status === 'ready');
    const uploading = pendingAttachments.some((a) => a.status === 'uploading');
    sendBtn.disabled = !isConnected || uploading || (!hasText && !hasReady);
  }

  function autoResize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + 'px';
  }

  // ── SLASH COMMAND AUTOCOMPLETE ("/" en début de saisie) ──────────────
  function slashNormalize(s) {
    return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  function ensureSlashMenu() {
    if (slashMenuEl) return slashMenuEl;
    slashMenuEl = document.createElement('div');
    slashMenuEl.className = 'slash-menu';
    slashMenuEl.style.display = 'none';
    (inputArea || document.body).appendChild(slashMenuEl);
    return slashMenuEl;
  }

  function hideSlashMenu() {
    slashMenuOpen = false;
    slashItems = [];
    if (slashMenuEl) slashMenuEl.style.display = 'none';
  }

  function updateSlashActive() {
    if (!slashMenuEl) return;
    const rows = slashMenuEl.querySelectorAll('.slash-item');
    rows.forEach((r, i) => {
      r.classList.toggle('active', i === slashIndex);
      if (i === slashIndex && r.scrollIntoView) r.scrollIntoView({ block: 'nearest' });
    });
  }

  function slashMove(delta) {
    if (!slashItems.length) return;
    slashIndex = (slashIndex + delta + slashItems.length) % slashItems.length;
    updateSlashActive();
  }

  function renderSlashMenu() {
    const el = ensureSlashMenu();
    el.innerHTML = '';
    slashItems.forEach((item, i) => {
      const row = document.createElement('div');
      row.className = 'slash-item' + (i === slashIndex ? ' active' : '');

      const cmd = document.createElement('div');
      cmd.className = 'slash-cmd';
      cmd.textContent = '/' + (item.command || '');
      row.appendChild(cmd);

      const sub = (item.title || '') + (item.description ? ' — ' + item.description : '');
      if (sub.trim()) {
        const desc = document.createElement('div');
        desc.className = 'slash-desc';
        desc.textContent = sub;
        row.appendChild(desc);
      }

      // mousedown (et non click) : devance le blur du textarea.
      row.addEventListener('mousedown', (e) => { e.preventDefault(); slashAccept(item); });
      row.addEventListener('mouseenter', () => { slashIndex = i; updateSlashActive(); });
      el.appendChild(row);
    });
  }

  function updateSlashMenu() {
    const m = /^\/(\S*)$/.exec(inputEl.value);
    if (!m || !slashPrompts.length) { hideSlashMenu(); return; }
    const pref = slashNormalize(m[1]);
    slashItems = slashPrompts
      .filter((p) => p.command && slashNormalize(p.command).indexOf(pref) === 0)
      .slice(0, 8);
    if (!slashItems.length) { hideSlashMenu(); return; }
    slashIndex = 0;
    renderSlashMenu();
    ensureSlashMenu().style.display = 'block';
    slashMenuOpen = true;
  }

  function slashAccept(item) {
    // Insère seulement « /commande » ; l'utilisateur tape ensuite son texte.
    // L'expansion en prompt détaillé se fait côté hôte (desktop) à l'envoi.
    inputEl.value = '/' + (item.command || '') + ' ';
    hideSlashMenu();
    inputEl.focus();
    const len = inputEl.value.length;
    try { inputEl.setSelectionRange(len, len); } catch (e) { /* noop */ }
    autoResize();
    updateSendButton();
  }

  // ── MENTION « @ » : attacher un fichier / dossier du workspace ───────────
  // Tapez « @ » suivi d'un terme : un menu propose les fichiers et dossiers du
  // workspace VS Code. Un fichier est joint au prochain message ; un dossier
  // est attaché comme @codebase (indexé côté host).
  const MENTION_RE = /(?:^|\s)@([^\s@]*)$/;

  function ensureMentionMenu() {
    if (mentionMenuEl) return mentionMenuEl;
    mentionMenuEl = document.createElement('div');
    mentionMenuEl.className = 'slash-menu mention-menu';
    mentionMenuEl.style.display = 'none';
    (inputArea || document.body).appendChild(mentionMenuEl);
    return mentionMenuEl;
  }

  function hideMentionMenu() {
    mentionMenuOpen = false;
    mentionItems = [];
    mentionQuery = null;
    if (mentionMenuEl) mentionMenuEl.style.display = 'none';
  }

  function updateMentionActive() {
    if (!mentionMenuEl) return;
    const rows = mentionMenuEl.querySelectorAll('.slash-item');
    rows.forEach((r, i) => {
      r.classList.toggle('active', i === mentionIndex);
      if (i === mentionIndex && r.scrollIntoView) r.scrollIntoView({ block: 'nearest' });
    });
  }

  function mentionMove(delta) {
    if (!mentionItems.length) return;
    mentionIndex = (mentionIndex + delta + mentionItems.length) % mentionItems.length;
    updateMentionActive();
  }

  function mentionIcon(item) {
    if (item.kind === 'folder') return item.action === 'attach' ? '📎 ' : '📁 ';
    return '📄 ';
  }

  function renderMentionMenu() {
    const el = ensureMentionMenu();
    el.innerHTML = '';
    mentionItems.forEach((item, i) => {
      const row = document.createElement('div');
      row.className = 'slash-item' + (i === mentionIndex ? ' active' : '');

      const cmd = document.createElement('div');
      cmd.className = 'slash-cmd';
      // Dossier navigable : suffixe « / » et chevron ; dossier-attache : libellé clair.
      let label = mentionIcon(item) + (item.label || '');
      if (item.kind === 'folder' && item.action === 'attach') {
        label = '📎 ' + (item.label || '') + '  —  ' + t('webview.mention.attachFolder');
      } else if (item.kind === 'folder') {
        label = '📁 ' + (item.label || '') + '/';
      }
      cmd.textContent = label;
      row.appendChild(cmd);

      if (item.detail && item.detail !== item.label) {
        const desc = document.createElement('div');
        desc.className = 'slash-desc';
        desc.textContent = item.detail + (item.kind === 'folder' && item.action !== 'attach' ? '/' : '');
        row.appendChild(desc);
      }

      row.addEventListener('mousedown', (e) => { e.preventDefault(); mentionAccept(item); });
      row.addEventListener('mouseenter', () => { mentionIndex = i; updateMentionActive(); });
      el.appendChild(row);
    });
  }

  // Remplace le token « @… » courant (de « @ » jusqu'au curseur) par newText.
  function replaceMentionToken(newText) {
    const text = inputEl.value;
    const caret = (typeof inputEl.selectionStart === 'number')
      ? inputEl.selectionStart : text.length;
    const before = text.slice(0, caret);
    const after = text.slice(caret);
    const atPos = before.lastIndexOf('@');
    const cut = atPos >= 0 ? atPos : before.length;
    inputEl.value = before.slice(0, cut) + newText + after;
    const pos = cut + newText.length;
    try { inputEl.setSelectionRange(pos, pos); } catch (e) { /* noop */ }
    autoResize();
    updateSendButton();
  }

  function updateMentionMenu() {
    const caret = (typeof inputEl.selectionStart === 'number')
      ? inputEl.selectionStart : inputEl.value.length;
    const before = inputEl.value.slice(0, caret);
    const m = MENTION_RE.exec(before);
    if (!m) { hideMentionMenu(); return; }
    // Slash et mention ne coexistent pas.
    hideSlashMenu();
    mentionQuery = m[1];
    clearTimeout(mentionDebounce);
    mentionDebounce = setTimeout(() => {
      vscode.postMessage({ type: 'mention-query', query: mentionQuery || '' });
    }, 120);
  }

  function applyMentionResults(query, items) {
    // Ignorer les résultats obsolètes (l'utilisateur a continué à taper).
    if (mentionQuery === null || query !== (mentionQuery || '')) return;
    mentionItems = items.slice(0, 20);
    if (!mentionItems.length) { hideMentionMenu(); return; }
    mentionIndex = 0;
    renderMentionMenu();
    ensureMentionMenu().style.display = 'block';
    mentionMenuOpen = true;
  }

  function mentionAccept(item) {
    if (!item) return;
    // Dossier navigable : on ENTRE dedans (insère « @dossier/ » et relance la
    // requête), sans attacher. L'attache se fait via l'entrée « 📎 attacher ce
    // dossier » ou en choisissant un fichier.
    if (item.kind === 'folder' && item.action !== 'attach') {
      replaceMentionToken('@' + (item.detail || item.label) + '/');
      inputEl.focus();
      updateMentionMenu();   // relance la requête sur le nouveau dossier
      return;
    }
    // Fichier ou « attacher ce dossier » : on retire le token et on attache
    // (retour visuel = barre de progression / notification d'indexation côté host).
    replaceMentionToken('');
    hideMentionMenu();
    inputEl.focus();
    if (item.path) {
      vscode.postMessage({
        type: 'attach-mention', kind: item.kind || 'file', path: item.path, name: item.label,
      });
    }
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
  // Message of the user; origin: where it was typed ('desktop', 'mobile'), labelled
  function addUserMessage(text, timestamp, origin) {
    if (welcomeEl) welcomeEl.style.display = 'none';
    const msg = document.createElement('div');
    msg.className = 'message user';
    const time = formatTime(timestamp ? new Date(timestamp) : new Date());
    const label = originText(origin);
    const bubble = '<div class="bubble">' + escapeHtml(text) +
      '<span class="time">' + time + '</span></div>';
    msg.innerHTML = label
      ? '<div class="user-stack">' +
        '<span class="origin-label" data-origin="' + escapeHtml(origin) + '">' +
        escapeHtml(label) + '</span>' + bubble + '</div>'
      : bubble;
    messagesEl.appendChild(msg);
    scrollToBottom();
  }

  function showTyping() {
    if (typingEl) return;
    typingEl = document.createElement('div');
    typingEl.className = 'message ai';
    typingEl.id = 'typingIndicator';
    typingEl.innerHTML =
      '<div class="ai-icon">' + ROBOT_SVG + '</div>' +
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
    // Vider le chat pendant une génération l'arrête, sinon la réponse
    // continuerait de s'écrire dans le chat vidé. Le bouton reste en mode
    // stop jusqu'à la réponse « interrompue » de l'hôte.
    if (isWaiting) {
      stopGeneration();
      discardingReply = true;
    }
    removeTyping();
    clearView();
    if (welcomeEl) welcomeEl.style.display = 'flex';
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

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatTime(date) {
    return date.toLocaleTimeString(timeLocale, { hour: '2-digit', minute: '2-digit' });
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
