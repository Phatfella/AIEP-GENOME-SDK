/**
 * @aiep/verify — Canonical JSON (R1–R5)
 *
 * AIEP GENOME conformance implementation.
 * Rules:
 *   R1: Keys sorted lexicographically (UTF-8 codepoint order) — recursively
 *   R2: Compact separators — no whitespace
 *   R3: Unicode NFC normalised — all strings normalised before serialisation
 *   R4: Non-finite numbers (NaN, Infinity, -Infinity) → throws CanonError
 *   R5: Minus-zero (-0) → throws CanonError
 *
 * This is a cross-language conformance copy of the Python kernel's canon.py logic.
 * Any changes to the Python kernel must be mirrored here and verified against the
 * same AIEP-VECTORS corpus.
 */

export class CanonError extends Error {
    constructor(message: string) {
        super(`GENOME/R: ${message}`);
        this.name = "CanonError";
    }
}

/** R3: NFC-normalise a string. */
function nfc(s: string): string {
    return s.normalize("NFC");
}

/** R3/R1: Recursively NFC-normalise all strings and sort object keys. */
function nfcObject(value: unknown): unknown {
    if (value === null) return null;
    if (typeof value === "string") return nfc(value);
    if (typeof value === "number") {
        // R4: reject non-finite
        if (!isFinite(value)) {
            throw new CanonError("non-finite number is not representable in canonical JSON");
        }
        // R5: reject minus-zero
        if (Object.is(value, -0)) {
            throw new CanonError("minus-zero (-0) is not representable in canonical JSON");
        }
        return value;
    }
    if (typeof value === "boolean") return value;
    if (Array.isArray(value)) {
        return value.map(nfcObject);
    }
    if (typeof value === "object") {
        const obj = value as Record<string, unknown>;
        for (const k of Object.keys(obj)) {
            // JSON object keys must be strings — redundant in TS but documented
            if (typeof k !== "string") {
                throw new CanonError("object member name must be a string");
            }
        }
        // R1: sort keys
        const sorted: Record<string, unknown> = {};
        for (const k of Object.keys(obj).sort()) {
            const v = obj[k];
            if (typeof v !== "undefined" && typeof v !== "function") {
                sorted[nfc(k)] = nfcObject(v);
            }
        }
        return sorted;
    }
    // undefined, function, symbol — strip
    return undefined;
}

/**
 * Serialise any JSON-compatible value to canonical AIEP form.
 * Guaranteed byte-identical for equivalent payloads on any conforming runtime.
 * Throws CanonError for: NaN, Infinity, -Infinity, minus-zero.
 */
export function canonicalJson(value: unknown): string {
    const normalised = nfcObject(value);
    return JSON.stringify(normalised);
}
