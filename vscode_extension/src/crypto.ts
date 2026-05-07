import { webcrypto } from 'crypto';

const subtle = webcrypto.subtle;

export function b64uDecode(s: string): Uint8Array {
  let str = s.replace(/-/g, '+').replace(/_/g, '/');
  while (str.length % 4) {
    str += '=';
  }
  return new Uint8Array(Buffer.from(str, 'base64'));
}

export function b64uEncode(bytes: Uint8Array): string {
  return Buffer.from(bytes).toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

export async function importAesGcmKey(rawKeyB64u: string): Promise<CryptoKey> {
  const raw = b64uDecode(rawKeyB64u);
  if (raw.length !== 32) {
    throw new Error(`AES-256-GCM key must be 32 bytes, got ${raw.length}`);
  }
  return subtle.importKey('raw', raw, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
}

export async function aesGcmEncryptBytes(key: CryptoKey, plain: Uint8Array): Promise<Uint8Array> {
  const nonce = webcrypto.getRandomValues(new Uint8Array(12));
  const ct = new Uint8Array(await subtle.encrypt({ name: 'AES-GCM', iv: nonce }, key, plain));
  const wire = new Uint8Array(12 + ct.byteLength);
  wire.set(nonce, 0);
  wire.set(ct, 12);
  return wire;
}

export async function aesGcmDecryptBytes(key: CryptoKey, wire: Uint8Array): Promise<Uint8Array> {
  if (wire.length < 12 + 16) {
    throw new Error('ciphertext too short');
  }
  const nonce = wire.slice(0, 12);
  const ct = wire.slice(12);
  const plain = await subtle.decrypt({ name: 'AES-GCM', iv: nonce }, key, ct);
  return new Uint8Array(plain);
}

export async function encryptEnvelope(key: CryptoKey, obj: unknown): Promise<{ e: string }> {
  const plain = new TextEncoder().encode(JSON.stringify(obj));
  const wire = await aesGcmEncryptBytes(key, plain);
  return { e: b64uEncode(wire) };
}

export async function decryptEnvelope(key: CryptoKey, wrapper: unknown): Promise<unknown> {
  if (!wrapper || typeof wrapper !== 'object' || !('e' in wrapper) || typeof (wrapper as { e: unknown }).e !== 'string') {
    throw new Error('missing E2EE envelope key "e"');
  }
  const wire = b64uDecode((wrapper as { e: string }).e);
  const plain = await aesGcmDecryptBytes(key, wire);
  return JSON.parse(new TextDecoder().decode(plain));
}
