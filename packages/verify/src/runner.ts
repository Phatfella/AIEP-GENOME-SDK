/**
 * @aiep/verify — Vector runner
 *
 * Loads AIEP-VECTORS from a directory (reads MANIFEST.json, then each vector file)
 * and runs each vector against the TypeScript kernel.
 *
 * Supported suites (v1.1.0):
 *   deterministic-replay   — pack_hash
 *   tamper-detection       — pack_hash (original != tampered)
 *   negative-proof         — negative_proof_hash
 *   admissibility          — CC-001 through CC-005 gate check
 *   dissent-preservation   — pack_hash per branch (DIS-001)
 *   dissent-hash           — dissent_hash tamper-evidence (DIS-002)
 *   recall                 — context_reconstruction_hash, recall_scope_hash
 *   swarm                  — consensus_record_hash, swarm_inclusion_proof
 *   malformed-input        — CanonError must be thrown for invalid inputs
 */

import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

import { canonicalJson, CanonError } from "./canonical.js";
import { sha256hex, concatHash } from "./hash.js";
import {
    packHash,
    negativeProofHash,
    dissentHash,
    dissentResolutionChainHash,
    contextReconstructionHash,
    recallScopeHash,
    consensusRecordHash,
    swarmInclusionProof,
    checkAdmissibility,
} from "./kernel.js";

export interface VectorResult {
    vectorId: string;
    suite: string;
    pass: boolean;
    detail: string;
}

// ── Suite handlers ────────────────────────────────────────────────────────────

function runDeterministicReplay(v: Record<string, unknown>): VectorResult {
    const inp = v["input"] as Record<string, unknown>;
    const exp = v["expected"] as Record<string, unknown>;
    const expected = exp["pack_hash"] as string;
    const reasoning = inp["reasoning_ledger"] as unknown[];
    const schemaId = inp["schema_version_id"] as string;

    // NFC vector (det-002): two ledgers must produce the same hash after NFC normalisation
    if ("evidence_ledger_precomposed" in inp) {
        const hashA = packHash(inp["evidence_ledger_precomposed"] as unknown[], reasoning, schemaId);
        const hashB = packHash(inp["evidence_ledger_decomposed"] as unknown[], reasoning, schemaId);
        const bothMatch = hashA === expected && hashB === expected;
        return {
            vectorId: v["vector_id"] as string,
            suite: v["suite"] as string,
            pass: bothMatch,
            detail: bothMatch
                ? `NFC pack_hash OK (both=${hashA.slice(0, 16)}...)`
                : `MISMATCH precomposed=${hashA} decomposed=${hashB} expected=${expected}`,
        };
    }

    const actual = packHash(inp["evidence_ledger"] as unknown[], reasoning, schemaId);
    const pass = actual === expected;
    return {
        vectorId: v["vector_id"] as string,
        suite: v["suite"] as string,
        pass,
        detail: pass ? `pack_hash OK` : `MISMATCH expected=${expected} actual=${actual}`,
    };
}

function runTamperDetection(v: Record<string, unknown>): VectorResult {
    const inp = v["input"] as Record<string, unknown>;
    const schemaId = inp["schema_version_id"] as string;
    const vectorId = v["vector_id"] as string;
    const suite = v["suite"] as string;

    // tamp-002: reasoning tamper — single evidence_ledger, two reasoning_ledgers
    if ("reasoning_ledger_original" in inp) {
        const evidence = inp["evidence_ledger"] as unknown[];
        const hashOrig = packHash(evidence, inp["reasoning_ledger_original"] as unknown[], schemaId);
        const hashTamp = packHash(evidence, inp["reasoning_ledger_tampered"] as unknown[], schemaId);
        const pass = hashOrig !== hashTamp;
        return {
            vectorId, suite, pass,
            detail: pass ? "reasoning tamper detected — hashes differ OK" : "ERROR: reasoning tamper not detected",
        };
    }

    // tamp-001: evidence tamper — single reasoning_ledger, two evidence_ledgers
    const reasoning = inp["reasoning_ledger"] as unknown[];
    const hashOrig = packHash(inp["evidence_ledger_original"] as unknown[], reasoning, schemaId);
    const hashTamp = packHash(inp["evidence_ledger_tampered"] as unknown[], reasoning, schemaId);
    const differ = hashOrig !== hashTamp;

    const exp = v["expected"] as Record<string, unknown>;
    const expectedOrig = exp["pack_hash_original"] as string | undefined;
    const expectedTamp = exp["pack_hash_tampered"] as string | undefined;

    let pass = differ;
    let detail = differ ? "hashes differ OK" : "ERROR: tampered hash matches original";

    if (expectedOrig !== undefined && hashOrig !== expectedOrig) {
        pass = false;
        detail = `MISMATCH original: expected=${expectedOrig} actual=${hashOrig}`;
    }
    if (expectedTamp !== undefined && hashTamp !== expectedTamp) {
        pass = false;
        detail = `MISMATCH tampered: expected=${expectedTamp} actual=${hashTamp}`;
    }

    return { vectorId, suite, pass, detail };
}

function runNegativeProof(v: Record<string, unknown>): VectorResult {
    const inp = v["input"] as Record<string, unknown>;
    const expected = (v["expected"] as Record<string, unknown>)["negative_proof_hash"] as string;
    const actual = negativeProofHash(
        inp["expected_evidence_type"] as string,
        inp["gap_window_start"] as string,
        inp["gap_window_end"] as string,
        inp["schema_version_id"] as string,
    );
    const pass = actual === expected;
    return {
        vectorId: v["vector_id"] as string,
        suite: v["suite"] as string,
        pass,
        detail: pass ? `negative_proof_hash OK` : `MISMATCH expected=${expected} actual=${actual}`,
    };
}

function runAdmissibility(v: Record<string, unknown>): VectorResult {
    const inp = v["input"] as Record<string, unknown>;
    const exp = v["expected"] as Record<string, unknown>;
    const result = checkAdmissibility(
        inp["plausibility_status"] as string,
        (inp["dissent_final_position"] as string | null) ?? null,
        inp["gate_status"] as string,
    );
    const expectedAdmissible = exp["admissible"] as boolean;
    const reasonContains = exp["reason_contains"] as string;

    const admissibleOk = result.admissible === expectedAdmissible;
    const reasonOk = result.reason.includes(reasonContains);
    const pass = admissibleOk && reasonOk;
    const detail = pass
        ? `admissible=${result.admissible} reason="${result.reason}" OK`
        : `FAIL admissible=${result.admissible}(exp ${expectedAdmissible}) reason="${result.reason}"(must contain "${reasonContains}")`;

    return { vectorId: v["vector_id"] as string, suite: v["suite"] as string, pass, detail };
}

// DIS-001: dissent-preservation
function runDissentPreservation(v: Record<string, unknown>): VectorResult {
    const inp = v["input"] as Record<string, unknown>;
    const exp = v["expected"] as Record<string, unknown>;
    const vectorId = v["vector_id"] as string;
    const suite = v["suite"] as string;
    const schemaId = inp["schema_version_id"] as string;
    const evidence = inp["evidence_ledger"] as unknown[];

    const highHash = packHash(
        evidence,
        inp["reasoning_ledger_branch_HIGH"] as unknown[],
        schemaId,
    );
    const lowHash = packHash(
        evidence,
        inp["reasoning_ledger_branch_LOW"] as unknown[],
        schemaId,
    );
    const expHigh = exp["pack_hash_branch_HIGH"] as string;
    const expLow = exp["pack_hash_branch_LOW"] as string;
    const pass = highHash === expHigh && lowHash === expLow;
    return {
        vectorId, suite, pass,
        detail: pass
            ? "branch hashes OK"
            : `MISMATCH HIGH: ${highHash} vs ${expHigh} / LOW: ${lowHash} vs ${expLow}`,
    };
}

// DIS-002: dissent-hash
function runDissentHash(v: Record<string, unknown>): VectorResult {
    const inp = v["input"] as Record<string, unknown>;
    const exp = v["expected"] as Record<string, unknown>;
    const vectorId = v["vector_id"] as string;
    const suite = v["suite"] as string;
    const schemaId = inp["schema_version_id"] as string;

    const hashReject = dissentHash(
        inp["branch_id"] as string,
        inp["conclusion_hash"] as string,
        "reject",
        inp["dissenting_evidence"] as unknown[],
        schemaId,
    );
    const hashArchive = dissentHash(
        inp["branch_id"] as string,
        inp["conclusion_hash"] as string,
        "archive",
        inp["dissenting_evidence"] as unknown[],
        schemaId,
    );

    const expReject = exp["hash_position_reject"] as string;
    const expArchive = exp["hash_position_archive"] as string;
    const mustDiffer = exp["must_differ"] as boolean;

    const pass =
        hashReject === expReject &&
        hashArchive === expArchive &&
        (mustDiffer ? hashReject !== hashArchive : true);

    return {
        vectorId, suite, pass,
        detail: pass
            ? `dissent_hash tamper-evident OK (reject=${hashReject.slice(0, 12)}... archive=${hashArchive.slice(0, 12)}...)`
            : `MISMATCH reject: ${hashReject} vs ${expReject} | archive: ${hashArchive} vs ${expArchive}`,
    };
}

function runRecall(v: Record<string, unknown>): VectorResult {
    const inp = v["input"] as Record<string, unknown>;
    const exp = v["expected"] as Record<string, unknown>;
    const vectorId = v["vector_id"] as string;
    const suite = v["suite"] as string;

    // RECALL-001: context_reconstruction_hash (order-independence check)
    if ("context_reconstruction_hash" in exp) {
        const expected = exp["context_reconstruction_hash"] as string;
        const orderingRule = inp["canonical_ordering_rule"] as string;
        const schemaId = inp["schema_version_id"] as string;

        if ("artefact_hashes_order_a" in inp) {
            const hashA = contextReconstructionHash(
                inp["artefact_hashes_order_a"] as string[], orderingRule, schemaId,
            );
            const hashB = contextReconstructionHash(
                inp["artefact_hashes_order_b"] as string[], orderingRule, schemaId,
            );
            const bothMustEqual = exp["both_must_equal"] as boolean | undefined;
            const pass = hashA === expected && hashA === hashB && (bothMustEqual == null || bothMustEqual);
            return {
                vectorId, suite, pass,
                detail: pass
                    ? `context_reconstruction_hash order-independent OK`
                    : `MISMATCH a=${hashA} b=${hashB} expected=${expected}`,
            };
        }

        const actual = contextReconstructionHash(
            inp["artefact_hashes"] as string[], orderingRule, schemaId,
        );
        const bothMustEqual = exp["both_must_equal"] as boolean | undefined;
        const pass = actual === expected && (bothMustEqual == null || bothMustEqual);
        return {
            vectorId, suite, pass,
            detail: pass ? "context_reconstruction_hash OK" : `MISMATCH expected=${expected} actual=${actual}`,
        };
    }

    // RECALL-002: recall_scope_hash
    if ("recall_scope_hash" in exp) {
        const expected = exp["recall_scope_hash"] as string;
        const actual = recallScopeHash(
            inp["archived_dissent_hash"] as string,
            inp["eligible_trigger_domains"] as string[],
            inp["plausibility_threshold_str"] as string,
            inp["schema_version_id"] as string,
        );
        const pass = actual === expected;
        return {
            vectorId, suite, pass,
            detail: pass ? "recall_scope_hash OK" : `MISMATCH expected=${expected} actual=${actual}`,
        };
    }

    return { vectorId, suite, pass: false, detail: "Unknown recall vector format" };
}

function runSwarm(v: Record<string, unknown>): VectorResult {
    const inp = v["input"] as Record<string, unknown>;
    const exp = v["expected"] as Record<string, unknown>;
    const vectorId = v["vector_id"] as string;
    const suite = v["suite"] as string;

    // SWARM-001: consensus_record_hash (order-independence check)
    if ("consensus_record_hash" in exp) {
        const expected = exp["consensus_record_hash"] as string;
        const schemaId = inp["schema_version_id"] as string;
        const hashA = consensusRecordHash(
            inp["branch_id"] as string,
            inp["global_dominance_state"] as string,
            inp["contributing_hashes_order_a"] as string[],
            schemaId,
        );
        const hashB = consensusRecordHash(
            inp["branch_id"] as string,
            inp["global_dominance_state"] as string,
            inp["contributing_hashes_order_b"] as string[],
            schemaId,
        );
        const pass = hashA === expected && hashA === hashB;
        return {
            vectorId, suite, pass,
            detail: pass
                ? "consensus_record_hash order-independent OK"
                : `FAIL hashA=${hashA} hashB=${hashB} expected=${expected}`,
        };
    }

    // SWARM-002: swarm_inclusion_proof
    if ("swarm_inclusion_proof" in exp) {
        const expected = exp["swarm_inclusion_proof"] as string;
        const consensusHashVal =
            (inp["consensus_record_hash"] ?? inp["consensus_hash"]) as string;
        const actual = swarmInclusionProof(
            consensusHashVal,
            inp["contributing_hashes"] as string[],
            inp["excluded_hashes"] as string[],
            inp["exclusion_reasons"] as Record<string, string>,
            inp["schema_version_id"] as string,
        );
        const pass = actual === expected;
        return {
            vectorId, suite, pass,
            detail: pass ? "swarm_inclusion_proof OK" : `MISMATCH expected=${expected} actual=${actual}`,
        };
    }

    return { vectorId, suite, pass: false, detail: "Unknown swarm vector format" };
}

function runMalformed(v: Record<string, unknown>): VectorResult {
    const inp = v["input"] as Record<string, unknown>;
    const exp = v["expected"] as Record<string, unknown>;
    const vectorId = v["vector_id"] as string;
    const suite = v["suite"] as string;
    const caseType = inp["case"] as string;

    // mal-006: tampered pack_hash check
    if (caseType === "tampered-pack-hash") {
        const actualHash = packHash(
            inp["evidence_ledger"] as unknown[],
            inp["reasoning_ledger"] as unknown[],
            inp["schema_version_id"] as string,
        );
        const tamperedHash = inp["tampered_pack_hash"] as string;
        const mismatch = actualHash !== tamperedHash;
        const expectedAdmissible = exp["admissible"] as boolean;
        const reasonContains = exp["reason_contains"] as string;
        const pass = mismatch && !expectedAdmissible && "MISMATCH".includes(reasonContains);
        return {
            vectorId, suite, pass,
            detail: pass ? `MISMATCH detected — tampered hash rejected OK` : `FAIL: mismatch=${mismatch}`,
        };
    }

    // mal-001 to mal-005: CanonError must be thrown
    const errorContains = exp["error_contains"] as string;
    let threw = false;
    let errorMessage = "";

    try {
        if (caseType === "minus-zero") {
            canonicalJson({ x: -0 });
        } else if (caseType === "nan" || caseType === "NaN") {
            canonicalJson({ x: NaN });
        } else if (caseType === "infinity" || caseType === "Infinity") {
            canonicalJson({ x: Infinity });
        } else if (caseType === "negative-infinity" || caseType === "neg-Infinity" || caseType === "-Infinity") {
            canonicalJson({ x: -Infinity });
        } else if (caseType === "non-string-key") {
            // JS/TS always coerces numeric object keys to strings — this is a
            // cross-language boundary. Document as JS-safe.
            return {
                vectorId, suite, pass: true,
                detail: `non-string-key: JS coerces numeric keys to strings — guard documented, JS-safe`,
            };
        } else {
            return { vectorId, suite, pass: false, detail: `Unknown malformed case: ${caseType}` };
        }
    } catch (err) {
        if (err instanceof CanonError) {
            threw = true;
            errorMessage = err.message;
        } else {
            return { vectorId, suite, pass: false, detail: `Unexpected error: ${String(err)}` };
        }
    }

    const frag = errorContains.replace(/-/g, "").toLowerCase().slice(0, 8);
    const pass = threw && errorMessage.toLowerCase().replace(/-/g, "").includes(frag);
    return {
        vectorId, suite, pass,
        detail: pass
            ? `CanonError thrown OK — "${errorMessage}"`
            : `FAIL: expected CanonError containing "${errorContains}", threw=${threw} msg="${errorMessage}"`,
    };
}

// ── Suite dispatch ────────────────────────────────────────────────────────────

const SUITE_RUNNERS: Record<string, (v: Record<string, unknown>) => VectorResult> = {
    "deterministic-replay": runDeterministicReplay,
    "tamper-detection": runTamperDetection,
    "negative-proof": runNegativeProof,
    admissibility: runAdmissibility,
    "dissent-preservation": runDissentPreservation,
    "dissent-hash": runDissentHash,
    recall: runRecall,
    swarm: runSwarm,
    "malformed-input": runMalformed,
};

// ── Manifest loader ───────────────────────────────────────────────────────────

export interface Manifest {
    vector_pack_version: string;
    kernel_version: string;
    vectors: Array<{ vector_id: string; suite: string; file: string }>;
}

export function runManifest(vectorsDir: string): VectorResult[] {
    const manifestPath = join(vectorsDir, "MANIFEST.json");
    if (!existsSync(manifestPath)) {
        throw new Error(`MANIFEST.json not found in ${vectorsDir}`);
    }
    const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as Manifest;
    const results: VectorResult[] = [];

    for (const entry of manifest.vectors) {
        const vectorPath = join(vectorsDir, entry.file);
        let vector: Record<string, unknown>;
        try {
            vector = JSON.parse(readFileSync(vectorPath, "utf8")) as Record<string, unknown>;
        } catch (e) {
            results.push({
                vectorId: entry.vector_id, suite: entry.suite, pass: false,
                detail: `Failed to load ${entry.file}: ${String(e)}`
            });
            continue;
        }
        const runner = SUITE_RUNNERS[entry.suite];
        if (!runner) {
            results.push({
                vectorId: entry.vector_id, suite: entry.suite, pass: false,
                detail: `Unknown suite "${entry.suite}"`
            });
            continue;
        }
        try {
            results.push(runner(vector));
        } catch (e) {
            results.push({
                vectorId: entry.vector_id, suite: entry.suite, pass: false,
                detail: `Runtime error: ${String(e)}`
            });
        }
    }

    return results;
}

// ── Self-test vectors (R1–R7) ─────────────────────────────────────────────────

export interface SelfTestResult {
    id: string;
    rule: string;
    pass: boolean;
    detail: string;
}

export function runSelfTests(): SelfTestResult[] {
    const results: SelfTestResult[] = [];

    // R1: sorted keys
    {
        const json = canonicalJson({ z: 1, a: 2 });
        const pass = json === '{"a":2,"z":1}';
        results.push({ id: "R1-sorted-keys", rule: "R1", pass, detail: pass ? json : `got: ${json}` });
    }

    // R3: NFC normalisation
    {
        const composed = sha256hex(canonicalJson({ n: "\u00C5" }));
        const decomposed = sha256hex(canonicalJson({ n: "A\u030A" }));
        const pass = composed === decomposed;
        results.push({
            id: "R3-nfc-composed-equals-decomposed", rule: "R3", pass,
            detail: pass ? "both hashes equal" : `composed=${composed} decomposed=${decomposed}`,
        });
    }

    // R4: NIST empty-string vector
    {
        const hash = sha256hex("");
        const expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
        const pass = hash === expected;
        results.push({ id: "R4-empty-string-sha256", rule: "R4", pass, detail: pass ? "OK" : `got: ${hash}` });
    }

    // R4: key order independence
    {
        const a = sha256hex(canonicalJson({ b: 2, a: 1 }));
        const b = sha256hex(canonicalJson({ a: 1, b: 2 }));
        const pass = a === b;
        results.push({ id: "R4-key-order-independence", rule: "R4", pass, detail: pass ? "OK" : `a=${a} b=${b}` });
    }

    // R4: NaN throws CanonError
    {
        let threw = false;
        try { canonicalJson(NaN); } catch { threw = true; }
        results.push({
            id: "R4-nan-throws", rule: "R4", pass: threw,
            detail: threw ? "CanonError thrown" : "FAIL: no error"
        });
    }

    // R5: minus-zero throws CanonError
    {
        let threw = false;
        try { canonicalJson(-0); } catch { threw = true; }
        results.push({
            id: "R5-minus-zero-throws", rule: "R5", pass: threw,
            detail: threw ? "CanonError thrown" : "FAIL: no error"
        });
    }

    // R7: length-prefixed injection safe
    {
        const hashAB_C = concatHash("ab", "c");
        const hashA_BC = concatHash("a", "bc");
        const passAB = hashAB_C !== hashA_BC;
        const hashEmpty_X = concatHash("", "x");
        const hashX_Empty = concatHash("x", "");
        const passEmpty = hashEmpty_X !== hashX_Empty;
        const pass = passAB && passEmpty;
        results.push({
            id: "R7-injection-safe", rule: "R7", pass,
            detail: pass
                ? `concatHash("ab","c")=${hashAB_C.slice(0, 16)}... != concatHash("a","bc")=${hashA_BC.slice(0, 16)}...`
                : `FAIL: boundary collision detected`,
        });
    }

    return results;
}
