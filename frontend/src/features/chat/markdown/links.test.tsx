import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { buildChatLinks, citationKey, parseCitationMap } from './links';
import { Markdown } from './Markdown';

const revealPath = vi.hoisted(() => vi.fn(() => Promise.resolve()));
vi.mock('../../../lib/actions', () => ({ revealPath }));

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

    fireEvent.click(paths[1]!);
    expect(revealPath).toHaveBeenCalledWith('C:\\Users\\moi\\notes.md');
  });

  it('ne touche à rien sans table ni chemin', () => {
    expect(buildChatLinks('', [])).toBeNull();
    const { container } = render(<Markdown text="Voir [1] plus haut." links={null} />);
    expect(container.querySelector('a')).toBeNull();
  });
});
