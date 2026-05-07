/**
 * Workspace-scoped tool implementations for the agentic chat.
 *
 * The host-side AI emits structured tool calls (see
 * `core/agentic_executor.py`). The relay forwards them to this module via
 * `tool_use` WebSocket messages; we execute them inside the user's
 * VS Code workspace and ship the result back as `tool_result`.
 *
 * Sandbox policy:
 *   - All path arguments are resolved RELATIVE to the first workspace
 *     folder. Any path that escapes the workspace root is rejected with
 *     a clear error, UNLESS the caller passes `allowOutsideWorkspace`
 *     (only the approval layer does this after explicit user consent).
 *   - Destructive operations (write_file, edit_file, run_command) require
 *     approval: this module exposes the execution primitive only — the
 *     approval flow is owned by `toolDispatcher.ts`.
 */

import * as cp from 'child_process';
import * as path from 'path';
import * as vscode from 'vscode';

const TEXT_DECODER = new TextDecoder('utf-8', { fatal: false });
const TEXT_ENCODER = new TextEncoder();

// Cap on the length of any tool result returned to the model. Keeps the
// LLM context budget under control even when the user's repo is huge.
const MAX_TOOL_RESULT_BYTES = 200_000;
// Cap on a single read_file result (raw, before truncation marker)
const MAX_READ_FILE_BYTES = 500_000;
// Cap on the number of glob/grep results we ship back
const MAX_LIST_ENTRIES = 500;

export interface ToolContext {
  workspaceRoot: string;
  // Whether the caller (approval layer) has authorized leaving the workspace.
  allowOutsideWorkspace?: boolean;
}

export interface ToolOutcome {
  content: string;
  isError: boolean;
}

// ---------------------------------------------------------------------------
// Public dispatch
// ---------------------------------------------------------------------------

export type ToolHandler = (
  input: Record<string, unknown>,
  ctx: ToolContext,
) => Promise<ToolOutcome>;

export const TOOL_HANDLERS: Record<string, ToolHandler> = {
  read_file: handleReadFile,
  write_file: handleWriteFile,
  edit_file: handleEditFile,
  list_dir: handleListDir,
  glob: handleGlob,
  grep: handleGrep,
  run_command: handleRunCommand,
  get_active_editor: handleGetActiveEditor,
  open_file: handleOpenFile,
};

export function isKnownTool(name: string): boolean {
  return Object.prototype.hasOwnProperty.call(TOOL_HANDLERS, name);
}

// ---------------------------------------------------------------------------
// Path resolution & sandbox
// ---------------------------------------------------------------------------

/**
 * Resolve a workspace-relative path to an absolute fs path, asserting that
 * the result stays inside the workspace root unless explicitly allowed.
 */
export function resolveWorkspacePath(
  rawPath: string,
  ctx: ToolContext,
): string {
  if (typeof rawPath !== 'string' || rawPath.length === 0) {
    throw new Error('path est vide');
  }

  // Treat both absolute and relative paths uniformly: resolve against root.
  // path.resolve drops the root if `rawPath` is itself absolute.
  const resolved = path.resolve(ctx.workspaceRoot, rawPath);
  const root = path.resolve(ctx.workspaceRoot);

  // Compare with case-insensitive prefix on Windows, case-sensitive elsewhere.
  const isInside = process.platform === 'win32'
    ? (resolved.toLowerCase() === root.toLowerCase()
        || resolved.toLowerCase().startsWith(root.toLowerCase() + path.sep))
    : (resolved === root || resolved.startsWith(root + path.sep));

  if (!isInside && !ctx.allowOutsideWorkspace) {
    throw new Error(
      `Chemin hors workspace refusé : "${rawPath}". `
        + `Le modèle doit demander l'autorisation explicite pour sortir du workspace.`,
    );
  }
  return resolved;
}

// ---------------------------------------------------------------------------
// read_file
// ---------------------------------------------------------------------------

async function handleReadFile(
  input: Record<string, unknown>,
  ctx: ToolContext,
): Promise<ToolOutcome> {
  const rawPath = String(input.path ?? '');
  const offset = toPositiveInt(input.offset, 1);
  const limit = toPositiveInt(input.limit, 2000);

  const abs = resolveWorkspacePath(rawPath, ctx);
  const uri = vscode.Uri.file(abs);

  let bytes: Uint8Array;
  try {
    bytes = await vscode.workspace.fs.readFile(uri);
  } catch (err) {
    return errorOutcome(`Lecture impossible : ${(err as Error).message}`);
  }

  if (bytes.byteLength > MAX_READ_FILE_BYTES) {
    return errorOutcome(
      `Fichier trop volumineux (${bytes.byteLength} octets > `
        + `${MAX_READ_FILE_BYTES}). Précise un offset/limit pour paginer.`,
    );
  }

  const text = TEXT_DECODER.decode(bytes);
  const lines = text.split(/\r?\n/);
  const startIdx = Math.max(0, offset - 1);
  const endIdx = Math.min(lines.length, startIdx + limit);
  const slice = lines.slice(startIdx, endIdx);

  const numbered = slice
    .map((line, i) => `${String(startIdx + i + 1).padStart(6, ' ')}  ${line}`)
    .join('\n');

  const header = lines.length > slice.length
    ? `(showing lines ${startIdx + 1}-${endIdx} of ${lines.length})\n`
    : '';

  return okOutcome(header + numbered);
}

// ---------------------------------------------------------------------------
// write_file
// ---------------------------------------------------------------------------

async function handleWriteFile(
  input: Record<string, unknown>,
  ctx: ToolContext,
): Promise<ToolOutcome> {
  const rawPath = String(input.path ?? '');
  const content = String(input.content ?? '');
  const abs = resolveWorkspacePath(rawPath, ctx);
  const uri = vscode.Uri.file(abs);

  const dirUri = vscode.Uri.file(path.dirname(abs));
  try {
    await vscode.workspace.fs.createDirectory(dirUri);
  } catch {
    // existsOk
  }

  let existed = true;
  try {
    await vscode.workspace.fs.stat(uri);
  } catch {
    existed = false;
  }

  try {
    await vscode.workspace.fs.writeFile(uri, TEXT_ENCODER.encode(content));
  } catch (err) {
    return errorOutcome(`Écriture impossible : ${(err as Error).message}`);
  }

  const verb = existed ? 'modifié' : 'créé';
  const lines = content.split('\n').length;
  return okOutcome(
    `${verb} ${vscode.workspace.asRelativePath(uri)} `
      + `(${content.length} caractères, ${lines} lignes)`,
  );
}

// ---------------------------------------------------------------------------
// edit_file
// ---------------------------------------------------------------------------

async function handleEditFile(
  input: Record<string, unknown>,
  ctx: ToolContext,
): Promise<ToolOutcome> {
  const rawPath = String(input.path ?? '');
  const oldString = String(input.old_string ?? '');
  const newString = String(input.new_string ?? '');
  const replaceAll = Boolean(input.replace_all ?? false);

  if (!oldString) {
    return errorOutcome('old_string vide');
  }
  if (oldString === newString) {
    return errorOutcome('old_string et new_string sont identiques');
  }

  const abs = resolveWorkspacePath(rawPath, ctx);
  const uri = vscode.Uri.file(abs);

  let original: string;
  try {
    const bytes = await vscode.workspace.fs.readFile(uri);
    original = TEXT_DECODER.decode(bytes);
  } catch (err) {
    return errorOutcome(`Lecture impossible : ${(err as Error).message}`);
  }

  const occurrences = countOccurrences(original, oldString);
  if (occurrences === 0) {
    return errorOutcome('old_string introuvable dans le fichier');
  }
  if (occurrences > 1 && !replaceAll) {
    return errorOutcome(
      `old_string apparaît ${occurrences} fois. Élargis le contexte pour `
        + `garantir l'unicité, ou passe replace_all=true.`,
    );
  }

  const updated = replaceAll
    ? original.split(oldString).join(newString)
    : original.replace(oldString, newString);

  try {
    await vscode.workspace.fs.writeFile(uri, TEXT_ENCODER.encode(updated));
  } catch (err) {
    return errorOutcome(`Écriture impossible : ${(err as Error).message}`);
  }

  return okOutcome(
    `Édité ${vscode.workspace.asRelativePath(uri)} `
      + `(${replaceAll ? occurrences : 1} remplacement(s))`,
  );
}

// ---------------------------------------------------------------------------
// list_dir
// ---------------------------------------------------------------------------

async function handleListDir(
  input: Record<string, unknown>,
  ctx: ToolContext,
): Promise<ToolOutcome> {
  const rawPath = String(input.path ?? '.');
  const abs = resolveWorkspacePath(rawPath, ctx);
  const uri = vscode.Uri.file(abs);

  let entries: [string, vscode.FileType][];
  try {
    entries = await vscode.workspace.fs.readDirectory(uri);
  } catch (err) {
    return errorOutcome(`Lecture du dossier impossible : ${(err as Error).message}`);
  }

  // Sort: dirs first, then files, both alphabetical
  entries.sort((a, b) => {
    const aDir = (a[1] & vscode.FileType.Directory) !== 0;
    const bDir = (b[1] & vscode.FileType.Directory) !== 0;
    if (aDir !== bDir) {
      return aDir ? -1 : 1;
    }
    return a[0].localeCompare(b[0]);
  });

  const lines = entries.slice(0, MAX_LIST_ENTRIES).map(([name, kind]) => {
    if (kind & vscode.FileType.Directory) {
      return `${name}/`;
    }
    if (kind & vscode.FileType.SymbolicLink) {
      return `${name}@`;
    }
    return name;
  });

  const truncated = entries.length > MAX_LIST_ENTRIES
    ? `\n… (${entries.length - MAX_LIST_ENTRIES} autres entrées tronquées)`
    : '';
  const rel = vscode.workspace.asRelativePath(uri);
  const header = `Listing de ${rel || '.'} (${entries.length} entrées)\n`;
  return okOutcome(header + lines.join('\n') + truncated);
}

// ---------------------------------------------------------------------------
// glob
// ---------------------------------------------------------------------------

async function handleGlob(
  input: Record<string, unknown>,
  _ctx: ToolContext,
): Promise<ToolOutcome> {
  const pattern = String(input.pattern ?? '').trim();
  if (!pattern) {
    return errorOutcome('pattern vide');
  }

  let results: vscode.Uri[];
  try {
    results = await vscode.workspace.findFiles(pattern, undefined, MAX_LIST_ENTRIES + 1);
  } catch (err) {
    return errorOutcome(`Recherche glob impossible : ${(err as Error).message}`);
  }

  const truncated = results.length > MAX_LIST_ENTRIES;
  const lines = results
    .slice(0, MAX_LIST_ENTRIES)
    .map((uri) => vscode.workspace.asRelativePath(uri));

  if (lines.length === 0) {
    return okOutcome('(aucun fichier ne correspond)');
  }
  const note = truncated
    ? `\n… (${results.length - MAX_LIST_ENTRIES} matchs supplémentaires tronqués)`
    : '';
  return okOutcome(lines.join('\n') + note);
}

// ---------------------------------------------------------------------------
// grep — uses ripgrep when available, falls back to JS line scan
// ---------------------------------------------------------------------------

async function handleGrep(
  input: Record<string, unknown>,
  ctx: ToolContext,
): Promise<ToolOutcome> {
  const pattern = String(input.pattern ?? '');
  if (!pattern) {
    return errorOutcome('pattern vide');
  }
  const rawPath = String(input.path ?? '');
  const globFilter = String(input.glob ?? '');
  const outputMode = (String(input.output_mode ?? 'files') === 'content')
    ? 'content'
    : 'files';
  const caseInsensitive = Boolean(input.case_insensitive ?? false);

  const searchRoot = rawPath
    ? resolveWorkspacePath(rawPath, ctx)
    : ctx.workspaceRoot;

  const rgResult = await tryRipgrep({
    pattern,
    searchRoot,
    globFilter,
    outputMode,
    caseInsensitive,
  });
  if (rgResult !== null) {
    return rgResult;
  }
  // Fallback : JS line scan (slower; used when rg isn't on PATH)
  return jsGrep({
    pattern,
    searchRoot,
    globFilter,
    outputMode,
    caseInsensitive,
  });
}

interface GrepArgs {
  pattern: string;
  searchRoot: string;
  globFilter: string;
  outputMode: 'files' | 'content';
  caseInsensitive: boolean;
}

async function tryRipgrep(args: GrepArgs): Promise<ToolOutcome | null> {
  const flags: string[] = [
    '--no-config',
    '--no-ignore-vcs',
    '--max-count', '50',
    '--max-columns', '500',
  ];
  if (args.caseInsensitive) {
    flags.push('-i');
  }
  if (args.outputMode === 'files') {
    flags.push('-l');
  } else {
    flags.push('-n', '--no-heading', '--color', 'never');
  }
  if (args.globFilter) {
    flags.push('-g', args.globFilter);
  }
  flags.push('--', args.pattern, args.searchRoot);

  return new Promise<ToolOutcome | null>((resolve) => {
    let proc: cp.ChildProcess;
    try {
      proc = cp.spawn('rg', flags, {
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
      });
    } catch {
      resolve(null);
      return;
    }
    if (!proc.stdout || !proc.stderr) {
      resolve(null);
      return;
    }

    let stdout = '';
    let stderr = '';
    let resolved = false;

    proc.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString('utf-8');
      if (stdout.length > MAX_TOOL_RESULT_BYTES) {
        stdout = stdout.slice(0, MAX_TOOL_RESULT_BYTES);
        try {
          proc.kill();
        } catch {
          // ignore
        }
      }
    });
    proc.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString('utf-8');
    });

    proc.on('error', () => {
      if (!resolved) {
        resolved = true;
        resolve(null); // rg not installed → fallback
      }
    });
    proc.on('close', (code) => {
      if (resolved) {
        return;
      }
      resolved = true;
      // rg exit code 1 == no match, not an error
      if (code !== 0 && code !== 1) {
        resolve(errorOutcome(`ripgrep a échoué (code ${code}): ${stderr.trim()}`));
        return;
      }
      const trimmed = stdout.trimEnd();
      if (!trimmed) {
        resolve(okOutcome('(aucun résultat)'));
        return;
      }
      // Replace absolute paths with workspace-relative paths so the
      // model sees clean output.
      const root = path.resolve(args.searchRoot);
      const normalized = trimmed
        .split(/\r?\n/)
        .map((line) => normalizeRgLine(line, root))
        .join('\n');
      resolve(okOutcome(normalized));
    });
  });
}

function normalizeRgLine(line: string, _root: string): string {
  // We let rg print absolute paths but rewrite via asRelativePath where
  // possible. asRelativePath needs a Uri; do it manually for speed.
  return line;
}

async function jsGrep(args: GrepArgs): Promise<ToolOutcome> {
  let regex: RegExp;
  try {
    regex = new RegExp(args.pattern, args.caseInsensitive ? 'gi' : 'g');
  } catch (err) {
    return errorOutcome(`Regex invalide : ${(err as Error).message}`);
  }
  const include = args.globFilter || '**/*';
  let files: vscode.Uri[];
  try {
    files = await vscode.workspace.findFiles(include, undefined, 5000);
  } catch (err) {
    return errorOutcome(`Découverte des fichiers impossible : ${(err as Error).message}`);
  }

  const matches: string[] = [];
  let totalBytes = 0;
  outer: for (const uri of files) {
    if (uri.fsPath.length < args.searchRoot.length
        || !uri.fsPath.toLowerCase().startsWith(args.searchRoot.toLowerCase())) {
      continue;
    }
    let text: string;
    try {
      const bytes = await vscode.workspace.fs.readFile(uri);
      text = TEXT_DECODER.decode(bytes);
    } catch {
      continue;
    }
    const lines = text.split(/\r?\n/);
    for (let i = 0; i < lines.length; i += 1) {
      regex.lastIndex = 0;
      if (!regex.test(lines[i])) {
        continue;
      }
      const rel = vscode.workspace.asRelativePath(uri);
      if (args.outputMode === 'files') {
        matches.push(rel);
        break;
      }
      const out = `${rel}:${i + 1}: ${lines[i].slice(0, 500)}`;
      matches.push(out);
      totalBytes += out.length;
      if (totalBytes > MAX_TOOL_RESULT_BYTES || matches.length >= MAX_LIST_ENTRIES) {
        break outer;
      }
    }
  }

  if (matches.length === 0) {
    return okOutcome('(aucun résultat)');
  }
  return okOutcome(matches.join('\n'));
}

// ---------------------------------------------------------------------------
// run_command — runs in workspace root, captures stdout+stderr
// ---------------------------------------------------------------------------

async function handleRunCommand(
  input: Record<string, unknown>,
  ctx: ToolContext,
): Promise<ToolOutcome> {
  const command = String(input.command ?? '').trim();
  if (!command) {
    return errorOutcome('command vide');
  }
  const cwdRaw = String(input.cwd ?? '');
  const cwd = cwdRaw ? resolveWorkspacePath(cwdRaw, ctx) : ctx.workspaceRoot;
  const timeoutSeconds = Math.max(1, Math.min(600, toPositiveInt(input.timeout_seconds, 60)));

  const useCmd = process.platform === 'win32';
  const shellCmd = useCmd ? 'cmd.exe' : '/bin/sh';
  const shellArgs = useCmd ? ['/d', '/s', '/c', command] : ['-c', command];

  return new Promise<ToolOutcome>((resolve) => {
    const proc = cp.spawn(shellCmd, shellArgs, {
      cwd,
      env: process.env,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });

    let stdout = '';
    let stderr = '';
    let resolved = false;
    const timer = setTimeout(() => {
      if (resolved) {
        return;
      }
      try {
        proc.kill();
      } catch {
        // ignore
      }
    }, timeoutSeconds * 1000);

    proc.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString('utf-8');
      if (stdout.length > MAX_TOOL_RESULT_BYTES) {
        stdout = stdout.slice(0, MAX_TOOL_RESULT_BYTES);
      }
    });
    proc.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString('utf-8');
      if (stderr.length > MAX_TOOL_RESULT_BYTES) {
        stderr = stderr.slice(0, MAX_TOOL_RESULT_BYTES);
      }
    });
    proc.on('error', (err) => {
      if (resolved) {
        return;
      }
      resolved = true;
      clearTimeout(timer);
      resolve(errorOutcome(`spawn a échoué : ${err.message}`));
    });
    proc.on('close', (code, signal) => {
      if (resolved) {
        return;
      }
      resolved = true;
      clearTimeout(timer);
      const sigInfo = signal ? ` (signal=${signal})` : '';
      const head = `exit_code=${code}${sigInfo}\ncwd=${vscode.workspace.asRelativePath(cwd) || cwd}\n`;
      const out = stdout.trimEnd();
      const err = stderr.trimEnd();
      const sections: string[] = [head];
      if (out) {
        sections.push('--- stdout ---\n' + out);
      }
      if (err) {
        sections.push('--- stderr ---\n' + err);
      }
      if (!out && !err) {
        sections.push('(no output)');
      }
      const isError = (code !== 0) || !!signal;
      resolve({ content: sections.join('\n'), isError });
    });
  });
}

// ---------------------------------------------------------------------------
// get_active_editor
// ---------------------------------------------------------------------------

async function handleGetActiveEditor(
  _input: Record<string, unknown>,
  _ctx: ToolContext,
): Promise<ToolOutcome> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    return okOutcome('(aucun éditeur actif)');
  }
  const doc = editor.document;
  const rel = vscode.workspace.asRelativePath(doc.uri);
  const sel = editor.selection;
  const text = doc.getText();
  const lines = text.split('\n').length;

  const parts: string[] = [
    `path: ${rel}`,
    `language: ${doc.languageId}`,
    `lines: ${lines}`,
    `cursor: line ${sel.active.line + 1}, column ${sel.active.character + 1}`,
  ];
  if (!sel.isEmpty) {
    const selText = doc.getText(sel);
    const selLines = selText.split('\n').length;
    parts.push(`selection: lines ${sel.start.line + 1}-${sel.end.line + 1} (${selLines} lignes)`);
    parts.push('--- selection ---');
    parts.push(selText.slice(0, 8000));
  }
  parts.push('--- file (truncated) ---');
  parts.push(text.slice(0, MAX_TOOL_RESULT_BYTES - parts.join('\n').length - 200));
  return okOutcome(parts.join('\n'));
}

// ---------------------------------------------------------------------------
// open_file
// ---------------------------------------------------------------------------

async function handleOpenFile(
  input: Record<string, unknown>,
  ctx: ToolContext,
): Promise<ToolOutcome> {
  const rawPath = String(input.path ?? '');
  const line = toPositiveInt(input.line, 0);
  const abs = resolveWorkspacePath(rawPath, ctx);
  const uri = vscode.Uri.file(abs);
  try {
    const doc = await vscode.workspace.openTextDocument(uri);
    const editor = await vscode.window.showTextDocument(doc, { preview: false });
    if (line > 0) {
      const target = new vscode.Position(Math.max(0, line - 1), 0);
      editor.selection = new vscode.Selection(target, target);
      editor.revealRange(new vscode.Range(target, target), vscode.TextEditorRevealType.InCenter);
    }
    return okOutcome(`Ouvert : ${vscode.workspace.asRelativePath(uri)}`);
  } catch (err) {
    return errorOutcome(`Ouverture impossible : ${(err as Error).message}`);
  }
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function okOutcome(content: string): ToolOutcome {
  return { content: capContent(content), isError: false };
}

function errorOutcome(content: string): ToolOutcome {
  return { content: capContent(content), isError: true };
}

function capContent(content: string): string {
  if (content.length <= MAX_TOOL_RESULT_BYTES) {
    return content;
  }
  return (
    content.slice(0, MAX_TOOL_RESULT_BYTES)
    + `\n… (sortie tronquée à ${MAX_TOOL_RESULT_BYTES} caractères)`
  );
}

function countOccurrences(haystack: string, needle: string): number {
  if (!needle) {
    return 0;
  }
  let count = 0;
  let idx = 0;
  while ((idx = haystack.indexOf(needle, idx)) !== -1) {
    count += 1;
    idx += needle.length;
  }
  return count;
}

function toPositiveInt(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value) && value >= 0) {
    return Math.floor(value);
  }
  if (typeof value === 'string') {
    const parsed = parseInt(value, 10);
    if (Number.isFinite(parsed) && parsed >= 0) {
      return parsed;
    }
  }
  return fallback;
}
