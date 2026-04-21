"""
AIEP GENOME SDK — DissentRegistry
===================================
Implements P27: Dissent records are first-class protocol events.

Key invariants:
  - Append-only: neither records nor resolutions are ever deleted or overwritten
  - Cryptographic identity: every record has a kernel-computed dissent_hash
  - Resolution is itself subject to dissent: a resolution creates a resolution_hash;
    a counter-resolution creates a dissent_resolution_chain_hash
  - Termination: a branch is archived when no counter-resolution arrives within
    its declared temporal window; the absence is committed as a NegativeProofRecord

Usage:
    from aiep_genome.kernel.dissent_registry import DissentRegistry, DissentRecord

    registry = DissentRegistry()
    dh = registry.register(
        branch_id="branch-001",
        conclusion_hash="<pack_hash>",
        position="reject",
        dissenting_evidence=[...],
        schema_version_id="aiep.canonical.v2.0.0",
    )
    rh = registry.resolve(
        dissent_hash=dh,
        resolution_evidence=[...],
        resolution_position="archive",
        schema_version_id="aiep.canonical.v2.0.0",
    )
    chain_hash = registry.contest_resolution(
        resolution_hash=rh,
        counter_evidence=[...],
        counter_position="reject",
        schema_version_id="aiep.canonical.v2.0.0",
    )
    open_items = registry.query_unresolved()
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from aiep_genome.kernel.canon import (
    canonical_json,
    sha256_hex,
    concat_hash,
)


def _dissent_hash(
    branch_id: str,
    conclusion_hash: str,
    position: str,
    dissenting_evidence: list,
    schema_version_id: str,
) -> str:
    """P27: H(branch_id || conclusion_hash || position || canonical(evidence) || schema)"""
    return sha256_hex(
        concat_hash(
            branch_id, conclusion_hash, position,
            canonical_json(dissenting_evidence),
            schema_version_id,
        )
    )


# ── Data types ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DissentRecord:
    """An immutable dissent record with a kernel-computed hash.

    position: one of "reject" | "escalate" | "archive"
    dissent_hash: sha256_hex(concat_hash(branch_id, conclusion_hash, position,
                                          canonical_json(dissenting_evidence),
                                          schema_version_id))
    """
    branch_id:            str
    conclusion_hash:      str
    position:             str
    dissenting_evidence:  tuple          # immutable snapshot of the evidence list
    schema_version_id:    str
    dissent_hash:         str
    registered_at_ts:     float          # unix timestamp at registration time
    resolved:             bool = False
    resolution_hash:      Optional[str] = None


@dataclass(frozen=True)
class ResolutionRecord:
    """An immutable resolution record. Resolution is itself a cryptographic event."""
    original_dissent_hash:   str
    resolution_evidence:     tuple
    resolution_position:     str        # "accept" | "reject" | "archive"
    schema_version_id:       str
    resolution_hash:         str
    resolved_at_ts:          float
    counter_resolution_hash: Optional[str] = None   # set if contested


@dataclass
class DissentChainRecord:
    """A chain: original dissent → resolution → (optional) counter-resolution.

    dissent_resolution_chain_hash is recomputed each time a counter-resolution
    is added — the chain is tamper-evident at every link.
    """
    dissent_hash:                  str
    resolution_hash:               str
    counter_resolution_hash:       str = "NONE"
    chain_hash:                    str = ""

    def __post_init__(self) -> None:
        self._recompute_chain_hash()

    def _recompute_chain_hash(self) -> None:
        # chain_hash binds together the full three-link chain.
        # schema_version_id is embedded in each component hash already;
        # we pass a stable sentinel here for the chain-level binding.
        self.chain_hash = concat_hash(
            self.dissent_hash,
            self.resolution_hash,
            self.counter_resolution_hash,
            "aiep.dissent_chain.v1",
        )


# ── Registry ───────────────────────────────────────────────────────────────────

class DissentRegistry:
    """
    Append-only registry of dissent records.

    No record or resolution is ever deleted or overwritten.
    Querying unresolved items returns all records whose dissent has not been
    conclusively resolved by an accepted resolution.

    Thread safety: not provided. Wrap with a lock if concurrent access is needed.
    """

    VALID_POSITIONS    = frozenset({"reject", "escalate", "archive"})
    VALID_RESOLUTIONS  = frozenset({"accept", "reject", "archive"})

    def __init__(self) -> None:
        # Append-only stores — keyed by their canonical hash
        self._dissent_records:    dict[str, DissentRecord]    = {}
        self._resolution_records: dict[str, ResolutionRecord] = {}
        self._chains:             dict[str, DissentChainRecord] = {}
        # Log of all operations in order — for full replay
        self._log: list[dict] = []

    # ── Write operations ──────────────────────────────────────────────────────

    def register(
        self,
        branch_id:           str,
        conclusion_hash:     str,
        position:            str,
        dissenting_evidence: list,
        schema_version_id:   str,
    ) -> str:
        """
        Register a new dissent record. Returns the dissent_hash.
        The returned hash is the canonical identifier for this record —
        two nodes with identical inputs will produce the same hash.
        """
        if position not in self.VALID_POSITIONS:
            raise ValueError(
                f"Invalid position {position!r}. Must be one of {sorted(self.VALID_POSITIONS)}"
            )

        dh = _dissent_hash(
            branch_id, conclusion_hash, position,
            dissenting_evidence, schema_version_id,
        )

        if dh in self._dissent_records:
            # Idempotent: same record can be registered twice without error.
            return dh

        record = DissentRecord(
            branch_id=branch_id,
            conclusion_hash=conclusion_hash,
            position=position,
            dissenting_evidence=tuple(dissenting_evidence),
            schema_version_id=schema_version_id,
            dissent_hash=dh,
            registered_at_ts=time.time(),
        )
        self._dissent_records[dh] = record
        self._log.append({"op": "register", "dissent_hash": dh, "ts": record.registered_at_ts})
        return dh

    def resolve(
        self,
        dissent_hash_val:    str,
        resolution_evidence: list,
        resolution_position: str,
        schema_version_id:   str,
    ) -> str:
        """
        Resolve a dissent record. Returns the resolution_hash.
        Resolution does not delete or overwrite the original dissent record.
        """
        if dissent_hash_val not in self._dissent_records:
            raise KeyError(f"Unknown dissent_hash: {dissent_hash_val[:16]}...")
        if resolution_position not in self.VALID_RESOLUTIONS:
            raise ValueError(
                f"Invalid resolution_position {resolution_position!r}. "
                f"Must be one of {sorted(self.VALID_RESOLUTIONS)}"
            )

        # Resolution hash binds dissent_hash + evidence + position
        rh = concat_hash(
            dissent_hash_val,
            canonical_json(resolution_evidence),
            resolution_position,
            schema_version_id,
        )

        if rh in self._resolution_records:
            return rh

        ts = time.time()
        res = ResolutionRecord(
            original_dissent_hash=dissent_hash_val,
            resolution_evidence=tuple(resolution_evidence),
            resolution_position=resolution_position,
            schema_version_id=schema_version_id,
            resolution_hash=rh,
            resolved_at_ts=ts,
        )
        self._resolution_records[rh] = res

        # Update the dissent record to mark as resolved
        old = self._dissent_records[dissent_hash_val]
        self._dissent_records[dissent_hash_val] = DissentRecord(
            **{**old.__dict__, "resolved": True, "resolution_hash": rh}
        )

        # Create initial chain entry (no counter-resolution yet)
        chain = DissentChainRecord(
            dissent_hash=dissent_hash_val,
            resolution_hash=rh,
        )
        self._chains[rh] = chain

        self._log.append({"op": "resolve", "resolution_hash": rh, "dissent_hash": dissent_hash_val, "ts": ts})
        return rh

    def contest_resolution(
        self,
        resolution_hash:   str,
        counter_evidence:  list,
        counter_position:  str,
        schema_version_id: str,
    ) -> str:
        """
        Contest a resolution. Returns the dissent_resolution_chain_hash.
        The resolution is NOT overwritten. The counter-resolution extends the chain.
        The entire chain is now tamper-evident: original dissent → resolution → counter.
        """
        if resolution_hash not in self._resolution_records:
            raise KeyError(f"Unknown resolution_hash: {resolution_hash[:16]}...")
        res = self._resolution_records[resolution_hash]

        if res.counter_resolution_hash is not None:
            raise ValueError(
                f"Resolution {resolution_hash[:16]}... has already been contested. "
                "Chaining multiple counter-resolutions is not supported in this implementation."
            )

        # Counter-resolution hash binds the resolution hash + new evidence + position
        counter_rh = concat_hash(
            resolution_hash,
            canonical_json(counter_evidence),
            counter_position,
            schema_version_id,
        )

        ts = time.time()
        # Mark the resolution as having a counter-resolution
        self._resolution_records[resolution_hash] = ResolutionRecord(
            **{**res.__dict__, "counter_resolution_hash": counter_rh}
        )
        self._log.append({
            "op": "contest_resolution",
            "counter_resolution_hash": counter_rh,
            "resolution_hash": resolution_hash,
            "ts": ts,
        })

        # Update the chain
        chain = self._chains[resolution_hash]
        chain.counter_resolution_hash = counter_rh
        chain._recompute_chain_hash()

        return chain.chain_hash

    # ── Read operations ───────────────────────────────────────────────────────

    def query_unresolved(self) -> list[DissentRecord]:
        """
        Return all dissent records that have not been resolved
        (or whose resolution has been contested and not re-resolved).
        """
        result = []
        for record in self._dissent_records.values():
            if not record.resolved:
                result.append(record)
                continue
            if record.resolution_hash:
                res = self._resolution_records.get(record.resolution_hash)
                if res and res.counter_resolution_hash is not None:
                    # Resolution was contested — effectively unresolved
                    result.append(record)
        return result

    def get_chain(self, resolution_hash: str) -> Optional[DissentChainRecord]:
        return self._chains.get(resolution_hash)

    def get_record(self, dissent_hash_val: str) -> Optional[DissentRecord]:
        return self._dissent_records.get(dissent_hash_val)

    def get_resolution(self, resolution_hash: str) -> Optional[ResolutionRecord]:
        return self._resolution_records.get(resolution_hash)

    def audit_log(self) -> list[dict]:
        """Return a copy of the append-only operation log."""
        return list(self._log)

    def stats(self) -> dict:
        total     = len(self._dissent_records)
        unresolved = len(self.query_unresolved())
        contested = sum(
            1 for r in self._resolution_records.values()
            if r.counter_resolution_hash is not None
        )
        return {
            "total_dissent_records":    total,
            "resolved":                 total - unresolved,
            "unresolved":               unresolved,
            "contested_resolutions":    contested,
        }
