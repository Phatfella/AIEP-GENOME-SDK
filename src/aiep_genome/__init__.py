"""
aiep_genome — AIEP GENOME SDK Python package
=============================================
Version: 1.2.0
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

__version__ = "1.2.0"
KERNEL_VERSION = "1.0.0"
LOCKFILE_VERSION = "1.0.0"

__all__ = [
    "__version__",
    "KERNEL_VERSION",
    "LOCKFILE_VERSION",
]
