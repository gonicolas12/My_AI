/*
 * KaTeX (D9) : chargé seulement quand une réponse contient une formule.
 * Le code, la feuille de style et les polices sont livrés avec l'appli.
 */

import { useEffect, useState } from 'react';
import type { Options } from 'react-markdown';

type PluggableList = NonNullable<Options['remarkPlugins']>;

export interface MathPlugins {
  remark: PluggableList;
  rehype: PluggableList;
}

let pending: Promise<MathPlugins> | null = null;
let ready: MathPlugins | null = null;

function loadMathPlugins(): Promise<MathPlugins> {
  pending ??= Promise.all([
    import('remark-math'),
    import('rehype-katex'),
    import('katex/dist/katex.min.css'),
  ]).then(([remarkMath, rehypeKatex]) => {
    ready = {
      remark: [[remarkMath.default, { singleDollarTextMath: true }]],
      rehype: [
        [
          rehypeKatex.default,
          { throwOnError: false, strict: 'ignore', errorColor: 'var(--error)', trust: false },
        ],
      ],
    };
    return ready;
  });
  return pending;
}

/** Greffons des formules, une fois chargés (null avant, ou sans formule) */
export function useMathPlugins(needed: boolean): MathPlugins | null {
  const [plugins, setPlugins] = useState<MathPlugins | null>(ready);
  useEffect(() => {
    if (!needed || plugins) return;
    let alive = true;
    loadMathPlugins()
      .then((loaded) => {
        if (alive) setPlugins(loaded);
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [needed, plugins]);
  return needed ? plugins : null;
}
