import * as vscode from 'vscode';
import { ChatViewProvider } from './chatViewProvider';
import { ConnectionManager } from './connectionManager';
import { InvalidConnectionStringError } from './connectionString';
import { WorkspaceBridge } from './workspaceBridge';

let manager: ConnectionManager | null = null;
let bridge: WorkspaceBridge | null = null;
let viewProvider: ChatViewProvider | null = null;
let statusBarItem: vscode.StatusBarItem | null = null;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  manager = new ConnectionManager(context);
  bridge = new WorkspaceBridge(context, manager);
  viewProvider = new ChatViewProvider(context, manager, bridge);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      ChatViewProvider.viewType,
      viewProvider,
      { webviewOptions: { retainContextWhenHidden: true } },
    ),
  );

  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'myai-relay.focusChat';
  context.subscriptions.push(statusBarItem);
  manager.on('state-changed', updateStatusBar);
  updateStatusBar(manager.getState());

  context.subscriptions.push(
    vscode.commands.registerCommand('myai-relay.connect', () => connectCommand()),
    vscode.commands.registerCommand('myai-relay.disconnect', () =>
      manager!.disconnect(false).catch(showError),
    ),
    vscode.commands.registerCommand('myai-relay.forgetCredentials', () =>
      forgetCommand(),
    ),
    vscode.commands.registerCommand('myai-relay.sendSelection', () =>
      bridge!.sendSelection().catch(showError),
    ),
    vscode.commands.registerCommand('myai-relay.sendActiveFile', () =>
      bridge!.sendActiveFile().catch(showError),
    ),
    vscode.commands.registerCommand('myai-relay.toggleAutoAttach', async () => {
      const next = await bridge!.toggleAutoAttach();
      vscode.window.showInformationMessage(
        next
          ? vscode.l10n.t('My_AI Relay: auto-attach enabled.')
          : vscode.l10n.t('My_AI Relay: auto-attach disabled.'),
      );
    }),
    vscode.commands.registerCommand('myai-relay.focusChat', async () => {
      await vscode.commands.executeCommand('workbench.view.extension.myai-relay');
    }),
    vscode.commands.registerCommand('myai-relay.moveToSecondarySidebar', async () => {
      await moveViewToSecondarySidebar();
    }),
  );

  // Try to silently restore an existing session.
  try {
    await manager.restoreFromStorage();
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('[my-ai-relay] restore failed:', err);
  }

  // First activation: optionally move the view to the Secondary Side Bar
  // (right side, like Copilot Chat). VS Code persists view location across
  // restarts, so we only do this once.
  await maybeAutoMoveToSecondarySidebar(context);
}

export function deactivate(): void {
  manager?.disconnect(false).catch(() => { /* shutting down */ });
}

async function connectCommand(): Promise<void> {
  if (!manager) {
    return;
  }
  const value = await vscode.window.showInputBox({
    title: vscode.l10n.t('My_AI Relay — Connect'),
    prompt: vscode.l10n.t(
      'Paste the connection string from My_AI (Relay popup → "Copy for the VS Code extension")',
    ),
    placeHolder: 'https://gonicolas12.github.io/My_AI/router.html#d=…',
    password: true,
    ignoreFocusOut: true,
  });
  if (!value) {
    return;
  }
  try {
    await manager.connectFromString(value);
  } catch (err) {
    if (err instanceof InvalidConnectionStringError) {
      vscode.window.showErrorMessage(
        vscode.l10n.t('My_AI Relay: {0}', err.message),
      );
    } else {
      showError(err as Error);
    }
  }
}

async function forgetCommand(): Promise<void> {
  if (!manager) {
    return;
  }
  const forgetLabel = vscode.l10n.t('Forget');
  const choice = await vscode.window.showWarningMessage(
    vscode.l10n.t(
      'Forget the saved My_AI Relay connection? You will need to paste the connection string again.',
    ),
    { modal: true },
    forgetLabel,
  );
  if (choice !== forgetLabel) {
    return;
  }
  await manager.disconnect(true);
  vscode.window.showInformationMessage(
    vscode.l10n.t('My_AI Relay: saved connection removed.'),
  );
}

function updateStatusBar(state: ReturnType<ConnectionManager['getState']>): void {
  if (!statusBarItem) {
    return;
  }
  switch (state.kind) {
    case 'connected':
      statusBarItem.text = vscode.l10n.t('$(robot) My_AI: connected');
      statusBarItem.tooltip = vscode.l10n.t('My_AI Relay connected via {0}', state.baseUrl);
      statusBarItem.backgroundColor = undefined;
      break;
    case 'connecting':
      statusBarItem.text = vscode.l10n.t('$(sync~spin) My_AI: connecting…');
      statusBarItem.tooltip = vscode.l10n.t('My_AI Relay connecting');
      statusBarItem.backgroundColor = undefined;
      break;
    case 'reconnecting':
      statusBarItem.text = vscode.l10n.t('$(sync~spin) My_AI: reconnecting…');
      statusBarItem.tooltip = vscode.l10n.t('My_AI Relay lost connection — reconnecting');
      statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
      break;
    case 'disconnected':
      statusBarItem.text = vscode.l10n.t('$(robot) My_AI: offline');
      statusBarItem.tooltip = vscode.l10n.t('My_AI Relay disconnected: {0}', state.reason);
      statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
      break;
    case 'idle':
    default:
      statusBarItem.text = vscode.l10n.t('$(robot) My_AI: not connected');
      statusBarItem.tooltip = vscode.l10n.t('Click to open My_AI Relay');
      statusBarItem.backgroundColor = undefined;
      break;
  }
  statusBarItem.show();
}

function showError(err: Error): void {
  vscode.window.showErrorMessage(vscode.l10n.t('My_AI Relay: {0}', err.message));
}

const SIDEBAR_PROMPT_KEY = 'myaiRelay.secondarySidebarPrompted.v1';

async function maybeAutoMoveToSecondarySidebar(
  context: vscode.ExtensionContext,
): Promise<void> {
  const wantMove = vscode.workspace
    .getConfiguration('myaiRelay')
    .get<boolean>('openInSecondarySidebar', true);
  if (!wantMove) {
    return;
  }
  if (context.globalState.get<boolean>(SIDEBAR_PROMPT_KEY, false)) {
    return;
  }
  // Mark BEFORE prompting so the user sees this only once.
  await context.globalState.update(SIDEBAR_PROMPT_KEY, true);
  const moveLabel = vscode.l10n.t('Move now');
  const keepLabel = vscode.l10n.t('Keep on the left');
  const choice = await vscode.window.showInformationMessage(
    vscode.l10n.t(
      'My_AI Relay: open the chat in the Secondary Side Bar (right side, like Copilot Chat)?',
    ),
    moveLabel,
    keepLabel,
  );
  if (choice === moveLabel) {
    await moveViewToSecondarySidebar();
  }
}

async function moveViewToSecondarySidebar(): Promise<void> {
  // VS Code does not expose a stable public command to programmatically
  // place a view into the Secondary Side Bar (extensions can only
  // contribute to "activitybar" or "panel" — see VS Code UX guidelines).
  // We open our view first so the interactive picker pre-selects it,
  // then run the built-in "Move View" command. The user confirms in one
  // click and VS Code remembers the placement across restarts.
  await vscode.commands.executeCommand('workbench.view.extension.myai-relay');
  await vscode.commands.executeCommand('myai-relay.chat.focus');
  await vscode.commands.executeCommand('workbench.action.moveView');
}
