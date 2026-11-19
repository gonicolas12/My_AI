import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MemoryLink } from '../../../lib/events';
import { buildChatLinks, citationKey, parseCitationMap, prepareLinks } from './links';
import { Markdown } from './Markdown';

const revealPath = vi.hoisted(() => vi.fn(() => Promise.resolve()));
vi.mock('../../../lib/actions', () => ({ revealPath }));
const showInMemory = vi.hoisted(() => vi.fn());
vi.mock('../../../stores/memory', () => ({ showInMemory }));
const openFilePreview = vi.hoisted(() => vi.fn());
vi.mock('../../../stores/preview', () => ({ openFilePreview }));

beforeEach(() => {
  vi.clearAllMocks();
});

const ANSWER = [
  'Python 3.14 apporte un mode sans GIL [1] et les template strings [2].',
  'Le rapport est dans `C:\\Users\\moi\\rapport.docx`, et aussi C:\\Users\\moi\\notes.md.',
  '',
  '```text',
  'Voir [1] et C:\\Users\\moi\\notes.md',
  '```',
  '',
  '📚 **Sources**',
  '[1] [docs.python.org](https://docs.python.org/3.14/whatsnew)',
  '[2] https://peps.python.org/pep-0750/.',
].join('\n');

describe('citations et chemins cliquables', () => {
  it('lit la table des sources comme utils/citations.py', () => {
    expect([...parseCitationMap(ANSWER)]).toEqual([
      [1, 'https://docs.python.org/3.14/whatsnew'],
      [2, 'https://peps.python.org/pep-0750/'],
    ]);
    expect(citationKey('Sans source')).toBe('');
  });

  it('rend les marqueurs [n] et les chemins cliquables, jamais dans un bloc de code', () => {
    const links = buildChatLinks(citationKey(ANSWER), [
      { text: 'C:\\Users\\moi\\rapport.docx', path: 'C:\\Users\\moi\\rapport.docx' },
      { text: 'C:\\Users\\moi\\notes.md', path: 'C:\\Users\\moi\\notes.md' },
    ]);
    const { container } = render(<Markdown text={ANSWER} links={links} />);

    const cites = [...container.querySelectorAll<HTMLAnchorElement>('a.md-cite')];
    // Deux dans le texte, deux dans le bloc Sources ; aucun dans le code
    expect(cites.map((a) => [a.textContent, a.getAttribute('href')])).toEqual([
      ['[1]', 'https://docs.python.org/3.14/whatsnew'],
      ['[2]', 'https://peps.python.org/pep-0750/'],
      ['[1]', 'https://docs.python.org/3.14/whatsnew'],
      ['[2]', 'https://peps.python.org/pep-0750/'],
    ]);
    const paths = screen.getAllByRole('link', { name: /C:\\Users\\moi/ });
    // Le chemin entre backticks et le chemin du texte ; pas celui du bloc de code
    expect(paths.map((button) => button.textContent)).toEqual([
      'C:\\Users\\moi\\rapport.docx',
      'C:\\Users\\moi\\notes.md',
    ]);
    expect(container.querySelector('pre')?.textContent).toContain('Voir [1] et C:\\Users');

    // Un fichier cité s'ouvre dans le volet d'aperçu, jamais dans l'Explorateur
    fireEvent.click(paths[1]!);
    expect(openFilePreview).toHaveBeenCalledWith('C:\\Users\\moi\\notes.md');
    expect(revealPath).not.toHaveBeenCalled();
  });

  it('un dossier cité s’ouvre dans l’Explorateur', () => {
    const folder = 'C:\\Users\\moi\\Projets';
    const links = buildChatLinks('', [{ text: folder, path: folder, dir: true }]);
    render(<Markdown text={`Tout est dans ${folder}.`} links={links} />);
    const link = screen.getByRole('link', { name: folder });
    expect(link).toHaveAttribute('title', `Afficher dans l’Explorateur : ${folder}`);
    fireEvent.click(link);
    expect(revealPath).toHaveBeenLastCalledWith(folder);
    expect(openFilePreview).not.toHaveBeenCalledWith(folder);
  });

  it('clic droit sur un fichier cité : « Afficher dans l’Explorateur » ; pas sur un dossier', async () => {
    const user = userEvent.setup();
    const file = 'C:\\Users\\moi\\rapport.docx';
    const folder = 'C:\\Users\\moi\\Projets';
    const links = buildChatLinks('', [
      { text: file, path: file },
      { text: folder, path: folder, dir: true },
    ]);
    render(<Markdown text={`Voir ${file} et ${folder}.`} links={links} />);
    fireEvent.contextMenu(screen.getByRole('link', { name: file }), { clientX: 40, clientY: 60 });
    const menu = await screen.findByRole('menu', { name: 'rapport.docx' });
    await user.click(within(menu).getByRole('menuitem', { name: 'Afficher dans l’Explorateur' }));
    expect(revealPath).toHaveBeenLastCalledWith(file);
    // L'aperçu, lui, reste au clic gauche
    expect(openFilePreview).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
    // Un dossier : son clic l'ouvre déjà dans l'Explorateur, pas de menu
    fireEvent.contextMenu(screen.getByRole('link', { name: folder }), { clientX: 40, clientY: 90 });
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it.each([
    ['macOS', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15', 'le Finder'],
    [
      'Linux',
      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15',
      'le gestionnaire de fichiers',
    ],
  ])(
    '%s : le menu et l’infobulle nomment son gestionnaire de fichiers',
    async (_os, agent, manager) => {
      const spy = vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(agent);
      try {
        const file = '/home/moi/rapport.docx';
        const folder = '/home/moi/Projets';
        const links = buildChatLinks('', [
          { text: file, path: file },
          { text: folder, path: folder, dir: true },
        ]);
        render(<Markdown text={`Voir ${file} et ${folder}.`} links={links} />);
        expect(screen.getByRole('link', { name: folder })).toHaveAttribute(
          'title',
          `Afficher dans ${manager} : ${folder}`,
        );
        fireEvent.contextMenu(screen.getByRole('link', { name: file }), {
          clientX: 40,
          clientY: 60,
        });
        const menu = await screen.findByRole('menu', { name: 'rapport.docx' });
        expect(within(menu).getByRole('menuitem')).toHaveTextContent(`Afficher dans ${manager}`);
      } finally {
        spy.mockRestore();
      }
    },
  );

  it('un fichier de la conversation nommé sans son chemin : cliquable entier, aperçu au clic', () => {
    const path = 'C:\\Users\\moi\\Téléchargements\\budget.xlsx';
    const links = buildChatLinks('', [{ text: 'budget.xlsx', path, name: true }]);
    render(
      <Markdown
        text="Dans budget.xlsx (pas MonBudget.xlsx ni budget.xlsx.bak ni D:\\autre\\budget.xlsx), voir `budget.xlsx`."
        links={links}
      />,
    );
    const named = screen.getAllByRole('link', { name: 'budget.xlsx' });
    // Le nom au fil du texte et en code ; ni dans un autre nom, ni dans un chemin
    expect(named).toHaveLength(2);
    fireEvent.click(named[0]!);
    expect(openFilePreview).toHaveBeenLastCalledWith(path);
  });

  it('ne touche à rien sans table ni chemin', () => {
    expect(buildChatLinks('', [])).toBeNull();
    const { container } = render(<Markdown text="Voir [1] plus haut." links={null} />);
    expect(container.querySelector('a')).toBeNull();
  });
});

// Réponse vue dans l'appli : un lien inventé, cible avec une espace, et des noms en code
const MEMORY_ANSWER = [
  'Dans ton dossier OneDrive, je trouve :',
  '',
  '📁 **[Dossier OneDrive_3_06-10-2026](memory://one drive)**',
  '',
  '- 📄 `modele-xml-cmd.xml` (déposé le 17/11/2026)',
  '- 📊 `Data.xlsx`, comme **Data.xlsx** au fil du texte',
  '- le dossier projet, et `projet` en code',
  '- [notes](notes.txt), [ailleurs](memory://ailleurs) et [la page](https://example.com/Data.xlsx)',
].join('\n');

const MEMORY: MemoryLink[] = [
  { text: 'OneDrive_3_06-10-2026', kind: 'folder', name: 'OneDrive_3_06-10-2026' },
  {
    text: 'modele-xml-cmd.xml',
    kind: 'document',
    name: 'modele-xml-cmd.xml',
    folder: 'OneDrive_3_06-10-2026',
  },
  { text: 'Data.xlsx', kind: 'document', name: 'Data.xlsx' },
  { text: 'notes.txt', kind: 'document', name: 'notes.txt' },
  { text: 'projet', kind: 'folder', name: 'projet', strict: true },
];

describe('documents et dossiers de la Mémoire cliquables', () => {
  it('met entre < > la cible d’un lien qui contient une espace, jamais dans du code', () => {
    expect(prepareLinks('[Dossier X](memory://one drive)')).toBe(
      '[Dossier X](<memory://one drive>)',
    );
    // Titre entre guillemets, code en ligne, bloc de code : intacts
    for (const text of [
      '[site](https://a.example "Le titre")',
      '`[a](b c)`',
      '```\n[a](b c)\n```',
    ]) {
      expect(prepareLinks(text)).toBe(text);
    }
  });

  it('rend cliquables les noms cités et les liens qui les visent', () => {
    const links = buildChatLinks('', undefined, MEMORY);
    const { container } = render(<Markdown text={MEMORY_ANSWER} links={links} />);

    // Plus de Markdown brut : le lien inventé n'apparaît plus tel quel
    expect(container.textContent).not.toContain('](');
    const refs = [...container.querySelectorAll<HTMLElement>('.md-memory')];
    expect(refs.map((ref) => ref.textContent)).toEqual([
      'Dossier OneDrive_3_06-10-2026',
      'modele-xml-cmd.xml',
      'Data.xlsx',
      'Data.xlsx',
      // « projet » au fil du texte reste un mot ; en code, c'est le dossier
      'projet',
      // Lien dont la cible est un document de la Mémoire
      'notes',
    ]);
    expect(refs.every((ref) => ref.getAttribute('role') === 'link')).toBe(true);
    expect(refs[0]?.getAttribute('title')).toContain('OneDrive_3_06-10-2026');

    // Lien inventé vers rien de connu : son seul texte ; page web : un vrai lien
    expect(container.querySelector('.md-link-inert')?.textContent).toBe('ailleurs');
    expect(container.querySelector('a[href="https://example.com/Data.xlsx"]')?.textContent).toBe(
      'la page',
    );

    // Un dossier : cherché sur son nom ; un fichier d'un dossier : tout le dossier, ce
    // fichier en évidence ; un document seul : cherché sur son nom, en évidence
    fireEvent.click(refs[0]!);
    expect(showInMemory).toHaveBeenLastCalledWith('OneDrive_3_06-10-2026');
    fireEvent.click(refs[1]!);
    expect(showInMemory).toHaveBeenLastCalledWith('OneDrive_3_06-10-2026', 'modele-xml-cmd.xml');
    fireEvent.keyDown(refs[5]!, { key: 'Enter' });
    expect(showInMemory).toHaveBeenLastCalledWith('notes.txt', 'notes.txt');
  });

  it('un nom collé au japonais ou au coréen est un lien ; collé à un mot latin, non', () => {
    const links = buildChatLinks('', undefined, [
      { text: 'Data.xlsx', kind: 'document', name: 'Data.xlsx' },
    ]);
    const { container } = render(
      <Markdown
        text={
          'Data.xlsxには注文が2件。Data.xlsx를 열어 보세요. [Data.xlsxの中身](memory://x). ' +
          'MyData.xlsx et Data.xlsx.bak : non.'
        }
        links={links}
      />,
    );
    expect([...container.querySelectorAll('.md-memory')].map((ref) => ref.textContent)).toEqual([
      'Data.xlsx',
      'Data.xlsx',
      'Data.xlsxの中身',
    ]);
  });

  it('un lien vers un fichier existant l’ouvre dans l’aperçu', () => {
    const path = 'C:\\Users\\moi\\Mes rapports\\rapport.docx';
    const links = buildChatLinks('', [{ text: path, path }], MEMORY);
    render(
      <Markdown
        text={`Voir [le rapport](${path}) ou [Data](file:///C:/x/Data.xlsx).`}
        links={links}
      />,
    );
    fireEvent.click(screen.getByRole('link', { name: 'le rapport' }));
    expect(openFilePreview).toHaveBeenLastCalledWith(path);
    // Chemin absent du disque, mais nom de la Mémoire : la Mémoire
    fireEvent.click(screen.getByRole('link', { name: 'Data' }));
    expect(showInMemory).toHaveBeenLastCalledWith('Data.xlsx', 'Data.xlsx');
  });
});
