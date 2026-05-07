/**
 * Routes incoming `tool_use` requests from the host's agentic loop to the
 * proper handler in `agentTools.ts`, applying the approval policy along
 * the way.
 *
 * Policy:
 *   - Read-only tools (read_file, list_dir, glob, grep, get_active_editor,
 *     open_file) run without prompting.
 *   - Mutating tools (write_file, edit_file, run_command) require the
 *     user's consent. The user can opt into "Allow this session" so the
 *     same kind of tool (or the exact pair name+path for file edits) is
 *     approved silently afterwards.
 *   - Paths that escape the workspace root are NEVER auto-approvable: the
 *     user is always prompted explicitly.
 */

import * as path from 'path';
import * as vscode from 'vscode';
import {
  isKnownTool,
  TOOL_HANDLERS,
  ToolContext,
  ToolOutcome,
} from './agentTools';
import { ToolCall, ToolResult } from './types';

// ---------------------------------------------------------------------------
// Approval scope
// ---------------------------------------------------------------------------

type ApprovalKey = string;

interface ApprovalPolicy {
  // Approvals granted "for the whole session" by tool name.
  approvedTools: Set<string>;
  // Approvals for a specific (tool, target) pair, e.g. "write_file:src/foo.ts".
  approvedTargets: Set<ApprovalKey>;
  // Approvals for paths that escape the workspace.
  approvedOutsidePaths: Set<string>;
}

function newPolicy(): ApprovalPolicy {
  return {
    approvedTools: new Set(),
    approvedTargets: new Set(),
    approvedOutsidePaths: new Set(),
  };
}

// One policy per ToolDispatcher (one per ConnectionManager session).
// Cleared on disconnect by re-instantiating the dispatcher.

// ---------------------------------------------------------------------------
// Dispatcher
// ---------------------------------------------------------------------------

export interface DispatchEvent {
  kind:
    | 'requested'
    | 'awaiting-approval'
    | 'denied'
    | 'running'
    | 'completed'
    | 'failed';
  callId: string;
  toolName: string;
  input: Record<string, unknown>;
  result?: ToolOutcome;
  error?: string;
}

export type DispatchListener = (event: DispatchEvent) => void;

export class ToolDispatcher {
  private policy: ApprovalPolicy = newPolicy();
  private listeners: DispatchListener[] = [];

  onEvent(listener: DispatchListener): vscode.Disposable {
    this.listeners.push(listener);
    return new vscode.Disposable(() => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    });
  }

  resetApprovals(): void {
    this.policy = newPolicy();
  }

  async dispatch(call: ToolCall): Promise<ToolResult> {
    const callId = call.call_id;
    const name = String(call.name ?? '');
    const input = (call.input && typeof call.input === 'object') ? call.input : {};

    this.emit({ kind: 'requested', callId, toolName: name, input });

    if (!isKnownTool(name)) {
      const result: ToolResult = {
        call_id: callId,
        content: `Outil inconnu : "${name}"`,
        is_error: true,
      };
      this.emit({
        kind: 'failed',
        callId,
        toolName: name,
        input,
        error: result.content,
      });
      return result;
    }

    const ctx = await this.buildContext(name, input);
    if (!ctx) {
      const result: ToolResult = {
        call_id: callId,
        content: 'Aucun workspace VS Code ouvert. '
          + 'Ouvre un dossier dans VS Code pour permettre à l\'agent d\'agir.',
        is_error: true,
      };
      this.emit({
        kind: 'failed',
        callId,
        toolName: name,
        input,
        error: result.content,
      });
      return result;
    }

    const decision = await this.requireApproval(name, input, ctx, callId);
    if (decision === 'denied') {
      const result: ToolResult = {
        call_id: callId,
        content: 'L\'utilisateur a refusé cette opération.',
        is_error: true,
      };
      this.emit({ kind: 'denied', callId, toolName: name, input });
      return result;
    }

    this.emit({ kind: 'running', callId, toolName: name, input });

    const handler = TOOL_HANDLERS[name];
    let outcome: ToolOutcome;
    try {
      outcome = await handler(input, ctx);
    } catch (err) {
      outcome = {
        content: `Exception côté extension : ${(err as Error).message}`,
        isError: true,
      };
    }

    const result: ToolResult = {
      call_id: callId,
      content: outcome.content,
      is_error: outcome.isError,
    };

    this.emit({
      kind: outcome.isError ? 'failed' : 'completed',
      callId,
      toolName: name,
      input,
      result: outcome,
      error: outcome.isError ? outcome.content : undefined,
    });
    return result;
  }

  // ----------------------------------------------------------------
  // Approval flow
  // ----------------------------------------------------------------

  private async buildContext(
    toolName: string,
    input: Record<string, unknown>,
  ): Promise<ToolContext | null> {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
      return null;
    }
    const root = folders[0].uri.fsPath;

    // Pre-flight: if the path argument resolves outside the workspace,
    // ask the user before anything else.
    const candidatePath = pickPathArg(toolName, input);
    if (candidatePath) {
      const resolved = path.resolve(root, candidatePath);
      const inside = isInsideRoot(resolved, root);
      if (!inside) {
        const allow = await this.promptOutsideWorkspace(toolName, candidatePath);
        if (!allow) {
          return null;
        }
        return { workspaceRoot: root, allowOutsideWorkspace: true };
      }
    }
    return { workspaceRoot: root };
  }

  private async promptOutsideWorkspace(
    toolName: string,
    rawPath: string,
  ): Promise<boolean> {
    if (this.policy.approvedOutsidePaths.has(rawPath)) {
      return true;
    }
    const allowOnce = vscode.l10n.t('Allow once');
    const choice = await vscode.window.showWarningMessage(
      vscode.l10n.t(
        'My_AI wants to access "{0}" via {1}, outside the VS Code workspace. Allow?',
        rawPath,
        toolName,
      ),
      { modal: true },
      allowOnce,
    );
    if (choice === allowOnce) {
      this.policy.approvedOutsidePaths.add(rawPath);
      return true;
    }
    return false;
  }

  private async requireApproval(
    toolName: string,
    input: Record<string, unknown>,
    ctx: ToolContext,
    callId: string,
  ): Promise<'approved' | 'denied'> {
    if (isReadOnlyTool(toolName)) {
      return 'approved';
    }

    const targetKey = `${toolName}:${pickPathArg(toolName, input) ?? ''}`;
    if (
      this.policy.approvedTools.has(toolName)
      || this.policy.approvedTargets.has(targetKey)
    ) {
      return 'approved';
    }

    this.emit({
      kind: 'awaiting-approval',
      callId,
      toolName,
      input,
    });

    const decision = await this.showApprovalDialog(toolName, input, ctx);
    switch (decision) {
      case 'allow-once':
        return 'approved';
      case 'allow-target':
        this.policy.approvedTargets.add(targetKey);
        return 'approved';
      case 'allow-tool':
        this.policy.approvedTools.add(toolName);
        return 'approved';
      case 'deny':
      default:
        return 'denied';
    }
  }

  private async showApprovalDialog(
    toolName: string,
    input: Record<string, unknown>,
    _ctx: ToolContext,
  ): Promise<'allow-once' | 'allow-target' | 'allow-tool' | 'deny'> {
    const summary = describeToolForApproval(toolName, input);
    const allowOnce = vscode.l10n.t('Allow once');
    const allowTarget = toolName === 'run_command'
      ? null
      : vscode.l10n.t('Allow for this file');
    const allowTool = vscode.l10n.t('Allow all {0} this session', toolName);

    const buttons: string[] = [allowOnce];
    if (allowTarget) {
      buttons.push(allowTarget);
    }
    buttons.push(allowTool);

    const choice = await vscode.window.showWarningMessage(
      summary,
      { modal: true, detail: vscode.l10n.t('Default: deny') },
      ...buttons,
    );

    if (choice === allowOnce) {
      return 'allow-once';
    }
    if (allowTarget && choice === allowTarget) {
      return 'allow-target';
    }
    if (choice === allowTool) {
      return 'allow-tool';
    }
    return 'deny';
  }

  private emit(event: DispatchEvent): void {
    for (const listener of this.listeners) {
      try {
        listener(event);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('[my-ai-relay] dispatcher listener threw:', err);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function isReadOnlyTool(name: string): boolean {
  return (
    name === 'read_file'
    || name === 'list_dir'
    || name === 'glob'
    || name === 'grep'
    || name === 'get_active_editor'
    || name === 'open_file'
  );
}

function pickPathArg(
  toolName: string,
  input: Record<string, unknown>,
): string | undefined {
  if (toolName === 'run_command') {
    return undefined;
  }
  const candidate = input.path;
  if (typeof candidate === 'string' && candidate.length > 0) {
    return candidate;
  }
  return undefined;
}

function isInsideRoot(absPath: string, root: string): boolean {
  const r = path.resolve(root);
  const p = path.resolve(absPath);
  if (process.platform === 'win32') {
    return p.toLowerCase() === r.toLowerCase()
      || p.toLowerCase().startsWith(r.toLowerCase() + path.sep);
  }
  return p === r || p.startsWith(r + path.sep);
}

function describeToolForApproval(
  toolName: string,
  input: Record<string, unknown>,
): string {
  switch (toolName) {
    case 'write_file':
      return vscode.l10n.t(
        'My_AI wants to WRITE file "{0}". Continue?',
        String(input.path ?? '?'),
      );
    case 'edit_file':
      return vscode.l10n.t(
        'My_AI wants to EDIT "{0}". Continue?',
        String(input.path ?? '?'),
      );
    case 'run_command': {
      const cmd = String(input.command ?? '');
      const preview = cmd.length > 200 ? cmd.slice(0, 200) + '…' : cmd;
      return vscode.l10n.t(
        'My_AI wants to run a shell command:\n\n{0}\n\nContinue?',
        preview,
      );
    }
    default:
      return vscode.l10n.t(
        'My_AI wants to use the "{0}" tool. Continue?',
        toolName,
      );
  }
}
