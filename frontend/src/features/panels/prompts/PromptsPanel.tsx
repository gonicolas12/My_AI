/*
 * Bibliothèque de prompts (prompts_panel.py de Tk) : créer, nommer, modifier
 * et supprimer des prompts réutilisables. Ceux qui ont une commande « /xxx »
 * apparaissent dans l'autocomplétion de la zone de saisie
 * (interfaces/desktop/prompts.py).
 */

import { BookText, LoaderCircle, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { type ChangeEvent, type ReactNode, useEffect, useId, useState } from 'react';

import { Button, IconButton } from '../../../components/ui/Button';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Dialog } from '../../../components/ui/Dialog';
import { type Translate, useT } from '../../../i18n';
import { ApiError, api, type PromptFields, type PromptTemplate } from '../../../lib/api';
import { notify } from '../../../stores/app';
import { closePanel } from '../../../stores/panels';
import { PanelDialog } from '../PanelDialog';

const errorText = (error: unknown) => (error instanceof ApiError ? error.message : String(error));

const inputClass =
  'h-9 w-full rounded-md border border-line bg-bg-3 px-2.5 text-sm text-fg placeholder:text-fg-3 focus:border-accent focus:outline-none';

/** Aperçu du contenu sur une ligne (Tk : 90 caractères) */
function preview(content: string) {
  const flat = content.split(/\s+/).filter(Boolean).join(' ');
  return flat.length > 90 ? `${flat.slice(0, 87)}…` : flat;
}

/** Nom dans la confirmation : la commande, sinon le titre (Tk) */
const nameOf = (prompt: PromptTemplate, t: Translate) =>
  prompt.command ? `/${prompt.command}` : prompt.title || t('prompts.thisPrompt');

function Row({
  prompt,
  onEdit,
  onDelete,
}: {
  prompt: PromptTemplate;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const t = useT();
  const text = preview(prompt.content);
  return (
    <li className="flex items-start gap-2 rounded-md border border-line bg-bg px-3.5 py-3">
      <div className="min-w-0 flex-1">
        <p className="flex min-w-0 items-baseline gap-2 text-sm font-semibold">
          {prompt.command ? (
            <>
              <span className="shrink-0 font-mono text-accent">/{prompt.command}</span>
              <span aria-hidden="true" className="text-fg-3">
                ·
              </span>
            </>
          ) : null}
          <span className="truncate">{prompt.title || t('prompts.untitled')}</span>
        </p>
        {prompt.description ? (
          <p className="mt-0.5 text-sm text-fg-2">{prompt.description}</p>
        ) : null}
        {text ? <p className="mt-1 truncate text-xs text-fg-3">{text}</p> : null}
      </div>
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
    </li>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: ReactNode;
  htmlFor: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-medium">
        {label}
      </label>
      {children}
    </div>
  );
}

/** Création (prompt null) ou modification d'un prompt */
function PromptForm({
  prompt,
  onClose,
  onSaved,
}: {
  prompt: PromptTemplate | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const t = useT();
  const [fields, setFields] = useState<PromptFields>(() => ({
    title: prompt?.title ?? '',
    command: prompt?.command ?? '',
    description: prompt?.description ?? '',
    content: prompt?.content ?? '',
  }));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const titleId = useId();
  const commandId = useId();
  const descriptionId = useId();
  const contentId = useId();

  const change =
    (name: keyof PromptFields) => (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setFields((current) => ({ ...current, [name]: event.target.value }));

  const save = async () => {
    // Contrôles du formulaire Tk, refaits par le serveur
    if (!fields.title.trim() && !fields.command.trim()) {
      setError(t('prompts.error.nameOrCommand'));
      return;
    }
    if (!fields.content.trim()) {
      setError(t('prompts.error.emptyContent'));
      return;
    }
    setBusy(true);
    setError('');
    try {
      await (prompt ? api.updatePrompt(prompt.id, fields) : api.createPrompt(fields));
      onSaved();
    } catch (failure) {
      setError(errorText(failure));
      setBusy(false);
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title={prompt ? t('prompts.edit') : t('prompts.new')}
      width={560}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button variant="primary" onClick={() => void save()} disabled={busy}>
            {busy ? <LoaderCircle size={15} className="spin" /> : null}
            {t('common.save')}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Field label={t('prompts.field.name')} htmlFor={titleId}>
          <input
            id={titleId}
            value={fields.title}
            onChange={change('title')}
            placeholder={t('prompts.field.namePlaceholder')}
            autoFocus
            className={inputClass}
          />
        </Field>
        <Field label={t('prompts.field.command')} htmlFor={commandId}>
          <div className="flex h-9 items-center rounded-md border border-line bg-bg-3 focus-within:border-accent">
            <span aria-hidden="true" className="ps-2.5 font-mono text-sm text-fg-3">
              /
            </span>
            <input
              id={commandId}
              value={fields.command}
              onChange={change('command')}
              placeholder={t('prompts.field.commandPlaceholder')}
              spellCheck={false}
              className="h-full min-w-0 flex-1 bg-transparent ps-1 pe-2.5 font-mono text-sm text-fg outline-none placeholder:font-sans placeholder:text-fg-3"
            />
          </div>
        </Field>
        <Field label={t('prompts.field.description')} htmlFor={descriptionId}>
          <input
            id={descriptionId}
            value={fields.description}
            onChange={change('description')}
            placeholder={t('prompts.field.descriptionPlaceholder')}
            className={inputClass}
          />
        </Field>
        <Field
          label={
            <>
              {t('prompts.field.content')}{' '}
              <span className="font-normal text-fg-3">{t('prompts.field.contentHint')}</span>
            </>
          }
          htmlFor={contentId}
        >
          <textarea
            id={contentId}
            value={fields.content}
            onChange={change('content')}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && event.ctrlKey) {
                event.preventDefault();
                void save();
              }
            }}
            rows={8}
            spellCheck={false}
            className="block w-full resize-y rounded-md border border-line bg-bg-3 px-2.5 py-2 font-mono text-xs leading-relaxed text-fg focus:border-accent focus:outline-none"
          />
        </Field>
        {error ? (
          <p role="alert" className="text-sm text-error">
            {error}
          </p>
        ) : null}
      </div>
    </Dialog>
  );
}

const Notice = ({ children }: { children: ReactNode }) => (
  <p className="flex items-center gap-2 px-1 py-2 text-sm text-fg-2">{children}</p>
);

export default function PromptsPanel() {
  const t = useT();
  const [prompts, setPrompts] = useState<PromptTemplate[] | null>(null);
  const [failed, setFailed] = useState('');
  const [tick, setTick] = useState(0);
  const [editing, setEditing] = useState<PromptTemplate | 'new' | null>(null);
  const [deleting, setDeleting] = useState<PromptTemplate | null>(null);

  useEffect(() => {
    let alive = true;
    api.prompts().then(
      ({ prompts: list }) => {
        if (!alive) return;
        setPrompts(list);
        setFailed('');
      },
      (error: unknown) => {
        if (alive) setFailed(errorText(error));
      },
    );
    return () => {
      alive = false;
    };
  }, [tick]);

  const reload = () => setTick((value) => value + 1);

  const remove = async (prompt: PromptTemplate) => {
    try {
      await api.deletePrompt(prompt.id);
      reload();
    } catch (error) {
      notify('error', t('common.errorWith', { error: errorText(error) }));
    }
  };

  let body: ReactNode;
  if (failed) {
    body = <Notice>{failed}</Notice>;
  } else if (!prompts) {
    body = (
      <Notice>
        <LoaderCircle size={14} className="spin text-accent" /> {t('common.loading')}
      </Notice>
    );
  } else if (!prompts.length) {
    body = <Notice>{t('prompts.empty')}</Notice>;
  } else {
    body = (
      <ul className="space-y-2">
        {prompts.map((prompt) => (
          <Row
            key={prompt.id}
            prompt={prompt}
            onEdit={() => setEditing(prompt)}
            onDelete={() => setDeleting(prompt)}
          />
        ))}
      </ul>
    );
  }

  return (
    <PanelDialog
      open
      onOpenChange={(open) => {
        if (!open) closePanel();
      }}
      icon={BookText}
      title={t('prompts.title')}
      description={t('prompts.description')}
      width={760}
      flush
    >
      <div className="flex h-full flex-col">
        <div className="flex shrink-0 items-center gap-2 border-b border-line px-5 py-3">
          <Button variant="primary" onClick={() => setEditing('new')} disabled={Boolean(failed)}>
            <Plus size={15} /> {t('prompts.new')}
          </Button>
          <span className="flex-1" />
          <IconButton label={t('common.refresh')} size="lg" onClick={reload}>
            <RefreshCw size={16} />
          </IconButton>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-3">{body}</div>
      </div>
      {editing ? (
        <PromptForm
          prompt={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      ) : null}
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title={t('prompts.delete.title')}
        message={deleting ? t('prompts.delete.message', { name: nameOf(deleting, t) }) : ''}
        confirmLabel={t('common.delete')}
        danger
        onConfirm={() => {
          if (deleting) void remove(deleting);
        }}
      />
    </PanelDialog>
  );
}
