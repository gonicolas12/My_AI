import { act, render, renderHook, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import type { CodeAssistantMessage, CodeUserMessage } from '../../lib/events';
import { resetFileLinks } from '../../lib/files';
import { useApp } from '../../stores/app';
import { resetCode, useCode } from '../../stores/code';
import { closePagePreview, openFilePreview, usePreview } from '../../stores/preview';
import { PreviewPane } from '../preview/PreviewPane';
import { CodeReply, CodeUserBubble } from './CodeTurn';
import { usePaneReset } from './usePaneReset';

const api = vi.hoisted(() => ({
  fileLinks: vi.fn(),
  fileText: vi.fn(),
  fileInfo: vi.fn(),
  documentPreview: vi.fn(),
  artifactPreview: vi.fn(),
}));
vi.mock('../../lib/api', () => ({ api, ApiError: class extends Error {} }));

const shell = vi.hoisted(() => ({
  nativePreview: {
    available: vi.fn(() => Promise.resolve(false)),
    show: vi.fn(() => Promise.resolve(true)),
    place: vi.fn(),
    close: vi.fn(),
  },
}));
vi.mock('../../lib/shell', () => ({ shell, externalUrl: (url: string) => url }));

const actions = vi.hoisted(() => ({
  openFile: vi.fn(() => Promise.resolve()),
  revealPath: vi.fn(() => Promise.resolve()),
  savePreviewWidth: vi.fn(),
}));
vi.mock('../../lib/actions', () => actions);

function renderUi(ui: React.ReactNode) {
  return render(<TooltipProvider>{ui}</TooltipProvider>);
}

const USER: CodeUserMessage = {
  message_id: 'code_1',
  role: 'user',
  text: 'Regarde ces fichiers',
  origin: 'mobile',
  timestamp: '2026-11-19T09:00:00',
  attachments: ['photo.png', 'notes.md'],
  files: [
    { name: 'photo.png', path: 'C:/docs/photo.png', type: 'Image' },
    { name: 'notes.md', path: 'C:/docs/notes.md', type: '' },
  ],
};

const REPLY: CodeAssistantMessage = {
  message_id: 'code_1',
  role: 'assistant',
  origin: 'mobile',
  timestamp: '2026-11-19T09:00:05',
  parts: [
    { kind: 'text', segment: 0, text: 'J’ai lu `src/app.ts`, puis le dossier src/lib.' },
    {
      kind: 'tool',
      call_id: 'c1',
      name: 'read_file',
      input: { path: 'src/app.ts' },
      status: 'completed',
      output: 'ok',
    },
    {
      kind: 'text',
      segment: 1,
      text: ['Voici la page :', '', '```html', '<h1>Bonjour</h1>', '```'].join('\n'),
    },
  ],
  text: '',
  status: 'done',
  paths: [
    { text: 'src/app.ts', path: 'C:/ws/src/app.ts', dir: false, name: true },
    { text: 'src/lib', path: 'C:/ws/src/lib', dir: true, name: true },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
  resetFileLinks();
  resetCode();
  api.fileLinks.mockImplementation((paths: string[]) =>
    Promise.resolve({ links: Object.fromEntries(paths.map((path) => [path, `/files/s/t/x`])) }),
  );
  api.fileInfo.mockResolvedValue({ size: 1200, modified: '2026-11-19T09:00:00' });
  api.fileText.mockResolvedValue({ text: 'x', truncated: false });
  usePreview.setState({ open: false, closing: false, page: 'chat', items: [], index: 0 });
  useApp.setState({ tab: 'code' });
});

describe('message de la page Code', () => {
  it('ses pièces jointes sont des noms cliquables, ouverts dans le volet de la page', async () => {
    const user = userEvent.setup();
    renderUi(<CodeUserBubble message={USER} />);
    // Le texte seul dans la bulle, plus de « 📎 nom »
    expect(screen.getByText('Regarde ces fichiers')).toBeInTheDocument();
    expect(screen.queryByText(/📎/u)).toBeNull();
    const notes = screen.getByRole('button', { name: 'notes.md' });
    expect(notes).toHaveAttribute('title', 'Aperçu de C:/docs/notes.md');
    // Une image montre sa vignette
    expect(await screen.findByRole('button', { name: 'photo.png' })).toContainHTML('<img');
    await user.click(notes);
    const state = usePreview.getState();
    expect(state.open).toBe(true);
    expect(state.page).toBe('code');
    expect(state.index).toBe(1);
    expect(state.items.map((item) => (item.kind === 'document' ? item.path : ''))).toEqual([
      'C:/docs/photo.png',
      'C:/docs/notes.md',
    ]);
  });

  it('d’une conversation d’avant leur aperçu : leurs noms seuls, dans la bulle', () => {
    renderUi(<CodeUserBubble message={{ ...USER, files: undefined }} />);
    expect(screen.getByText(/📎 photo\.png/u)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'photo.png' })).toBeNull();
  });
});

describe('réponse de la page Code', () => {
  it('un fichier qu’elle cite s’ouvre dans le volet de la page, un dossier dans l’Explorateur', async () => {
    const user = userEvent.setup();
    renderUi(<CodeReply message={REPLY} isLast />);
    const file = screen.getByRole('link', { name: 'src/app.ts' });
    expect(file).toHaveAttribute('title', 'Aperçu : C:/ws/src/app.ts');
    await user.click(file);
    const state = usePreview.getState();
    expect(state).toMatchObject({ open: true, page: 'code' });
    expect(state.items[0]).toMatchObject({ kind: 'document', path: 'C:/ws/src/app.ts' });
    await user.click(screen.getByRole('link', { name: 'src/lib' }));
    expect(actions.revealPath).toHaveBeenCalledWith('C:/ws/src/lib');
  });

  it('un bloc HTML a son bouton « Aperçu », qui ouvre le volet de la page sur lui', async () => {
    const user = userEvent.setup();
    renderUi(<CodeReply message={REPLY} isLast />);
    await user.click(screen.getByRole('button', { name: 'Afficher l’aperçu de ce bloc' }));
    const state = usePreview.getState();
    expect(state).toMatchObject({ open: true, page: 'code', mid: 'code_1' });
    expect(state.items.map((item) => item.kind)).toEqual(['html']);
  });

  it('en cours : ni liens ni bouton « Aperçu »', () => {
    renderUi(<CodeReply message={{ ...REPLY, status: 'streaming', paths: undefined }} isLast />);
    expect(screen.queryByRole('link', { name: 'src/app.ts' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Afficher l’aperçu de ce bloc' })).toBeNull();
  });
});

describe('volet de chaque page', () => {
  it('ouvert de la page Code, il ne paraît que sur elle', async () => {
    renderUi(
      <>
        <section aria-label="chat">
          <PreviewPane page="chat" />
        </section>
        <section aria-label="code">
          <PreviewPane page="code" />
        </section>
      </>,
    );
    act(() => openFilePreview('C:/ws/src/app.ts'));
    const code = screen.getByRole('region', { name: 'code' });
    expect(await within(code).findByRole('complementary', { name: 'Aperçu' })).toBeInTheDocument();
    expect(
      within(screen.getByRole('region', { name: 'chat' })).queryByRole('complementary'),
    ).toBeNull();
    // Changer de conversation dans le chat ne ferme pas celui de la page Code
    act(() => closePagePreview('chat'));
    expect(usePreview.getState()).toMatchObject({ open: true, closing: false });
    act(() => closePagePreview('code'));
    expect(usePreview.getState().closing).toBe(true);
  });

  it('se ferme quand la conversation Code est effacée, d’où que ce soit', () => {
    useCode.setState({ loaded: true, messages: [USER, REPLY] });
    renderHook(() => usePaneReset());
    act(() => openFilePreview('C:/ws/src/app.ts'));
    // Un message de plus ne le ferme pas
    act(() => useCode.setState({ messages: [USER, REPLY, { ...USER, message_id: 'code_2' }] }));
    expect(usePreview.getState().closing).toBe(false);
    act(() => useCode.setState({ messages: [] }));
    expect(usePreview.getState().closing).toBe(true);
  });
});
