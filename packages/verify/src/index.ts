/**
 * @aiep/verify — Public API
 *
 * TypeScript cross-language conformance implementation of the AIEP GENOME kernel.
 * Produces byte-identical hashes to the Python kernel (aiep-genome-sdk).
 *
 * Quick start (testing conformance against AIEP-VECTORS):
 *   npx tsx src/cli.ts --self-test
 *   npx tsx src/cli.ts --vectors ../../AIEP-VECTORS/v1.1.0/
 */

// Canonical JSON
export { canonicalJson, CanonError } from "./canonical.js";

// Hashing primitives
export { sha256hex, sha256bytes, concatHash } from "./hash.js";

// Kernel primitives
export {
    packHash,
    negativeProofHash,
    dissentHash,
    dissentResolutionChainHash,
    contextReconstructionHash,
    recallScopeHash,
    localDominanceHash,
    consensusRecordHash,
    swarmInclusionProof,
    checkAdmissibility,
} from "./kernel.js";

// Vector runner
export type { VectorResult, SelfTestResult, Manifest } from "./runner.js";
export { runManifest, runSelfTests } from "./runner.js";
