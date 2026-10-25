/*
 * Bouton « Sources » sous une réponse appuyée sur une recherche web : les
 * icônes des trois premières sources, puis la liste de toutes, en liens, dans
 * un menu déroulant. Il remplace le bloc « 📚 Sources » retiré du texte
 * affiché (markdown/sources.ts).
 */

import { Globe } from 'lucide-react';
import { useState } from 'react';

import { Menu, MenuContent, MenuLink, MenuTrigger } from '../../components/ui/Menu';
import { useT } from '../../i18n';
import { faviconUrl } from '../../lib/api';
import { cn } from '../../lib/cn';
import type { SourceLink } from './markdown/sources';

/** Icône d'un site, sur un disque clair ; un globe si le site n'en a pas */
export function SiteIcon({ host, className }: { host: string; className?: string }) {
  const [failed, setFailed] = useState(!host);
  return (
    <span
      className={cn(
        'inline-flex h-4 w-4 shrink-0 items-center justify-center overflow-hidden rounded-full bg-favicon',
        className,
      )}
      aria-hidden
    >
      {failed ? (
        <Globe size={11} className="text-bg" />
      ) : (
        <img
          src={faviconUrl(host)}
          alt=""
          width={12}
          height={12}
          loading="lazy"
          className="h-3 w-3"
          onError={() => setFailed(true)}
        />
      )}
    </span>
  );
}

export function SourcesButton({ sources }: { sources: SourceLink[] }) {
  const t = useT();
  if (!sources.length) return null;
  return (
    <Menu>
      <MenuTrigger asChild>
        <button
          type="button"
          aria-label={t('chat.sources.label', { count: sources.length })}
          className="flex h-7 items-center gap-1.5 rounded-md px-1.5 text-xs text-fg-2 transition-colors duration-150 hover:bg-hover hover:text-fg data-[state=open]:bg-hover data-[state=open]:text-fg"
        >
          <span className="flex items-center">
            {sources.slice(0, 3).map((source, index) => (
              <SiteIcon
                key={source.url}
                host={source.host}
                className={cn('ring-2 ring-bg', index > 0 && '-ms-1')}
              />
            ))}
          </span>
          {t('chat.sources.button')}
        </button>
      </MenuTrigger>
      <MenuContent label={t('chat.sources.menu')} className="max-w-sm">
        {sources.map((source) => (
          <MenuLink
            key={source.url}
            href={source.url}
            title={source.url}
            icon={<SiteIcon host={source.host} />}
          >
            {source.title}
          </MenuLink>
        ))}
      </MenuContent>
    </Menu>
  );
}
