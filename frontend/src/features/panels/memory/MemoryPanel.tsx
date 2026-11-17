/*
 * Mémoire locale (memory_panel.py de Tk) : faits de la base de connaissances,
 * documents et messages de conversation indexés, par pages de 20 ; recherche,
 * catégorie, ajout d'un fait, modification, suppression. Un message de
 * conversation modifié, ou supprimé avec son origine, change aussi dans sa
 * conversation (interfaces/desktop/memory.py).
 *
 * Onglet Documents : un élément par document, et par dossier déposé, à déplier
 * pour voir ses fichiers ; chacun se supprime en entier. Les morceaux (chunks)
 * d'un document servent à la recherche et restent internes. « Ajouter » (ou un
 * dépôt de fichiers ou de dossiers) met des fichiers en mémoire (adding.ts),
 * lus en arrière-plan par le serveur, un à la fois ; ceux qui attendent ou se
 * lisent s'affichent en tête de liste (événement memory.jobs), un dossier sur
 * une seule ligne. Deux documents du même nom restent, distingués par leur
 * date ; un fichier ou un dossier remis sous un nom déjà pris : l'utilisateur
 * choisit de le mettre à jour ou de garder les deux (UpdateDialog).
 */

import * as Tabs from '@radix-ui/react-tabs';
import {
  Bot,
  Brain,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileText,
  Folder,
  FolderOpen,
  Info,
  KeyRound,
  LoaderCircle,
  type LucideIcon,
  MessagesSquare,
  Pencil,
  Pin,
  Plus,
  RefreshCw,
  Save,
  Search,
  Trash2,
  Upload,
  User,
  X,
} from 'lucide-react';
import { type ReactNode, useCallback, useEffect, useId, useRef, useState } from 'react';

import { Button, IconButton } from '../../../components/ui/Button';
import { Dialog } from '../../../components/ui/Dialog';
import { Tooltip } from '../../../components/ui/Tooltip';
import { type MessageKey, type Translate, useT } from '../../../i18n';
import {
  ApiError,
  api,
  type ExistingItem,
  type MemoryDocument,
  type MemoryFolder,
  type MemoryGroup,
  type MemoryItem,
  type MemoryPage,
  type MemoryTab,
} from '../../../lib/api';
import { cn } from '../../../lib/cn';
import type { MemoryJob } from '../../../lib/events';
import { formatDay, formatTime } from '../../../lib/format';
import { shell } from '../../../lib/shell';
import { notify } from '../../../stores/app';
import {
  answerUpdate,
  applyMemoryJobs,
  setMemoryDropping,
  type UpdateQuestion,
  useMemory,
} from '../../../stores/memory';
import { closePanel } from '../../../stores/panels';
import { ACCEPT_ALL } from '../../chat/attach';
import { type DropTarget, useFileDrop } from '../../chat/useFileDrop';
import { PanelDialog } from '../PanelDialog';
import { addToMemory, baseName } from './adding';

const errorText = (error: unknown) => (error instanceof ApiError ? error.message : String(error));

/**
 * Fichiers et dossiers déposés sur le panneau (objet stable, cf. useFileDrop) :
 * par leur contenu, fenêtre de l'appli comprise. La Mémoire n'a pas besoin du
 * chemin, et un fichier glissé depuis Outlook ou une archive ZIP n'en a pas :
 * par son chemin, le dépôt ne donnait rien. Un dossier se parcourt dans la
 * page (folders.ts), ses fichiers rangés sous son nom.
 */
const DOCUMENTS_DROP: DropTarget = {
  onFiles: (files) => void addToMemory({ files }),
  onFolders: (folders, files) => void addToMemory({ folders, files }),
  setDropping: setMemoryDropping,
};

const JOB_STATES: Record<MemoryJob['state'], MessageKey> = {
  queued: 'memory.documents.state.queued',
  reading: 'memory.documents.state.reading',
  describing: 'memory.documents.state.describing',
};

const TABS: { id: MemoryTab; label: MessageKey; icon: LucideIcon }[] = [
  { id: 'facts', label: 'memory.tab.facts', icon: Pin },
  { id: 'document', label: 'memory.tab.documents', icon: FileText },
  { id: 'conversation', label: 'memory.tab.conversations', icon: MessagesSquare },
];

/** Catégories d'un fait (memory.py), « Toutes » en tête du filtre */
const CATEGORIES = ['general', 'preference', 'decision', 'person', 'procedure', 'technical'];
const ALL = '';

const CATEGORY_LABELS: Record<string, MessageKey> = {
  general: 'memory.category.general',
  preference: 'memory.category.preference',
  decision: 'memory.category.decision',
  person: 'memory.category.person',
  procedure: 'memory.category.procedure',
  technical: 'memory.category.technical',
};

/** Nom affiché d'une catégorie (une catégorie inconnue garde le sien) */
function categoryLabel(name: string, t: Translate): string {
  const key = CATEGORY_LABELS[name];
  return key ? t(key) : name;
}

/** Couleur d'une catégorie (jetons --memory-*) */
const CATEGORY_CLASS: Record<string, string> = {
  general: 'bg-memory-general/15 text-memory-general',
  preference: 'bg-memory-preference/15 text-memory-preference',
  decision: 'bg-memory-decision/15 text-memory-decision',
  person: 'bg-memory-person/15 text-memory-person',
  procedure: 'bg-memory-procedure/15 text-memory-procedure',
  technical: 'bg-memory-technical/15 text-memory-technical',
};

const inputClass =
  'h-9 rounded-md border border-line bg-bg-3 px-2.5 text-sm text-fg placeholder:text-fg-3 focus:border-accent focus:outline-none';

const contentOf = (item: MemoryItem) => (item.kind === 'fact' ? item.value : item.content) ?? '';
const keyOf = (item: MemoryItem) => `${item.kind === 'fact' ? 'fact' : item.collection}:${item.id}`;

/** Aperçu sur une ligne, coupé comme dans Tk */
function preview(text: string, limit: number) {
  const flat = text.replace(/\n/g, ' ').trim();
  return flat.length > limit ? `${flat.slice(0, limit)}…` : flat;
}

function Badge({ item }: { item: MemoryItem }) {
  const t = useT();
  let label = t('memory.badge.document');
  let Icon: LucideIcon | null = FileText;
  let tone = 'bg-warning-soft text-warning';
  if (item.kind === 'fact') {
    const category = item.category ?? 'general';
    label = categoryLabel(category, t);
    Icon = null;
    tone = CATEGORY_CLASS[category] ?? 'bg-memory-general/15 text-memory-general';
  } else if (item.collection === 'conversation') {
    const user = item.metadata?.role === 'user';
    label = user ? t('memory.badge.you') : t('memory.badge.assistant');
    Icon = user ? User : Bot;
    tone = user ? 'bg-success-soft text-success' : 'bg-info-soft text-info';
  }
  return (
    <span
      className={cn(
        'inline-flex h-5 shrink-0 items-center gap-1 rounded-sm px-1.5 text-2xs font-semibold',
        tone,
      )}
    >
      {Icon ? <Icon size={12} /> : null}
      {label}
    </span>
  );
}

function Provenance({ item }: { item: MemoryItem }) {
  return (
    <p className="mt-1 flex min-w-0 items-center gap-1.5 text-xs text-fg-3">
      {item.kind === 'fact' && item.key ? (
        <>
          <KeyRound size={12} className="shrink-0" />
          <span className="max-w-[40%] truncate">{item.key}</span>
          <span aria-hidden="true">·</span>
        </>
      ) : null}
      <span className="truncate">{item.provenance}</span>
    </p>
  );
}

function Row({
  item,
  onEdit,
  onDelete,
}: {
  item: MemoryItem;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const t = useT();
  const content = contentOf(item);
  return (
    <li className="rounded-md border border-line bg-bg px-3 py-2">
      <div className="flex items-center gap-2.5">
        <Badge item={item} />
        <Tooltip
          label={
            <span className="block max-w-md text-xs leading-relaxed whitespace-pre-wrap">
              {content.length > 600 ? `${content.slice(0, 600)}…` : content}
            </span>
          }
        >
          <p className="min-w-0 flex-1 truncate text-sm">
            {preview(content, 120) || t('common.empty')}
          </p>
        </Tooltip>
        <IconButton label={t('common.edit')} size="sm" onClick={onEdit}>
          <Pencil size={14} />
        </IconButton>
        <IconButton
          label={t('common.delete')}
          size="sm"
          onClick={onDelete}
          className="hover:text-error!"
        >
          <Trash2 size={14} />
        </IconButton>
      </div>
      <Provenance item={item} />
    </li>
  );
}

function EditRow({
  item,
  tab,
  onSaved,
  onCancel,
}: {
  item: MemoryItem;
  tab: MemoryTab;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const t = useT();
  const [text, setText] = useState(() => contentOf(item));
  const [saving, setSaving] = useState(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);

  // Curseur en fin de texte, comme Tk
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;
    editor.focus();
    editor.setSelectionRange(editor.value.length, editor.value.length);
  }, []);

  const save = async () => {
    const value = text.trim();
    if (!value) {
      notify('info', t('memory.edit.empty'));
      return;
    }
    setSaving(true);
    try {
      await api.updateMemory(tab, item.id, value);
      onSaved();
    } catch (error) {
      notify('error', errorText(error));
      setSaving(false);
    }
  };

  return (
    <li className="rounded-md border border-accent bg-bg px-3 py-2.5">
      <div className="mb-2 flex items-center gap-2">
        <Pencil size={13} className="text-accent" />
        <Badge item={item} />
      </div>
      <textarea
        ref={editorRef}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && event.ctrlKey) {
            event.preventDefault();
            void save();
          }
        }}
        rows={4}
        aria-label={t('memory.edit.label')}
        className="block w-full resize-y rounded-md border border-line bg-bg-3 px-2.5 py-2 text-sm leading-relaxed text-fg focus:border-accent focus:outline-none"
      />
      <div className="mt-2 flex items-center gap-2">
        <Button size="sm" variant="primary" onClick={() => void save()} disabled={saving}>
          {saving ? <LoaderCircle size={14} className="spin" /> : <Save size={14} />}
          {t('common.save')}
        </Button>
        <Button size="sm" onClick={onCancel} disabled={saving}>
          <X size={14} /> {t('common.cancel')}
        </Button>
      </div>
      {tab === 'conversation' ? (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-fg-2">
          <Info size={13} className="shrink-0" />
          {t('memory.edit.conversationNote')}
        </p>
      ) : null}
    </li>
  );
}

function DeleteDialog({
  item,
  tab,
  onClose,
  onDeleted,
}: {
  item: MemoryItem;
  tab: MemoryTab;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const t = useT();
  const [atSource, setAtSource] = useState(true);
  const conversation = item.kind === 'vector' && item.collection === 'conversation';

  const remove = async () => {
    onClose();
    try {
      await api.deleteMemory(tab, item.id, conversation && atSource);
      onDeleted();
    } catch (error) {
      notify('error', errorText(error));
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={t('chat.confirmDelete.title')}
      description={t('memory.delete.description')}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} autoFocus>
            {t('chat.confirmDelete.no')}
          </Button>
          <Button variant="danger" onClick={() => void remove()}>
            {t('chat.confirmDelete.yes')}
          </Button>
        </>
      }
    >
      <p className="rounded-md border border-line bg-bg px-3 py-2 font-mono text-xs font-semibold break-words text-accent">
        {preview(contentOf(item), 70) || t('common.empty')}
      </p>
      {conversation ? (
        <label className="mt-3 flex cursor-pointer items-start gap-2 text-sm text-fg-2">
          <input
            type="checkbox"
            checked={atSource}
            onChange={(event) => setAtSource(event.target.checked)}
            className="mt-1 accent-[var(--accent)]"
          />
          <span>
            {t('memory.delete.atSource')}
            <span className="block text-xs text-fg-3">{t('memory.delete.atSourceNote')}</span>
          </span>
        </label>
      ) : null}
    </Dialog>
  );
}

function AddFactDialog({ onClose, onAdded }: { onClose: () => void; onAdded: () => void }) {
  const t = useT();
  const [category, setCategory] = useState('general');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const categoryId = useId();
  const contentId = useId();
  const empty = !text.trim();

  const add = async () => {
    if (empty || busy) return;
    setBusy(true);
    try {
      await api.addFact(category, text);
      onAdded();
    } catch (error) {
      notify('error', errorText(error));
      setBusy(false);
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={t('memory.add.title')}
      width={520}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button variant="primary" onClick={() => void add()} disabled={empty || busy}>
            {busy ? <LoaderCircle size={15} className="spin" /> : <Plus size={15} />}
            {t('common.add')}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <label htmlFor={categoryId} className="w-24 text-sm text-fg-2">
            {t('memory.category.label')}
          </label>
          <select
            id={categoryId}
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className={cn(inputClass, 'w-40')}
          >
            {CATEGORIES.map((name) => (
              <option key={name} value={name}>
                {categoryLabel(name, t)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={contentId} className="mb-1.5 block text-sm text-fg-2">
            {t('memory.add.content')}
          </label>
          <textarea
            id={contentId}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && event.ctrlKey) {
                event.preventDefault();
                void add();
              }
            }}
            rows={5}
            autoFocus
            className="block w-full resize-y rounded-md border border-line bg-bg-3 px-2.5 py-2 text-sm leading-relaxed text-fg focus:border-accent focus:outline-none"
          />
        </div>
      </div>
    </Dialog>
  );
}

const Notice = ({ children }: { children: ReactNode }) => (
  <p className="flex items-center gap-2 px-1 py-2 text-sm text-fg-2">{children}</p>
);

/**
 * Documents ajoutés pas encore rangés : en attente, puis lus (une image est
 * décrite). Un dossier déposé tient sur une ligne : ses fichiers restants et
 * celui qui se lit.
 */
function JobRows({ jobs }: { jobs: MemoryJob[] }) {
  const t = useT();
  if (!jobs.length) return null;
  return (
    <ul aria-label={t('memory.documents.jobsLabel')} aria-live="polite" className="mb-2 space-y-2">
      {jobs.map((job) => (
        <li
          key={job.id}
          className="flex items-center gap-2.5 rounded-md border border-dashed border-line-2 bg-bg px-3 py-2"
        >
          {job.state === 'queued' ? (
            <Clock size={14} className="shrink-0 text-fg-3" />
          ) : (
            <LoaderCircle size={14} className="spin shrink-0 text-accent" />
          )}
          {job.folder ? <Folder size={14} className="shrink-0 text-fg-2" /> : null}
          <span className="min-w-0 shrink-0 truncate text-sm">{job.name}</span>
          {job.folder ? (
            <span className="shrink-0 text-xs text-fg-3">
              {t('memory.documents.folderFiles', { count: job.files ?? 0 })}
            </span>
          ) : null}
          {job.current ? (
            <span className="min-w-0 truncate font-mono text-xs text-fg-2">{job.current}</span>
          ) : null}
          <span className="shrink-0 text-xs text-fg-3">{t(JOB_STATES[job.state])}</span>
        </li>
      ))}
    </ul>
  );
}

// ── Onglet Documents : documents et dossiers à déplier ─────────────────────

/** Document ou dossier (onglet Documents), et non fait ou message */
const isGroup = (entry: MemoryItem | MemoryGroup): entry is MemoryGroup =>
  entry.kind === 'document' || entry.kind === 'folder';

/** Ce que font les lignes des dossiers et des documents, fourni par le panneau */
interface GroupActions {
  /** Dossiers dépliés */
  expanded: ReadonlySet<string>;
  toggle: (id: string) => void;
  deleteGroup: (group: MemoryGroup) => void;
}

const IMAGE_NAME = /\.(png|jpe?g|gif|bmp|webp|tiff?)$/i;

/** Icône d'un document d'après son type (sans type, une image se reconnaît à son nom) */
function DocumentIcon({ doc }: { doc: MemoryDocument }) {
  const props = { size: 15, className: 'shrink-0 text-warning' };
  if (doc.type === 'Image' || (!doc.type && IMAGE_NAME.test(doc.name))) {
    return <FileImage {...props} />;
  }
  if (doc.type === 'Code') return <FileCode {...props} />;
  if (doc.type === 'Excel') return <FileSpreadsheet {...props} />;
  return <FileText {...props} />;
}

/** « Aujourd'hui 14:32 », « 12 oct. 09:05 » */
function addedOn(iso: string): string {
  return [formatDay(iso), formatTime(iso)].filter(Boolean).join(' ');
}

const metaLine = (parts: (string | false | null)[]) => parts.filter(Boolean).join(' · ');

/** Chevron d'un dossier, déplié ou non */
const Chevron = ({ open }: { open: boolean }) =>
  open ? (
    <ChevronDown size={15} className="shrink-0 text-fg-3" />
  ) : (
    <ChevronRight size={15} className="shrink-0 text-fg-3 rtl:-scale-x-100" />
  );

/**
 * Document : nom, date, ajouté à la main ; il se supprime en entier. Ses
 * morceaux (chunks) servent à la recherche et restent internes : il ne se
 * déplie pas.
 */
function DocumentRow({
  doc,
  onDelete,
}: {
  doc: MemoryDocument;
  onDelete: (doc: MemoryDocument) => void;
}) {
  const t = useT();
  const label = doc.folder ? doc.label : doc.name;
  return (
    <li className="flex items-center gap-2 rounded-md border border-line bg-bg py-1 ps-3 pe-1.5">
      <DocumentIcon doc={doc} />
      <span className="min-w-0 truncate py-1 text-sm font-medium">{label}</span>
      <span className="ms-auto shrink-0 ps-3 text-xs text-fg-3">
        {metaLine([
          addedOn(doc.created),
          !doc.folder && doc.source === 'manual' && t('memory.group.byHand'),
        ])}
      </span>
      <IconButton
        label={t('memory.group.deleteDocument')}
        aria-label={t('memory.group.deleteNamed', { name: label })}
        size="sm"
        onClick={() => onDelete(doc)}
        className="hover:text-error!"
      >
        <Trash2 size={14} />
      </IconButton>
    </li>
  );
}

/** Dossier déposé : nom, fichiers, date ; à déplier sur ses fichiers, ou à supprimer */
function FolderRow({ folder, actions }: { folder: MemoryFolder; actions: GroupActions }) {
  const t = useT();
  const listId = useId();
  const open = actions.expanded.has(folder.id);
  const Icon = open ? FolderOpen : Folder;
  return (
    <li className="rounded-md border border-line bg-bg">
      <div className="flex items-center gap-1.5 py-1 ps-2 pe-1.5">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={open ? listId : undefined}
          onClick={() => actions.toggle(folder.id)}
          className="flex min-w-0 flex-1 items-center gap-2 rounded-sm px-1 py-1 text-start text-fg hover:text-accent focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent"
        >
          <Chevron open={open} />
          <Icon size={15} className="shrink-0 text-accent" />
          <span className="min-w-0 truncate text-sm font-semibold">{folder.name}</span>
          <span className="ms-auto shrink-0 ps-3 text-xs text-fg-3">
            {metaLine([t('memory.group.files', { count: folder.files }), addedOn(folder.created)])}
          </span>
        </button>
        <IconButton
          label={t('memory.group.deleteFolder')}
          aria-label={t('memory.group.deleteNamed', { name: folder.name })}
          size="sm"
          onClick={() => actions.deleteGroup(folder)}
          className="hover:text-error!"
        >
          <Trash2 size={14} />
        </IconButton>
      </div>
      {open ? (
        <ul
          id={listId}
          aria-label={t('memory.group.filesLabel', { name: folder.name })}
          className="space-y-1.5 border-t border-line py-2 ps-6 pe-2"
        >
          {folder.documents.map((doc) => (
            <DocumentRow key={doc.id} doc={doc} onDelete={actions.deleteGroup} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/** Supprimer un document entier, ou un dossier et tous ses fichiers */
function DeleteGroupDialog({
  group,
  onClose,
  onDeleted,
}: {
  group: MemoryGroup;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const t = useT();
  const folder = group.kind === 'folder';

  const remove = async () => {
    onClose();
    try {
      if (group.kind === 'folder') await api.deleteMemoryFolder(group.key);
      else await api.deleteMemoryDocument(group.id);
      onDeleted();
    } catch (error) {
      notify('error', errorText(error));
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={t('chat.confirmDelete.title')}
      description={
        group.kind === 'folder'
          ? t('memory.group.deleteFolderConfirm', { count: group.files })
          : t('memory.group.deleteDocumentConfirm')
      }
      footer={
        <>
          <Button variant="secondary" onClick={onClose} autoFocus>
            {t('chat.confirmDelete.no')}
          </Button>
          <Button variant="danger" onClick={() => void remove()}>
            {t('chat.confirmDelete.yes')}
          </Button>
        </>
      }
    >
      <p className="flex items-center gap-2 rounded-md border border-line bg-bg px-3 py-2 font-mono text-xs font-semibold break-all text-accent">
        {folder ? <Folder size={14} className="shrink-0" /> : null}
        {group.name}
      </p>
    </Dialog>
  );
}

/** Un fichier ou dossier déjà en mémoire sous ce nom : sa date, et combien le portent */
function ExistingRow({ item, folder }: { item: ExistingItem; folder: boolean }) {
  const t = useT();
  const Icon = folder ? Folder : FileText;
  return (
    <li className="flex items-center gap-2">
      <Icon size={14} className="shrink-0 text-accent" />
      <span className="min-w-0 font-mono text-xs font-semibold break-all text-accent">
        {baseName(item.name)}
      </span>
      <span className="ms-auto shrink-0 ps-3 text-xs text-fg-3">
        {metaLine([
          addedOn(item.created),
          item.count > 1 && t('memory.update.newest', { count: item.count }),
        ])}
      </span>
    </li>
  );
}

/**
 * Fichiers ou dossiers remis (« Ajouter », dépôt) alors qu'un autre porte déjà
 * leur nom : les mettre à jour (remplacer le plus récent du même nom), garder
 * les deux, ou ne pas les envoyer ; les nouveaux partent de toute façon
 * (adding.ts). La date de celui qui est déjà là aide à choisir.
 */
function UpdateDialog({ question }: { question: UpdateQuestion }) {
  const t = useT();
  const { files, folders } = question;
  let description: string;
  if (!folders.length) description = t('memory.update.files', { count: files.length });
  else if (!files.length) description = t('memory.update.folders', { count: folders.length });
  else description = t('memory.update.mixed');
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) answerUpdate('cancel');
      }}
      title={t('memory.update.title')}
      description={description}
      width={520}
      footer={
        <>
          <Button variant="ghost" onClick={() => answerUpdate('cancel')} className="me-auto">
            {t('common.cancel')}
          </Button>
          <Button variant="secondary" onClick={() => answerUpdate('keep')}>
            {t('memory.update.keep')}
          </Button>
          <Button variant="primary" onClick={() => answerUpdate('update')} autoFocus>
            {t('memory.update.yes')}
          </Button>
        </>
      }
    >
      <ul className="max-h-48 space-y-1.5 overflow-y-auto rounded-md border border-line bg-bg px-3 py-2">
        {folders.map((item) => (
          <ExistingRow key={`folder:${item.name}`} item={item} folder />
        ))}
        {files.map((item) => (
          <ExistingRow key={`file:${item.name}`} item={item} folder={false} />
        ))}
      </ul>
      {folders.length ? (
        <p className="mt-3 flex items-start gap-1.5 text-xs text-fg-2">
          <Info size={13} className="mt-0.5 shrink-0" />
          {t('memory.update.folderNote')}
        </p>
      ) : null}
    </Dialog>
  );
}

/**
 * Onglet Documents : consigne pendant un glisser de fichiers (le panneau
 * entier les reçoit, son contour s'éclaire), file des documents ajoutés, puis
 * la liste
 */
function DocumentsTab({ children }: { children: ReactNode }) {
  const t = useT();
  const dropping = useMemory((state) => state.dropping);
  const jobs = useMemory((state) => state.jobs);
  return (
    <>
      {dropping ? (
        <p className="flex items-center gap-2 px-1 pb-2 text-sm font-medium text-accent">
          <Upload size={15} className="shrink-0" /> {t('memory.documents.drop')}
        </p>
      ) : null}
      <JobRows jobs={jobs} />
      {children}
    </>
  );
}

interface Loaded {
  key: string;
  tab: MemoryTab;
  view?: MemoryPage;
  error?: string;
}

export default function MemoryPanel() {
  const t = useT();
  const [tab, setTab] = useState<MemoryTab>('facts');
  const [query, setQuery] = useState('');
  /** Recherche appliquée (Entrée, bouton, catégorie, rafraîchir) */
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState(ALL);
  const [page, setPage] = useState(0);
  const [tick, setTick] = useState(0);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<MemoryItem | null>(null);
  const [deletingGroup, setDeletingGroup] = useState<MemoryGroup | null>(null);
  const [adding, setAdding] = useState(false);
  // Dossiers dépliés (onglet Documents), gardés d'une relecture à l'autre
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(() => new Set());
  // Changement venu du serveur (document rangé) : la page se relit
  const revision = useMemory((state) => state.revision);
  const jobs = useMemory((state) => state.jobs);
  // Fichiers ou dossiers remis déjà en mémoire : les mettre à jour ?
  const update = useMemory((state) => state.update);
  const fileInput = useRef<HTMLInputElement>(null);
  // Fichiers glissés sur la fenêtre : l'onglet Documents les reçoit, le panneau s'éclaire
  const drop = useFileDrop('memory', DOCUMENTS_DROP);
  const dropping = useMemory((state) => state.dropping);
  const documents = tab === 'document';

  const filter = tab === 'facts' && category !== ALL ? category : null;
  const requestKey = [tab, search, filter, page, tick, revision].join('|');

  useEffect(() => {
    let alive = true;
    const key = [tab, search, filter, page, tick, revision].join('|');
    api.memoryPage(tab, search, filter, page).then(
      (view) => {
        if (!alive) return;
        setLoaded({ key, tab, view });
        // File relue avec la page : un événement manqué (reconnexion) ne la fige pas
        if (view.jobs) applyMemoryJobs(view.jobs);
      },
      (error: unknown) => {
        if (alive) setLoaded({ key, tab, error: errorText(error) });
      },
    );
    return () => {
      alive = false;
    };
  }, [tab, search, filter, page, tick, revision]);

  // Panneau fermé pendant la question : ceux déjà là ne sont pas envoyés
  useEffect(() => () => answerUpdate('cancel'), []);

  // Page d'un autre onglet : pas affichée en attendant la bonne
  const shown = loaded?.tab === tab ? loaded : null;
  const view = shown?.view;
  const loading = loaded?.key !== requestKey;
  const stats = loaded?.view?.stats;
  // Page affichée : le serveur ramène à la dernière une page au-delà de la fin
  const current = view?.page ?? 0;
  const pages = view?.pages ?? 1;

  const reload = () => setTick((value) => value + 1);

  const toggle = useCallback((id: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const actions: GroupActions = { expanded, toggle, deleteGroup: setDeletingGroup };

  const selectTab = (value: string) => {
    const next = TABS.find((entry) => entry.id === value);
    if (!next) return;
    setTab(next.id);
    setPage(0);
    setEditing(null);
    setQuery('');
    setSearch('');
    setCategory(ALL);
  };

  const runSearch = () => {
    setSearch(query.trim());
    setPage(0);
    setEditing(null);
    reload();
  };

  const goTo = (target: number) => {
    setPage(target);
    setEditing(null);
  };

  /** « Ajouter » de l'onglet Documents : dialogue du système, ou sélecteur du navigateur */
  const chooseDocuments = () => {
    if (shell.canPickFiles()) {
      void shell.pickFiles('All').then((paths) => addToMemory({ paths }));
      return;
    }
    fileInput.current?.click();
  };

  let body: ReactNode;
  if (shown?.error) {
    body = <Notice>{shown.error}</Notice>;
  } else if (!view) {
    body = (
      <Notice>
        <LoaderCircle size={14} className="spin text-accent" /> {t('common.loading')}
      </Notice>
    );
  } else if (!view.items.length) {
    if (search) body = <Notice>{t('memory.noMatch')}</Notice>;
    else if (tab !== 'document') body = <Notice>{t('memory.nothing')}</Notice>;
    // Documents en cours de lecture : ils s'affichent, la liste vide n'est pas annoncée
    else body = jobs.length ? null : <Notice>{t('memory.documents.empty')}</Notice>;
  } else {
    body = (
      <ul className="space-y-2">
        {view.items.map((item) =>
          isGroup(item) ? (
            item.kind === 'folder' ? (
              <FolderRow key={item.id} folder={item} actions={actions} />
            ) : (
              <DocumentRow key={item.id} doc={item} onDelete={setDeletingGroup} />
            )
          ) : editing === keyOf(item) ? (
            <EditRow
              key={keyOf(item)}
              item={item}
              tab={tab}
              onCancel={() => setEditing(null)}
              onSaved={() => {
                setEditing(null);
                reload();
              }}
            />
          ) : (
            <Row
              key={keyOf(item)}
              item={item}
              onEdit={() => setEditing(keyOf(item))}
              onDelete={() => setDeleting(item)}
            />
          ),
        )}
      </ul>
    );
  }

  return (
    <PanelDialog
      open
      onOpenChange={(open) => {
        if (!open) closePanel();
      }}
      // Échap pendant une modification l'annule, sans fermer le panneau
      onEscapeKeyDown={(event) => {
        if (editing) {
          event.preventDefault();
          setEditing(null);
        }
      }}
      icon={Brain}
      title={t('memory.title')}
      description={
        <>
          {t('memory.description')}
          {stats ? (
            <span className="mt-0.5 block text-xs text-fg-3">
              {[
                t('memory.stats.facts', { count: stats.facts }),
                t('memory.stats.documents', { count: stats.documents }),
                t('memory.stats.conversations', { count: stats.conversations }),
              ].join(' · ')}
            </span>
          ) : null}
        </>
      }
      width={880}
      flush
      dropTarget={documents ? drop : undefined}
      glow={documents && dropping}
      footer={
        <div className="flex w-full items-center justify-between">
          <Button size="sm" onClick={() => goTo(current - 1)} disabled={!view || current <= 0}>
            <ChevronLeft size={15} className="rtl:-scale-x-100" /> {t('common.previous')}
          </Button>
          <span className="text-sm text-fg-2 tabular-nums" role="status">
            {t('memory.page', { page: Math.min(current + 1, pages), pages })}{' '}
            <span className="ms-1 text-fg-3">({view?.total ?? 0})</span>
          </span>
          <Button
            size="sm"
            onClick={() => goTo(current + 1)}
            disabled={!view || current >= pages - 1}
          >
            {t('common.next')} <ChevronRight size={15} className="rtl:-scale-x-100" />
          </Button>
        </div>
      }
    >
      <Tabs.Root value={tab} onValueChange={selectTab} className="flex h-full flex-col">
        <div className="shrink-0 space-y-3 border-b border-line px-5 pt-4 pb-3">
          <Tabs.List
            aria-label={t('memory.tabsLabel')}
            className="flex gap-1 rounded-md bg-bg-3 p-1"
          >
            {TABS.map(({ id, label, icon: Icon }) => (
              <Tabs.Trigger
                key={id}
                value={id}
                className={cn(
                  'flex h-8 flex-1 items-center justify-center gap-2 rounded-sm text-sm font-medium text-fg-2',
                  'transition-colors duration-150 hover:text-fg',
                  'data-[state=active]:bg-accent data-[state=active]:text-on-accent',
                )}
              >
                <Icon size={15} /> {t(label)}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
          <div className="flex items-center gap-2">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') runSearch();
              }}
              placeholder={t('common.searchEllipsis')}
              aria-label={t('memory.search.label')}
              spellCheck={false}
              className={cn(inputClass, 'min-w-0 flex-1')}
            />
            <IconButton label={t('common.search')} shortcut="Enter" size="lg" onClick={runSearch}>
              <Search size={16} />
            </IconButton>
            {tab === 'facts' ? (
              <>
                <select
                  value={category}
                  onChange={(event) => {
                    setCategory(event.target.value);
                    setSearch(query.trim());
                    setPage(0);
                    setEditing(null);
                  }}
                  aria-label={t('memory.category.label')}
                  className={cn(inputClass, 'w-36')}
                >
                  {[ALL, ...CATEGORIES].map((name) => (
                    <option key={name} value={name}>
                      {name === ALL ? t('memory.category.all') : categoryLabel(name, t)}
                    </option>
                  ))}
                </select>
                <Button
                  variant="primary"
                  onClick={() => setAdding(true)}
                  disabled={Boolean(shown?.error)}
                >
                  <Plus size={15} /> {t('common.add')}
                </Button>
              </>
            ) : null}
            {tab === 'document' ? (
              <Tooltip label={t('memory.documents.addHint')}>
                <Button
                  variant="primary"
                  onClick={chooseDocuments}
                  disabled={Boolean(shown?.error)}
                >
                  <Plus size={15} /> {t('common.add')}
                </Button>
              </Tooltip>
            ) : null}
            <IconButton
              label={t('common.refresh')}
              size="lg"
              onClick={() => {
                setSearch(query.trim());
                reload();
              }}
            >
              <RefreshCw size={16} className={cn(loading && 'spin')} />
            </IconButton>
          </div>
        </div>
        {TABS.map(({ id }) => (
          <Tabs.Content
            key={id}
            value={id}
            className="min-h-0 flex-1 overflow-y-auto px-5 py-3 focus:outline-none"
          >
            {tab !== id ? null : id === 'document' ? <DocumentsTab>{body}</DocumentsTab> : body}
          </Tabs.Content>
        ))}
      </Tabs.Root>
      <input
        ref={fileInput}
        type="file"
        multiple
        hidden
        accept={ACCEPT_ALL}
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          event.target.value = '';
          void addToMemory({ files });
        }}
      />
      {deleting ? (
        <DeleteDialog
          item={deleting}
          tab={tab}
          onClose={() => setDeleting(null)}
          onDeleted={reload}
        />
      ) : null}
      {update ? <UpdateDialog question={update} /> : null}
      {deletingGroup ? (
        <DeleteGroupDialog
          group={deletingGroup}
          onClose={() => setDeletingGroup(null)}
          onDeleted={reload}
        />
      ) : null}
      {adding ? (
        <AddFactDialog
          onClose={() => setAdding(false)}
          onAdded={() => {
            setAdding(false);
            setPage(0);
            reload();
          }}
        />
      ) : null}
    </PanelDialog>
  );
}
