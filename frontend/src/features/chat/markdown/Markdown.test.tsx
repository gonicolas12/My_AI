import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Markdown } from './Markdown';

describe('Markdown (contenu non fiable)', () => {
  it("affiche le HTML brut comme du texte, sans l'interpréter", () => {
    const { container } = render(
      <Markdown text={'Avant <img src=x onerror="alert(1)"> et <script>alert(2)</script>'} />,
    );
    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('script')).toBeNull();
    expect(container.textContent).toContain('<img src=x onerror="alert(1)">');
  });

  it('ouvre les liens web hors de la fenêtre et neutralise les autres', () => {
    const { container } = render(
      <Markdown
        text={'[site](https://example.com) [piège](javascript:alert(1)) [local](file:///C:/a.exe)'}
      />,
    );
    const links = container.querySelectorAll('a');
    expect(links).toHaveLength(1);
    expect(links[0]?.getAttribute('href')).toBe('https://example.com/');
    expect(links[0]?.getAttribute('target')).toBe('_blank');
    expect(links[0]?.getAttribute('rel')).toContain('noopener');
    expect(container.textContent).toContain('piège');
    expect(container.textContent).toContain('local');
  });

  it('ne charge pas les images distantes', () => {
    const { container } = render(<Markdown text={'![schéma](https://example.com/a.png)'} />);
    expect(container.querySelector('img')).toBeNull();
    expect(screen.getByText('schéma')).toBeInTheDocument();
  });

  it('rend tableaux, listes et code avec son bouton Copier', () => {
    const { container } = render(
      <Markdown
        text={'| a | b |\n|---|---|\n| 1 | 2 |\n\n- un\n- deux\n\n```python\nprint(1)\n```'}
      />,
    );
    expect(container.querySelector('.md-table-wrap table')).not.toBeNull();
    expect(container.querySelectorAll('li')).toHaveLength(2);
    expect(container.querySelector('.code-lang')?.textContent).toBe('python');
    expect(screen.getByRole('button', { name: 'Copier le code' })).toBeInTheDocument();
    expect(container.querySelector('.code-body')?.textContent).toBe('print(1)');
  });

  it('garde les sauts de ligne simples, comme Tk et la PWA', () => {
    const { container } = render(
      <Markdown text={'📚 **Sources**\n[1] https://a.example\n[2] https://b.example'} />,
    );
    expect(container.querySelectorAll('br')).toHaveLength(2);
    expect(container.querySelectorAll('a')).toHaveLength(2);
  });

  it('referme le Markdown incomplet du dernier bloc pendant le streaming', () => {
    const { container } = render(<Markdown text={'Un texte **en gras'} streaming />);
    expect(container.querySelector('strong')?.textContent).toBe('en gras');
  });

  it('affiche un bloc de code encore ouvert pendant le streaming', () => {
    const { container } = render(<Markdown text={'```js\nconst a = 1;\nconst b'} streaming />);
    expect(container.querySelector('.code-body')?.textContent).toBe('const a = 1;\nconst b');
  });
});
