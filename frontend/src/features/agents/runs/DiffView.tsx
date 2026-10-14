/*
 * Diff d'un code modifié par un agent (§8) : le code fourni et la version de
 * l'agent ligne à ligne (retirées en rouge, ajoutées en vert, le reste replié
 * autour des changements), puis l'explication de l'agent sans ce bloc.
 */

import { FileText } from 'lucide-react';
import { useMemo } from 'react';

import { Markdown } from '../../chat/markdown/Markdown';
import { tint } from '../agentMeta';
import { type CodeChange, diffRows, withoutBlock } from './diff';

const ROW_TINT = { '-': tint('var(--error)', 13), '+': tint('var(--success)', 13) };
const SIGN_COLOR = { '-': 'var(--error)', '+': 'var(--success)' };

export function DiffView({ change, output }: { change: CodeChange; output: string }) {
  const rows = useMemo(() => diffRows(change.lines), [change.lines]);
  const rest = useMemo(() => withoutBlock(output, change.block), [output, change.block]);
  return (
    <div>
      <div className="overflow-hidden rounded-md border border-line/70 bg-bg font-mono text-[12.5px] leading-[1.65]">
        <div className="flex h-8 items-center gap-2 border-b border-line/60 px-3 font-sans text-xs text-fg-2">
          <FileText size={13} />
          {change.name}
          {change.block.lang ? <span className="text-fg-3">· {change.block.lang}</span> : null}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <tbody>
              {rows.map((row, index) =>
                row.kind === 'gap' ? (
                  <tr key={index} className="text-fg-3">
                    <td colSpan={4} className="bg-bg-2/60 px-3 py-0.5 font-sans text-xs">
                      ⋯ {row.hidden} ligne{row.hidden > 1 ? 's' : ''} identique
                      {row.hidden > 1 ? 's' : ''}
                    </td>
                  </tr>
                ) : (
                  <tr
                    key={index}
                    style={{ background: row.kind === ' ' ? undefined : ROW_TINT[row.kind] }}
                  >
                    <td className="w-10 pr-2 text-right align-top text-fg-3 select-none">
                      {row.old ?? ''}
                    </td>
                    <td className="w-10 pr-2 text-right align-top text-fg-3 select-none">
                      {row.new ?? ''}
                    </td>
                    <td
                      className="w-5 text-center align-top select-none"
                      style={{ color: row.kind === ' ' ? undefined : SIGN_COLOR[row.kind] }}
                    >
                      {row.kind === '-' ? '−' : row.kind === '+' ? '+' : ''}
                    </td>
                    <td className="pr-3 whitespace-pre text-[var(--shiki-foreground)]">
                      {row.text || ' '}
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      </div>
      {rest ? (
        <div className="mt-3">
          <Markdown text={rest} />
        </div>
      ) : null}
    </div>
  );
}
