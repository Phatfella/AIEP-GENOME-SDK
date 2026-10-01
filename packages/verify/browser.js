/**
 * Browser/Worker commitment adapter for the pinned AIEP Genome kernel.
 * Canonicalisation is byte-compatible with the TypeScript verifier; hashing
 * uses Web Crypto so applications do not carry app-local commitment logic.
 */
export class CanonError extends Error {
  constructor(message) {
    super(`GENOME/R: ${message}`);
    this.name = "CanonError";
  }
}

function normalise(value) {
  if (value === null) return null;
  if (typeof value === "string") return value.normalize("NFC");
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new CanonError("non-finite number is not representable in canonical JSON");
    if (Object.is(value, -0)) throw new CanonError("minus-zero (-0) is not representable in canonical JSON");
    return value;
  }
  if (typeof value === "boolean") return value;
  if (Array.isArray(value)) return value.map(normalise);
  if (typeof value === "object") {
    const result = {};
    for (const key of Object.keys(value).sort()) {
      const child = value[key];
      if (typeof child !== "undefined" && typeof child !== "function" && typeof child !== "symbol") {
        result[key.normalize("NFC")] = normalise(child);
      }
    }
    return result;
  }
  return undefined;
}

export function canonicalJson(value) {
  return JSON.stringify(normalise(value));
}

const hex = (buffer) => Array.from(new Uint8Array(buffer), (byte) => byte.toString(16).padStart(2, "0")).join("");

export async function sha256hex(value) {
  return hex(await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)));
}

export async function sha256bytes(value) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  return hex(await globalThis.crypto.subtle.digest("SHA-256", bytes));
}

export async function concatHash(...parts) {
  const encoded = parts.map((part) => new TextEncoder().encode(part));
  const size = encoded.reduce((sum, value) => sum + 8 + value.byteLength, 0);
  const joined = new Uint8Array(size);
  const view = new DataView(joined.buffer);
  let offset = 0;
  for (const value of encoded) {
    view.setBigUint64(offset, BigInt(value.byteLength), false);
    offset += 8;
    joined.set(value, offset);
    offset += value.byteLength;
  }
  return sha256bytes(joined);
}

export async function commitCanonical(value) {
  return sha256hex(canonicalJson(value));
}

