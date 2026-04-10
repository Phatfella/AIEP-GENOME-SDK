/**
 * @aiep/verify — AIEP GENOME Kernel Primitives (TypeScript)
 *
 * Cross-language conformance copy of Python kernel/canon.py.
 * Every function here produces identical output to its Python counterpart
 * given the same inputs. Conformance is verified by running the same
 * AIEP-VECTORS corpus against both implementations.
 *
 * Functions:
 *   packHash               — P80 I6: deterministic replay pack hash
 *   negativeProofHash      — P16: evidence gap commitment
 *   dissentHash            — P27: dissent record commitment
 *   dissentResolutionChainHash — P27: resolution chain commitment
 *   contextReconstructionHash  — P22: deterministic context reconstruction
 *   recallScopeHash        — P83: recall scope commitment
 *   localDominanceHash     — P90: per-node evidence weight commitment
 *   consensusRecordHash    — P90: swarm consensus commitment (order-independent)
 *   swarmInclusionProof    — P90: swarm inclusion + exclusion commitment
 */

import { canonicalJson } from "./canonical.js";
import { sha256hex, concatHash } from "./hash.js";

/**
 * P80 I6: Deterministic replay pack hash.
 * generated_ts is excluded intentionally — the hash must be replay-stable.
 */
export function packHash(
    evidenceLedger: unknown[],
    reasoningLedger: unknown[],
    schemaVersionId: string,
): string {
    const state = {
        evidence_ledger: evidenceLedger,
        reasoning_ledger: reasoningLedger,
        schema_version_id: schemaVersionId,
    };
    return sha256hex(canonicalJson(state));
}

/**
 * P16: Evidence gap commitment.
 * H(expected_evidence_type || gap_window_start || gap_window_end || schema_version_id)
 */
export function negativeProofHash(
    expectedEvidenceType: string,
    gapWindowStart: string,
    gapWindowEnd: string,
    schemaVersionId: string,
): string {
    return concatHash(expectedEvidenceType, gapWindowStart, gapWindowEnd, schemaVersionId);
}

/**
 * P27: Cryptographic commitment of a dissent record.
 * position must be one of: "reject" | "escalate" | "archive"
 */
export function dissentHash(
    branchId: string,
    conclusionHash: string,
    position: string,
    dissentingEvidence: unknown[],
    schemaVersionId: string,
): string {
    return concatHash(
        branchId,
        conclusionHash,
        position,
        canonicalJson(dissentingEvidence),
        schemaVersionId,
    );
}

/**
 * P27: Resolution of dissent is itself subject to dissent.
 * counterResolutionHash is "NONE" if the resolution was not challenged.
 */
export function dissentResolutionChainHash(
    originalDissentHash: string,
    resolutionHash: string,
    counterResolutionHash: string | null,
    schemaVersionId: string,
): string {
    return concatHash(
        originalDissentHash,
        resolutionHash,
        counterResolutionHash ?? "NONE",
        schemaVersionId,
    );
}

/**
 * P22: Deterministic context reconstruction.
 * Artefacts are sorted before hashing — insertion order does not matter.
 */
export function contextReconstructionHash(
    artefactHashes: string[],
    canonicalOrderingRule: string,
    schemaVersionId: string,
): string {
    const ordered = [...artefactHashes].sort();
    return concatHash(canonicalJson(ordered), canonicalOrderingRule, schemaVersionId);
}

/**
 * P83: Recall scope commitment.
 * Two nodes must agree on this hash before either can initiate recall.
 */
export function recallScopeHash(
    archivedDissentHash: string,
    eligibleTriggerDomains: string[],
    plausibilityThresholdStr: string,
    schemaVersionId: string,
): string {
    return concatHash(
        archivedDissentHash,
        canonicalJson([...eligibleTriggerDomains].sort()),
        plausibilityThresholdStr,
        schemaVersionId,
    );
}

/**
 * P90: Per-node evidence-weighted contribution to swarm consensus.
 * evidenceWeightVector: Record<evidenceId, weightStr>
 */
export function localDominanceHash(
    evidenceWeightVector: Record<string, string>,
    nodeId: string,
    schemaVersionId: string,
): string {
    return concatHash(canonicalJson(evidenceWeightVector), nodeId, schemaVersionId);
}

/**
 * P90: Verifiable swarm consensus commitment.
 * contributingHashes is sorted before hashing — order does not affect output.
 */
export function consensusRecordHash(
    branchId: string,
    globalDominanceState: string,
    contributingHashes: string[],
    schemaVersionId: string,
): string {
    return concatHash(
        branchId,
        globalDominanceState,
        canonicalJson([...contributingHashes].sort()),
        schemaVersionId,
    );
}

/**
 * P90: Swarm inclusion + exclusion commitment.
 * A swarm that silently excludes a dissenting node produces a different proof
 * than one that declared the exclusion — suppression is cryptographically detectable.
 */
export function swarmInclusionProof(
    consensusHash: string,
    contributingHashes: string[],
    excludedHashes: string[],
    exclusionReasons: Record<string, string>,
    schemaVersionId: string,
): string {
    return concatHash(
        consensusHash,
        canonicalJson([...contributingHashes].sort()),
        canonicalJson([...excludedHashes].sort()),
        canonicalJson(exclusionReasons),
        schemaVersionId,
    );
}

/** Admissibility check (CC-001 through CC-005). */
export function checkAdmissibility(
    plausibilityStatus: string,
    dissentFinalPosition: string | null,
    gateStatus: string,
): { admissible: boolean; reason: string } {
    // CC-005: gate must be OPEN
    if (gateStatus !== "OPEN") {
        return { admissible: false, reason: "CC-005: gate is not OPEN" };
    }
    // CC-001: plausibility must be plausible
    if (plausibilityStatus !== "plausible") {
        return { admissible: false, reason: "CC-001: plausibility_status is not plausible" };
    }
    // CC-003: dissent (if present) must be accepted
    if (
        dissentFinalPosition !== null &&
        dissentFinalPosition !== "accept"
    ) {
        return { admissible: false, reason: "CC-003: unresolved dissent" };
    }
    return { admissible: true, reason: "ADMISSIBLE" };
}
