"""
aiep_genome.scaffold — New AIEP-compliant project scaffolding
=============================================================
Implements the `aiep-genome init` command: produces a complete, runnable,
genome-compliant project from zero in one command.

Patterns
--------
  bare             Kernel + config only. No domain logic.
  evidence-ledger  Full ledger pattern (P01, P10, P14).  [default]
  mirror           Static-site mirror integration (P60-P63).
  governance       Policy + constitutional arbitration layer (P82, P89).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

PATTERN = Literal["bare", "evidence-ledger", "mirror", "governance"]


# ── Result dataclass ──────────────────────────────────────────────────────────

class ScaffoldResult:
    def __init__(self):
        self.created: list[str] = []
        self.skipped: list[str] = []

    def add(self, path: str):
        self.created.append(path)

    def skip(self, path: str):
        self.skipped.append(path)

    @property
    def success(self):
        return True

    # Convenience aliases
    @property
    def ok(self) -> bool:
        return True

    @property
    def created_files(self) -> list:
        return self.created


# ── File templates ────────────────────────────────────────────────────────────

def _pyproject(name: str, version: str, description: str) -> str:
    safe_name = name.replace("_", "-")
    module_name = name.replace("-", "_")
    return f'''\
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{safe_name}"
version = "{version}"
license = "Apache-2.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "aiep-genome-sdk>=1.2.0",
]

[project.optional-dependencies]
dev = ["pytest>=7"]

[project.scripts]
{safe_name} = "{module_name}.__main__:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
'''


def _init_py(name: str, version: str) -> str:
    module_name = name.replace("-", "_")
    return f'''\
"""
{module_name} — AIEP-compliant package
Version: {version}
"""
from __future__ import annotations

__version__ = "{version}"
'''


def _main_py_bare(name: str) -> str:
    module_name = name.replace("-", "_")
    return f'''\
"""
{module_name} CLI
"""
from __future__ import annotations
import sys

try:
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

from aiep_genome.kernel import run_self_test
from {module_name} import __version__


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(prog="{name}", description="{module_name} v{{__version__}}")
    parser.add_argument("--version", action="version", version=f"{{__version__}}")
    parser.add_argument("--self-test", action="store_true", help="Run AIEP kernel self-test")
    args = parser.parse_args()

    if args.self_test:
        ok = run_self_test()
        print(f"Kernel self-test: {{\'PASS\' if ok else \'FAIL\'}}")
        sys.exit(0 if ok else 1)

    parser.print_help()


if __name__ == "__main__":
    main()
'''


def _ledger_py(name: str) -> str:
    module_name = name.replace("-", "_")
    return '''\
"""
genome/ledger.py — Evidence Ledger integration layer
Wraps aiep_genome.kernel to provide a simple append-only ledger for this project.
"""
from __future__ import annotations

import json
from pathlib import Path
from aiep_genome.kernel import (
    canonical_json, sha256_hex, evidence_commitment,
    lifecycle_hash, pack_hash, evaluate_gate, GateResult,
)

SCHEMA_VERSION_ID = "aiep.evidence.v1.0.0"


class EvidenceLedger:
    """
    Append-only, cryptographically anchored evidence ledger.

    Usage::

        ledger = EvidenceLedger()
        ec = ledger.commit({"source": "api", "value": 42}, provenance="system-a")
        gate = ledger.gate(ec)
        assert gate.is_open
    """

    def __init__(self):
        self._evidence: dict[str, dict] = {}   # evidence_hash -> lifecycle record
        self._reasoning: list[dict]     = []   # append-only reasoning entries
        self._active_branches: set[str] = set()

    def commit(
        self,
        data: dict,
        provenance: str,
        permitted_use_scope: str = "UNRESTRICTED",
        retention_policy_id: str = "retain-7-years",
        expiry_ts: str = "",
    ) -> str:
        """
        Commit an evidence record. Returns the evidence_commitment hash.
        """
        canon = canonical_json(data)
        ec = evidence_commitment(canon, provenance, SCHEMA_VERSION_ID)
        lh = lifecycle_hash(ec, permitted_use_scope, retention_policy_id, expiry_ts, SCHEMA_VERSION_ID)
        self._evidence[ec] = {
            "content_hash": sha256_hex(canon),
            "evidence_commitment": ec,
            "lifecycle_hash": lh,
            "provenance": provenance,
            "permitted_use_scope": permitted_use_scope,
            "retention_policy_id": retention_policy_id,
            "expiry_ts": expiry_ts or "NONE",
        }
        return ec

    def append_reasoning(
        self,
        entry_hash: str,
        kind: str,
        evidence_refs: list[str],
        branch_id: str = "",
        conclusion: str = "",
    ) -> None:
        """Append an immutable reasoning entry."""
        self._reasoning.append({
            "entry_hash": entry_hash,
            "kind": kind,
            "evidence_refs": evidence_refs,
            "branch_id": branch_id,
            "conclusion": conclusion,
        })
        if kind == "ACTIVATION" and branch_id:
            self._active_branches.add(branch_id)
        elif kind in ("DEMOTION", "ARCHIVAL") and branch_id:
            self._active_branches.discard(branch_id)

    def gate(self, evidence_hash: str, branch_id: str = "", operation_label: str = "") -> GateResult:
        """Evaluate gate invariants I1–I5 for the given evidence hash."""
        return evaluate_gate(
            evidence_hash,
            self._evidence,
            self._reasoning,
            self._active_branches,
            branch_id=branch_id,
            operation_label=operation_label,
        )

    def replay_hash(self) -> str:
        """I6: Compute deterministic replay pack hash for the current state."""
        return pack_hash(
            list(self._evidence.values()),
            self._reasoning,
            SCHEMA_VERSION_ID,
        )

    def export(self) -> dict:
        """Export full ledger state for audit or persistence."""
        return {
            "evidence": dict(self._evidence),
            "reasoning": list(self._reasoning),
            "replay_hash": self.replay_hash(),
            "schema_version_id": SCHEMA_VERSION_ID,
        }
'''


def _mirror_py() -> str:
    return '''\
"""
genome/mirror.py — Mirror integration layer
Wraps aiep_genome.kernel to generate .well-known/aiep/ artefacts from this project.
See also: aiep-mirror SDK (pip install aiep-mirror)
"""
from __future__ import annotations

from aiep_genome.kernel import canonical_json, sha256_hex, concat_hash

SCHEMA_VERSION_ID = "aiep.mirror.v1.0.0"


def content_hash(html: str) -> str:
    """Canonical content hash for a page. RC §1."""
    return sha256_hex(html.strip())


def capability_hash(site_base: str, schema_version_id: str = SCHEMA_VERSION_ID) -> str:
    """Capability hash — binds this deployment to its site_base (FC §3)."""
    return concat_hash(site_base, schema_version_id)


def policy_hash(visibility_default: str, schema_version_id: str = SCHEMA_VERSION_ID) -> str:
    """Policy hash — binds visibility policy (FC §4)."""
    return concat_hash(visibility_default, schema_version_id)
'''


def _governance_py() -> str:
    return '''\
"""
genome/governance.py — Policy and constitutional arbitration layer
Wraps aiep_genome.kernel for project-level governance operations.
"""
from __future__ import annotations

from aiep_genome.kernel import (
    canonical_json, sha256_hex, concat_hash,
    arbitration_hash, evaluate_admissibility,
    CONSTITUTIONAL_CONSTRAINTS,
)

SCHEMA_VERSION_ID = "aiep.governance.v1.0.0"


def make_arbitration_record(
    branch_id: str,
    conclusion: dict,
    plausibility_status: str,      # "plausible" | "implausible" | "indeterminate"
    dissent_final_position: str,   # "accept" | "reject" | "escalate"
    gate_status: str,              # "OPEN" | "CLOSED"
) -> dict:
    """
    Produce a constitutional arbitration record.
    Returns the record or raises if conclusion is inadmissible.
    """
    admissible, reason = evaluate_admissibility(
        plausibility_status, dissent_final_position, gate_status
    )
    if not admissible:
        raise ValueError(f"Conclusion inadmissible: {reason}")

    conclusion_hash = sha256_hex(canonical_json(conclusion))
    ah = arbitration_hash(
        branch_id, conclusion_hash, True, plausibility_status, SCHEMA_VERSION_ID
    )
    return {
        "arbitration_hash": ah,
        "branch_id": branch_id,
        "conclusion_hash": conclusion_hash,
        "plausibility_status": plausibility_status,
        "dissent_final_position": dissent_final_position,
        "admissible": admissible,
        "schema_version_id": SCHEMA_VERSION_ID,
    }
'''


def _test_genome_bare(name: str) -> str:
    module_name = name.replace("-", "_")
    return f'''\
"""
tests/test_genome.py — Genome compliance tests for {module_name}
"""
import unittest
from aiep_genome.kernel import run_self_test, canonical_json, sha256_hex, concat_hash


class TestKernelCanon(unittest.TestCase):

    def test_self_test_passes(self):
        self.assertTrue(run_self_test())

    def test_key_ordering(self):
        self.assertEqual(canonical_json({{"z": 1, "a": 2}}), \'{{"a":2,"z":1}}\')

    def test_no_whitespace(self):
        self.assertNotIn(" ", canonical_json({{"k": "v"}}))

    def test_deterministic_across_key_order(self):
        h1 = sha256_hex(canonical_json({{"b": 2, "a": 1}}))
        h2 = sha256_hex(canonical_json({{"a": 1, "b": 2}}))
        self.assertEqual(h1, h2)

    def test_concat_hash_boundary_safety(self):
        self.assertNotEqual(concat_hash("ab", "c"), concat_hash("a", "bc"))
        self.assertNotEqual(concat_hash("", "x"), concat_hash("x", ""))

    def test_known_empty_sha256_vector(self):
        self.assertEqual(
            sha256_hex(""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )


if __name__ == "__main__":
    unittest.main()
'''


def _test_genome_ledger(name: str) -> str:
    module_name = name.replace("-", "_")
    return _test_genome_bare(name) + f'''

class TestEvidenceLedger(unittest.TestCase):

    def setUp(self):
        from {module_name}.genome.ledger import EvidenceLedger
        self.ledger = EvidenceLedger()

    def test_commit_returns_hash(self):
        ec = self.ledger.commit({{"value": 1}}, provenance="test")
        self.assertRegex(ec, r"^[a-f0-9]{{64}}$")

    def test_gate_open_after_commit(self):
        ec = self.ledger.commit({{"v": "x"}}, provenance="p")
        gate = self.ledger.gate(ec)
        self.assertTrue(gate.is_open)
        self.assertEqual(gate.status, "OPEN")

    def test_gate_closed_for_unknown_hash(self):
        gate = self.ledger.gate("a" * 64)
        self.assertFalse(gate.is_open)

    def test_commit_determinism(self):
        ec1 = self.ledger.commit({{"data": 42}}, provenance="src")
        ledger2 = type(self.ledger)()
        ec2 = ledger2.commit({{"data": 42}}, provenance="src")
        self.assertEqual(ec1, ec2)

    def test_replay_hash_deterministic(self):
        self.ledger.commit({{"a": 1}}, provenance="p1")
        self.ledger.commit({{"b": 2}}, provenance="p2")
        h1 = self.ledger.replay_hash()
        h2 = self.ledger.replay_hash()
        self.assertEqual(h1, h2)

    def test_append_reasoning_appends(self):
        ec = self.ledger.commit({{"x": 1}}, provenance="p")
        from aiep_genome.kernel import sha256_hex, canonical_json
        entry_hash = sha256_hex(canonical_json({{"kind": "ACTIVATION", "ec": ec}}))
        self.ledger.append_reasoning(entry_hash, "ACTIVATION", [ec], branch_id="b1")
        exported = self.ledger.export()
        self.assertEqual(len(exported["reasoning"]), 1)
'''


def _readme(name: str, pattern: str) -> str:
    module_name = name.replace("-", "_")
    return f'''\
# {name}

AIEP-compliant package — pattern: `{pattern}`

Built with the [AIEP GENOME SDK](https://aiep.dev/docs/genome).

## Quick start

```bash
pip install -e ".[dev]"
{module_name.replace("_", "-")} --self-test
pytest
```

## AIEP Compliance

This package uses the AIEP GENOME kernel (frozen at v1.0.0).

- All evidence commitments are deterministic: `H(CanonicalJSON || provenance || schema_version_id)`
- Kernel hash: SHA-256, hex-lower, length-prefixed concatenation (R7)
- Gate invariants I1–I5 enforced on every operation
- RFC compliant: `GENESIS` sentinel for chain genesis

## Licence

Apache License 2.0
'''


def _aiep_genome_json(name: str, pattern: str) -> dict:
    module_name = name.replace("-", "_")
    return {
        "name": name,
        "module": module_name,
        "genome_sdk_version": "1.2.0",
        "kernel_version": "1.0.0",
        "lockfile_version": "1.0.0",
        "pattern": pattern,
        "schema_version_id": f"aiep.{pattern.replace('-', '_')}.v1.0.0",
        "adoption_mode": "scaffold",
    }


# ── Main scaffold function ───────────────────────────────────────────────────

def scaffold_new_project(
    dest_dir: str | Path,
    *,
    name: str,
    version: str = "0.1.0",
    description: str = "",
    pattern: str = "evidence-ledger",
    force: bool = False,
) -> ScaffoldResult:
    """
    Scaffold a new AIEP-compliant project at dest_dir.

    Parameters
    ----------
    dest_dir    : Destination directory (will be created if it doesn't exist).
    name        : Package name (e.g. "my-evidence-service").
    version     : Initial version string [0.1.0].
    description : Short one-line description.
    pattern     : Scaffold pattern — bare | evidence-ledger | mirror | governance.
    force       : Overwrite existing files.
    """
    valid_patterns = ("bare", "evidence-ledger", "mirror", "governance")
    if pattern not in valid_patterns:
        raise ValueError(f"Unknown pattern '{pattern}'. Valid: {valid_patterns}")

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    result = ScaffoldResult()
    module_name = name.replace("-", "_")
    description = description or f"AIEP-compliant {pattern} service"

    def write(rel: str, content: str) -> None:
        p = dest / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.exists() and not force:
            result.skip(rel)
            return
        p.write_text(content, encoding="utf-8")
        result.add(rel)

    def write_json(rel: str, data: dict) -> None:
        write(rel, json.dumps(data, indent=2) + "\n")

    # ── Universal files (all patterns) ───────────────────────────────────────
    write("pyproject.toml", _pyproject(name, version, description))
    write("README.md", _readme(name, pattern))
    write(f"src/{module_name}/__init__.py", _init_py(name, version))
    write(f"src/{module_name}/__main__.py", _main_py_bare(name))
    write("tests/__init__.py", "")
    write("schemas/.gitkeep", "")
    write_json(".aiep-genome.json", _aiep_genome_json(name, pattern))

    # ── Pattern: bare ────────────────────────────────────────────────────────
    if pattern == "bare":
        write(f"src/{module_name}/genome/__init__.py", "")
        write("tests/test_genome.py", _test_genome_bare(name))

    # ── Pattern: evidence-ledger ─────────────────────────────────────────────
    elif pattern == "evidence-ledger":
        write(f"src/{module_name}/genome/__init__.py", "")
        write(f"src/{module_name}/genome/ledger.py", _ledger_py(name))
        write("tests/test_genome.py", _test_genome_ledger(name))
        # Sample schema
        schema = {
            "$schema": "https://aiep.dev/schemas/evidence.v1.0.0.schema.json",
            "schema_version_id": f"aiep.evidence.v1.0.0",
            "name": name,
            "description": description,
        }
        write_json("schemas/evidence.schema.json", schema)

    # ── Pattern: mirror ──────────────────────────────────────────────────────
    elif pattern == "mirror":
        write(f"src/{module_name}/genome/__init__.py", "")
        write(f"src/{module_name}/genome/mirror.py", _mirror_py())
        write("tests/test_genome.py", _test_genome_bare(name))
        # Mirror config
        mirror_cfg = {
            "site_base": "https://example.com",
            "in_dir": "./dist",
            "out_dir": ".",
            "visibility_default": "PRIVATE",
        }
        write_json(".aiep-mirror.json", mirror_cfg)

    # ── Pattern: governance ──────────────────────────────────────────────────
    elif pattern == "governance":
        write(f"src/{module_name}/genome/__init__.py", "")
        write(f"src/{module_name}/genome/ledger.py", _ledger_py(name))
        write(f"src/{module_name}/genome/governance.py", _governance_py())
        write("tests/test_genome.py", _test_genome_ledger(name))

    return result
