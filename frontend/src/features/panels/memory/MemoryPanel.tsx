/*
 * Mémoire locale (memory_panel.py de Tk) : faits de la base de connaissances,
 * documents et messages de conversation indexés, par pages de 20 ; recherche,
 * catégorie, ajout d'un fait, modification, suppression. Un message de
 * conversation modifié, ou supprimé avec son origine, change aussi dans sa
 * conversation (interfaces/desktop/memory.py).
 */

import * as Tabs from '@radix-ui/react-tabs';
import {
  Bot,
  Brain,
  ChevronLeft,
  ChevronRight,
  FileText,
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
  User,
  X,
} from 'lucide-react';
import { type ReactNode, useEffect, useId, useRef, useState } from 'react';

import { Button, IconButton } from '../../../components/ui/Button';
import { Dialog } from '../../../components/ui/Dialog';
import { Tooltip } from '../../../components/ui/Tooltip';
import { type MessageKey, type Translate, useT } from '../../../i18n';
import { ApiError, api, type MemoryItem, type MemoryPage, type MemoryTab } from '../../../lib/api';
import { cn } from '../../../lib/cn';
import { notify } from '../../../stores/app';
import { closePanel } from '../../../stores/panels';
import { PanelDialog } from '../PanelDialog';

const errorText = (error: unknown) => (error instanceof ApiError ? error.message : String(error));

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
  const [adding, setAdding] = useState(false);

  const filter = tab === 'facts' && category !== ALL ? category : null;
  const requestKey = [tab, search, filter, page, tick].join('|');

  useEffect(() => {
    let alive = true;
    const key = [tab, search, filter, page, tick].join('|');
    api.memoryPage(tab, search, filter, page).then(
      (view) => {
        if (alive) setLoaded({ key, tab, view });
      },
      (error: unknown) => {
        if (alive) setLoaded({ key, tab, error: errorText(error) });
      },
    );
    return () => {
      alive = false;
    };
  }, [tab, search, filter, page, tick]);

  // Page d'un autre onglet : pas affichée en attendant la bonne
  const shown = loaded?.tab === tab ? loaded : null;
  const view = shown?.view;
  const loading = loaded?.key !== requestKey;
  const stats = loaded?.view?.stats;
  // Page affichée : le serveur ramène à la dernière une page au-delà de la fin
  const current = view?.page ?? 0;
  const pages = view?.pages ?? 1;

  const reload = () => setTick((value) => value + 1);

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
    body = <Notice>{search ? t('memory.noMatch') : t('memory.nothing')}</Notice>;
  } else {
    body = (
      <ul className="space-y-2">
        {view.items.map((item) =>
          editing === keyOf(item) ? (
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
            {tab === id ? body : null}
          </Tabs.Content>
        ))}
      </Tabs.Root>
      {deleting ? (
        <DeleteDialog
          item={deleting}
          tab={tab}
          onClose={() => setDeleting(null)}
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
