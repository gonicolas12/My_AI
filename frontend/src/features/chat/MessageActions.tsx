import { Check, Copy } from 'lucide-react';
import { useState, type ReactNode } from 'react';

import { IconButton } from '../../components/ui/Button';
import { cn } from '../../lib/cn';

export function CopyButton({ text, label = 'Copier' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard
      .writeText(text)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      })
      .catch(() => undefined);
  };
  return (
    <IconButton label={copied ? 'Copié' : label} size="sm" onClick={copy} tooltipSide="bottom">
      {copied ? <Check size={15} className="text-success" /> : <Copy size={15} />}
    </IconButton>
  );
}

/** Actions sous un message : visibles au survol, toujours sous le dernier */
export function MessageActions({
  children,
  meta,
  pinned,
  align = 'start',
}: {
  children: ReactNode;
  meta?: string;
  pinned?: boolean;
  align?: 'start' | 'end';
}) {
  return (
    <div
      className={cn(
        'mt-1 flex items-center gap-1 transition-opacity duration-150',
        align === 'end' && 'flex-row-reverse',
        pinned
          ? 'opacity-100'
          : 'opacity-0 group-focus-within/msg:opacity-100 group-hover/msg:opacity-100',
      )}
    >
      {children}
      {meta ? <span className="px-1.5 text-xs text-fg-3 tabular-nums">{meta}</span> : null}
    </div>
  );
}
