"""
aiep_genome — AIEP GENOME SDK Python package
=============================================
Version: 1.0.0
Kernel:  Frozen at 1.0.0  (LOCKFILE v1.0.0)

Two primary surfaces:
  CLI:
    aiep-genome init     — scaffold a new AIEP-compliant project
    aiep-genome adopt    — retrofit an existing project to the genome standard
    aiep-genome verify   — check genome compliance of current directory
    aiep-genome status   — show current config and compliance state

  Library:
    from aiep_genome.kernel import canon, sha256_hex, concat_hash, ...
    from aiep_genome.kernel.invariants import evaluate_gate
    from aiep_genome.kernel.arbitration import evaluate_admissibility
    from aiep_genome.scaffold import scaffold_new_project
    from aiep_genome.adopt import adopt_project
"""
from __future__ import annotations

__version__ = "1.0.0"
KERNEL_VERSION = "1.0.0"
LOCKFILE_VERSION = "1.0.0"

# FIX-013: The kernel's own constitutional rules are committed here.
# sha256_hex(canonical_json({rules, constraints, claims_hash, boundaries_hash, canon_spec_hash}))
# Any change to CLAIMS.md, BOUNDARIES.md, or CANON_SPEC.md produces a different hash.
# Published at /.well-known/aiep/genome_constitution.json
GENOME_CONSTITUTION_HASH = "542a0e5587190ed48f0eabc3f70e4d0fabad672c48be61287d3b4c42a0b3ca74"

__all__ = [
    "__version__",
    "KERNEL_VERSION",
    "LOCKFILE_VERSION",
    "GENOME_CONSTITUTION_HASH",
]
