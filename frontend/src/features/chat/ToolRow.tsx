import { ChevronRight, CircleAlert, LoaderCircle } from 'lucide-react';
import { createElement, useState } from 'react';

import { cn } from '../../lib/cn';
import type { ToolCallView } from '../../lib/events';
import { toolIcon, toolOutcome, toolText } from './tools';

/** Appel d'outil en ligne compacte : « Recherche sur internet : « … » · 3 sources » */
export function ToolRow({ tool, running }: { tool: ToolCallView; running: boolean }) {
  const [open, setOpen] = useState(false);
  const failed = tool.ok === false;
  const outcome = toolOutcome(tool);
  const details = tool.summary && (failed || tool.name !== 'web_search') ? tool.summary : '';

  return (
    <div className="my-1.5">
      <button
        type="button"
        disabled={!details}
        onClick={() => setOpen(!open)}
        aria-expanded={details ? open : undefined}
        className={cn(
          'group inline-flex max-w-full items-center gap-2 rounded-sm py-0.5 text-left text-sm text-fg-2',
          details && 'hover:text-fg',
        )}
      >
        {running ? (
          <LoaderCircle size={15} className="spin shrink-0 text-accent" />
        ) : failed ? (
          <CircleAlert size={15} className="shrink-0 text-error" />
        ) : (
          createElement(toolIcon(tool.name), { size: 15, className: 'shrink-0' })
        )}
        <span className={cn('truncate', running && 'shimmer')}>{toolText(tool.label)}</span>
        {outcome ? <span className="shrink-0 text-fg-3">· {outcome}</span> : null}
        {details ? (
          <ChevronRight
            size={14}
            className={cn('shrink-0 transition-transform duration-150', open && 'rotate-90')}
          />
        ) : null}
      </button>
      {open && details ? (
        <div className="mt-1 ml-[23px] border-l-2 border-line pl-3 text-sm text-fg-3">
          {details}
        </div>
      ) : null}
    </div>
  );
}
