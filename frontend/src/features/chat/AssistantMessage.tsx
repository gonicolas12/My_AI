import { CircleAlert, Eye, OctagonX } from 'lucide-react';
import { memo, useMemo } from 'react';

import { RobotLogo } from '../../components/ui/RobotLogo';
import { baseName, messageArtifacts } from '../../lib/artifacts';
import type { MessageView, ToolCallView } from '../../lib/events';
import { formatDecimal, formatDuration, formatTime } from '../../lib/format';
import type { LiveTurn } from '../../stores/chatReducer';
import { openPreview } from '../../stores/preview';
import { FileCard, GeneratedImage } from './FileCard';
import { buildChatLinks, citationKey } from './markdown/links';
import { Markdown } from './markdown/Markdown';
import { CopyButton, MessageActions } from './MessageActions';
import { buildParts } from './parts';
import { Reasoning } from './Reasoning';
import { ToolRow } from './ToolRow';
import { toolText } from './tools';

const NO_TOOLS: ToolCallView[] = [];
const NO_DOCUMENTS: string[] = [];

/**
 * Bloc « Réflexion » en attente : requête complexe (comme Tk, affiché dès
 * le début), ou jetons de réflexion en cours de réception.
 */
function reasoningActive(live: LiveTurn | null): boolean {
  if (!live) return false;
  if (live.thinkingActive) return true;
  return live.reasoning && !live.thinking && !live.text && live.tools.length === 0;
}

/** Ce que fait l'IA quand rien d'autre ne le montre (outil, réflexion, texte) */
function activityOf(live: LiveTurn | null): string | null {
  if (!live) return "L'IA réfléchit";
  if (live.kind !== 'chat') return live.status || null;
  if (reasoningActive(live)) return null; // le bloc Réflexion s'anime
  const last = live.tools[live.tools.length - 1];
  if (last?.name === 'synthesis') {
    return live.text.length <= (last.at ?? 0) ? toolText(last.label) : null;
  }
  if (last && last.ok === undefined) return null; // la ligne de l'outil s'anime
  if (!live.text) return live.thinking ? 'Rédaction de la réponse' : "L'IA réfléchit";
  if (last && live.text.length <= (last.at ?? 0)) return "L'IA réfléchit";
  return null;
}

function Activity({ label, progress }: { label: string; progress?: number | null }) {
  return (
    <div className="my-1.5 flex items-center gap-2 text-sm" role="status" aria-live="polite">
      <RobotLogo size={16} className="pulse-soft shrink-0 text-accent" />
      <span className="shimmer">{label}…</span>
      {progress !== null && progress !== undefined ? (
        <span className="ml-1 h-1 w-28 overflow-hidden rounded-full bg-bg-3">
          <span
            className="block h-full rounded-full bg-accent transition-[width] duration-200"
            style={{ width: `${Math.round(Math.min(1, Math.max(0, progress)) * 100)}%` }}
          />
        </span>
      ) : null}
    </div>
  );
}

/**
 * Texte affiché d'une réponse. Celui d'une génération de fichier finit par le
 * nom du fichier, que Tk rendait cliquable : la carte du fichier le montre.
 */
function shownText(message: MessageView | undefined): string {
  const text = message?.text ?? '';
  const name = message?.file_path ? baseName(message.file_path) : '';
  if (message?.type === 'file_generation' && name && text.endsWith(name)) {
    return text.slice(0, -name.length).trimEnd();
  }
  return text;
}

interface AssistantMessageProps {
  message?: MessageView | undefined;
  live?: LiveTurn | null;
  /** Message de l'utilisateur traité, réponse pas encore commencée */
  pending?: boolean;
  isLast?: boolean;
}

export const AssistantMessage = memo(function AssistantMessage({
  message,
  live = null,
  pending = false,
  isLast = false,
}: AssistantMessageProps) {
  const streaming = live !== null || pending;
  const mid = live?.mid ?? message?.mid ?? null;
  const text = live ? live.text : shownText(message);
  const tools = live ? live.tools : (message?.tool_calls ?? NO_TOOLS);
  const thinking = live ? live.thinking : (message?.thinking ?? '');
  const documents = live ? live.documents : (message?.documents ?? NO_DOCUMENTS);
  const parts = useMemo(() => buildParts(text, tools), [text, tools]);
  const lastText = parts.findLastIndex((part) => part.kind === 'text');
  const activity = streaming ? activityOf(live) : null;
  const thinkingNow = reasoningActive(live);
  const error = Boolean(message?.error);

  // Citations « [n] » et chemins cliquables : références stables tant qu'ils ne changent pas
  const citations = useMemo(() => citationKey(text), [text]);
  const paths = message?.paths;
  const links = useMemo(() => buildChatLinks(citations, paths), [citations, paths]);

  // Artefacts (blocs HTML/SVG, documents), une fois la réponse écrite
  const artifacts = useMemo(
    () => (streaming || error ? [] : messageArtifacts(text, documents)),
    [streaming, error, text, documents],
  );

  // Fichier généré : sa carte paraît une fois le fichier écrit
  const filePath = live?.file?.path || message?.file_path;
  const imagePath =
    live?.image?.path ?? (message?.type === 'image_generation' ? message.image_path : null);

  const meta = message
    ? [
        formatTime(message.timestamp),
        message.duration_ms ? formatDuration(message.duration_ms) : '',
        message.tokens_per_s ? `${formatDecimal(message.tokens_per_s)} tokens/s` : '',
      ]
        .filter(Boolean)
        .join(' · ')
    : '';

  return (
    <article className="group/msg py-3" aria-busy={streaming}>
      {thinking || thinkingNow ? (
        <Reasoning
          text={thinking}
          active={thinkingNow}
          durationMs={live ? live.thinkingMs : message?.thinking_ms}
          live={live !== null}
        />
      ) : null}

      {error ? (
        <div className="flex items-start gap-2 rounded-md border border-error/40 bg-error-soft px-3 py-2 text-sm text-fg">
          <CircleAlert size={16} className="mt-0.5 shrink-0 text-error" />
          {/* L'encadré porte déjà l'icône : sans le « ❌ » du texte (format Tk) */}
          <span className="whitespace-pre-wrap">{text.replace(/^❌\s*/u, '')}</span>
        </div>
      ) : (
        parts.map((part, index) =>
          part.kind === 'text' ? (
            <Markdown
              key={part.key}
              text={part.text}
              streaming={live !== null && index === lastText && index === parts.length - 1}
              links={links}
            />
          ) : (
            <ToolRow
              key={part.key}
              tool={part.tool}
              running={live !== null && part.tool.ok === undefined}
            />
          ),
        )
      )}

      {activity ? (
        <Activity label={activity} progress={live?.kind === 'image' ? live.progress : null} />
      ) : null}

      {imagePath ? <GeneratedImage path={imagePath} /> : null}

      {filePath ? <FileCard path={filePath} name={live?.file?.name} kind="file" /> : null}

      {documents.map((path) => {
        const index = artifacts.findIndex(
          (artifact) => artifact.kind === 'document' && artifact.path === path,
        );
        return (
          <FileCard
            key={path}
            path={path}
            kind="document"
            onPreview={index >= 0 ? () => openPreview(mid, artifacts, index) : undefined}
          />
        );
      })}

      {artifacts.length ? (
        <button
          type="button"
          onClick={() => openPreview(mid, artifacts, 0)}
          className="mt-1 inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-sm font-semibold text-accent transition-colors duration-150 hover:bg-accent-soft"
        >
          <Eye size={15} />
          Aperçu{artifacts.length > 1 ? ` (${artifacts.length})` : ''}
        </button>
      ) : null}

      {message?.interrupted ? (
        <div className="mt-1 inline-flex items-center gap-1.5 text-xs text-warning">
          <OctagonX size={13} />
          Réponse interrompue
        </div>
      ) : null}

      {message && !streaming ? (
        <MessageActions meta={meta} pinned={isLast}>
          <CopyButton text={text} label="Copier la réponse" />
        </MessageActions>
      ) : null}
    </article>
  );
});
