import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../../components/ui/Tooltip';
import type { MemoryDocument, MemoryFolder, MemoryPage } from '../../../lib/api';
import { dispatchDroppedPaths } from '../../../lib/drops';
import { useApp } from '../../../stores/app';
import {
  applyMemoryChanged,
  applyMemoryJobs,
  showInMemory,
  useMemory,
} from '../../../stores/memory';
import { usePanels } from '../../../stores/panels';
import MemoryPanel from './MemoryPanel';

const api = vi.hoisted(() => ({
  memoryPage: vi.fn(),
  existingMemoryDocuments: vi.fn(),
  addMemoryDocuments: vi.fn(),
  uploadMemoryDocument: vi.fn(),
  uploadMemoryFolder: vi.fn(),
  addFact: vi.fn(),
  updateMemory: vi.fn(),
  deleteMemory: vi.fn(),
  deleteMemoryDocument: vi.fn(),
  deleteMemoryFolder: vi.fn(),
}));
vi.mock('../../../lib/api', () => ({ api, ApiError: class ApiError extends Error {} }));

const shell = vi.hoisted(() => ({
  canPickFiles: vi.fn(() => true),
  pickFiles: vi.fn(),
  isDesktop: vi.fn(() => true),
}));
vi.mock('../../../lib/shell', () => ({ shell }));

function page(overrides: Partial<MemoryPage> = {}): MemoryPage {
  return {
    items: [],
    total: 0,
    page: 0,
    pages: 1,
    stats: { facts: 0, documents: 0, conversations: 0 },
    categories: [],
    jobs: [],
    ...overrides,
  };
}

/** Document de l'onglet Documents (MemoryStore.list_document_groups) */
function documentGroup(overrides: Partial<MemoryDocument> = {}): MemoryDocument {
  return {
    kind: 'document',
    id: 'rapport_pdf_1',
    name: 'rapport.pdf',
    label: 'rapport.pdf',
    folder: null,
    created: '2026-11-17T14:32:00',
    type: 'PDF',
    source: 'manual',
    ...overrides,
  };
}

const FOLDER: MemoryFolder = {
  kind: 'folder',
  id: 'folder:site_1',
  key: 'site_1',
  name: 'site',
  files: 2,
  created: '2026-11-16T09:05:00',
  source: 'manual',
  documents: [
    documentGroup({
      id: 'folder_a',
      name: 'site/README.md',
      label: 'README.md',
      folder: 'site',
      type: 'Code',
    }),
    documentGroup({
      id: 'folder_b',
      name: 'site/src/app.py',
      label: 'src/app.py',
      folder: 'site',
      type: 'Code',
    }),
  ],
};

async function openDocuments() {
  const user = userEvent.setup();
  render(
    <TooltipProvider>
      <MemoryPanel />
    </TooltipProvider>,
  );
  await user.click(screen.getByRole('tab', { name: /Documents/ }));
  return user;
}

const toasts = () => useApp.getState().toasts.map((toast) => toast.message);

/** Fichiers glissés (DataTransfer du navigateur, réduit à ce que lit useFileDrop) */
function transferOf(...files: File[]) {
  return {
    types: ['Files'],
    files,
    items: files.map((file) => ({
      kind: 'file',
      webkitGetAsEntry: (): unknown => null,
      getAsFile: (): File | null => file,
    })),
    dropEffect: 'none',
  };
}

/** Entrées FileSystem d'un dossier déposé (ce que lit folders.ts) */
interface FakeFile {
  name: string;
  isFile: true;
  isDirectory: false;
  file: (resolve: (file: File) => void) => void;
}

interface FakeFolder {
  name: string;
  isFile: false;
  isDirectory: true;
  createReader: () => { readEntries: (resolve: (entries: FakeEntry[]) => void) => void };
}

type FakeEntry = FakeFile | FakeFolder;

function fileEntry(name: string, size = 4): FakeFile {
  const file = new File(['x'.repeat(size)], name);
  return { name, isFile: true, isDirectory: false, file: (resolve) => resolve(file) };
}

function folderEntry(name: string, children: FakeEntry[]): FakeFolder {
  return {
    name,
    isFile: false,
    isDirectory: true,
    // readEntries rend les entrées par lots, puis un lot vide
    createReader: () => {
      const batches = [children.slice(0, 2), children.slice(2), []];
      return { readEntries: (resolve) => resolve(batches.shift() ?? []) };
    },
  };
}

/** Dossier glissé, et d'éventuels fichiers à côté */
function transferWithFolder(folder: FakeFolder, ...files: File[]) {
  const transfer = transferOf(...files);
  transfer.items.push({
    kind: 'file',
    webkitGetAsEntry: (): unknown => folder,
    getAsFile: (): File | null => null,
  });
  return transfer;
}

const drop = (transfer: ReturnType<typeof transferOf>) =>
  fireEvent.drop(screen.getByRole('dialog', { name: 'Mémoire locale' }), {
    dataTransfer: transfer,
  });

beforeEach(() => {
  vi.clearAllMocks();
  // Réponses « une fois » d'un test en échec : pas pour le suivant
  for (const mock of Object.values(api)) mock.mockReset();
  shell.canPickFiles.mockReturnValue(true);
  shell.isDesktop.mockReturnValue(true);
  useMemory.setState({ jobs: [], revision: 0, dropping: false, update: null, focus: null });
  useApp.setState({ toasts: [] });
  api.memoryPage.mockResolvedValue(page());
  api.existingMemoryDocuments.mockResolvedValue({ files: [], folders: [] });
  api.addMemoryDocuments.mockResolvedValue({ jobs: [], refused: [] });
  api.uploadMemoryDocument.mockResolvedValue({ jobs: [], refused: [] });
  api.uploadMemoryFolder.mockResolvedValue({ jobs: [], refused: [] });
  api.deleteMemoryDocument.mockResolvedValue({ ok: true });
  api.deleteMemoryFolder.mockResolvedValue({ ok: true });
  api.updateMemory.mockResolvedValue({ ok: true });
  api.deleteMemory.mockResolvedValue({ ok: true });
});

describe('MemoryPanel, onglet Documents', () => {
  it('explique d’où viennent les documents quand la mémoire est vide', async () => {
    await openDocuments();
    expect(
      await screen.findByText(/Les fichiers joints dans le chat arrivent ici d'eux-mêmes/),
    ).toBeInTheDocument();
    expect(api.memoryPage).toHaveBeenLastCalledWith('document', '', null, 0);
  });

  it('« Ajouter » ouvre le dialogue du système, tous types, puis met les fichiers en mémoire', async () => {
    shell.pickFiles.mockResolvedValue(['C:/docs/rapport.pdf', 'C:/docs/archive.zip']);
    api.addMemoryDocuments.mockResolvedValue({
      jobs: [{ id: '1', name: 'rapport.pdf', state: 'queued' }],
      refused: [{ name: 'archive.zip', message: '❌ Format non supporté : .zip' }],
    });
    const user = await openDocuments();
    await user.click(await screen.findByRole('button', { name: 'Ajouter' }));
    await waitFor(() =>
      expect(api.addMemoryDocuments).toHaveBeenCalledWith(
        ['C:/docs/rapport.pdf', 'C:/docs/archive.zip'],
        {},
      ),
    );
    expect(shell.pickFiles).toHaveBeenCalledWith('All');
    // Déjà en mémoire ? Demandé par leur nom
    expect(api.existingMemoryDocuments).toHaveBeenCalledWith(['rapport.pdf', 'archive.zip'], []);
    expect(toasts()).toEqual(['❌ Format non supporté : .zip']);
  });

  it('dialogue annulé : rien n’est envoyé', async () => {
    shell.pickFiles.mockResolvedValue([]);
    const user = await openDocuments();
    await user.click(await screen.findByRole('button', { name: 'Ajouter' }));
    await waitFor(() => expect(shell.pickFiles).toHaveBeenCalled());
    expect(api.existingMemoryDocuments).not.toHaveBeenCalled();
    expect(api.addMemoryDocuments).not.toHaveBeenCalled();
  });

  it('dans un navigateur, le sélecteur de la page envoie chaque fichier', async () => {
    shell.canPickFiles.mockReturnValue(false);
    const user = await openDocuments();
    const input = document.querySelector<HTMLInputElement>('input[type="file"]');
    expect(input).not.toBeNull();
    expect(input?.multiple).toBe(true);
    expect(input?.accept).toContain('.pdf');
    expect(input?.accept).toContain('.png');
    const click = vi.spyOn(input as HTMLInputElement, 'click');
    await user.click(await screen.findByRole('button', { name: 'Ajouter' }));
    expect(click).toHaveBeenCalled();

    const pdf = new File(['%PDF'], 'rapport.pdf', { type: 'application/pdf' });
    const photo = new File(['png'], 'photo.png', { type: 'image/png' });
    await user.upload(input as HTMLInputElement, [pdf, photo]);
    await waitFor(() => expect(api.uploadMemoryDocument).toHaveBeenCalledTimes(2));
    expect(api.uploadMemoryDocument).toHaveBeenNthCalledWith(1, pdf, 'rapport.pdf', undefined);
    expect(api.uploadMemoryDocument).toHaveBeenNthCalledWith(2, photo, 'photo.png', undefined);
  });

  it('montre les documents en cours, puis relit la liste quand l’un est rangé', async () => {
    api.memoryPage.mockResolvedValue(
      page({
        jobs: [
          { id: '1', name: 'rapport.pdf', state: 'reading' },
          { id: '2', name: 'photo.png', state: 'describing' },
          { id: '3', name: 'notes.md', state: 'queued' },
        ],
      }),
    );
    await openDocuments();
    const jobs = await screen.findByRole('list', { name: 'Documents en cours de mise en mémoire' });
    expect(
      within(jobs)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual([
      'rapport.pdflecture du fichier…',
      "photo.pngdescription de l'image…",
      'notes.mden attente',
    ]);
    // La liste vide n'est pas annoncée pendant la lecture
    expect(screen.queryByText(/Aucun document en mémoire/)).not.toBeInTheDocument();

    api.memoryPage.mockResolvedValue(page({ items: [documentGroup()], total: 1 }));
    const calls = api.memoryPage.mock.calls.length;
    act(() => {
      applyMemoryJobs([{ id: '3', name: 'notes.md', state: 'reading' }]);
      applyMemoryChanged();
    });
    const name = await screen.findByText('rapport.pdf');
    expect(api.memoryPage.mock.calls.length).toBeGreaterThan(calls);
    expect(name.closest('li')).toHaveTextContent(/rapport\.pdf.* · ajouté à la main$/);
  });

  it('un dossier déposé tient sur une ligne : fichiers restants, fichier en cours', async () => {
    api.memoryPage.mockResolvedValue(
      page({
        jobs: [
          {
            id: 'b1',
            name: 'site',
            state: 'describing',
            folder: 'site',
            files: 3,
            current: 'img/logo.png',
          },
        ],
      }),
    );
    await openDocuments();
    const jobs = await screen.findByRole('list', { name: 'Documents en cours de mise en mémoire' });
    expect(
      within(jobs)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(["site3 fichiers restantsimg/logo.pngdescription de l'image…"]);
  });

  it('des fichiers glissés sur la fenêtre éclairent le contour du panneau, onglet Documents seulement', async () => {
    const user = userEvent.setup();
    render(
      <TooltipProvider>
        <MemoryPanel />
      </TooltipProvider>,
    );
    const dialog = await screen.findByRole('dialog');
    act(() => useMemory.setState({ dropping: true }));
    expect(dialog).not.toHaveClass('drop-glow'); // onglet Faits
    await user.click(screen.getByRole('tab', { name: /Documents/ }));
    expect(dialog).toHaveClass('drop-glow', 'border-accent');
    expect(
      screen.getByText('Déposez vos fichiers ou dossiers ici pour les mettre en mémoire'),
    ).toBeInTheDocument();
    act(() => useMemory.setState({ dropping: false }));
    expect(dialog).not.toHaveClass('drop-glow');
    expect(dialog).toHaveClass('border-line');
  });

  it('dans un navigateur, un fichier déposé sur le panneau est envoyé', async () => {
    shell.isDesktop.mockReturnValue(false);
    await openDocuments();
    const dialog = screen.getByRole('dialog');
    const pdf = new File(['%PDF'], 'contrat.pdf', { type: 'application/pdf' });
    fireEvent.dragOver(dialog, { dataTransfer: transferOf(pdf) });
    fireEvent.drop(dialog, { dataTransfer: transferOf(pdf) });
    await waitFor(() =>
      expect(api.uploadMemoryDocument).toHaveBeenCalledWith(pdf, 'contrat.pdf', undefined),
    );
    expect(api.addMemoryDocuments).not.toHaveBeenCalled();
  });

  it('dans la fenêtre de l’appli aussi, le panneau lit le contenu du fichier déposé', async () => {
    // Un fichier sans vrai chemin (glissé depuis Outlook, une archive ZIP…) n'a pas
    // de files.dropped : par son chemin, le dépôt ne donnait rien
    await openDocuments();
    const pdf = new File(['%PDF'], 'contrat.pdf', { type: 'application/pdf' });
    drop(transferOf(pdf));
    await waitFor(() =>
      expect(api.uploadMemoryDocument).toHaveBeenCalledWith(pdf, 'contrat.pdf', undefined),
    );
    // Les chemins que WebView2 envoie ensuite ne le rangent pas une seconde fois
    dispatchDroppedPaths(['C:/docs/contrat.pdf']);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(api.addMemoryDocuments).not.toHaveBeenCalled();
    expect(api.uploadMemoryDocument).toHaveBeenCalledTimes(1);
  });

  it('un dossier déposé est parcouru puis envoyé, chaque fichier avec son chemin', async () => {
    await openDocuments();
    const pdf = new File(['%PDF'], 'contrat.pdf', { type: 'application/pdf' });
    const folder = folderEntry('projet', [
      fileEntry('README.md'),
      fileEntry('.env'), // caché : ni lu ni compté
      fileEntry('logo.png'),
      fileEntry('archive.zip'), // format non pris en charge
      fileEntry('dump.log', 3 * 1024 * 1024), // texte trop lourd
      folderEntry('node_modules', [fileEntry('lib.js')]), // jamais parcouru
      folderEntry('src', [fileEntry('app.py'), folderEntry('util', [fileEntry('helpers.ts')])]),
    ]);
    drop(transferWithFolder(folder, pdf));
    await waitFor(() => expect(api.uploadMemoryFolder).toHaveBeenCalledTimes(1));
    // Un seul « déjà en mémoire ? » pour le dépôt entier
    expect(api.existingMemoryDocuments).toHaveBeenCalledTimes(1);
    expect(api.existingMemoryDocuments).toHaveBeenCalledWith(['contrat.pdf'], ['projet']);
    const [name, files] = api.uploadMemoryFolder.mock.calls[0] as [string, { path: string }[]];
    expect(name).toBe('projet');
    // Dans l'ordre alphabétique, dossier par dossier
    expect(files.map((file) => file.path)).toEqual([
      'logo.png',
      'README.md',
      'src/app.py',
      'src/util/helpers.ts',
    ]);
    // Le fichier déposé à côté du dossier est rangé seul
    expect(api.uploadMemoryDocument).toHaveBeenCalledWith(pdf, 'contrat.pdf', undefined);
    expect(toasts()).toEqual([
      '📁 « projet » : 2 fichiers ignorés (format non pris en charge ou trop lourds)',
    ]);
  });

  it('un dossier sans fichier lisible, ou trop gros, le dit sans rien envoyer', async () => {
    await openDocuments();
    const empty = folderEntry('vide', [fileEntry('archive.zip'), folderEntry('.git', [])]);
    drop(transferWithFolder(empty));
    await waitFor(() =>
      expect(toasts()).toEqual(['📁 Aucun fichier à mettre en mémoire dans « vide »']),
    );

    const many = Array.from({ length: 201 }, (_, index) => fileEntry(`note_${index}.md`));
    drop(transferWithFolder(folderEntry('enorme', many)));
    await waitFor(() => expect(toasts()).toHaveLength(2));
    expect(toasts()[1]).toBe(
      '📁 « enorme » contient plus de 200 fichiers à mettre en mémoire : déposez plutôt ses sous-dossiers, un par un.',
    );
    expect(api.uploadMemoryFolder).not.toHaveBeenCalled();
  });

  it('onglet Faits : un dépôt ne met rien en mémoire', async () => {
    render(
      <TooltipProvider>
        <MemoryPanel />
      </TooltipProvider>,
    );
    const pdf = new File(['%PDF'], 'contrat.pdf', { type: 'application/pdf' });
    fireEvent.drop(await screen.findByRole('dialog'), { dataTransfer: transferOf(pdf) });
    dispatchDroppedPaths(['C:/docs/contrat.pdf']);
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(api.addMemoryDocuments).not.toHaveBeenCalled();
    expect(api.uploadMemoryDocument).not.toHaveBeenCalled();
  });

  it('l’onglet Faits garde son propre « Ajouter » (nouveau fait)', async () => {
    const user = userEvent.setup();
    render(
      <TooltipProvider>
        <MemoryPanel />
      </TooltipProvider>,
    );
    await user.click(await screen.findByRole('button', { name: 'Ajouter' }));
    expect(await screen.findByRole('dialog', { name: 'Nouveau fait' })).toBeInTheDocument();
    expect(shell.pickFiles).not.toHaveBeenCalled();
  });
});

describe('MemoryPanel, documents et dossiers', () => {
  it('un document tient sur une ligne, sans chunks ni rien à déplier', async () => {
    api.memoryPage.mockResolvedValue(
      page({
        items: [documentGroup()],
        total: 1,
        stats: { facts: 2, documents: 4, conversations: 0 },
      }),
    );
    await openDocuments();
    const name = await screen.findByText('rapport.pdf');
    const row = name.closest('li') as HTMLElement;
    expect(within(row).queryByRole('button', { expanded: false })).not.toBeInTheDocument();
    expect(
      within(row)
        .getAllByRole('button')
        .map((button) => button.getAttribute('aria-label')),
    ).toEqual(['Supprimer « rapport.pdf »']);
    expect(screen.getByRole('dialog', { name: 'Mémoire locale' })).not.toHaveTextContent(/chunk/i);
    // L'en-tête compte des documents, plus leurs chunks
    expect(screen.getByText('2 faits · 4 documents · 0 entrée conversation')).toBeInTheDocument();
  });

  it('un document se supprime en entier, après confirmation', async () => {
    api.memoryPage.mockResolvedValue(page({ items: [documentGroup()], total: 1 }));
    const user = await openDocuments();
    await user.click(await screen.findByRole('button', { name: 'Supprimer « rapport.pdf »' }));
    const confirm = await screen.findByRole('dialog', { name: 'Confirmation de suppression' });
    expect(confirm).toHaveTextContent('Supprimer définitivement ce document de la mémoire ?');
    const calls = api.memoryPage.mock.calls.length;
    await user.click(within(confirm).getByRole('button', { name: 'Oui, supprimer' }));
    await waitFor(() => expect(api.deleteMemoryDocument).toHaveBeenCalledWith('rapport_pdf_1'));
    await waitFor(() => expect(api.memoryPage.mock.calls.length).toBeGreaterThan(calls));
  });

  it('ouvert par un lien du chat : onglet Documents, cherché sur le nom, dossier déplié', async () => {
    showInMemory('site');
    expect(usePanels.getState().open).toBe('memory');
    api.memoryPage.mockResolvedValue(page({ items: [FOLDER], total: 1 }));
    render(
      <TooltipProvider>
        <MemoryPanel />
      </TooltipProvider>,
    );
    const folder = await screen.findByRole('button', { name: /^site/ });
    await waitFor(() => expect(folder).toHaveAttribute('aria-expanded', 'true'));
    expect(screen.getByRole('list', { name: 'Fichiers de « site »' })).toBeInTheDocument();
    // Directement l'onglet Documents, cherché sur ce nom : jamais les Faits d'abord
    expect(api.memoryPage.mock.calls).toEqual([['document', 'site', null, 0]]);
    expect(screen.getByRole('tab', { name: /Documents/ })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByDisplayValue('site')).toBeInTheDocument();
    // Nom pris : la prochaine ouverture repart des Faits
    expect(useMemory.getState().focus).toBeNull();
  });

  it('un fichier d’un dossier, ouvert par un lien : tout le dossier, ce fichier en évidence', async () => {
    showInMemory('site', 'README.md');
    api.memoryPage.mockResolvedValue(page({ items: [FOLDER], total: 1 }));
    render(
      <TooltipProvider>
        <MemoryPanel />
      </TooltipProvider>,
    );
    const files = await screen.findByRole('list', { name: 'Fichiers de « site »' });
    // Cherché sur le dossier, pas sur le fichier : ses deux fichiers restent visibles
    expect(api.memoryPage.mock.calls).toEqual([['document', 'site', null, 0]]);
    const rows = within(files).getAllByRole('listitem');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveAttribute('aria-current', 'true');
    expect(rows[0]).toHaveTextContent(/^README\.md/);
    expect(rows[1]).not.toHaveAttribute('aria-current');
  });

  it('une recherche qui ne trouve qu’une partie d’un dossier dit combien il en a en tout', async () => {
    const partial: MemoryFolder = {
      ...FOLDER,
      files: 1,
      total: 5,
      documents: [FOLDER.documents[0]!],
    };
    api.memoryPage.mockResolvedValue(page({ items: [partial], total: 1 }));
    await openDocuments();
    const folder = await screen.findByRole('button', { name: /^site/ });
    expect(folder).toHaveTextContent(/1 fichier sur 5 · /);
  });

  it('seul un dossier se déplie, sur ses fichiers, chacun à supprimer', async () => {
    api.memoryPage.mockResolvedValue(page({ items: [FOLDER, documentGroup()], total: 2 }));
    const user = await openDocuments();
    const folder = await screen.findByRole('button', { name: /^site/ });
    expect(folder).toHaveAttribute('aria-expanded', 'false');
    expect(folder).toHaveTextContent(/2 fichiers · /);
    expect(folder).not.toHaveTextContent(/chunk/);
    await user.click(folder);
    expect(folder).toHaveAttribute('aria-expanded', 'true');
    const files = await screen.findByRole('list', { name: 'Fichiers de « site »' });
    const rows = within(files).getAllByRole('listitem');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent(/^README\.md/);
    expect(rows[1]).toHaveTextContent(/^src\/app\.py/);
    // Les fichiers ne se déplient pas : leur seul bouton les supprime
    expect(within(files).queryAllByRole('button', { expanded: false })).toHaveLength(0);
    // Dans un dossier, « ajouté à la main » ne se répète pas
    expect(rows[1]).not.toHaveTextContent('ajouté à la main');

    await user.click(within(files).getByRole('button', { name: 'Supprimer « src/app.py »' }));
    const confirm = await screen.findByRole('dialog', { name: 'Confirmation de suppression' });
    expect(confirm).toHaveTextContent('site/src/app.py');
    await user.click(within(confirm).getByRole('button', { name: 'Oui, supprimer' }));
    await waitFor(() => expect(api.deleteMemoryDocument).toHaveBeenCalledWith('folder_b'));

    await user.click(folder);
    expect(screen.queryByRole('list', { name: 'Fichiers de « site »' })).not.toBeInTheDocument();
  });

  it('un dossier se supprime avec tous ses fichiers, après confirmation', async () => {
    api.memoryPage.mockResolvedValue(page({ items: [FOLDER], total: 1 }));
    const user = await openDocuments();
    await user.click(await screen.findByRole('button', { name: 'Supprimer « site »' }));
    const confirm = await screen.findByRole('dialog', { name: 'Confirmation de suppression' });
    expect(confirm).toHaveTextContent('Supprimer définitivement ce dossier et ses 2 fichiers ?');
    await user.click(within(confirm).getByRole('button', { name: 'Non, annuler' }));
    expect(api.deleteMemoryFolder).not.toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: 'Supprimer « site »' }));
    await user.click(
      within(await screen.findByRole('dialog', { name: 'Confirmation de suppression' })).getByRole(
        'button',
        { name: 'Oui, supprimer' },
      ),
    );
    // Par sa clé : un autre dossier du même nom reste
    await waitFor(() => expect(api.deleteMemoryFolder).toHaveBeenCalledWith('site_1'));
    expect(api.deleteMemoryDocument).not.toHaveBeenCalled();
  });
});

describe('MemoryPanel, fichier ou dossier déjà en mémoire', () => {
  const RAPPORT = {
    name: 'rapport.pdf',
    target: 'rapport_v1',
    created: '2026-11-17T11:19:00',
    count: 1,
  };

  it('un fichier du même nom : la fenêtre le dit, avec la date de celui qui est là', async () => {
    api.existingMemoryDocuments.mockResolvedValue({ files: [RAPPORT], folders: [] });
    const user = await openDocuments();
    const pdf = new File(['%PDF v2'], 'rapport.pdf', { type: 'application/pdf' });
    drop(transferOf(pdf));
    const question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    expect(question).toHaveTextContent(
      'Un fichier du même nom est déjà en mémoire. Le mettre à jour avec cette version, ou garder les deux ?',
    );
    const row = within(question).getByText('rapport.pdf').closest('li') as HTMLElement;
    expect(row).toHaveTextContent(/rapport\.pdf.*11:19/);
    expect(api.uploadMemoryDocument).not.toHaveBeenCalled(); // rien avant la réponse
    // « Mettre à jour » : il remplace celui-là (sa cible)
    await user.click(within(question).getByRole('button', { name: 'Mettre à jour' }));
    await waitFor(() =>
      expect(api.uploadMemoryDocument).toHaveBeenCalledWith(pdf, 'rapport.pdf', 'rapport_v1'),
    );
    expect(screen.queryByRole('dialog', { name: 'Déjà en mémoire' })).not.toBeInTheDocument();
  });

  it('« Garder les deux » : il s’ajoute à côté, sans rien remplacer', async () => {
    api.existingMemoryDocuments.mockResolvedValue({
      files: [{ ...RAPPORT, count: 2 }],
      folders: [],
    });
    const user = await openDocuments();
    const pdf = new File(['%PDF autre'], 'rapport.pdf', { type: 'application/pdf' });
    drop(transferOf(pdf));
    const question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    // Deux portent déjà ce nom : la date montrée est celle du plus récent
    expect(question).toHaveTextContent('le plus récent des 2');
    await user.click(within(question).getByRole('button', { name: 'Garder les deux' }));
    await waitFor(() =>
      expect(api.uploadMemoryDocument).toHaveBeenCalledWith(pdf, 'rapport.pdf', undefined),
    );
  });

  it('« Annuler » : celui déjà là n’est pas envoyé, les nouveaux partent', async () => {
    api.existingMemoryDocuments.mockResolvedValue({ files: [RAPPORT], folders: [] });
    const user = await openDocuments();
    const old = new File(['%PDF v2'], 'rapport.pdf', { type: 'application/pdf' });
    const fresh = new File(['# Notes'], 'notes.md', { type: 'text/markdown' });
    drop(transferOf(old, fresh));
    const question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    await user.click(within(question).getByRole('button', { name: 'Annuler' }));
    await waitFor(() =>
      expect(api.uploadMemoryDocument).toHaveBeenCalledWith(fresh, 'notes.md', undefined),
    );
    expect(api.uploadMemoryDocument).toHaveBeenCalledTimes(1);
  });

  it('« Ajouter » : plusieurs du même nom, une seule question ; Échap n’envoie qu’eux pas', async () => {
    shell.pickFiles.mockResolvedValue(['C:/docs/a.pdf', 'C:/docs/b.docx', 'C:/docs/c.txt']);
    const existing = {
      files: [
        { name: 'a.pdf', target: 'a_v1', created: '2026-11-10T08:00:00', count: 1 },
        { name: 'b.docx', target: 'b_v1', created: '2026-11-11T08:00:00', count: 1 },
      ],
      folders: [],
    };
    api.existingMemoryDocuments.mockResolvedValue(existing);
    const user = await openDocuments();
    await user.click(await screen.findByRole('button', { name: 'Ajouter' }));
    let question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    expect(question).toHaveTextContent(
      '2 fichiers portent un nom déjà en mémoire. Les mettre à jour avec ces versions, ou garder les deux ?',
    );
    await user.keyboard('{Escape}');
    await waitFor(() => expect(api.addMemoryDocuments).toHaveBeenCalledWith(['C:/docs/c.txt'], {}));
    // Le panneau reste ouvert
    expect(screen.getByRole('dialog', { name: 'Mémoire locale' })).toBeInTheDocument();

    // Mis à jour : chacun avec sa cible
    await user.click(screen.getByRole('button', { name: 'Ajouter' }));
    question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    await user.click(within(question).getByRole('button', { name: 'Mettre à jour' }));
    await waitFor(() =>
      expect(api.addMemoryDocuments).toHaveBeenLastCalledWith(
        ['C:/docs/a.pdf', 'C:/docs/b.docx', 'C:/docs/c.txt'],
        { 'a.pdf': 'a_v1', 'b.docx': 'b_v1' },
      ),
    );
  });

  it('un dossier du même nom : mis à jour, gardé à côté, ou pas envoyé du tout', async () => {
    api.existingMemoryDocuments.mockResolvedValue({
      files: [],
      folders: [{ name: 'site', target: 'site_1', created: '2026-11-16T09:05:00', count: 1 }],
    });
    const user = await openDocuments();
    const site = folderEntry('site', [fileEntry('README.md'), fileEntry('index.html')]);
    const reader = vi.spyOn(site, 'createReader');
    drop(transferWithFolder(site));
    let question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    expect(question).toHaveTextContent(
      'Un dossier du même nom est déjà en mémoire. Le mettre à jour, ou garder les deux ?',
    );
    expect(question).toHaveTextContent(
      "Mettre à jour un dossier remplace ses fichiers modifiés, ajoute les nouveaux et retire ceux qu'il ne contient plus.",
    );
    await user.click(within(question).getByRole('button', { name: 'Annuler' }));
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: 'Déjà en mémoire' })).not.toBeInTheDocument(),
    );
    expect(reader).not.toHaveBeenCalled(); // pas même parcouru
    expect(api.uploadMemoryFolder).not.toHaveBeenCalled();

    drop(transferWithFolder(site));
    question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    await user.click(within(question).getByRole('button', { name: 'Mettre à jour' }));
    await waitFor(() => expect(api.uploadMemoryFolder).toHaveBeenCalledTimes(1));
    expect(api.uploadMemoryFolder.mock.calls[0]?.[0]).toBe('site');
    expect(api.uploadMemoryFolder.mock.calls[0]?.[2]).toBe('site_1');

    drop(transferWithFolder(site));
    question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    await user.click(within(question).getByRole('button', { name: 'Garder les deux' }));
    await waitFor(() => expect(api.uploadMemoryFolder).toHaveBeenCalledTimes(2));
    expect(api.uploadMemoryFolder.mock.calls[1]?.[2]).toBeUndefined();
  });

  it('deux dépôts de suite : une question après l’autre', async () => {
    api.existingMemoryDocuments
      .mockResolvedValueOnce({ files: [{ ...RAPPORT, name: 'a.md', target: 'a1' }], folders: [] })
      .mockResolvedValueOnce({ files: [{ ...RAPPORT, name: 'b.md', target: 'b1' }], folders: [] });
    const user = await openDocuments();
    const first = new File(['a'], 'a.md');
    const second = new File(['b'], 'b.md');
    drop(transferOf(first));
    drop(transferOf(second));
    let question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    expect(within(question).getByText('a.md')).toBeInTheDocument();
    await user.click(within(question).getByRole('button', { name: 'Mettre à jour' }));
    await waitFor(() => expect(api.uploadMemoryDocument).toHaveBeenCalledWith(first, 'a.md', 'a1'));
    question = await screen.findByRole('dialog', { name: 'Déjà en mémoire' });
    expect(within(question).getByText('b.md')).toBeInTheDocument();
    await user.click(within(question).getByRole('button', { name: 'Annuler' }));
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: 'Déjà en mémoire' })).not.toBeInTheDocument(),
    );
    expect(api.uploadMemoryDocument).toHaveBeenCalledTimes(1);
  });
});
