/**
 * @aiep/verify — SHA-256 hashing utilities (R4, R7)
 *
 * Uses Node.js `node:crypto` (synchronous) — suitable for CLI tooling and
 * cross-language conformance testing. Web Crypto variant is available in
 * @forecast/genome for browser/Workers environments.
 *
 * R4: sha256hex(s)          — SHA-256 of UTF-8 encoded string → lowercase hex
 * R7: concatHash(...parts)  — Length-prefixed 8-byte big-endian concatenation hash
 *                             Prevents boundary collision injection attacks.
 *                             Identical to Python canon.concat_hash().
 */

import { createHash } from "node:crypto";

/** R4: SHA-256 of a UTF-8 string. Returns lowercase hex. */
export function sha256hex(input: string): string {
    return createHash("sha256").update(input, "utf8").digest("hex");
}

/** SHA-256 of raw bytes. Returns lowercase hex. */
export function sha256bytes(input: Buffer | Uint8Array): string {
    return createHash("sha256").update(input).digest("hex");
}

/**
 * R7: Length-prefixed concatenation hash.
 *
 * For each part: encode as UTF-8, prepend 8-byte big-endian length, then SHA-256.
 * This matches Python canon.concat_hash() exactly:
 *
 *   buf = b""
 *   for part in parts:
 *       encoded = part.encode("utf-8")
 *       buf += len(encoded).to_bytes(8, "big") + encoded
 *   return hashlib.sha256(buf).hexdigest()
 */
export function concatHash(...parts: string[]): string {
    const chunks: Buffer[] = [];
    for (const part of parts) {
        const encoded = Buffer.from(part, "utf8");
        const lenBuf = Buffer.allocUnsafe(8);
        lenBuf.writeBigUInt64BE(BigInt(encoded.length), 0);
        chunks.push(lenBuf, encoded);
    }
    const full = Buffer.concat(chunks);
    return createHash("sha256").update(full).digest("hex");
}
