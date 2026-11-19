/* ═══════════════════════════════════════════════════════ */
/* My_AI — Aperçu d'un fichier ou d'un bloc HTML/SVG, dans  */
/* une modale qui recouvre la vue                          */
/*                                                         */
/* Copié tel quel dans relay/static/ (page du téléphone) et */
/* vscode_extension/media/ (vue de l'extension VS Code)     */
/* (tests/test_web_assets.py). Ces vues sont en hauteur :   */
/* l'aperçu les recouvre, là où la fenêtre du PC ouvre son  */
/* volet de droite. Rien n'est lu du disque ici : la page   */
/* donne le contenu, ou une fonction qui le demande (au     */
/* Relay pour un fichier du PC, à l'extension pour un       */
/* fichier de son projet). Styles : thread.css (.pv-*).     */
/* ═══════════════════════════════════════════════════════ */

(function (root) {
  'use strict';

  // Blocs rendables d'une réponse : miroir de interfaces/artifacts.py et de
  // frontend/src/lib/artifacts.ts (un bloc HTML écrit sans langage compte aussi)
  var FENCE = /```([\w+#.-]+)?[ \t]*\n?([\s\S]*?)```/g;
  var HTML_HINT = /<!doctype html|<html[\s>]|<body[\s>]|<head[\s>]|<div[\s>]|<table[\s>]/i;
  var SVG_HINT = /<svg[\s>]/i;
  var HTML_LANGS = ['html', 'htm', 'xhtml'];

  function escapeHtml(text) {
    return String(text == null ? '' : text)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function fill(template, values) {
    return String(template || '').replace(/\{(\w+)\}/g, function (match, name) {
      return values[name] === undefined ? match : String(values[name]);
    });
  }

  /** Genre d'un bloc de code : 'svg', 'html' ou null (pas d'aperçu) */
  function artifactKind(code, lang) {
    lang = String(lang || '').toLowerCase().trim();
    code = String(code || '').trim();
    if (!code) return null;
    if (lang === 'svg' || (SVG_HINT.test(code.slice(0, 300)) && SVG_HINT.test(code))) return 'svg';
    if (HTML_LANGS.indexOf(lang) !== -1) return 'html';
    if ((lang === 'xml' || lang === '' || HTML_LANGS.indexOf(lang) === -1) && HTML_HINT.test(code)) {
      return 'html';
    }
    return null;
  }

  function artifactTitle(code) {
    var title = code.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    if (title && title[1].trim()) return title[1].trim().slice(0, 80);
    var heading = code.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
    if (heading) {
      var text = heading[1].replace(/<[^>]+>/g, '').trim();
      if (text) return text.slice(0, 80);
    }
    return '';
  }

  /**
   * Blocs HTML et SVG d'une réponse, dans l'ordre : [{ type: 'artifact', kind,
   * code, title }]. untitled(kind, index) : titre d'un bloc sans <title> ni <h1>.
   */
  function detectArtifacts(text, untitled) {
    var found = [];
    if (!text || text.indexOf('```') === -1) return found;
    var match;
    FENCE.lastIndex = 0;
    while ((match = FENCE.exec(text)) !== null) {
      var code = (match[2] || '').trim();
      var kind = artifactKind(code, match[1]);
      if (!kind) continue;
      found.push({
        type: 'artifact', kind: kind, code: code,
        title: artifactTitle(code) || (untitled ? untitled(kind, found.length) : kind.toUpperCase())
      });
    }
    return found;
  }

  /** Page d'un bloc : telle quelle si c'est un document complet, enveloppée sinon */
  function artifactDoc(item) {
    var code = String(item.code || '');
    var head = code.replace(/^\s+/, '').slice(0, 200).toLowerCase();
    var full = head.indexOf('<!doctype') === 0 || head.slice(0, 50).indexOf('<html') !== -1;
    if (item.kind === 'html' && full) return code;
    var body = item.kind === 'svg'
      ? '<div style="display:flex;justify-content:center">' + code + '</div>'
      : code;
    return '<!DOCTYPE html><html><head><meta charset="UTF-8">' +
      '<meta name="viewport" content="width=device-width, initial-scale=1.0">' +
      '<style>html,body{margin:0;padding:0}body{background:#212121;color:#fff;' +
      'font-family:"Segoe UI",system-ui,sans-serif;padding:16px;box-sizing:border-box}</style>' +
      '</head><body>' + body + '</body></html>';
  }

  /**
   * Page dont les scripts s'exécutent sous une politique à nonce (vue VS Code :
   * l'iframe srcdoc hérite de la politique de la vue) : chaque <script> reçoit
   * le nonce, et les gestionnaires en ligne (onclick=…) deviennent des écouteurs
   * posés par un script final. La page reste isolée (iframe sandbox, sans
   * allow-same-origin) : le nonce ne lui ouvre que son propre document.
   */
  function scriptable(doc, nonce) {
    if (!nonce || typeof DOMParser === 'undefined') return doc;
    var parsed = new DOMParser().parseFromString(doc, 'text/html');
    var scripts = parsed.querySelectorAll('script');
    for (var s = 0; s < scripts.length; s++) scripts[s].setAttribute('nonce', nonce);
    var binds = [];
    var all = parsed.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      for (var j = el.attributes.length - 1; j >= 0; j--) {
        var attr = el.attributes[j];
        if (!/^on[a-z]+$/i.test(attr.name)) continue;
        el.setAttribute('data-myai-on', String(i));
        binds.push('bind(' + i + ',' + JSON.stringify(attr.name.slice(2).toLowerCase()) +
          ',function(event){' + attr.value + '\n});');
        el.removeAttribute(attr.name);
      }
    }
    if (binds.length) {
      var script = parsed.createElement('script');
      script.setAttribute('nonce', nonce);
      script.textContent = '(function(){function bind(n,type,handler){' +
        'var el=document.querySelector(\'[data-myai-on="\'+n+\'"]\');if(!el)return;' +
        'el.addEventListener(type,function(event){if(handler.call(el,event)===false)' +
        'event.preventDefault();});}' + binds.join('') + '})();';
      (parsed.body || parsed.documentElement).appendChild(script);
    }
    return '<!DOCTYPE html>' + parsed.documentElement.outerHTML;
  }

  function formatSize(bytes, locale) {
    if (typeof bytes !== 'number' || !isFinite(bytes) || bytes < 0) return '';
    var units = ['byte', 'kilobyte', 'megabyte', 'gigabyte'];
    var value = bytes;
    var unit = 0;
    while (value >= 1000 && unit < units.length - 1) { value /= 1000; unit++; }
    try {
      return new Intl.NumberFormat(locale || undefined, {
        style: 'unit', unit: units[unit], unitDisplay: 'short',
        maximumFractionDigits: unit === 0 || value >= 100 ? 0 : 1
      }).format(value);
    } catch (err) {
      return Math.round(value * 10) / 10 + ' ' + ['B', 'kB', 'MB', 'GB'][unit];
    }
  }

  function base64Blob(data, mime) {
    var binary = atob(data);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Blob([bytes], { type: mime || 'application/octet-stream' });
  }

  // Le fichier entier est-il déjà là (image, son, vidéo, document produit) ?
  function fileData(payload) {
    if (!payload) return '';
    if (payload.fileData) return payload.fileData;
    if (payload.download || payload.kind === 'image' || payload.kind === 'audio' ||
        payload.kind === 'video') {
      return payload.data || '';
    }
    return '';
  }

  /**
   * Modale d'aperçu. options :
   *   strings    textes : close, previous, next, position ({index}/{count}),
   *              download, openBrowser, openEditor, preview, code, copy, copied,
   *              loading, none, failed ({error}), truncated
   *   locale     langue des tailles (« 12,3 ko »)
   *   request(item, download) → Promise du contenu d'un fichier (message
   *              file_preview : { ok, kind, name, size… } ou { ok: false, error })
   *   save(name, mime, base64)  enregistre un fichier (bouton Télécharger)
   *   copy(text) → Promise      copie la source (onglet Code)
   *   openBrowser(html)         ouvre la page hors de la vue (facultatif)
   *   openEditor(item)          ouvre le fichier dans l'éditeur (VS Code)
   *   scriptNonce               nonce de la politique de la vue (VS Code)
   *   history                   le bouton Retour du téléphone ferme l'aperçu
   *
   * open(items, index) : items, ceux d'une même réponse ou d'un même message
   * (‹ k/n › passe de l'un à l'autre) :
   *   { type: 'artifact', kind: 'html' | 'svg', code, title }
   *   { type: 'file', name, path?, fileId?, payload?, editable?, download? } :
   *     payload donné (document ou image déjà reçus), sinon demandé par
   *     request() ; editable : bouton « Ouvrir dans l'éditeur » ; download:
   *     false, sans bouton Télécharger
   */
  function create(options) {
    options = options || {};
    var strings = options.strings || {};
    var state = { items: [], index: 0, token: 0, tab: 'preview', pushed: false, urls: [] };
    var els = null;

    function text(key) { return strings[key] || ''; }

    function button(cls, label, icon) {
      var el = document.createElement('button');
      el.type = 'button';
      el.className = cls;
      el.title = label;
      el.setAttribute('aria-label', label);
      el.innerHTML = icon;
      return el;
    }

    function build() {
      if (els) return els;
      var overlay = document.createElement('div');
      overlay.className = 'pv-overlay';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.innerHTML =
        '<div class="pv-modal">' +
          '<div class="pv-head">' +
            '<div class="pv-heading"><div class="pv-title" dir="auto"></div>' +
              '<div class="pv-meta" dir="auto"></div></div>' +
            '<div class="pv-nav"></div>' +
            '<div class="pv-tools"></div>' +
          '</div>' +
          '<div class="pv-tabs" role="tablist"></div>' +
          '<div class="pv-body"></div>' +
        '</div>';
      document.body.appendChild(overlay);
      els = {
        overlay: overlay,
        title: overlay.querySelector('.pv-title'),
        meta: overlay.querySelector('.pv-meta'),
        nav: overlay.querySelector('.pv-nav'),
        tools: overlay.querySelector('.pv-tools'),
        tabs: overlay.querySelector('.pv-tabs'),
        body: overlay.querySelector('.pv-body')
      };
      els.prev = button('pv-tool pv-prev', text('previous'), '&#x2039;');
      els.position = document.createElement('span');
      els.position.className = 'pv-position';
      els.next = button('pv-tool pv-next', text('next'), '&#x203A;');
      els.nav.appendChild(els.prev);
      els.nav.appendChild(els.position);
      els.nav.appendChild(els.next);
      els.prev.onclick = function () { go(-1); };
      els.next.onclick = function () { go(1); };
      els.editor = button('pv-tool', text('openEditor'), '&#x270E;');
      els.browser = button('pv-tool', text('openBrowser'), '&#x2197;');
      els.download = button('pv-tool', text('download'), '&#x2B07;');
      els.close = button('pv-tool pv-close', text('close'), '&#x2715;');
      [els.editor, els.browser, els.download, els.close].forEach(function (el) {
        els.tools.appendChild(el);
      });
      els.close.onclick = function () { close(); };
      overlay.addEventListener('click', function (event) {
        if (event.target === overlay) close();
      });
      document.addEventListener('keydown', function (event) {
        if (!isOpen()) return;
        if (event.key === 'Escape') { event.preventDefault(); close(); }
        var typing = event.target && /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName);
        if (typing) return;
        if (event.key === 'ArrowLeft') go(document.dir === 'rtl' ? 1 : -1);
        if (event.key === 'ArrowRight') go(document.dir === 'rtl' ? -1 : 1);
      });
      if (options.history && root.history && root.addEventListener) {
        root.addEventListener('popstate', function () {
          if (state.pushed) { state.pushed = false; hide(); }
        });
      }
      return els;
    }

    function isOpen() {
      return !!(els && els.overlay.classList.contains('active'));
    }

    function revoke() {
      state.urls.forEach(function (url) {
        try { URL.revokeObjectURL(url); } catch (err) { /* déjà libérée */ }
      });
      state.urls = [];
    }

    function objectUrl(data, mime) {
      var url = URL.createObjectURL(base64Blob(data, mime));
      state.urls.push(url);
      return url;
    }

    function frame(doc, sandbox) {
      var el = document.createElement('iframe');
      el.className = 'pv-frame';
      el.setAttribute('sandbox', sandbox);
      el.setAttribute('referrerpolicy', 'no-referrer');
      el.srcdoc = doc;
      return el;
    }

    function codeView(source, language, truncated) {
      var wrap = document.createElement('div');
      wrap.className = 'md pv-source';
      wrap.innerHTML =
        '<div class="md-code"><div class="md-code-head"><span class="md-code-lang">' +
          escapeHtml(language || '') + '</span><span class="md-code-actions">' +
          '<button type="button" class="md-code-btn pv-copy">' + escapeHtml(text('copy')) +
          '</button></span></div><pre dir="ltr"><code>' + escapeHtml(source) +
        '</code></pre></div>' +
        (truncated ? '<p class="pv-note">' + escapeHtml(text('truncated')) + '</p>' : '');
      var copyButton = wrap.querySelector('.pv-copy');
      if (options.copy) {
        copyButton.onclick = function () {
          Promise.resolve(options.copy(source)).then(function () {
            copyButton.textContent = text('copied');
            setTimeout(function () { copyButton.textContent = text('copy'); }, 1200);
          }).catch(function () { /* copie refusée */ });
        };
      } else {
        copyButton.style.display = 'none';
      }
      return wrap;
    }

    function message(content, cls) {
      var el = document.createElement('div');
      el.className = 'pv-message' + (cls ? ' ' + cls : '');
      el.textContent = content;
      return el;
    }

    // Les vues d'un élément : [{ id: 'preview' | 'code', render() → Element }]
    function views(item, payload) {
      var list = [];
      if (item.type === 'artifact') {
        var doc = artifactDoc(item);
        list.push({ id: 'preview', render: function () {
          return frame(scriptable(doc, options.scriptNonce), 'allow-scripts allow-forms allow-modals');
        }, page: doc });
        list.push({ id: 'code', render: function () {
          return codeView(item.code, item.kind === 'svg' ? 'svg' : 'html');
        } });
        return list;
      }
      if (!payload) return list;
      if (payload.ok === false) {
        list.push({ id: 'preview', render: function () {
          return message(fill(text('failed'), { error: payload.error || '' }), 'pv-error');
        } });
        return list;
      }
      var kind = payload.kind;
      if (kind === 'image') {
        list.push({ id: 'preview', render: function () {
          var box = document.createElement('div');
          box.className = 'pv-image';
          var img = document.createElement('img');
          img.alt = payload.name || item.name || '';
          img.src = payload.url || ('data:' + (payload.mime || 'image/png') + ';base64,' + payload.data);
          // Toucher l'image : taille réelle (on la parcourt), toucher encore : ajustée
          img.onclick = function () { box.classList.toggle('pv-zoomed'); };
          box.appendChild(img);
          return box;
        } });
      } else if (kind === 'document') {
        list.push({ id: 'preview', render: function () {
          // Page rendue par le PC (document_preview.py) : sans script ; ses liens
          // s'ouvrent dans un nouvel onglet
          return frame(payload.html || '', 'allow-popups allow-popups-to-escape-sandbox');
        }, page: payload.html || '' });
      } else if (kind === 'html') {
        // page : la même avec les feuilles de style, scripts et images de son
        // dossier (le cadre n'a pas son adresse sur le disque) ; text : sa source
        var webPage = payload.page || payload.text || '';
        list.push({ id: 'preview', render: function () {
          return frame(scriptable(webPage, options.scriptNonce),
            'allow-scripts allow-forms allow-modals');
        }, page: webPage });
      } else if (kind === 'audio' || kind === 'video') {
        list.push({ id: 'preview', render: function () {
          var box = document.createElement('div');
          box.className = 'pv-media';
          var media = document.createElement(kind);
          media.controls = true;
          if (kind === 'video') media.setAttribute('playsinline', '');
          media.src = objectUrl(payload.data, payload.mime);
          box.appendChild(media);
          return box;
        } });
      } else if (kind === 'text') {
        list.push({ id: 'preview', render: function () {
          return codeView(payload.text || '', payload.language, payload.truncated);
        } });
        return list;
      } else {
        list.push({ id: 'preview', render: function () {
          return message(text('none'), 'pv-none');
        } });
      }
      // Markdown, SVG, page web : leur source en second onglet
      if (typeof payload.text === 'string' && kind !== 'text') {
        list.push({ id: 'code', render: function () {
          return codeView(payload.text, payload.language, payload.truncated);
        } });
      }
      return list;
    }

    function showViews(item, payload) {
      var list = views(item, payload);
      els.tabs.innerHTML = '';
      els.tabs.style.display = list.length > 1 ? '' : 'none';
      if (!list.some(function (view) { return view.id === state.tab; })) state.tab = 'preview';
      list.forEach(function (view) {
        if (list.length < 2) return;
        var tab = document.createElement('button');
        tab.type = 'button';
        tab.className = 'pv-tab' + (view.id === state.tab ? ' active' : '');
        tab.setAttribute('role', 'tab');
        tab.setAttribute('aria-selected', view.id === state.tab ? 'true' : 'false');
        tab.textContent = text(view.id);
        tab.onclick = function () {
          if (state.tab === view.id) return;
          state.tab = view.id;
          showViews(item, payload);
        };
        els.tabs.appendChild(tab);
      });
      var current = list.filter(function (view) { return view.id === state.tab; })[0] || list[0];
      els.body.innerHTML = '';
      if (current) els.body.appendChild(current.render());
      var page = list.filter(function (view) { return view.page; })[0];
      els.browser.style.display = options.openBrowser && page ? '' : 'none';
      els.browser.onclick = page ? function () { options.openBrowser(page.page); } : null;
    }

    function describe(item, payload) {
      els.title.textContent = item.title || (payload && payload.name) || item.name || text('preview');
      var parts = [];
      if (payload && payload.ok !== false) {
        var size = formatSize(payload.size, options.locale);
        if (size) parts.push(size);
        if (payload.label) parts.push(payload.label);
      }
      els.meta.textContent = parts.join(' · ');
      els.meta.style.display = parts.length ? '' : 'none';
    }

    function tools(item, payload) {
      var isFile = item.type === 'file';
      var saved = fileData(payload);
      // download: false : fichier déjà sur cette machine (projet ouvert dans VS Code)
      var canSave = isFile && item.download !== false && options.save && payload &&
        payload.ok !== false && (saved || options.request);
      els.download.style.display = canSave ? '' : 'none';
      els.download.onclick = canSave ? function () { download(item, payload); } : null;
      var canEdit = isFile && item.editable && options.openEditor;
      els.editor.style.display = canEdit ? '' : 'none';
      els.editor.onclick = canEdit ? function () { options.openEditor(item); } : null;
    }

    function download(item, payload) {
      var name = (payload && payload.name) || item.name || 'fichier';
      var saved = fileData(payload);
      if (saved) {
        options.save(name, payload.mime, saved);
        return;
      }
      els.download.disabled = true;
      Promise.resolve(options.request(item, true)).then(function (file) {
        if (file && file.ok !== false && file.data) {
          options.save(file.name || name, file.mime, file.data);
        } else if (file && file.error) {
          els.meta.textContent = fill(text('failed'), { error: file.error });
          els.meta.style.display = '';
        }
      }).catch(function (err) {
        els.meta.textContent = fill(text('failed'), { error: (err && err.message) || '' });
        els.meta.style.display = '';
      }).then(function () { els.download.disabled = false; });
    }

    function show(index) {
      var item = state.items[index];
      if (!item) return;
      state.index = index;
      var token = ++state.token;
      revoke();
      var count = state.items.length;
      els.nav.style.display = count > 1 ? '' : 'none';
      els.position.textContent = fill(text('position') || '{index}/{count}',
        { index: index + 1, count: count });
      els.prev.disabled = index === 0;
      els.next.disabled = index === count - 1;
      if (item.type === 'artifact' || item.payload) {
        describe(item, item.payload);
        tools(item, item.payload);
        showViews(item, item.payload);
        return;
      }
      describe(item, null);
      tools(item, null);
      els.tabs.style.display = 'none';
      els.browser.style.display = 'none';
      els.body.innerHTML = '';
      var waiting = message(text('loading'), 'pv-loading');
      els.body.appendChild(waiting);
      var request = options.request ? options.request(item, false) : null;
      Promise.resolve(request).then(function (payload) {
        if (token !== state.token) return;
        payload = payload || { ok: false, error: '' };
        // Gardé : revenir sur ce fichier ne le redemande pas
        if (payload.ok !== false) item.payload = payload;
        describe(item, payload);
        tools(item, payload);
        showViews(item, payload);
      }).catch(function (err) {
        if (token !== state.token) return;
        var failed = { ok: false, error: (err && err.message) || String(err || '') };
        describe(item, failed);
        showViews(item, failed);
      });
    }

    function go(step) {
      var next = state.index + step;
      if (next < 0 || next >= state.items.length) return;
      state.tab = 'preview';
      show(next);
    }

    function open(items, index) {
      items = (items || []).filter(Boolean);
      if (!items.length) return;
      build();
      state.items = items;
      state.tab = 'preview';
      var wasOpen = isOpen();
      els.overlay.classList.add('active');
      show(Math.max(0, Math.min(index || 0, items.length - 1)));
      if (!wasOpen && options.history && root.history && root.history.pushState) {
        try {
          root.history.pushState({ myaiPreview: true }, '');
          state.pushed = true;
        } catch (err) { /* historique indisponible */ }
      }
      if (!wasOpen) els.close.focus();
    }

    function hide() {
      if (!els) return;
      state.token++;
      els.overlay.classList.remove('active');
      els.body.innerHTML = '';
      revoke();
    }

    function close() {
      if (state.pushed) {
        // Le retour de l'historique ferme l'aperçu (popstate)
        state.pushed = false;
        try { root.history.back(); } catch (err) { /* historique indisponible */ }
      }
      hide();
    }

    return { open: open, close: close, isOpen: isOpen };
  }

  root.MyAIPreview = {
    create: create,
    artifactKind: artifactKind,
    detectArtifacts: detectArtifacts,
    artifactDoc: artifactDoc,
    scriptable: scriptable,
    formatSize: formatSize
  };
})(typeof window !== 'undefined' ? window : this);
