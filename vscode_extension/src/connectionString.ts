import { RelayCredentials } from './types';

const FRAGMENT_KEY = 'd';

export class InvalidConnectionStringError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'InvalidConnectionStringError';
  }
}

function decodeBase64Url(s: string): string {
  let str = s.replace(/-/g, '+').replace(/_/g, '/');
  while (str.length % 4) {
    str += '=';
  }
  return Buffer.from(str, 'base64').toString('utf-8');
}

function extractFragmentPayload(input: string): string {
  const trimmed = input.trim();
  if (!trimmed) {
    throw new InvalidConnectionStringError('Empty connection string.');
  }

  const hashIdx = trimmed.indexOf('#');
  if (hashIdx >= 0) {
    const fragment = trimmed.substring(hashIdx + 1);
    const params = new Map<string, string>();
    for (const pair of fragment.split('&')) {
      const eq = pair.indexOf('=');
      if (eq < 0) {
        continue;
      }
      params.set(pair.substring(0, eq), pair.substring(eq + 1));
    }
    const d = params.get(FRAGMENT_KEY);
    if (d) {
      return decodeURIComponent(d);
    }
    throw new InvalidConnectionStringError(
      `URL fragment is missing the "${FRAGMENT_KEY}=" payload.`,
    );
  }

  return trimmed;
}

export function parseConnectionString(input: string): RelayCredentials {
  const encoded = extractFragmentPayload(input);

  let json: string;
  try {
    json = decodeBase64Url(encoded);
  } catch {
    throw new InvalidConnectionStringError('Connection string is not valid base64url.');
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(json);
  } catch {
    throw new InvalidConnectionStringError('Connection string payload is not valid JSON.');
  }

  if (!parsed || typeof parsed !== 'object') {
    throw new InvalidConnectionStringError('Connection string payload must be an object.');
  }

  const obj = parsed as Record<string, unknown>;
  const urls = obj.urls;
  const token = obj.token;
  const key = obj.key;

  if (!Array.isArray(urls) || urls.length === 0 || urls.some((u) => typeof u !== 'string' || !u)) {
    throw new InvalidConnectionStringError('Connection string is missing tunnel URLs.');
  }
  if (typeof token !== 'string' || !token) {
    throw new InvalidConnectionStringError('Connection string is missing the auth token.');
  }
  if (typeof key !== 'string' || !key) {
    throw new InvalidConnectionStringError('Connection string is missing the encryption key.');
  }

  return {
    urls: urls.map((u) => String(u).replace(/\/$/, '')),
    token,
    keyB64u: key,
  };
}
