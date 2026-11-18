import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { relativeImagePath, resetFileLinks } from '../../../lib/files';
import { Markdown } from './Markdown';

const api = vi.hoisted(() => ({ fileLinks: vi.fn() }));
vi.mock('../../../lib/api', () => ({ api, ApiError: class ApiError extends Error {} }));

const README = 'C:\\Users\\moi\\Projet\\README.md';

// En-tête d'un README de GitHub : HTML autour de Markdown, sur plusieurs blocs
const HEADER = [
  '<div align="center">',
  '  <img src="frontend/public/logo.svg" alt="Logo" width="96">',
  '',
  '# My_AI',
  '',
  'Propulsé par [Ollama](https://ollama.com).<br>',
  'En 12 langues.',
  '',
  '<img src="https://img.shields.io/badge/x-y.svg" alt="Badge">',
  '</div>',
  '',
  '<details><summary>Plus</summary>',
  '',
  'Caché par défaut.',
  '',
  '</details>',
].join('\n');

beforeEach(() => {
  vi.clearAllMocks();
  resetFileLinks();
  api.fileLinks.mockImplementation((paths: string[]) =>
    Promise.resolve({
      links: Object.fromEntries(paths.map((path) => [path, '/files/s/t/logo.svg'])),
    }),
  );
});

describe('fichier Markdown en aperçu', () => {
  it('rend le HTML d’un README : bloc centré, logo de son dossier, saut de ligne, détails', async () => {
    const { container } = render(<Markdown text={HEADER} file={README} />);
    // Aucune balise affichée en texte
    expect(container.textContent).not.toContain('<div');
    expect(container.textContent).not.toContain('<img');
    const centered = container.querySelector('div[align="center"]');
    expect(centered?.querySelector('h1')?.textContent).toBe('My_AI');
    // Le logo vient du dossier du README, par un lien signé que le serveur vérifie
    const logo = await screen.findByRole('img', { name: 'Logo' });
    expect(logo).toHaveAttribute('src', '/files/s/t/logo.svg');
    expect(logo).toHaveAttribute('width', '96');
    expect(api.fileLinks).toHaveBeenCalledWith(
      ['C:\\Users\\moi\\Projet\\frontend\\public\\logo.svg'],
      README,
    );
    // Image distante : un lien, jamais chargée (appli hors ligne)
    expect(screen.queryByRole('img', { name: 'Badge' })).not.toBeInTheDocument();
    expect(screen.getByText('Badge')).toBeInTheDocument();
    // <br> lu, et pas de saut de ligne forcé en plus (comme sur GitHub)
    expect(centered?.querySelectorAll('br')).toHaveLength(1);
    expect(container.querySelector('details summary')?.textContent).toBe('Plus');
  });

  it('assainit le HTML : ni script, ni gestionnaire d’événement, ni style', () => {
    const { container } = render(
      <Markdown
        text={
          'Avant <img src="a.png" onerror="alert(1)" alt="a"> <script>alert(2)</script>' +
          ' <a href="javascript:alert(3)">piège</a> <span style="color:red">rouge</span>' +
          ' <iframe src="https://example.com"></iframe>'
        }
        file={README}
      />,
    );
    expect(container.querySelector('script')).toBeNull();
    expect(container.querySelector('iframe')).toBeNull();
    expect(container.querySelector('[onerror]')).toBeNull();
    expect(container.querySelector('[style]')).toBeNull();
    expect(container.querySelector('a[href^="javascript"]')).toBeNull();
    expect(container.textContent).toContain('piège');
    expect(container.textContent).toContain('rouge');
  });

  it('une image refusée par le serveur reste un libellé', async () => {
    api.fileLinks.mockResolvedValue({ links: {} });
    render(<Markdown text={'![Schéma](docs/schema.png)'} file={README} />);
    await waitFor(() => expect(api.fileLinks).toHaveBeenCalled());
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByText('Schéma')).toBeInTheDocument();
  });

  it('une réponse du modèle n’interprète toujours pas le HTML', () => {
    const { container } = render(<Markdown text={HEADER} />);
    expect(container.querySelector('div[align]')).toBeNull();
    expect(container.textContent).toContain('<div align="center">');
  });

  it('trouve les images relatives à côté du fichier, jamais ailleurs', () => {
    expect(relativeImagePath(README, 'docs/a%20b.png')).toBe(
      'C:\\Users\\moi\\Projet\\docs\\a b.png',
    );
    expect(relativeImagePath(README, './logo.svg?v=2#x')).toBe('C:\\Users\\moi\\Projet\\logo.svg');
    expect(relativeImagePath('/home/moi/notes/a.md', 'img/b.png')).toBe(
      '/home/moi/notes/img/b.png',
    );
    for (const source of [
      'https://x.org/a.png',
      'data:image/png;base64,x',
      '/abs/a.png',
      'C:\\a.png',
      '',
    ]) {
      expect(relativeImagePath(README, source)).toBeNull();
    }
  });
});
