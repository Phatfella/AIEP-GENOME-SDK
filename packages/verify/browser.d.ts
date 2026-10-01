export class CanonError extends Error {}
export function canonicalJson(value: unknown): string;
export function sha256hex(value: string): Promise<string>;
export function sha256bytes(value: Uint8Array | ArrayBuffer): Promise<string>;
export function concatHash(...parts: string[]): Promise<string>;
export function commitCanonical(value: unknown): Promise<string>;
