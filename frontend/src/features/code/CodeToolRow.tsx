import { Ban, ChevronRight, CircleAlert, LoaderCircle, Lock, OctagonX } from 'lucide-react';
import { createElement, useState } from 'react';

import { Button } from '../../components/ui/Button';
import { type MessageKey, useT } from '../../i18n';
import { cn } from '../../lib/cn';
import type { ApprovalDecision, CodeToolCall, CodeToolStatus } from '../../lib/events';
import { approveCode } from '../../stores/code';
import { codeToolIcon, codeToolInput, codeToolLabel } from './codeTools';

const DECISIONS: Record<ApprovalDecision, MessageKey> = {
  'allow-once': 'code.approval.allowOnce',
  'allow-target': 'code.approval.allowTarget',
  'allow-tool': 'code.approval.allowTool',
  deny: 'code.approval.deny',
};

const OUTCOMES: Partial<Record<CodeToolStatus, MessageKey>> = {
  'awaiting-approval': 'code.toolStatus.awaiting',
  failed: 'code.toolStatus.failed',
  denied: 'code.toolStatus.denied',
  stopped: 'code.toolStatus.stopped',
};

function StatusIcon({ tool }: { tool: CodeToolCall }) {
  switch (tool.status) {
    case 'requested':
    case 'running':
      return <LoaderCircle size={15} className="spin shrink-0 text-accent" />;
    case 'awaiting-approval':
      return <Lock size={15} className="shrink-0 text-warning" />;
    case 'failed':
      return <CircleAlert size={15} className="shrink-0 text-error" />;
    case 'denied':
      return <Ban size={15} className="shrink-0 text-fg-3" />;
    case 'stopped':
      return <OctagonX size={15} className="shrink-0 text-fg-3" />;
    default:
      return createElement(codeToolIcon(tool.name), { size: 15, className: 'shrink-0' });
  }
}

function Detail({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <div className="mb-1 text-2xs font-semibold tracking-wide text-fg-3 uppercase">{label}</div>
      {/* Code et chemins se lisent de gauche à droite, même en arabe */}
      <pre
        dir="ltr"
        className="max-h-72 overflow-auto rounded-sm bg-bg-2 px-2.5 py-2 font-mono text-xs leading-relaxed break-words whitespace-pre-wrap text-fg-2"
      >
        {text}
      </pre>
    </div>
  );
}

/**
 * Appel d'outil de l'extension VS Code, en ligne compacte (« Lecture de
 * src/app.ts »), ses arguments et sa sortie au clic. Une écriture ou une
 * commande demandée pour un message du PC ou du téléphone attend l'accord de
 * l'utilisateur : ses boutons sont ici, dans VS Code et sur le téléphone, la
 * première réponse comptant. Pour un message tapé dans VS Code, c'est VS Code
 * qui demande.
 */
export function CodeToolRow({ tool }: { tool: CodeToolCall }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  // Réponse donnée à cette demande-ci : une nouvelle demande est un nouvel objet
  const [answered, setAnswered] = useState<CodeToolCall | null>(null);
  const running = tool.status === 'requested' || tool.status === 'running';
  const waiting = tool.status === 'awaiting-approval';
  const options = waiting ? (tool.options ?? []) : [];
  const outcome = OUTCOMES[tool.status];

  return (
    <div className="my-1.5">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="group inline-flex max-w-full items-center gap-2 rounded-sm py-0.5 text-start text-sm text-fg-2 hover:text-fg"
      >
        <StatusIcon tool={tool} />
        <span className={cn('truncate', running && 'shimmer')}>{codeToolLabel(tool, t)}</span>
        {outcome ? <span className="shrink-0 text-fg-3">· {t(outcome)}</span> : null}
        <ChevronRight
          size={14}
          className={cn(
            'shrink-0 transition-transform duration-150 rtl:-scale-x-100',
            open && 'rotate-90 rtl:-rotate-90',
          )}
        />
      </button>
      {waiting && options.length ? (
        <div className="ms-[23px] mt-1.5 rounded-md border border-warning/40 bg-warning-soft px-3 py-2.5">
          <p className="text-sm text-fg">{t('code.approval.prompt')}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {options.map((decision, index) => (
              <Button
                key={decision}
                size="sm"
                variant={decision === 'deny' ? 'ghost' : index === 0 ? 'primary' : 'secondary'}
                disabled={answered === tool}
                onClick={() => {
                  setAnswered(tool);
                  void approveCode(tool.call_id, decision);
                }}
              >
                {t(DECISIONS[decision], { tool: tool.name })}
              </Button>
            ))}
          </div>
        </div>
      ) : null}
      {waiting && !options.length ? (
        <p className="ms-[23px] mt-1 text-xs text-fg-3">{t('code.approval.inVscode')}</p>
      ) : null}
      {open ? (
        <div className="ms-[23px] mt-1 space-y-2 border-s-2 border-line ps-3">
          <Detail label={t('code.tool.input')} text={codeToolInput(tool)} />
          {tool.output !== undefined ? (
            <Detail label={t('code.tool.output')} text={tool.output || t('code.tool.empty')} />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
