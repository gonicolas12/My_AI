import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import { codeLanguage, fileKind, hasSource } from '../../lib/fileKinds';
import { resetFileLinks } from '../../lib/files';
import { formatSize, formatWhen } from '../../lib/format';
import type { MessageView } from '../../lib/events';
import {
  openAttachmentPreview,
  openPreviewWindow,
  useAttachmentPreview,
} from '../../stores/attachmentPreview';
import { useChat } from '../../stores/chat';
import { closePreview, openFilePreview, usePreview } from '../../stores/preview';
import { AttachmentChips } from '../chat/AttachmentChips';
import { UserMessage } from '../chat/UserMessage';
import { AttachmentPreviewDialog } from './AttachmentPreviewDialog';
import { FilePreview } from './FilePreview';
import { PreviewPane } from './PreviewPane';

const { ApiError } = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    readonly status: number;

    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
}));

const api = vi.hoisted(() => ({
  fileLinks: vi.fn(),
  fileText: vi.fn(),
  fileInfo: vi.fn(),
  documentPreview: vi.fn(),
  artifactPreview: vi.fn(),
  previewInBrowser: vi.fn(),
  removeAttachment: vi.fn(),
}));
vi.mock('../../lib/api', () => ({ api, ApiError }));

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

beforeEach(() => {
  vi.clearAllMocks();
  resetFileLinks();
  api.fileLinks.mockImplementation((paths: string[]) =>
    Promise.resolve({
      links: Object.fromEntries(paths.map((path) => [path, `/files/sig/${path.length}/x`])),
    }),
  );
  api.fileInfo.mockResolvedValue({ size: 38_400, modified: '2026-10-30T10:00:00' });
  usePreview.setState({ open: false, closing: false, items: [], index: 0, tab: 'preview' });
  useAttachmentPreview.setState({ open: false, items: [], index: 0, tab: 'preview' });
});

describe('formats', () => {
  it('reconnaît le format d’un fichier et son langage', () => {
    expect(fileKind('C:/a/photo.JPG')).toBe('image');
    expect(fileKind('logo.svg')).toBe('svg');
    expect(fileKind('rapport.docx')).toBe('office');
    expect(fileKind('notes.pdf')).toBe('pdf');
    expect(fileKind('table.csv')).toBe('table');
    expect(fileKind('README.md')).toBe('markdown');
    expect(fileKind('page.html')).toBe('html');
    expect(fileKind('main.py')).toBe('code');
    expect(fileKind('C:/projet/Dockerfile')).toBe('code');
    expect(fileKind('journal.log')).toBe('text');
    expect(fileKind('archive.zip')).toBe('other');
    expect(codeLanguage('main.py')).toBe('python');
    expect(codeLanguage('app.tsx')).toBe('tsx');
    expect(codeLanguage('logo.svg')).toBe('xml');
    expect(codeLanguage('Phrases.csv')).toBe('csv');
    expect(hasSource('markdown')).toBe(true);
    expect(hasSource('table')).toBe(true);
    expect(hasSource('code')).toBe(false);
  });

  it('écrit la taille et la date d’un fichier dans la langue de l’interface', () => {
    expect(formatSize(512)).toMatch(/^512\s?o$/);
    expect(formatSize(38_400)).toMatch(/^38,4\s?ko$/);
    expect(formatSize(5_300_000)).toMatch(/^5,3\s?Mo$/);
    const now = new Date('2026-11-18T12:00:00');
    expect(formatWhen('2026-11-18T05:00:00', now)).toBe('il y a 7 heures');
    expect(formatWhen('2026-11-17T12:00:00', now)).toBe('hier');
    expect(formatWhen('2026-10-30T12:00:00', now)).toBe('30 oct.');
    expect(formatWhen('', now)).toBe('');
  });
});

describe('FilePreview', () => {
  it('une image : affichée par son lien signé ; refusée : de quoi la retrouver', async () => {
    renderUi(<FilePreview path="C:/docs/photo.png" />);
    const image = await screen.findByRole('img', { name: 'photo.png' });
    expect(image.getAttribute('src')).toMatch(/^\/files\//);

    api.fileLinks.mockResolvedValue({ links: { 'C:/docs/autre.png': null } });
    renderUi(<FilePreview path="C:/docs/autre.png" />);
    expect(await screen.findByText('Ce fichier n’est plus disponible.')).toBeInTheDocument();
    await userEvent
      .setup()
      .click(screen.getByRole('button', { name: /Afficher dans l’Explorateur/ }));
    expect(actions.revealPath).toHaveBeenCalledWith('C:/docs/autre.png');
  });

  it('du code : coloré, le début seulement d’un long fichier', async () => {
    api.fileText.mockResolvedValue({ text: 'print("bonjour")', truncated: true });
    renderUi(<FilePreview path="C:/projet/main.py" />);
    expect(await screen.findByText('python')).toBeInTheDocument();
    expect(screen.getByText('print("bonjour")')).toBeInTheDocument();
    expect(screen.getByText('Fichier long : seul son début est affiché.')).toBeInTheDocument();
    expect(api.fileText).toHaveBeenCalledWith('C:/projet/main.py');
  });

  it('du Markdown : rendu, ou sa source dans l’onglet Code', async () => {
    api.fileText.mockResolvedValue({ text: '# Scénario\n\nNoah et Joan.', truncated: false });
    const { rerender } = renderUi(<FilePreview path="C:/docs/Scenario.md" />);
    expect(await screen.findByRole('heading', { name: 'Scénario' })).toBeInTheDocument();
    rerender(
      <TooltipProvider>
        <FilePreview path="C:/docs/Scenario.md" tab="code" />
      </TooltipProvider>,
    );
    expect(screen.queryByRole('heading', { name: 'Scénario' })).not.toBeInTheDocument();
    expect(screen.getByText('markdown')).toBeInTheDocument();
  });

  it('une page web : rendue avec ses fichiers voisins, sa source dans l’onglet Code', async () => {
    const source = '<link rel="stylesheet" href="style.css"><h1>Catalogue</h1>';
    const page = '<style data-href="style.css">h1{color:#2b5797}</style><h1>Catalogue</h1>';
    api.fileText.mockResolvedValue({ text: source, truncated: false, page });
    api.artifactPreview.mockResolvedValue({ id: 'p2', url: '/preview/p2', title: 'index.html' });
    const { rerender } = renderUi(<FilePreview path="C:/projet/web/index.html" />);
    // La page rendue est celle du serveur, feuille de style dedans
    await waitFor(() =>
      expect(api.artifactPreview).toHaveBeenCalledWith(
        expect.objectContaining({ kind: 'html', code: page }),
      ),
    );
    rerender(
      <TooltipProvider>
        <FilePreview path="C:/projet/web/index.html" tab="code" />
      </TooltipProvider>,
    );
    expect(await screen.findByText('html')).toBeInTheDocument();
    expect(screen.getByText(source)).toBeInTheDocument();
  });

  it('un format inconnu et binaire : pas d’aperçu, l’ouvrir s’il vient de l’appli', async () => {
    api.fileText.mockRejectedValue(new ApiError(415, 'binaire'));
    renderUi(<FilePreview path="C:/out/archive.zip" generated />);
    expect(await screen.findByText('Pas d’aperçu pour ce format.')).toBeInTheDocument();
    await userEvent
      .setup()
      .click(screen.getByRole('button', { name: /Ouvrir dans son application/ }));
    expect(actions.openFile).toHaveBeenCalledWith('C:/out/archive.zip');
  });

  it('un PDF : la page du serveur (lecteur de WebView2)', async () => {
    api.documentPreview.mockResolvedValue({
      id: 'p1',
      kind: 'pdf',
      title: 'notes.pdf',
      url: '/files/sig/tok/notes.pdf',
      path: 'C:/docs/notes.pdf',
    });
    const { container } = renderUi(<FilePreview path="C:/docs/notes.pdf" />);
    await waitFor(() =>
      expect(container.querySelector('iframe')).toHaveAttribute('src', '/files/sig/tok/notes.pdf'),
    );
    expect(api.documentPreview).toHaveBeenCalledWith('C:/docs/notes.pdf', false);
  });

  it('un CSV : son tableau (page du serveur), ou son texte dans l’onglet Code', async () => {
    api.documentPreview.mockResolvedValue({
      id: 'p2',
      kind: 'document',
      title: 'Phrases.csv',
      url: '/preview/p2',
      path: 'C:/docs/Phrases.csv',
    });
    api.fileText.mockResolvedValue({ text: 'Code Phrase;"(GC) Description"', truncated: false });
    const { container, rerender } = renderUi(<FilePreview path="C:/docs/Phrases.csv" />);
    await waitFor(() =>
      expect(container.querySelector('iframe')).toHaveAttribute('src', '/preview/p2'),
    );
    expect(api.fileText).not.toHaveBeenCalled();
    rerender(
      <TooltipProvider>
        <FilePreview path="C:/docs/Phrases.csv" tab="code" />
      </TooltipProvider>,
    );
    expect(await screen.findByText('Code Phrase;"(GC) Description"')).toBeInTheDocument();
    expect(screen.getByText('csv')).toBeInTheDocument();
    expect(container.querySelector('iframe')).toBeNull();
    expect(api.fileText).toHaveBeenCalledWith('C:/docs/Phrases.csv');
  });
});

describe('volet de droite', () => {
  it('s’ouvre sur un fichier du chat, avec son format, sa taille et sa date, et se replie', async () => {
    api.fileText.mockResolvedValue({ text: 'x = 1', truncated: false });
    renderUi(<PreviewPane page="chat" />);
    act(() => openFilePreview('C:/projet/calcul.py'));
    const pane = await screen.findByRole('complementary', { name: 'Aperçu' });
    expect(within(pane).getByText('calcul.py')).toBeInTheDocument();
    await waitFor(() => expect(pane).toHaveTextContent(/Fichier py · 38,4\s?ko · /));
    expect(pane).toHaveClass('pane-open');
    act(() => closePreview());
    expect(usePreview.getState().closing).toBe(true);
    expect(pane).toHaveClass('pane-close');
    await waitFor(() =>
      expect(screen.queryByRole('complementary', { name: 'Aperçu' })).not.toBeInTheDocument(),
    );
  });

  it('redimensionné à la souris, il garde la visionneuse Office affichée', async () => {
    shell.nativePreview.available.mockResolvedValue(true);
    api.documentPreview.mockResolvedValue({
      id: 'n1',
      kind: 'native',
      title: 'tableau.xlsx',
      url: '',
      path: 'C:/docs/tableau.xlsx',
    });
    globalThis.ResizeObserver ??= class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
    // Capture du pointeur (absente de jsdom), rendue ensuite telle qu'elle était
    const saved = (['setPointerCapture', 'releasePointerCapture'] as const).map(
      (name) => [name, Object.getOwnPropertyDescriptor(HTMLElement.prototype, name)] as const,
    );
    for (const [name] of saved) {
      Object.defineProperty(HTMLElement.prototype, name, {
        configurable: true,
        writable: true,
        value: vi.fn(),
      });
    }
    try {
      renderUi(<PreviewPane page="chat" />);
      act(() => openFilePreview('C:/docs/tableau.xlsx'));
      const pane = await screen.findByRole('complementary', { name: 'Aperçu' });
      // Ouverture finie : la visionneuse est posée, visible
      await waitFor(() =>
        expect(shell.nativePreview.place).toHaveBeenLastCalledWith(expect.anything(), true),
      );
      const body = pane.querySelector('[data-native-preview]')?.closest('.flex-1');
      const handle = within(pane).getByRole('separator');
      const start = usePreview.getState().width;
      shell.nativePreview.place.mockClear();

      fireEvent.pointerDown(handle, { clientX: 600, pointerId: 1 });
      fireEvent.pointerMove(handle, { clientX: 580, pointerId: 1 });
      expect(usePreview.getState().width).toBe(start + 20);
      // Le corps ne prend pas le pointeur, la visionneuse n'est jamais masquée
      expect(body).toHaveClass('pointer-events-none');
      await act(() => new Promise((resolve) => setTimeout(resolve, 60)));
      expect(shell.nativePreview.place).not.toHaveBeenCalledWith(expect.anything(), false);

      fireEvent.pointerUp(handle, { clientX: 580, pointerId: 1 });
      expect(body).not.toHaveClass('pointer-events-none');
      expect(actions.savePreviewWidth).toHaveBeenCalled();
    } finally {
      for (const [name, descriptor] of saved) {
        if (descriptor) Object.defineProperty(HTMLElement.prototype, name, descriptor);
        else Reflect.deleteProperty(HTMLElement.prototype, name);
      }
      shell.nativePreview.available.mockResolvedValue(false);
    }
  });
});

describe('pièces jointes', () => {
  it('pas encore envoyée : un clic ouvre la fenêtre d’aperçu, qui passe de l’une à l’autre', async () => {
    const user = userEvent.setup();
    api.fileText.mockResolvedValue({ text: 'a,b', truncated: false });
    useChat.setState({
      attachments: [
        { id: 'a1', path: 'C:/docs/photo.png', name: 'photo.png', type: 'Image', status: 'ready' },
        { id: 'a2', path: 'C:/docs/notes.txt', name: 'notes.txt', type: 'Code', status: 'loading' },
      ],
    });
    renderUi(
      <>
        <AttachmentChips />
        <AttachmentPreviewDialog />
      </>,
    );
    await user.click(screen.getByRole('button', { name: 'Aperçu de notes.txt' }));
    const dialog = await screen.findByRole('dialog', { name: 'notes.txt' });
    expect(within(dialog).getByText('2/2')).toBeInTheDocument();
    expect(await within(dialog).findByText('a,b')).toBeInTheDocument();
    // Le volet de droite n'est pas concerné
    expect(usePreview.getState().open).toBe(false);
    await user.click(within(dialog).getByRole('button', { name: 'Aperçu précédent' }));
    expect(await screen.findByRole('dialog', { name: 'photo.png' })).toBeInTheDocument();
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(useAttachmentPreview.getState().open).toBe(false);
  });

  it('d’un message envoyé : un clic l’ouvre dans le volet de droite, avec les autres', async () => {
    const user = userEvent.setup();
    const message: MessageView = {
      mid: 'm1',
      role: 'user',
      text: 'Voici',
      timestamp: '2026-11-18T09:00:00',
      type: 'text',
      attachments: [
        { path: 'C:/docs/plan.pdf', name: 'plan.pdf', type: 'PDF' },
        { path: 'C:/docs/photo.png', name: 'photo.png', type: 'Image' },
      ],
      image_path: null,
    };
    renderUi(<UserMessage message={message} busy={false} />);
    // Nom gris comme le message, souligné en bleu seulement sous la souris
    const name = screen.getByText('photo.png');
    expect(name).not.toHaveClass('text-link');
    expect(name).toHaveClass('text-fg-2', 'decoration-transparent');
    expect(name).toHaveClass('group-hover:text-link', 'group-hover:decoration-link');
    // Sa couleur et son soulignement en fondu, au rythme de celui du bouton
    const chip = screen.getByRole('button', { name: /photo\.png/ });
    expect(name).toHaveClass('transition-colors', 'duration-150');
    expect(chip).toHaveClass('transition-colors', 'duration-150');
    await user.click(screen.getByRole('button', { name: /photo\.png/ }));
    const state = usePreview.getState();
    expect(state.open).toBe(true);
    expect(state.mid).toBe('m1');
    expect(state.index).toBe(1);
    expect(state.items.map((item) => (item.kind === 'document' ? item.path : ''))).toEqual([
      'C:/docs/plan.pdf',
      'C:/docs/photo.png',
    ]);
    expect(useAttachmentPreview.getState().open).toBe(false);
  });

  it('la fenêtre s’ouvre aussi depuis la zone de tâche et la page Code', () => {
    openAttachmentPreview([{ path: 'C:/t/a.md', name: 'a.md' }], 4);
    expect(useAttachmentPreview.getState()).toMatchObject({ open: true, index: 0 });
  });

  it('montre aussi un bloc HTML (page Agents) : sa page, son code, le navigateur', async () => {
    const user = userEvent.setup();
    api.artifactPreview.mockResolvedValue({ id: 'p1', url: '/preview/p1', title: 'Démo' });
    api.previewInBrowser.mockResolvedValue(undefined);
    openPreviewWindow([
      { kind: 'html', code: '<h1>Démo</h1>', title: 'Démo', language: 'html', index: 0 },
    ]);
    renderUi(<AttachmentPreviewDialog />);
    const dialog = await screen.findByRole('dialog', { name: 'Démo' });
    const frame = await waitFor(() => {
      const element = dialog.querySelector('iframe');
      expect(element).not.toBeNull();
      return element!;
    });
    expect(frame.getAttribute('src')).toBe('/preview/p1');
    // Sans allow-same-origin : la page ne lit ni l'appli ni son API
    expect(frame.getAttribute('sandbox')).not.toContain('allow-same-origin');
    await user.click(within(dialog).getByRole('button', { name: 'Ouvrir dans le navigateur' }));
    expect(api.previewInBrowser).toHaveBeenCalledWith('p1');
    await user.click(within(dialog).getByRole('tab', { name: 'Code' }));
    expect(await within(dialog).findByText('<h1>Démo</h1>')).toBeInTheDocument();
    expect(usePreview.getState().open).toBe(false);
  });
});
