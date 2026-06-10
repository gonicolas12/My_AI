/* ═══════════════════════════════════════════════════ */
/* My_AI Relay — Page Agents (mobile)                   */
/*                                                       */
/* Reprend les fonctionnalités de la page « Agents » du  */
/* GUI desktop : grille d'agents, création/édition       */
/* d'agents personnalisés, workflow visuel tactile       */
/* (n8n-like), mode débat. Tout transite par la même     */
/* connexion WebSocket chiffrée E2EE (via window.RelayCore*/
/* exposé par app.js). Le modèle tourne en local côté PC.*/
/* ═══════════════════════════════════════════════════ */

(function () {
  'use strict';

  // ── Constantes géométriques du nœud workflow ──────────
  var NODE_W = 190;
  var NODE_H = 64;
  var WORLD_W = 1400;
  var WORLD_H = 1000;
  var WF_STORAGE_KEY = 'myai_relay_workflow_v1';

  // ── State ─────────────────────────────────────────────
  var agents = { builtin: [], custom: [], default_model: '' };
  var agentsLoaded = false;
  var nodes = [];                 // {id, agent_type, name, color, icon, x, y, el, status}
  var connections = [];           // {from, to}
  var nextNodeId = 1;
  var connectingFrom = null;      // id du nœud dont le port de sortie est armé
  var isExecuting = false;
  var currentExecId = null;
  var sections = {};              // sectionId -> {el, body, text, stateEl}
  var editingKey = null;          // clé de l'agent en cours d'édition (null = création)
  var modalBusy = false;
  // Pièces jointes en attente : [{localId, fileId, name, isImage, status, error}]
  var attachments = [];
  var attCounter = 0;

  // ── DOM refs (résolus à l'init) ───────────────────────
  var el = {};

  function $(id) { return document.getElementById(id); }

  function init() {
    el.viewChat = $('viewChat');
    el.viewAgents = $('viewAgents');
    el.tabChat = $('tabChat');
    el.tabAgents = $('tabAgents');
    el.clearChatBtn = $('clearChatBtn');
    el.grid = $('agentsGrid');
    el.canvas = $('wfCanvas');
    el.world = $('wfWorld');
    el.links = $('wfLinks');
    el.empty = $('wfEmpty');
    el.output = $('agentOutput');
    el.outputWelcome = $('agentOutputWelcome');
    el.task = $('agentTask');
    el.status = $('agentStatus');
    el.execBtn = $('agentExecBtn');
    el.createBtn = $('agentCreateBtn');
    el.debateBtn = $('agentDebateBtn');
    el.clearBtn = $('agentClearBtn');
    el.attachBtn = $('agentAttachBtn');
    el.fileInput = $('agentFileInput');
    el.attachments = $('agentAttachments');
    // Modale agent
    el.modal = $('agentModal');
    el.modalTitle = $('agentModalTitle');
    el.modalName = $('agentModalName');
    el.modalRole = $('agentModalRole');
    el.modalMsg = $('agentModalMsg');
    el.modalCancel = $('agentModalCancel');
    el.modalOk = $('agentModalOk');
    // Modale débat
    el.debateModal = $('debateModal');
    el.debateA = $('debateAgentA');
    el.debateB = $('debateAgentB');
    el.debateTopic = $('debateTopic');
    el.debateRounds = $('debateRounds');
    el.debateMsg = $('debateModalMsg');
    el.debateCancel = $('debateModalCancel');
    el.debateOk = $('debateModalOk');

    bindEvents();
    restoreWorkflow();
  }

  // ════════════════════════════════════════════════════
  // TAB SWITCHING
  // ════════════════════════════════════════════════════
  function switchTab(tab) {
    var toAgents = tab === 'agents';
    el.viewChat.classList.toggle('active', !toAgents);
    el.viewAgents.classList.toggle('active', toAgents);
    el.tabChat.classList.toggle('active', !toAgents);
    el.tabAgents.classList.toggle('active', toAgents);
    // Le bouton « Effacer » du header ne concerne que le chat.
    if (el.clearChatBtn) el.clearChatBtn.style.display = toAgents ? 'none' : '';
    // Rafraîchir la liste à chaque ouverture de la page Agents pour rester
    // synchrone avec les agents personnalisés éventuellement créés sur le PC.
    if (toAgents) {
      requestAgentsList();
    }
  }
  window.switchTab = switchTab;

  // Appelé par app.js quand le WebSocket (re)connecte.
  function onConnect() {
    if (el.viewAgents && el.viewAgents.classList.contains('active')) {
      requestAgentsList();
    }
  }

  // ════════════════════════════════════════════════════
  // WEBSOCKET — envoi / réception
  // ════════════════════════════════════════════════════
  function send(obj) {
    if (!window.RelayCore || !window.RelayCore.isConnected()) {
      toast('Hors ligne — connexion en cours...', true);
      return Promise.resolve();
    }
    return window.RelayCore.send(obj).catch(function (e) {
      console.error('[Agents] envoi échoué', e);
    });
  }

  function requestAgentsList() {
    send({ type: 'agents_list' });
  }

  function onMessage(data) {
    switch (data.type) {
      case 'agents_list_result':
        agents.builtin = data.builtin || [];
        agents.custom = data.custom || [];
        agents.default_model = data.default_model || '';
        agentsLoaded = true;
        renderGrid();
        break;
      case 'agent_create_result':
        handleCreateResult(data);
        break;
      case 'agent_edit_result':
        handleEditResult(data);
        break;
      case 'agent_delete_result':
        handleDeleteResult(data);
        break;
      case 'agent_exec_start':
        onExecStart(data);
        break;
      case 'agent_debate_topic':
        addOutputHeader('🎭 Sujet : ' + (data.topic || ''));
        break;
      case 'agent_section_start':
        onSectionStart(data);
        break;
      case 'agent_section_chunk':
        onSectionChunk(data);
        break;
      case 'agent_section_end':
        onSectionEnd(data);
        break;
      case 'agent_node_status':
        setNodeStatus(data.node_id, data.status);
        break;
      case 'agent_exec_end':
        onExecEnd(data);
        break;
      case 'agent_exec_error':
        onExecError(data);
        break;
    }
  }

  // ════════════════════════════════════════════════════
  // GRILLE D'AGENTS
  // ════════════════════════════════════════════════════
  function renderGrid() {
    el.grid.innerHTML = '';
    var all = agents.builtin.concat(agents.custom);
    all.forEach(function (a) { el.grid.appendChild(buildCard(a)); });
  }

  function buildCard(a) {
    var card = document.createElement('div');
    card.className = 'agent-card';
    card.style.borderColor = a.color;

    var actions = '';
    if (a.custom) {
      actions =
        '<div class="ac-actions">' +
        '<button class="ac-act edit" title="Modifier">📝</button>' +
        '<button class="ac-act del" title="Supprimer">✕</button>' +
        '</div>';
    }
    card.innerHTML =
      actions +
      '<div class="ac-head">' +
      '<span class="ac-icon">' + (a.icon || '🤖') + '</span>' +
      '<span class="ac-name" style="color:' + a.color + '">' +
      esc(a.name) + '</span>' +
      '</div>' +
      '<div class="ac-desc">' + esc(a.desc || '') + '</div>';

    // Tap carte → ajout au workflow
    card.addEventListener('click', function (e) {
      if (e.target.closest('.ac-act')) return;
      addNode(a);
      toast('Ajouté : ' + a.name);
    });

    if (a.custom) {
      card.querySelector('.ac-act.edit').addEventListener('click', function (e) {
        e.stopPropagation();
        openAgentModal(a);
      });
      card.querySelector('.ac-act.del').addEventListener('click', function (e) {
        e.stopPropagation();
        if (window.confirm("Supprimer l'agent « " + a.name + " » ?")) {
          send({ type: 'agent_delete', key: a.key });
        }
      });
    }
    return card;
  }

  // ════════════════════════════════════════════════════
  // WORKFLOW CANVAS (n8n tactile)
  // ════════════════════════════════════════════════════
  function addNode(agent, x, y) {
    var id = 'n' + (nextNodeId++);
    if (x == null || y == null) {
      // Placement en cascade dans la zone visible du canvas.
      var count = nodes.length;
      x = el.canvas.scrollLeft + 30 + (count % 3) * 60;
      y = el.canvas.scrollTop + 30 + (count % 5) * 30;
    }
    x = clamp(x, 0, WORLD_W - NODE_W);
    y = clamp(y, 0, WORLD_H - NODE_H);
    var node = {
      id: id, agent_type: agent.key, name: agent.name,
      color: agent.color, icon: agent.icon || '🤖',
      x: x, y: y, status: 'idle', el: null,
    };
    node.el = buildNodeEl(node);
    el.world.appendChild(node.el);
    nodes.push(node);
    el.empty.style.display = 'none';
    redrawLinks();
    persistWorkflow();
    return node;
  }

  function buildNodeEl(node) {
    var d = document.createElement('div');
    d.className = 'wf-node';
    d.style.left = node.x + 'px';
    d.style.top = node.y + 'px';
    d.innerHTML =
      '<div class="wn-bar" style="background:' + node.color + '"></div>' +
      '<div class="wn-icon" style="background:' + node.color + '">' + node.icon + '</div>' +
      '<div class="wn-body">' +
      '<div class="wn-name">' + esc(node.name) + '</div>' +
      '<div class="wn-status"><span class="wn-dot"></span><span class="wn-stxt">En attente</span></div>' +
      '</div>' +
      '<div class="wn-del">✕</div>' +
      '<div class="wf-port in" title="Entrée"></div>' +
      '<div class="wf-port out" title="Sortie"></div>';

    // Drag (pointer events — tactile + souris)
    var drag = null;
    d.addEventListener('pointerdown', function (e) {
      if (e.target.closest('.wf-port') || e.target.closest('.wn-del')) return;
      var wr = el.world.getBoundingClientRect();
      drag = { ox: (e.clientX - wr.left) - node.x, oy: (e.clientY - wr.top) - node.y };
      d.setPointerCapture(e.pointerId);
      d.style.zIndex = 10;
      e.preventDefault();
    });
    d.addEventListener('pointermove', function (e) {
      if (!drag) return;
      var wr = el.world.getBoundingClientRect();
      node.x = clamp((e.clientX - wr.left) - drag.ox, 0, WORLD_W - NODE_W);
      node.y = clamp((e.clientY - wr.top) - drag.oy, 0, WORLD_H - NODE_H);
      d.style.left = node.x + 'px';
      d.style.top = node.y + 'px';
      redrawLinks();
    });
    function endDrag(e) {
      if (!drag) return;
      drag = null;
      d.style.zIndex = '';
      try { d.releasePointerCapture(e.pointerId); } catch (_) {}
      persistWorkflow();
    }
    d.addEventListener('pointerup', endDrag);
    d.addEventListener('pointercancel', endDrag);

    // Suppression
    var del = d.querySelector('.wn-del');
    del.addEventListener('pointerdown', function (e) { e.stopPropagation(); });
    del.addEventListener('click', function (e) {
      e.stopPropagation();
      removeNode(node.id);
    });

    // Ports : connexion / déconnexion
    var outPort = d.querySelector('.wf-port.out');
    var inPort = d.querySelector('.wf-port.in');
    outPort.addEventListener('pointerdown', function (e) { e.stopPropagation(); });
    inPort.addEventListener('pointerdown', function (e) { e.stopPropagation(); });
    outPort.addEventListener('click', function (e) {
      e.stopPropagation();
      armConnection(node.id);
    });
    inPort.addEventListener('click', function (e) {
      e.stopPropagation();
      if (connectingFrom != null) {
        addConnection(connectingFrom, node.id);
        disarmConnection();
      } else {
        // Tap sur un port d'entrée déjà relié → on retire ses connexions
        var had = connections.some(function (c) { return c.to === node.id; });
        if (had) {
          connections = connections.filter(function (c) { return c.to !== node.id; });
          redrawLinks();
          persistWorkflow();
          toast('Connexion retirée');
        }
      }
    });

    return d;
  }

  function armConnection(fromId) {
    if (connectingFrom === fromId) { disarmConnection(); return; }
    disarmConnection();
    connectingFrom = fromId;
    var node = findNode(fromId);
    if (node) {
      var p = node.el.querySelector('.wf-port.out');
      if (p) p.classList.add('armed');
    }
    setStatus('Touchez le port d\'entrée (gauche) d\'un autre nœud pour relier.', '#f59e0b');
  }

  function disarmConnection() {
    if (connectingFrom != null) {
      var node = findNode(connectingFrom);
      if (node) {
        var p = node.el.querySelector('.wf-port.out');
        if (p) p.classList.remove('armed');
      }
    }
    connectingFrom = null;
  }

  function addConnection(fromId, toId) {
    if (fromId === toId) return;
    if (connections.some(function (c) { return c.from === fromId && c.to === toId; })) return;
    // Pas de cycle simple (A→B et B→A)
    if (connections.some(function (c) { return c.from === toId && c.to === fromId; })) {
      toast('Connexion inverse déjà présente', true);
      return;
    }
    connections.push({ from: fromId, to: toId });
    redrawLinks();
    persistWorkflow();
  }

  function removeNode(id) {
    var node = findNode(id);
    if (node && node.el) node.el.remove();
    nodes = nodes.filter(function (n) { return n.id !== id; });
    connections = connections.filter(function (c) { return c.from !== id && c.to !== id; });
    if (connectingFrom === id) disarmConnection();
    if (nodes.length === 0) el.empty.style.display = '';
    redrawLinks();
    persistWorkflow();
  }

  function findNode(id) {
    for (var i = 0; i < nodes.length; i++) if (nodes[i].id === id) return nodes[i];
    return null;
  }

  function redrawLinks() {
    var svg = el.links;
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    connections.forEach(function (c) {
      var fn = findNode(c.from), tn = findNode(c.to);
      if (!fn || !tn) return;
      var x1 = fn.x + NODE_W, y1 = fn.y + NODE_H / 2;
      var x2 = tn.x, y2 = tn.y + NODE_H / 2;
      var off = Math.max(40, Math.abs(x2 - x1) * 0.4);
      var dpath = 'M ' + x1 + ' ' + y1 +
                  ' C ' + (x1 + off) + ' ' + y1 + ' ' +
                  (x2 - off) + ' ' + y2 + ' ' + x2 + ' ' + y2;
      var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', dpath);
      path.setAttribute('fill', 'none');
      path.setAttribute('stroke', fn.color);
      path.setAttribute('stroke-width', '2.5');
      svg.appendChild(path);
      // Pointe de flèche
      var ah = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      ah.setAttribute('points',
        x2 + ',' + y2 + ' ' + (x2 - 8) + ',' + (y2 - 4) + ' ' + (x2 - 8) + ',' + (y2 + 4));
      ah.setAttribute('fill', fn.color);
      svg.appendChild(ah);
    });
  }

  function setNodeStatus(id, status) {
    var node = findNode(id);
    if (!node || !node.el) return;
    node.status = status;
    var meta = {
      idle: ['#6b7280', 'En attente'],
      running: ['#f59e0b', 'En cours'],
      done: ['#10b981', 'Terminé'],
      error: ['#ef4444', 'Erreur'],
    }[status] || ['#6b7280', status];
    var dot = node.el.querySelector('.wn-dot');
    var txt = node.el.querySelector('.wn-stxt');
    if (dot) dot.style.background = meta[0];
    if (txt) txt.textContent = meta[1];
  }

  function clearWorkflow() {
    nodes.forEach(function (n) { if (n.el) n.el.remove(); });
    nodes = [];
    connections = [];
    disarmConnection();
    el.empty.style.display = '';
    redrawLinks();
    persistWorkflow();
    setStatus('Glissez-déposez des agents pour créer votre workflow', '');
  }

  // ── Persistance (localStorage + export/import) ────────
  function workflowToData() {
    return {
      version: '1.0',
      nodes: nodes.map(function (n) {
        return {
          id: n.id, agent_type: n.agent_type, name: n.name,
          color: n.color, icon: n.icon, x: n.x, y: n.y,
        };
      }),
      connections: connections.map(function (c) { return { from: c.from, to: c.to }; }),
    };
  }

  function persistWorkflow() {
    try { localStorage.setItem(WF_STORAGE_KEY, JSON.stringify(workflowToData())); } catch (_) {}
  }

  function restoreWorkflow() {
    var raw;
    try { raw = localStorage.getItem(WF_STORAGE_KEY); } catch (_) { raw = null; }
    if (!raw) return;
    try { loadWorkflowData(JSON.parse(raw)); } catch (_) {}
  }

  function loadWorkflowData(data) {
    clearWorkflow();
    var maxNum = 0;
    (data.nodes || []).forEach(function (n) {
      var node = {
        id: n.id, agent_type: n.agent_type, name: n.name,
        color: n.color, icon: n.icon || '🤖',
        x: n.x || 0, y: n.y || 0, status: 'idle', el: null,
      };
      node.el = buildNodeEl(node);
      el.world.appendChild(node.el);
      nodes.push(node);
      var num = parseInt(String(n.id).replace(/\D/g, ''), 10);
      if (!isNaN(num) && num > maxNum) maxNum = num;
    });
    nextNodeId = maxNum + 1;
    connections = (data.connections || []).filter(function (c) {
      return findNode(c.from) && findNode(c.to);
    });
    el.empty.style.display = nodes.length ? 'none' : '';
    redrawLinks();
    persistWorkflow();
  }

  function exportWorkflow() {
    var blob = new Blob([JSON.stringify(workflowToData(), null, 2)],
      { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = 'workflow.json';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    toast('Workflow exporté');
  }

  function importWorkflowFile() {
    var inp = document.createElement('input');
    inp.type = 'file'; inp.accept = '.json,application/json';
    inp.addEventListener('change', function () {
      var f = inp.files && inp.files[0];
      if (!f) return;
      var r = new FileReader();
      r.onload = function () {
        try { loadWorkflowData(JSON.parse(r.result)); toast('Workflow chargé'); }
        catch (_) { toast('Fichier invalide', true); }
      };
      r.readAsText(f);
    });
    inp.click();
  }

  // ════════════════════════════════════════════════════
  // PIÈCES JOINTES (même mécanisme chiffré que le chat)
  // ════════════════════════════════════════════════════
  function handleFileSelect(e) {
    var files = e.target.files;
    if (!files || !files.length) return;
    for (var i = 0; i < files.length; i++) uploadFile(files[i]);
    e.target.value = '';  // permet de re-sélectionner le même fichier
  }

  function uploadFile(file) {
    var localId = 'aatt_' + (++attCounter);
    var isImage = /^image\//i.test(file.type) ||
      /\.(png|jpe?g|gif|bmp|webp|tiff?|heic|heif)$/i.test(file.name);
    var entry = {
      localId: localId, fileId: null, name: file.name || 'fichier',
      isImage: isImage, status: 'uploading', error: null,
    };
    attachments.push(entry);
    renderChips();
    if (!window.RelayCore || !window.RelayCore.uploadEncryptedFile) {
      entry.status = 'error'; entry.error = 'indisponible'; renderChips(); return;
    }
    window.RelayCore.uploadEncryptedFile(file).then(function (resp) {
      entry.fileId = resp.file_id;
      entry.isImage = !!resp.is_image;
      entry.name = resp.filename || entry.name;
      entry.status = 'ready';
      renderChips();
    }).catch(function (err) {
      entry.status = 'error';
      entry.error = (err && err.message) ? err.message : 'Erreur upload';
      renderChips();
    });
  }

  function removeAttachment(localId) {
    attachments = attachments.filter(function (a) { return a.localId !== localId; });
    renderChips();
  }

  function renderChips() {
    if (!el.attachments) return;
    el.attachments.innerHTML = '';
    attachments.forEach(function (a) {
      var chip = document.createElement('div');
      chip.className = 'attachment-chip' +
        (a.status === 'uploading' ? ' uploading' : '') +
        (a.status === 'error' ? ' error' : '');
      var icon = document.createElement('span');
      icon.className = 'chip-icon';
      icon.textContent = a.status === 'uploading' ? '⏳'
        : a.status === 'error' ? '⚠️' : (a.isImage ? '🖼️' : '📎');
      chip.appendChild(icon);
      var name = document.createElement('span');
      name.className = 'chip-name';
      name.textContent = a.status === 'error'
        ? (a.name + ' · ' + (a.error || 'erreur')) : a.name;
      chip.appendChild(name);
      var rm = document.createElement('button');
      rm.className = 'chip-remove'; rm.type = 'button'; rm.textContent = '×';
      rm.setAttribute('aria-label', 'Retirer');
      rm.onclick = function () { removeAttachment(a.localId); };
      chip.appendChild(rm);
      el.attachments.appendChild(chip);
    });
  }

  function clearAttachments() {
    attachments = [];
    renderChips();
  }

  // ════════════════════════════════════════════════════
  // EXÉCUTION
  // ════════════════════════════════════════════════════
  function execute() {
    if (isExecuting) { stopExecution(); return; }
    if (nodes.length === 0) {
      toast("Ajoutez au moins un agent au workflow", true);
      return;
    }
    var task = el.task.value.trim();
    if (!task) { toast('Décrivez la tâche à effectuer', true); return; }
    if (attachments.some(function (a) { return a.status === 'uploading'; })) {
      toast('Upload en cours, patientez…', true);
      return;
    }
    var fileIds = attachments
      .filter(function (a) { return a.status === 'ready' && a.fileId; })
      .map(function (a) { return a.fileId; });

    currentExecId = 'exec_' + Date.now() + '_' + Math.floor(Math.random() * 1e6);
    clearOutput();
    setExecuting(true);
    setStatus('⏳ Workflow en cours...', '#f59e0b');
    send({
      type: 'agent_execute',
      exec_id: currentExecId,
      task: task,
      file_ids: fileIds,
      nodes: nodes.map(function (n) {
        return { id: n.id, agent_type: n.agent_type, name: n.name, color: n.color, icon: n.icon };
      }),
      connections: connections.map(function (c) { return { from: c.from, to: c.to }; }),
    });
    // Les pièces jointes sont consommées côté serveur : on vide la liste.
    clearAttachments();
  }

  function stopExecution() {
    if (currentExecId) send({ type: 'agent_stop', exec_id: currentExecId });
    setStatus('⛔ Interruption en cours...', '#ef4444');
  }

  function setExecuting(on) {
    isExecuting = on;
    if (on) {
      el.execBtn.innerHTML = '■ Stop';
      el.execBtn.classList.add('stopmode');
      el.createBtn.disabled = true;
      el.debateBtn.disabled = true;
      el.clearBtn.disabled = true;
      if (el.attachBtn) el.attachBtn.disabled = true;
    } else {
      el.execBtn.innerHTML = '▶ Exécuter';
      el.execBtn.classList.remove('stopmode');
      el.createBtn.disabled = false;
      el.debateBtn.disabled = false;
      el.clearBtn.disabled = false;
      if (el.attachBtn) el.attachBtn.disabled = false;
      currentExecId = null;
    }
  }

  function startDebate(agentA, agentB, topic, rounds) {
    currentExecId = 'deb_' + Date.now() + '_' + Math.floor(Math.random() * 1e6);
    clearOutput();
    setExecuting(true);
    setStatus('🎭 Débat en cours...', '#8b5cf6');
    send({
      type: 'agent_debate', exec_id: currentExecId,
      agent_a: agentA, agent_b: agentB, topic: topic, rounds: rounds,
    });
  }

  // ── Rendu de la sortie ────────────────────────────────
  function clearOutput() {
    el.output.innerHTML = '';
    sections = {};
  }

  function addOutputHeader(text) {
    var h = document.createElement('div');
    h.className = 'ag-output-head';
    h.textContent = text;
    el.output.appendChild(h);
  }

  function onExecStart(data) {
    // (re)initialise la zone de sortie
    if (Object.keys(sections).length === 0 && !el.output.querySelector('.ag-output-head')) {
      clearOutput();
    }
  }

  function onSectionStart(data) {
    var sid = String(data.section_id);
    var sec = document.createElement('div');
    sec.className = 'ag-sec';
    sec.innerHTML =
      '<div class="ag-sec-head" style="border-left-color:' + (data.color || '#ff6b47') + '">' +
      '<span class="ag-sec-arrow">▾</span>' +
      '<span class="ag-sec-name">' + esc(data.title || 'Agent') + '</span>' +
      '<span class="ag-sec-state">⏳ En cours...</span>' +
      '</div>' +
      '<div class="ag-sec-body"></div>';
    var head = sec.querySelector('.ag-sec-head');
    head.addEventListener('click', function () { sec.classList.toggle('collapsed'); });
    el.output.appendChild(sec);
    sections[sid] = {
      el: sec,
      body: sec.querySelector('.ag-sec-body'),
      stateEl: sec.querySelector('.ag-sec-state'),
      text: '',
    };
    scrollOutput();
  }

  function onSectionChunk(data) {
    var s = sections[String(data.section_id)];
    if (!s) return;
    s.text = data.text || '';
    var md = window.RelayCore.renderMarkdown(
      window.RelayCore.balanceMarkdownForStreaming(s.text));
    s.body.innerHTML = md + '<span class="stream-cursor"></span>';
    s.body.scrollTop = s.body.scrollHeight;
    scrollOutput();
  }

  function onSectionEnd(data) {
    var s = sections[String(data.section_id)];
    if (!s) return;
    s.body.innerHTML = window.RelayCore.renderMarkdown(s.text);
    s.stateEl.textContent = data.success ? '✅ Terminé' : '❌ Erreur';
  }

  function onExecEnd(data) {
    setExecuting(false);
    setStatus(data.status_text || '✅ Terminé',
      data.success ? '#10b981' : (data.interrupted ? '#ef4444' : '#f59e0b'));
  }

  function onExecError(data) {
    setExecuting(false);
    setStatus('❌ ' + (data.message || 'Erreur'), '#ef4444');
    toast(data.message || 'Erreur', true);
  }

  function scrollOutput() {
    // Garde le bas de la zone de résultats visible pendant la génération.
    var scroll = $('agentsScroll');
    if (scroll) scroll.scrollTop = scroll.scrollHeight;
  }

  // ════════════════════════════════════════════════════
  // MODALE : Créer / Modifier un agent
  // ════════════════════════════════════════════════════
  function openAgentModal(agent) {
    editingKey = agent ? agent.key : null;
    el.modalTitle.innerHTML = agent ? '📝 Modifier ' + esc(agent.name)
      : '🤖 Créer un Agent Personnalisé';
    el.modalName.value = agent ? agent.name : '';
    el.modalRole.value = agent ? (agent.full_desc || agent.desc || '') : '';
    el.modalMsg.textContent = '';
    el.modalMsg.className = 'modal-msg';
    el.modalOk.textContent = agent ? 'Sauvegarder' : 'Créer';
    setModalBusy(false);
    el.modal.classList.add('visible');
  }

  function closeAgentModal() {
    el.modal.classList.remove('visible');
    editingKey = null;
  }

  function submitAgentModal() {
    if (modalBusy) return;
    var name = el.modalName.value.trim();
    var role = el.modalRole.value.trim();
    if (!name) { showModalMsg('Veuillez entrer un nom.', 'err'); return; }
    if (!role) { showModalMsg('Veuillez décrire le rôle.', 'err'); return; }
    setModalBusy(true);
    showModalMsg('⏳ Génération du system prompt en cours...', 'load');
    if (editingKey) {
      send({ type: 'agent_edit', key: editingKey, name: name, role: role });
    } else {
      send({ type: 'agent_create', name: name, role: role });
    }
  }

  function handleCreateResult(data) {
    setModalBusy(false);
    if (data.success && data.agent) {
      agents.custom.push(data.agent);
      renderGrid();
      closeAgentModal();
      toast('✅ Agent créé !');
    } else {
      showModalMsg('❌ ' + (data.error || 'Erreur'), 'err');
    }
  }

  function handleEditResult(data) {
    setModalBusy(false);
    if (data.success && data.agent) {
      var idx = -1;
      for (var i = 0; i < agents.custom.length; i++) {
        if (agents.custom[i].key === data.agent.key) { idx = i; break; }
      }
      if (idx >= 0) agents.custom[idx] = data.agent;
      else agents.custom.push(data.agent);
      renderGrid();
      closeAgentModal();
      toast('✅ Agent modifié !');
    } else {
      showModalMsg('❌ ' + (data.error || 'Erreur'), 'err');
    }
  }

  function handleDeleteResult(data) {
    if (data.success) {
      agents.custom = agents.custom.filter(function (a) { return a.key !== data.key; });
      // Retire aussi du workflow les nœuds de cet agent supprimé
      nodes.filter(function (n) { return n.agent_type === data.key; })
        .forEach(function (n) { removeNode(n.id); });
      renderGrid();
      toast('Agent supprimé');
    } else {
      toast(data.error || 'Suppression impossible', true);
    }
  }

  function setModalBusy(busy) {
    modalBusy = busy;
    el.modalOk.disabled = busy;
    el.modalCancel.disabled = busy;
  }

  function showModalMsg(text, kind) {
    el.modalMsg.textContent = text;
    el.modalMsg.className = 'modal-msg' + (kind ? ' ' + kind : '');
  }

  // ════════════════════════════════════════════════════
  // MODALE : Mode Débat
  // ════════════════════════════════════════════════════
  function openDebateModal() {
    var all = agents.builtin.concat(agents.custom);
    if (all.length < 2) { toast('Il faut au moins 2 agents', true); return; }
    var opts = all.map(function (a) {
      return '<option value="' + a.key + '">' + esc(a.icon + ' ' + a.name) + '</option>';
    }).join('');
    el.debateA.innerHTML = opts;
    el.debateB.innerHTML = opts;
    el.debateA.selectedIndex = 0;
    el.debateB.selectedIndex = Math.min(1, all.length - 1);
    el.debateTopic.value = '';
    el.debateRounds.value = 3;
    el.debateMsg.textContent = '';
    el.debateMsg.className = 'modal-msg';
    el.debateModal.classList.add('visible');
  }

  function closeDebateModal() { el.debateModal.classList.remove('visible'); }

  function submitDebateModal() {
    var a = el.debateA.value, b = el.debateB.value;
    var topic = el.debateTopic.value.trim();
    var rounds = parseInt(el.debateRounds.value, 10) || 3;
    rounds = clamp(rounds, 1, 10);
    if (a === b) { showDebateMsg('Choisis deux agents différents'); return; }
    if (!topic) { showDebateMsg('Sujet requis'); return; }
    closeDebateModal();
    startDebate(a, b, topic, rounds);
  }

  function showDebateMsg(text) {
    el.debateMsg.textContent = text;
    el.debateMsg.className = 'modal-msg err';
  }

  // ════════════════════════════════════════════════════
  // ÉVÉNEMENTS
  // ════════════════════════════════════════════════════
  function bindEvents() {
    el.execBtn.addEventListener('click', execute);
    el.createBtn.addEventListener('click', function () { openAgentModal(null); });
    el.debateBtn.addEventListener('click', openDebateModal);
    el.clearBtn.addEventListener('click', clearWorkflow);

    // Pièces jointes (bouton + → ouverture du sélecteur de fichiers)
    if (el.attachBtn && el.fileInput) {
      el.attachBtn.addEventListener('click', function () {
        if (!el.attachBtn.disabled) el.fileInput.click();
      });
      el.fileInput.addEventListener('change', handleFileSelect);
    }

    $('wfSaveBtn').addEventListener('click', function () {
      persistWorkflow(); toast('Workflow sauvegardé');
    });
    $('wfLoadBtn').addEventListener('click', importWorkflowFile);
    $('wfExportBtn').addEventListener('click', exportWorkflow);

    el.modalCancel.addEventListener('click', closeAgentModal);
    el.modalOk.addEventListener('click', submitAgentModal);
    el.modal.addEventListener('click', function (e) {
      if (e.target === el.modal && !modalBusy) closeAgentModal();
    });

    el.debateCancel.addEventListener('click', closeDebateModal);
    el.debateOk.addEventListener('click', submitDebateModal);
    el.debateModal.addEventListener('click', function (e) {
      if (e.target === el.debateModal) closeDebateModal();
    });

    // Auto-resize du textarea de tâche
    el.task.addEventListener('input', function () {
      el.task.style.height = 'auto';
      el.task.style.height = Math.min(el.task.scrollHeight, 100) + 'px';
    });

    // Annuler une connexion armée en touchant le fond du canvas
    el.canvas.addEventListener('click', function (e) {
      if (e.target === el.canvas || e.target === el.world || e.target === el.empty) {
        disarmConnection();
      }
    });
  }

  // ════════════════════════════════════════════════════
  // UTILITAIRES
  // ════════════════════════════════════════════════════
  function setStatus(text, color) {
    el.status.textContent = text;
    el.status.style.color = color || 'var(--text-secondary)';
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function esc(s) {
    return (window.RelayCore && window.RelayCore.escapeHtml)
      ? window.RelayCore.escapeHtml(String(s == null ? '' : s))
      : String(s == null ? '' : s);
  }

  var toastEl = null, toastTimer = null;
  function toast(msg, isErr) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'ag-toast';
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.className = 'ag-toast visible' + (isErr ? ' err' : '');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toastEl.className = 'ag-toast' + (isErr ? ' err' : '');
    }, 2400);
  }

  // ── Expose ────────────────────────────────────────────
  window.AgentsUI = { onMessage: onMessage, onConnect: onConnect };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
