import { CircleAlert, FolderOpen, OctagonX } from 'lucide-react';
import { memo, useCallback, useMemo } from 'react';

import { RobotLogo } from '../../components/ui/RobotLogo';
import { type Translate, useLocale, useT } from '../../i18n';
import { baseName, messageArtifacts } from '../../lib/artifacts';
import type { MessageView, NearFolder, ToolCallView } from '../../lib/events';
import { formatDecimal, formatDuration, formatTime } from '../../lib/format';
import type { LiveTurn } from '../../stores/chatReducer';
import { showInMemory } from '../../stores/memory';
import { openFilePreview, openPreview } from '../../stores/preview';
import { FileCard, GeneratedImage } from './FileCard';
import { CodePreview } from './markdown/codePreview';
import { buildChatLinks, citationKey } from './markdown/links';
import { Markdown } from './markdown/Markdown';
import { splitSources } from './markdown/sources';
import { CopyButton, MessageActions } from './MessageActions';
import { RegenerateButton, SpeakButton, StarRating } from './MessageControls';
import { buildParts, textIndex } from './parts';
import { Reasoning } from './Reasoning';
import { SourcesButton } from './SourcesButton';
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
function activityOf(live: LiveTurn | null, t: Translate): string | null {
  if (!live) return t('chat.activity.thinking');
  if (live.kind !== 'chat') return live.status || null;
  if (reasoningActive(live)) return null; // le bloc Réflexion s'anime
  const last = live.tools[live.tools.length - 1];
  // Rien d'écrit depuis le dernier appel (sa position, convertie : textIndex)
  const nothingSince = last ? textIndex(live.text, last.at ?? 0) >= live.text.length : false;
  if (last?.name === 'synthesis') {
    return nothingSince ? toolText(last.label) : null;
  }
  if (last && last.ok === undefined) return null; // la ligne de l'outil s'anime
  if (!live.text) return live.thinking ? t('chat.activity.writing') : t('chat.activity.thinking');
  if (nothingSince) return t('chat.activity.thinking');
  return null;
}

/**
 * Dossiers de la Mémoire au nom proche de celui de la question (« mon dossier
 * onedrive » pour « OneDrive_3_06-10-2026 »), que la réponse ne cite pas : peut-être
 * a-t-elle regardé le disque. Signalés ici plutôt que par le modèle, qui l'oubliait.
 */
function NearMemory({ folders }: { folders: NearFolder[] }) {
  const t = useT();
  return (
    <p className="mt-1.5 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-fg-2">
      <span>{t('chat.memory.near')}</span>
      {folders.map((folder) => (
        <button
          key={folder.name}
          type="button"
          onClick={() => showInMemory(folder.name)}
          title={t('chat.memory.open', { name: folder.name })}
          className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-semibold text-accent transition-colors duration-150 hover:bg-accent-soft"
        >
          <FolderOpen size={14} aria-hidden />
          {folder.name}
          <span className="font-normal text-fg-3">
            ({t('memory.group.files', { count: folder.files })})
          </span>
        </button>
      ))}
    </p>
  );
}

/** Ce que fait l'IA, robot animé (aussi sur la page Code) */
export function Activity({ label, progress }: { label: string; progress?: number | null }) {
  return (
    <div className="my-1.5 flex items-center gap-2 text-sm" role="status" aria-live="polite">
      <RobotLogo size={16} className="pulse-soft shrink-0 text-accent" />
      <span className="shimmer">{label}…</span>
      {progress !== null && progress !== undefined ? (
        <span className="ms-1 h-1 w-28 overflow-hidden rounded-full bg-bg-3">
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
  /** Question de ce tour (régénération) */
  userMid?: string | undefined;
  /** Des messages suivent cette réponse */
  hasFollowing?: boolean;
  /** Réponse en cours ailleurs : pas de régénération */
  busy?: boolean;
}

export const AssistantMessage = memo(function AssistantMessage({
  message,
  live = null,
  pending = false,
  isLast = false,
  userMid,
  hasFollowing = false,
  busy = false,
}: AssistantMessageProps) {
  const t = useT();
  const locale = useLocale();
  const streaming = live !== null || pending;
  const mid = live?.mid ?? message?.mid ?? null;
  const text = live ? live.text : shownText(message);
  const tools = live ? live.tools : (message?.tool_calls ?? NO_TOOLS);
  const thinking = live ? live.thinking : (message?.thinking ?? '');
  const documents = live ? live.documents : (message?.documents ?? NO_DOCUMENTS);
  // Bloc « 📚 Sources » final : hors du texte affiché, sous le bouton Sources
  const { body, sources } = useMemo(() => splitSources(text), [text]);
  const parts = useMemo(() => buildParts(body, tools), [body, tools]);
  const lastText = parts.findLastIndex((part) => part.kind === 'text');
  const activity = streaming ? activityOf(live, t) : null;
  const thinkingNow = reasoningActive(live);
  const error = Boolean(message?.error);

  // Citations « [n] », chemins et noms de la Mémoire cliquables : références
  // stables tant qu'ils ne changent pas
  const citations = useMemo(() => citationKey(text), [text]);
  const paths = message?.paths;
  const memory = message?.memory;
  const links = useMemo(() => buildChatLinks(citations, paths, memory), [citations, paths, memory]);

  // Artefacts (blocs HTML/SVG, documents), une fois la réponse écrite ; leurs
  // titres par défaut suivent la langue
  const artifacts = useMemo(
    () => (streaming || error ? [] : messageArtifacts(text, documents)),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- titres traduits
    [streaming, error, text, documents, locale],
  );
  // Bloc HTML ou SVG : son bouton « Aperçu » ouvre le volet sur lui (les autres
  // aperçus de la réponse s'y suivent, ‹ k/n ›)
  const findPreview = useCallback(
    (code: string) => {
      const wanted = code.trim();
      const index = artifacts.findIndex(
        (artifact) => artifact.kind !== 'document' && artifact.code === wanted,
      );
      return index >= 0 ? () => openPreview(mid, artifacts, index) : null;
    },
    [artifacts, mid],
  );
  const hasBlocks = artifacts.some((artifact) => artifact.kind !== 'document');

  // Fichier généré : sa carte paraît une fois le fichier écrit
  const filePath = live?.file?.path || message?.file_path;
  const imagePath =
    live?.image?.path ?? (message?.type === 'image_generation' ? message.image_path : null);

  const meta = message
    ? [
        formatTime(message.timestamp),
        message.duration_ms ? formatDuration(message.duration_ms) : '',
        message.tokens_per_s
          ? t('chat.message.tokensPerSecond', { value: formatDecimal(message.tokens_per_s) })
          : '',
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
        <CodePreview.Provider value={hasBlocks ? findPreview : null}>
          {parts.map((part, index) =>
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
          )}
        </CodePreview.Provider>
      )}

      {!streaming && message?.memory_near?.length ? (
        <NearMemory folders={message.memory_near} />
      ) : null}

      {activity ? (
        <Activity label={activity} progress={live?.kind === 'image' ? live.progress : null} />
      ) : null}

      {imagePath ? (
        <GeneratedImage path={imagePath} onPreview={() => openFilePreview(imagePath, true, mid)} />
      ) : null}

      {filePath ? (
        <FileCard
          path={filePath}
          name={live?.file?.name}
          kind="file"
          onPreview={() => openFilePreview(filePath, true, mid)}
        />
      ) : null}

      {documents.map((path) => {
        // Document de la réponse : le volet passe de l'un à l'autre (‹ k/n ›)
        const index = artifacts.findIndex(
          (artifact) => artifact.kind === 'document' && artifact.path === path,
        );
        return (
          <FileCard
            key={path}
            path={path}
            kind="document"
            onPreview={() =>
              index >= 0 ? openPreview(mid, artifacts, index) : openFilePreview(path, true, mid)
            }
          />
        );
      })}

      {message?.interrupted ? (
        <div className="mt-1 inline-flex items-center gap-1.5 text-xs text-warning">
          <OctagonX size={13} />
          {t('chat.message.interrupted')}
        </div>
      ) : null}

      {message && !streaming ? (
        <MessageActions
          meta={meta}
          pinned={isLast}
          after={!error ? <SourcesButton sources={sources} /> : null}
        >
          <CopyButton text={text} label={t('chat.message.copyAnswer')} />
          {!error ? <SpeakButton text={body} mid={message.mid} /> : null}
          {userMid ? (
            <RegenerateButton userMid={userMid} hasFollowing={hasFollowing} busy={busy} />
          ) : null}
          {!error ? <StarRating mid={message.mid} rating={message.rating} /> : null}
        </MessageActions>
      ) : null}
    </article>
  );
});
