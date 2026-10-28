/* ═══════════════════════════════════════════════════ */
/* My_AI — Markdown des réponses                         */
/*                                                       */
/* Un seul rendu pour la page du téléphone (Relay) et la */
/* vue de l'extension VS Code : ce fichier est copié tel */
/* quel dans relay/static/ et vscode_extension/media/    */
/* (tests/test_web_assets.py vérifie qu'ils sont         */
/* identiques).                                          */
/*                                                       */
/* Blocs : titres, paragraphes (un retour à la ligne     */
/* reste un retour à la ligne, comme dans la fenêtre du  */
/* PC), listes imbriquées et numérotées (le numéro de    */
/* départ est gardé), cases à cocher, blocs de code (un  */
/* bloc pas encore fermé pendant le streaming va jusqu'à */
/* la fin), tableaux, citations, séparateurs. En ligne : */
/* code, gras, italique, barré, liens http(s) et mailto, */
/* URL nues, marqueurs [n] liés au bloc 📚 Sources.      */
/*                                                       */
/* Tout le texte est échappé : seules les balises de ce  */
/* rendu arrivent dans la page, jamais celles du modèle. */
/* ═══════════════════════════════════════════════════ */

(function (root) {
  'use strict';

  // ── Lignes ────────────────────────────────────────────
  var HEADING = /^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*$/;
  var HR = /^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$/;
  var QUOTE = /^ {0,3}> ?/;
  var BULLET = /^( {0,3})([-*+])(?:([ \t]+)(.*))?$/;
  var ORDERED = /^( {0,3})(\d{1,9})([.)])(?:([ \t]+)(.*))?$/;
  var FENCE = /^( {0,3})(`{3,}|~{3,})(.*)$/;
  var SETEXT_H1 = /^ {0,3}=+[ \t]*$/;
  var TABLE_DELIM = /^ {0,3}\|?[ \t]*:?-+:?[ \t]*(?:\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/;
  var TASK = /^\[([ xX])\][ \t]+/;

  // ── En ligne ──────────────────────────────────────────
  var SPECIAL = '[\\\\`!\\[<hH]';
  var PUNCT = /[!-\/:-@\[-`{-~]/;
  var BARE_URL = /https?:\/\/[^\s<>"'`]+/iy;
  var AUTOLINK = /<((?:https?:\/\/|mailto:)[^\s<>]+)>/iy;
  var SAFE_URL = /^(?:https?:\/\/|mailto:)/i;
  // Bloc « 📚 Sources » (utils/citations.py) : « [n] [titre](url) » ou « [n] url »
  var CITATION_SOURCE = /\[(\d{1,3})\]\s*(?:\[[^\]]*\]\()?(https?:\/\/[^)\s]+)/g;

  var CURSOR = '<span class="md-cursor"></span>';
  var SLOT = /\uE000(\d+)\uE001/g;

  function escapeHtml(text) {
    return String(text == null ? '' : text)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Tabulations de l'indentation en espaces (taquets de 4) : seules les
  // espaces comptent ensuite pour l'imbrication des listes
  function expandIndent(line) {
    var match = /^[ \t]+/.exec(line);
    if (!match || match[0].indexOf('\t') === -1) return line;
    var width = 0;
    for (var i = 0; i < match[0].length; i++) {
      width = match[0].charAt(i) === '\t' ? width + 4 - (width % 4) : width + 1;
    }
    return new Array(width + 1).join(' ') + line.slice(match[0].length);
  }

  function indentOf(line) {
    return /^ */.exec(line)[0].length;
  }

  function isBlank(line) {
    return !line || !line.trim();
  }

  // ════════════════════════════════════════════════════
  // BLOCS
  // ════════════════════════════════════════════════════

  function fenceOpen(line) {
    var match = FENCE.exec(line);
    if (!match) return null;
    var info = match[3].trim();
    // « ```code``` » sur une ligne : du code en ligne, pas un bloc
    if (match[2].charAt(0) === '`' && info.indexOf('`') !== -1) return null;
    return { indent: match[1].length, marker: match[2], lang: info.split(/\s+/)[0] || '' };
  }

  function listMarker(line) {
    if (HR.test(line)) return null;
    var match = BULLET.exec(line);
    var ordered = false;
    if (!match) {
      match = ORDERED.exec(line);
      ordered = !!match;
    }
    if (!match) return null;
    var width = ordered ? match[2].length + 1 : 1;
    var gap = ordered ? match[4] : match[3];
    var rest = (ordered ? match[5] : match[4]) || '';
    var indent = match[1].length;
    var content = indent + width + (gap && rest && gap.length <= 4 ? gap.length : 1);
    return {
      ordered: ordered, indent: indent, content: content, rest: rest.replace(/^\s+/, ''),
      start: ordered ? parseInt(match[2], 10) : 1,
    };
  }

  function splitCells(line) {
    var text = line.trim();
    if (text.charAt(0) === '|') text = text.slice(1);
    if (text.charAt(text.length - 1) === '|' && text.charAt(text.length - 2) !== '\\') {
      text = text.slice(0, -1);
    }
    var cells = [];
    var cell = '';
    var code = 0;
    for (var i = 0; i < text.length; i++) {
      var ch = text.charAt(i);
      if (ch === '\\' && text.charAt(i + 1) === '|') {
        cell += '|';
        i++;
      } else if (ch === '`') {
        var run = /`+/y;
        run.lastIndex = i;
        var ticks = run.exec(text)[0];
        if (!code) code = ticks.length;
        else if (code === ticks.length) code = 0;
        cell += ticks;
        i += ticks.length - 1;
      } else if (ch === '|' && !code) {
        cells.push(cell.trim());
        cell = '';
      } else {
        cell += ch;
      }
    }
    cells.push(cell.trim());
    return cells;
  }

  function isTableStart(lines, i) {
    var head = lines[i];
    var delim = lines[i + 1];
    if (delim === undefined || head.indexOf('|') === -1 || delim.indexOf('|') === -1) return false;
    if (!TABLE_DELIM.test(delim)) return false;
    return splitCells(head).length === splitCells(delim).length;
  }

  // Une ligne qui ouvre un autre bloc arrête un paragraphe (ou une suite paresseuse)
  function startsBlock(lines, i) {
    var line = lines[i];
    return !!(fenceOpen(line) || HEADING.test(line) || HR.test(line) || QUOTE.test(line)
      || listMarker(line) || isTableStart(lines, i));
  }

  // blocks.gaps : une ligne vide sépare deux de ces blocs (liste « lâche »)
  function parseBlocks(lines) {
    var blocks = [];
    var blankBefore = false;
    var i = 0;
    while (i < lines.length) {
      var line = lines[i];
      if (isBlank(line)) {
        blankBefore = blocks.length > 0;
        i++;
        continue;
      }
      if (blankBefore) blocks.gaps = true;
      blankBefore = false;
      var fence = fenceOpen(line);
      var heading = !fence && HEADING.exec(line);
      if (fence) {
        i = parseFence(lines, i, fence, blocks);
      } else if (heading) {
        blocks.push({
          type: 'heading', level: heading[1].length,
          text: (heading[2] || '').replace(/(?:^|[ \t]+)#+$/, ''),
        });
        i++;
      } else if (HR.test(line)) {
        blocks.push({ type: 'hr' });
        i++;
      } else if (QUOTE.test(line)) {
        i = parseQuote(lines, i, blocks);
      } else if (listMarker(line)) {
        i = parseList(lines, i, blocks);
      } else if (isTableStart(lines, i)) {
        i = parseTable(lines, i, blocks);
      } else {
        i = parseParagraph(lines, i, blocks);
      }
    }
    return blocks;
  }

  function parseFence(lines, i, open, blocks) {
    var close = new RegExp('^ {0,3}' + open.marker.charAt(0) + '{' + open.marker.length + ',}[ \\t]*$');
    var body = [];
    var j = i + 1;
    var closed = false;
    while (j < lines.length) {
      if (close.test(lines[j])) {
        closed = true;
        j++;
        break;
      }
      var line = lines[j];
      body.push(line.slice(Math.min(indentOf(line), open.indent)));
      j++;
    }
    blocks.push({ type: 'code', lang: open.lang, text: body.join('\n'), open: !closed });
    return j;
  }

  function parseQuote(lines, i, blocks) {
    var inner = [];
    var j = i;
    while (j < lines.length) {
      var line = lines[j];
      if (QUOTE.test(line)) {
        inner.push(line.replace(QUOTE, ''));
      } else if (!isBlank(line) && inner.length && !isBlank(inner[inner.length - 1])
          && !startsBlock(lines, j)) {
        // Suite paresseuse : la ligne continue le paragraphe cité
        inner.push(line);
      } else {
        break;
      }
      j++;
    }
    blocks.push({ type: 'quote', children: parseBlocks(inner) });
    return j;
  }

  function parseList(lines, i, blocks) {
    var first = listMarker(lines[i]);
    var list = { type: 'list', ordered: first.ordered, start: first.start, loose: false, items: [] };
    var j = i;
    while (j < lines.length) {
      var marker = listMarker(lines[j]);
      if (!marker || marker.ordered !== list.ordered) break;
      // Indentation qui garde une ligne dans l'élément : celle de son texte,
      // ou deux espaces de plus que sa puce (« 1. a » puis «   - b » ou «  - b »)
      var keep = Math.min(marker.content, marker.indent + 2);
      var body = [marker.rest];
      var blank = false;
      j++;
      while (j < lines.length) {
        var line = lines[j];
        if (isBlank(line)) {
          body.push('');
          blank = true;
        } else if (indentOf(line) >= keep) {
          body.push(line.slice(Math.min(indentOf(line), marker.content)));
          blank = false;
        } else if (!blank && !startsBlock(lines, j)) {
          // Suite paresseuse du paragraphe de l'élément
          body.push(line.trim());
        } else {
          break;
        }
        j++;
      }
      var trailing = 0;
      while (body.length > 1 && isBlank(body[body.length - 1])) {
        body.pop();
        trailing++;
      }
      var children = parseBlocks(body);
      if (children.gaps) list.loose = true;
      var item = { children: children, task: null };
      var head = children[0];
      if (head && head.type === 'paragraph' && TASK.test(head.text)) {
        item.task = head.text.charAt(1) !== ' ';
        head.text = head.text.replace(TASK, '');
      }
      list.items.push(item);
      var next = j < lines.length ? listMarker(lines[j]) : null;
      if (!next || next.ordered !== list.ordered) break;
      if (trailing) list.loose = true;
    }
    blocks.push(list);
    return j;
  }

  function parseTable(lines, i, blocks) {
    var header = splitCells(lines[i]);
    var align = splitCells(lines[i + 1]).map(function (cell) {
      var left = cell.charAt(0) === ':';
      var right = cell.charAt(cell.length - 1) === ':';
      return left && right ? 'center' : right ? 'right' : left ? 'left' : '';
    });
    var rows = [];
    var j = i + 2;
    while (j < lines.length && !isBlank(lines[j]) && lines[j].indexOf('|') !== -1
        && !fenceOpen(lines[j]) && !QUOTE.test(lines[j])) {
      var cells = splitCells(lines[j]).slice(0, header.length);
      while (cells.length < header.length) cells.push('');
      rows.push(cells);
      j++;
    }
    blocks.push({ type: 'table', header: header, align: align, rows: rows });
    return j;
  }

  function parseParagraph(lines, i, blocks) {
    var text = [lines[i].trim()];
    var j = i + 1;
    while (j < lines.length && !isBlank(lines[j])) {
      if (SETEXT_H1.test(lines[j])) {
        blocks.push({ type: 'heading', level: 1, text: text.join(' ') });
        return j + 1;
      }
      if (startsBlock(lines, j)) break;
      text.push(lines[j].trim());
      j++;
    }
    blocks.push({ type: 'paragraph', text: text.join('\n') });
    return j;
  }

  // Le curseur du streaming suit le dernier caractère écrit
  function markLast(blocks) {
    var last = blocks[blocks.length - 1];
    if (!last) return false;
    if (last.type === 'quote') return markLast(last.children) || (last.cursor = true);
    if (last.type === 'list') {
      var item = last.items[last.items.length - 1];
      return markLast(item.children) || (item.cursor = true);
    }
    last.cursor = true;
    return true;
  }

  // ════════════════════════════════════════════════════
  // EN LIGNE
  // ════════════════════════════════════════════════════

  function anchor(url, html, cls) {
    return '<a href="' + escapeHtml(url) + '"' + (cls ? ' class="' + cls + '"' : '') +
      ' target="_blank" rel="noopener noreferrer">' + html + '</a>';
  }

  // Ponctuation de fin de phrase, parenthèse fermante sans ouvrante : hors de l'URL
  function trimUrl(url) {
    for (;;) {
      var last = url.charAt(url.length - 1);
      if (/[.,;:!?*_~]/.test(last)
          || (last === ')' && url.split('(').length < url.split(')').length)
          || (last === ']' && url.split('[').length < url.split(']').length)) {
        url = url.slice(0, -1);
      } else {
        return url;
      }
    }
  }

  // [texte](url "titre") à partir du « [ » en position i, ou null
  function matchLink(src, i) {
    var depth = 0;
    var j = i;
    for (; j < src.length; j++) {
      var ch = src.charAt(j);
      if (ch === '\\') {
        j++;
      } else if (ch === '[') {
        depth++;
      } else if (ch === ']') {
        depth--;
        if (!depth) break;
      } else if (ch === '\n' && src.charAt(j + 1) === '\n') {
        return null;
      }
    }
    if (j >= src.length || src.charAt(j + 1) !== '(') return null;
    var k = j + 2;
    while (src.charAt(k) === ' ') k++;
    var url;
    if (src.charAt(k) === '<') {
      var end = src.indexOf('>', k);
      if (end === -1) return null;
      url = src.slice(k + 1, end);
      k = end + 1;
    } else {
      var start = k;
      var parens = 0;
      for (; k < src.length; k++) {
        var c = src.charAt(k);
        if (c === '\\') {
          k++;
        } else if (c === '(') {
          parens++;
        } else if (c === ')') {
          if (!parens) break;
          parens--;
        } else if (/\s/.test(c)) {
          break;
        }
      }
      url = src.slice(start, k);
    }
    while (/[ \t\n]/.test(src.charAt(k))) k++;
    var quote = src.charAt(k);
    if (quote === '"' || quote === '\'') {
      var close = src.indexOf(quote, k + 1);
      if (close === -1) return null;
      k = close + 1;
      while (/[ \t]/.test(src.charAt(k))) k++;
    }
    if (src.charAt(k) !== ')') return null;
    return { label: src.slice(i + 1, j), url: url, end: k + 1 };
  }

  function emphasis(html) {
    return html
      .replace(/\*\*\*(?=[^\s*])([\s\S]*?[^\s*])\*\*\*/g, '<strong><em>$1</em></strong>')
      .replace(/\*\*(?=[^\s*])([\s\S]*?[^\s*])\*\*/g, '<strong>$1</strong>')
      .replace(/(^|[^\w])__(?=[^\s_])([\s\S]*?[^\s_])__(?!\w)/g, '$1<strong>$2</strong>')
      .replace(/(^|[^*\w])\*(?=[^\s*])([\s\S]*?[^\s*])\*(?![*\w])/g, '$1<em>$2</em>')
      .replace(/(^|[^\w])_(?=[^\s_])([\s\S]*?[^\s_])_(?!\w)/g, '$1<em>$2</em>')
      .replace(/~~(?=\S)([\s\S]*?\S)~~/g, '<del>$1</del>');
  }

  // Texte d'un paragraphe, d'un titre, d'une cellule → HTML. Le code, les
  // échappements et les liens sont mis de côté (emplacements \uE000n\uE001)
  // avant l'échappement du reste, puis remis à la fin.
  function inline(text, ctx, inLink) {
    var slots = [];
    function hold(html) {
      slots.push(html);
      return '\uE000' + (slots.length - 1) + '\uE001';
    }
    var out = '';
    var last = 0;
    var match;
    // Propre à cet appel : un lien rend son texte par un appel imbriqué
    var special = new RegExp(SPECIAL, 'g');
    while ((match = special.exec(text))) {
      var i = match.index;
      var ch = match[0];
      var taken = 0;
      var html = '';
      if (ch === '\\') {
        if (PUNCT.test(text.charAt(i + 1))) {
          html = escapeHtml(text.charAt(i + 1));
          taken = 2;
        }
      } else if (ch === '`') {
        var run = /`+/y;
        run.lastIndex = i;
        var ticks = run.exec(text)[0];
        var close = text.indexOf(ticks, i + ticks.length);
        while (close !== -1 && text.charAt(close + ticks.length) === '`') {
          close = text.indexOf(ticks, close + ticks.length + 1);
        }
        if (close === -1) {
          taken = ticks.length;
          html = ticks;
        } else {
          var code = text.slice(i + ticks.length, close).replace(/\n/g, ' ');
          if (/^ [\s\S]* $/.test(code) && code.trim()) code = code.slice(1, -1);
          html = '<code>' + escapeHtml(code) + '</code>';
          taken = close + ticks.length - i;
        }
      } else if (!inLink && (ch === '[' || (ch === '!' && text.charAt(i + 1) === '['))) {
        var image = ch === '!';
        var link = matchLink(text, image ? i + 1 : i);
        if (link) {
          var url = link.url.replace(/\\(.)/g, '$1');
          if (image) {
            // Pas d'image distante dans la page : un lien vers elle
            var alt = escapeHtml(link.label || url);
            html = SAFE_URL.test(url) ? anchor(url, '🖼️ ' + alt) : alt;
          } else {
            var label = inline(link.label, ctx, true);
            html = SAFE_URL.test(url) ? anchor(url, label) : label;
          }
          taken = link.end - i;
        }
      } else if (!inLink && ch === '<') {
        AUTOLINK.lastIndex = i;
        var auto = AUTOLINK.exec(text);
        if (auto) {
          html = anchor(auto[1], escapeHtml(auto[1]));
          taken = auto[0].length;
        }
      } else if (!inLink && (ch === 'h' || ch === 'H') && !/[\w\/]/.test(text.charAt(i - 1))) {
        BARE_URL.lastIndex = i;
        var bare = BARE_URL.exec(text);
        if (bare) {
          var href = trimUrl(bare[0]);
          html = anchor(href, escapeHtml(href));
          taken = href.length;
        }
      }
      if (!taken) continue;
      out += text.slice(last, i) + hold(html);
      last = i + taken;
      special.lastIndex = last;
    }
    out += text.slice(last);

    var result = emphasis(escapeHtml(out));
    if (ctx.citations && !inLink) {
      result = result.replace(/\[(\d{1,3})\]/g, function (marker, n) {
        var source = ctx.citations[n];
        return source ? anchor(source, marker, 'md-cite') : marker;
      });
    }
    // Code et liens à leur place (le texte d'un lien est déjà rendu, emplacements compris)
    return result.replace(/\n/g, '<br>').replace(SLOT, function (m, n) { return slots[n]; });
  }

  // Table n → url des sources numérotées, ou null
  function citationMap(text) {
    if (text.indexOf('http') === -1) return null;
    var sources = null;
    var match;
    CITATION_SOURCE.lastIndex = 0;
    while ((match = CITATION_SOURCE.exec(text))) {
      sources = sources || {};
      if (!(match[1] in sources)) sources[match[1]] = match[2].replace(/[.,;:) ]+$/, '');
    }
    return sources;
  }

  // ════════════════════════════════════════════════════
  // RENDU
  // ════════════════════════════════════════════════════

  function renderCode(block, ctx) {
    var lang = (block.lang || '').replace(/[^\w+#.\-]/g, '').slice(0, 24);
    var actions = ctx.codeActions || [];
    var head = '';
    if (lang || actions.length) {
      head = '<div class="md-code-head"><span class="md-code-lang">' + escapeHtml(lang) + '</span>';
      if (actions.length) {
        head += '<span class="md-code-actions">' + actions.map(function (action) {
          return '<button type="button" class="md-code-btn" data-action="' +
            escapeHtml(action.action) + '">' + escapeHtml(action.label) + '</button>';
        }).join('') + '</span>';
      }
      head += '</div>';
    }
    return '<div class="md-code">' + head + '<pre dir="ltr"><code>' + escapeHtml(block.text) +
      (block.cursor ? CURSOR : '') + '</code></pre></div>';
  }

  function renderTable(block, ctx) {
    function cell(tag, text, index, cursor) {
      var align = block.align[index];
      return '<' + tag + (align ? ' style="text-align:' + align + '"' : '') + '>' +
        inline(text, ctx) + (cursor ? CURSOR : '') + '</' + tag + '>';
    }
    var head = block.header.map(function (text, index) {
      return cell('th', text, index, block.cursor && !block.rows.length && index === block.header.length - 1);
    }).join('');
    var body = block.rows.map(function (row, r) {
      return '<tr>' + row.map(function (text, index) {
        return cell('td', text, index, block.cursor && r === block.rows.length - 1 && index === row.length - 1);
      }).join('') + '</tr>';
    }).join('');
    return '<div class="md-table"><table><thead><tr>' + head + '</tr></thead>' +
      (body ? '<tbody>' + body + '</tbody>' : '') + '</table></div>';
  }

  function renderList(block, ctx) {
    var tag = block.ordered ? 'ol' : 'ul';
    var open = '<' + tag + (block.ordered && block.start !== 1 ? ' start="' + block.start + '"' : '') + '>';
    return open + block.items.map(function (item) {
      var box = item.task === null ? ''
        : '<input type="checkbox" disabled' + (item.task ? ' checked' : '') + '> ';
      return '<li' + (item.task === null ? '' : ' class="md-task"') + '>' + box +
        renderBlocks(item.children, ctx, !block.loose) + (item.cursor ? CURSOR : '') + '</li>';
    }).join('') + '</' + tag + '>';
  }

  // tight : paragraphes d'une liste serrée, sans marge (pas de <p>)
  function renderBlocks(blocks, ctx, tight) {
    return blocks.map(function (block) {
      var cursor = block.cursor ? CURSOR : '';
      switch (block.type) {
        case 'heading':
          return '<h' + block.level + '>' + inline(block.text, ctx) + cursor + '</h' + block.level + '>';
        case 'hr':
          return '<hr>' + cursor;
        case 'code':
          return renderCode(block, ctx);
        case 'quote':
          return '<blockquote>' + renderBlocks(block.children, ctx, false) + cursor + '</blockquote>';
        case 'list':
          return renderList(block, ctx);
        case 'table':
          return renderTable(block, ctx);
        default: {
          var html = inline(block.text, ctx) + cursor;
          if (tight) return html;
          // Bloc 📚 Sources d'une recherche web : plus discret que la réponse
          return block.text.indexOf('📚') === 0 ? '<p class="md-sources">' + html + '</p>'
            : '<p>' + html + '</p>';
        }
      }
    }).join('');
  }

  /**
   * Markdown → HTML.
   * options.cursor : curseur du streaming après le dernier caractère ;
   * options.codeActions : boutons des blocs de code, [{ action, label }]
   * (la page gère leurs clics : data-action, texte dans pre > code).
   */
  function render(text, options) {
    options = options || {};
    var source = String(text == null ? '' : text)
      .replace(/[\uE000\uE001]/g, '').replace(/\r\n?/g, '\n');
    var ctx = { citations: citationMap(source), codeActions: options.codeActions };
    var blocks = parseBlocks(source.split('\n').map(expandIndent));
    if (options.cursor && !markLast(blocks)) return '<p>' + CURSOR + '</p>';
    return renderBlocks(blocks, ctx, false);
  }

  var api = { render: render, escapeHtml: escapeHtml };
  root.MyAIMarkdown = api;
  if (typeof module === 'object' && module && module.exports) module.exports = api;
})(typeof window !== 'undefined' ? window : globalThis);
