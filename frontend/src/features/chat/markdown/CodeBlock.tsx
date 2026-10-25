import { Check, Copy } from 'lucide-react';
import { memo, useEffect, useRef, useState } from 'react';

import { useT } from '../../../i18n';
import { type CodeToken, highlightCode, resolveLanguage } from './highlight';

/** Pendant le streaming, la coloration suit le texte au plus toutes les… (ms) */
const STREAM_HIGHLIGHT_INTERVAL = 400;

interface Highlighted {
  /** Texte coloré : début du code affiché */
  source: string;
  /** Nombre de lignes colorées (les suivantes s'affichent en texte brut) */
  lines: number;
  tokens: CodeToken[][];
}

/** Attente avant la prochaine coloration, pour en faire au plus une par intervalle */
function throttleDelay(lastRun: number): number {
  return Math.max(0, lastRun + STREAM_HIGHLIGHT_INTERVAL - performance.now());
}

const FONT_STYLE_ITALIC = 1;
const FONT_STYLE_BOLD = 2;
const FONT_STYLE_UNDERLINE = 4;

function TokenSpan({ token }: { token: CodeToken }) {
  const style: React.CSSProperties = {};
  if (token.color) style.color = token.color;
  const fontStyle = token.fontStyle ?? 0;
  if (fontStyle & FONT_STYLE_ITALIC) style.fontStyle = 'italic';
  if (fontStyle & FONT_STYLE_BOLD) style.fontWeight = 600;
  if (fontStyle & FONT_STYLE_UNDERLINE) style.textDecoration = 'underline';
  return <span style={style}>{token.content}</span>;
}

interface CodeBlockProps {
  code: string;
  lang?: string | undefined;
  /** Bloc encore en cours d'écriture (dernier bloc d'une réponse en streaming) */
  streaming?: boolean;
}

export const CodeBlock = memo(function CodeBlock({ code, lang, streaming }: CodeBlockProps) {
  const t = useT();
  const [highlighted, setHighlighted] = useState<Highlighted | null>(null);
  const [copied, setCopied] = useState(false);
  // Une demande de coloration à la fois ; sa réponse relance la suivante si besoin
  const [waiting, setWaiting] = useState(false);
  const lastRun = useRef(0);
  const known = resolveLanguage(lang) !== null;

  const lines = code.split('\n');
  // Pendant l'écriture, la dernière ligne peut être incomplète
  const complete = streaming ? Math.max(0, lines.length - 1) : lines.length;
  // Coloration d'un autre texte (bloc remplacé) : ignorée
  const current = highlighted && code.startsWith(highlighted.source) ? highlighted : null;
  const upToDate = current !== null && current.lines >= complete;

  useEffect(() => {
    if (!known || upToDate || waiting) return;
    const source = code.split('\n').slice(0, complete).join('\n');
    const run = () => {
      lastRun.current = performance.now();
      setWaiting(true);
      // Demandes successives, réponses dans l'ordre : chacune couvre au moins
      // les lignes de la précédente
      void highlightCode(source, lang).then((tokens) => {
        setWaiting(false);
        if (tokens) setHighlighted({ source, lines: complete, tokens });
      });
    };
    const timer = setTimeout(run, streaming ? throttleDelay(lastRun.current) : 0);
    return () => clearTimeout(timer);
  }, [code, lang, streaming, complete, known, upToDate, waiting]);

  const copy = () => {
    void navigator.clipboard
      .writeText(code)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      })
      .catch(() => undefined);
  };

  const label = (lang ?? '').trim() || t('chat.code.plainText');

  return (
    <div className="code-block">
      <div className="code-header">
        <span className="code-lang">{label}</span>
        <button
          type="button"
          className="code-copy"
          onClick={copy}
          aria-label={copied ? t('chat.code.copied') : t('chat.code.copy')}
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
          <span>{copied ? t('common.copied') : t('common.copy')}</span>
        </button>
      </div>
      <pre className="code-body">
        <code>
          {lines.map((line, index) => {
            const tokens = current && index < current.lines ? current.tokens[index] : null;
            return (
              <span className="code-line" key={index}>
                {tokens ? tokens.map((token, i) => <TokenSpan key={i} token={token} />) : line}
                {index < lines.length - 1 ? '\n' : null}
              </span>
            );
          })}
        </code>
      </pre>
    </div>
  );
});
