/*
 * Preview of a file of the VS Code workspace in the modal of the chat view
 * (media/preview.js), the same as for a file of the PC (relay/file_preview.py
 * builds those): image, text or code, web page, Markdown rendered with its
 * HTML, sound, video. PDF, Word, Excel and PowerPoint files are rendered by
 * My_AI on the PC, as on the phone: `upload: true` tells the provider to send
 * the file there first.
 */

import * as path from 'path';
import * as vscode from 'vscode';
import { t } from './i18n';

/** Image, sound or video put in the preview; beyond, nothing is shown */
const INLINE_MAX = 12 * 1024 * 1024;
/** Beginning of a text file shown (as much as the PC shows) */
const TEXT_MAX = 512 * 1024;
/** A bigger file is not read at all */
const READ_MAX = 64 * 1024 * 1024;
/** Images of a Markdown file put in its page (only data: images show there) */
const MARKDOWN_IMAGE_MAX = 3 * 1024 * 1024;
const MARKDOWN_IMAGES_TOTAL = 8 * 1024 * 1024;

const IMAGES: Record<string, string> = {
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif',
  '.webp': 'image/webp', '.bmp': 'image/bmp', '.ico': 'image/x-icon', '.avif': 'image/avif',
  '.svg': 'image/svg+xml',
};
const AUDIO: Record<string, string> = {
  '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.oga': 'audio/ogg',
  '.m4a': 'audio/mp4', '.aac': 'audio/aac', '.flac': 'audio/flac', '.opus': 'audio/ogg',
};
const VIDEO: Record<string, string> = {
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime', '.m4v': 'video/mp4',
  '.ogv': 'video/ogg',
};
/** Rendered by My_AI on the PC (interfaces/document_preview.py) */
const RENDERED_ON_PC = new Set(['.pdf', '.docx', '.xlsx', '.xls', '.csv', '.pptx', '.potx']);
const MARKDOWN = new Set(['.md', '.markdown']);
const HTML = new Set(['.html', '.htm', '.xhtml']);
/** Extension → language shown at the top of the code (as relay/file_preview.py) */
const LANGUAGES: Record<string, string> = {
  '.py': 'python', '.pyw': 'python', '.pyi': 'python', '.ipynb': 'json',
  '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript', '.jsx': 'jsx',
  '.ts': 'typescript', '.mts': 'typescript', '.cts': 'typescript', '.tsx': 'tsx',
  '.json': 'json', '.jsonc': 'jsonc', '.json5': 'jsonc', '.yaml': 'yaml', '.yml': 'yaml',
  '.toml': 'toml', '.ini': 'ini', '.cfg': 'ini', '.conf': 'ini', '.properties': 'ini',
  '.env': 'ini', '.xml': 'xml', '.xsd': 'xml', '.xsl': 'xml', '.csproj': 'xml',
  '.css': 'css', '.scss': 'scss', '.sass': 'scss', '.less': 'css', '.sql': 'sql',
  '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash', '.ps1': 'powershell', '.psm1': 'powershell',
  '.bat': 'bat', '.cmd': 'bat', '.c': 'c', '.h': 'c', '.cpp': 'cpp', '.cc': 'cpp',
  '.cxx': 'cpp', '.hpp': 'cpp', '.hh': 'cpp', '.cs': 'csharp', '.java': 'java',
  '.kt': 'kotlin', '.kts': 'kotlin', '.go': 'go', '.rs': 'rust', '.rb': 'ruby', '.php': 'php',
  '.pl': 'perl', '.pm': 'perl', '.lua': 'lua', '.r': 'r', '.swift': 'swift', '.scala': 'scala',
  '.dart': 'dart', '.hs': 'haskell', '.m': 'matlab', '.tex': 'latex', '.graphql': 'graphql',
  '.gql': 'graphql', '.diff': 'diff', '.patch': 'diff', '.vue': 'html', '.svelte': 'html',
  '.gradle': 'kotlin', '.dockerfile': 'dockerfile', '.mk': 'makefile',
};
const NAMED: Record<string, string> = {
  dockerfile: 'dockerfile', makefile: 'makefile', '.gitignore': 'ini',
  '.gitattributes': 'ini', '.editorconfig': 'ini', '.env': 'ini',
};

export type Preview = Record<string, unknown>;

function base64(data: Uint8Array): string {
  return Buffer.from(data).toString('base64');
}

/** Text of a file, decoded as the PC does (BOM, UTF-16), or null for a binary file */
function decode(data: Uint8Array): { text: string; truncated: boolean } | null {
  const truncated = data.length > TEXT_MAX;
  let head = data.subarray(0, TEXT_MAX);
  if (head[0] === 0xff && head[1] === 0xfe) {
    return { text: new TextDecoder('utf-16le').decode(head.subarray(2)), truncated };
  }
  if (head[0] === 0xfe && head[1] === 0xff) {
    return { text: new TextDecoder('utf-16be').decode(head.subarray(2)), truncated };
  }
  if (head[0] === 0xef && head[1] === 0xbb && head[2] === 0xbf) {
    head = head.subarray(3);
  }
  if (head.subarray(0, 8192).includes(0)) {
    return null;
  }
  try {
    return { text: new TextDecoder('utf-8', { fatal: true }).decode(head), truncated };
  } catch {
    // Cut in the middle of a character, or not UTF-8: read as Windows-1252
    try {
      return { text: new TextDecoder('windows-1252').decode(head), truncated };
    } catch {
      return { text: new TextDecoder('utf-8').decode(head), truncated };
    }
  }
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Relative images of a Markdown file (logo of a README), put in its page: only
 * those of its folder (and below), the others keep their address (the view
 * shows no image from elsewhere).
 */
async function inlineImages(html: string, file: vscode.Uri): Promise<string> {
  const folder = path.dirname(file.fsPath);
  let budget = MARKDOWN_IMAGES_TOTAL;
  const found = Array.from(html.matchAll(/(<img\b[^>]*?\bsrc\s*=\s*)(["'])([^"']*)\2/gi));
  const replaced = new Map<string, string>();
  for (const match of found) {
    const src = match[3];
    if (!src || replaced.has(src) || /^[a-z][a-z0-9+.-]*:|^[\\/#]/i.test(src)) continue;
    let relative = src.split('#')[0].split('?')[0];
    try {
      relative = decodeURIComponent(relative);
    } catch {
      continue;
    }
    const target = path.resolve(folder, relative);
    const inside = path.relative(folder, target);
    const mime = IMAGES[path.extname(target).toLowerCase()];
    if (!mime || !inside || inside.startsWith('..') || path.isAbsolute(inside)) continue;
    try {
      const uri = file.with({ path: vscode.Uri.file(target).path });
      const stat = await vscode.workspace.fs.stat(uri);
      if (stat.size > MARKDOWN_IMAGE_MAX || stat.size > budget) continue;
      const data = await vscode.workspace.fs.readFile(uri);
      budget -= data.length;
      replaced.set(src, `data:${mime};base64,${base64(data)}`);
    } catch {
      // Missing image: its address stays (nothing is shown)
    }
  }
  if (!replaced.size) return html;
  return html.replace(/(<img\b[^>]*?\bsrc\s*=\s*)(["'])([^"']*)\2/gi,
    (all, start: string, quote: string, src: string) => {
      const data = replaced.get(src);
      return data ? `${start}${quote}${data}${quote}` : all;
    });
}

/**
 * Markdown rendered by VS Code (its HTML included, as on GitHub), in a page
 * like those of the PC. The view runs no script of it (sandboxed frame).
 */
async function markdownPage(source: string, file: vscode.Uri, name: string): Promise<string | null> {
  let body: unknown;
  try {
    body = await vscode.commands.executeCommand('markdown.api.render', source);
  } catch {
    return null;
  }
  if (typeof body !== 'string') return null;
  const html = await inlineImages(body, file);
  return '<!DOCTYPE html><html><head><meta charset="UTF-8">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">' +
    `<style>${MARKDOWN_STYLE}</style></head><body><div class="sheet">` +
    `<div class="doc-kind">Markdown</div><h1 class="doc-name" dir="auto">${escapeHtml(name)}</h1>` +
    `<div class="md-file" dir="auto">${html}</div></div></body></html>`;
}

/**
 * Preview of a file of the workspace (or of this machine), for the modal.
 * Throws when the file can't be read (message for the view).
 */
export async function buildLocalPreview(uri: vscode.Uri): Promise<Preview> {
  let stat: vscode.FileStat;
  try {
    stat = await vscode.workspace.fs.stat(uri);
  } catch {
    throw new Error(t('File not found.'));
  }
  if (stat.type & vscode.FileType.Directory) {
    throw new Error(t('File not found.'));
  }
  const name = path.basename(uri.fsPath);
  const extension = path.extname(name).toLowerCase();
  const preview: Preview = { ok: true, name, size: stat.size, kind: 'none' };
  if (RENDERED_ON_PC.has(extension)) {
    return { ...preview, upload: true };
  }
  const media = IMAGES[extension] || AUDIO[extension] || VIDEO[extension];
  if (media) {
    if (stat.size > INLINE_MAX) return preview;
    const data = await vscode.workspace.fs.readFile(uri);
    const kind = IMAGES[extension] ? 'image' : AUDIO[extension] ? 'audio' : 'video';
    Object.assign(preview, { kind, mime: media, data: base64(data) });
    if (extension === '.svg') {
      const source = decode(data);
      if (source) Object.assign(preview, source, { language: 'xml' });
    }
    return preview;
  }
  if (stat.size > READ_MAX) return preview;
  const decoded = decode(await vscode.workspace.fs.readFile(uri));
  if (!decoded) return preview;
  if (MARKDOWN.has(extension)) {
    const page = await markdownPage(decoded.text, uri, name);
    if (page) {
      return { ...preview, ...decoded, kind: 'document', html: page, language: 'markdown', label: 'Markdown' };
    }
    return { ...preview, ...decoded, kind: 'text', language: 'markdown' };
  }
  if (HTML.has(extension)) {
    return { ...preview, ...decoded, kind: 'html', language: 'html' };
  }
  const language = LANGUAGES[extension] || NAMED[name.toLowerCase()] || '';
  return { ...preview, ...decoded, kind: 'text', language };
}

// Style of the pages of the PC (interfaces/document_preview.py), for a Markdown file
const MARKDOWN_STYLE = [
  ':root{--ink:#1a1a1a;--muted:#6b7280;--accent:#1f4e79;--rule:#e3e6ea}',
  'html,body{margin:0;padding:0}',
  'body{background:#212121;font-family:"Segoe UI",system-ui,-apple-system,sans-serif;',
  'padding:20px 16px 48px;box-sizing:border-box}',
  '.sheet{background:#fff;color:var(--ink);max-width:820px;margin:0 auto;',
  'padding:40px 48px 52px;border-radius:6px;box-shadow:0 6px 28px rgba(0,0,0,.45);',
  'line-height:1.6;font-size:15px}',
  '.doc-kind{color:var(--muted);font-size:11px;letter-spacing:.09em;text-transform:uppercase;',
  'margin-bottom:6px}',
  '.doc-name{color:var(--accent);font-size:25px;font-weight:650;margin:0 0 22px;',
  'padding-bottom:14px;border-bottom:2px solid var(--rule);word-break:break-word}',
  'h1,h2,h3,h4,h5,h6{color:var(--accent);line-height:1.3}',
  'h1{font-size:22px;margin:26px 0 10px}h2{font-size:19px;margin:22px 0 9px}',
  'h3{font-size:16.5px;margin:18px 0 8px}h4,h5,h6{font-size:15px;margin:15px 0 7px}',
  'p{margin:0 0 11px}ul,ol{margin:0 0 12px;padding-inline-start:24px}li{margin-bottom:4px}',
  'a{color:var(--accent)}',
  'code{background:#f2f3f5;border-radius:3px;padding:1px 5px;',
  'font-family:Consolas,"SF Mono",monospace;font-size:13px}',
  'pre{background:#f7f8fa;border:1px solid var(--rule);border-inline-start:3px solid var(--accent);',
  'border-radius:4px;padding:12px 14px;overflow-x:auto;',
  'font-family:Consolas,"SF Mono",monospace;font-size:12.5px;line-height:1.5}',
  'pre code{background:none;padding:0;font-size:inherit}',
  'blockquote{margin:12px 0;padding-block:4px;padding-inline:15px 0;',
  'border-inline-start:3px solid var(--accent);color:#4b5563;font-style:italic}',
  'hr{border:none;border-top:1px solid var(--rule);margin:22px 0}',
  'table{border-collapse:collapse;width:100%;margin:12px 0 18px;font-size:13.5px}',
  'th,td{border:1px solid #d8dde3;padding:7px 10px;text-align:start;vertical-align:top}',
  'th{background:var(--accent);color:#fff;font-weight:600}tbody tr:nth-child(even){background:#f7f9fc}',
  '.md-file img{max-width:100%;height:auto;vertical-align:middle}',
  '.md-file div[align="center"],.md-file p[align="center"]{text-align:center}',
  '.md-file summary{cursor:pointer;font-weight:600}',
  '@media (max-width:640px){body{padding:12px 8px 32px}.sheet{padding:24px 20px 32px;font-size:14.5px}}',
].join('');
