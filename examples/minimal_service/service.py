"""
Minimal AIEP-compliant decision service.

Demonstrates the complete cycle:
  collect_evidence() → make_decision() → decision_record()

The record produced is verifiable by any third party with:
  aiep-verify decision-record.json
"""
import hashlib
import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from aiep_genome.kernel.canon import pack_hash, negative_proof_hash

# If aiep-validator is installed, enforce constitutional constraints at runtime.
# It is optional — the core record production works without it.
try:
    from aiep_validator.monitor import AiepMonitor, AiepConstraintError  # type: ignore
    _MONITOR = AiepMonitor()
    _MONITOR_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MONITOR_AVAILABLE = False
    _MONITOR = None

SCHEMA_VERSION = "aiep.canonical.v2.0.0"
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class EvidenceItem:
    evidence_id: str
    evidence_type: str
    content: str
    collected_ts: str
    source_uri: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "content": self.content,
            "collected_ts": self.collected_ts,
        }
        if self.source_uri:
            d["source_uri"] = self.source_uri
        return d


@dataclass
class ReasoningStep:
    entry_hash: str
    kind: str  # ACTIVATION | INFERENCE | REJECTION | DISSENT
    reasoning: str
    branch_id: str
    evidence_refs: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "entry_hash": self.entry_hash,
            "kind": self.kind,
            "reasoning": self.reasoning,
            "branch_id": self.branch_id,
            "evidence_refs": self.evidence_refs,
        }


@dataclass
class DecisionRecord:
    schema_version_id: str
    pack_hash_val: str
    evidence_ledger: list
    reasoning_ledger: list
    plausibility_status: str
    gate_status: str
    verdict: str
    committed_ts: str
    negative_proof_hash_val: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "schema_version_id": self.schema_version_id,
            "pack_hash": self.pack_hash_val,
            "evidence_ledger": self.evidence_ledger,
            "reasoning_ledger": self.reasoning_ledger,
            "plausibility_status": self.plausibility_status,
            "gate_status": self.gate_status,
            "verdict": self.verdict,
            "committed_ts": self.committed_ts,
        }
        if self.negative_proof_hash_val:
            d["negative_proof_hash"] = self.negative_proof_hash_val
        return d


class AiepConstraintError(Exception):
    """Raised when a decision record fails constitutional constraints."""


# ---------------------------------------------------------------------------
# Core service functions
# ---------------------------------------------------------------------------

def collect_evidence(source_uri: str, evidence_id: str = "e1") -> EvidenceItem:
    """
    Fetch content from source_uri and wrap it as an EvidenceItem.

    The content is stored verbatim — not by URL. If the source disappears,
    the pack_hash still verifies against the stored content.

    For your implementation: replace this with your evidence source —
    an API call, a database query, a sensor reading, a document parser.
    """
    try:
        req = urllib.request.Request(
            source_uri,
            headers={"User-Agent": "aiep-minimal-service/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read(65536)  # 64KB max; adjust for your use case
            content = raw.decode("utf-8", errors="replace")
        evidence_type = "text/html" if "html" in resp.headers.get("content-type", "") else "text/plain"
    except (urllib.error.URLError, OSError) as exc:
        logger.warning("Evidence collection failed for %s: %s", source_uri, exc)
        raise

    return EvidenceItem(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        content=content[:4096],  # truncate to 4KB; store full content for production use
        collected_ts=_now_iso(),
        source_uri=source_uri,
    )


def collect_text_evidence(text: str, label: str, evidence_id: str = "e1") -> EvidenceItem:
    """
    Wrap a text string as an EvidenceItem.

    Use this when the evidence is a document you already hold rather than a URL.
    """
    return EvidenceItem(
        evidence_id=evidence_id,
        evidence_type="structured_data",
        content=text,
        collected_ts=_now_iso(),
        source_uri=f"text://{_sha256_short(text)}",
    )


def make_decision(
    evidence_items: list[EvidenceItem],
    query: str = "default",
) -> tuple[list, list, str, str]:
    """
    Apply reasoning to evidence and produce (evidence_ledger, reasoning_ledger, plausibility, gate).

    For your implementation: replace the reasoning logic here with your domain logic.
    Keep the structure — EvidenceItem list in, (ledgers, plausibility, gate) out.

    Returns:
        evidence_ledger   — list of dicts, ready for pack_hash
        reasoning_ledger  — list of dicts, ready for pack_hash
        plausibility_status — "plausible" | "speculative" | "implausible"
        gate_status       — "OPEN" | "CLOSED"
    """
    if not evidence_items:
        # No evidence → produce a governed negative proof, not a hallucinated answer.
        logger.warning("No evidence available for query '%s' — producing NegativeProofRecord", query)
        ts = _now_iso()
        neg_hash = negative_proof_hash(
            expected_evidence_type="any",
            gap_window_start=ts,
            gap_window_end=ts,
            schema_version_id=SCHEMA_VERSION,
        )
        # A negative proof record uses an empty evidence ledger and records the gap.
        return (
            [],
            [{"entry_hash": neg_hash[:16], "kind": "DISSENT",
              "reasoning": f"No evidence available for: {query}. NegativeProofHash: {neg_hash}",
              "branch_id": "negative", "evidence_refs": []}],
            "implausible",
            "CLOSED",
        )

    evidence_ledger = [e.to_dict() for e in evidence_items]

    # Minimal reasoning: accept the evidence as-is.
    # In a real system: apply your model, extract claims, evaluate plausibility.
    reasoning_steps = [
        ReasoningStep(
            entry_hash=_sha256_short(e.content),
            kind="ACTIVATION",
            reasoning=f"Evidence '{e.evidence_id}' collected and accepted. No contradictions detected.",
            branch_id="main",
            evidence_refs=[e.evidence_id],
        )
        for e in evidence_items
    ]

    # Plausibility gate: in a real system, your model evaluates this.
    # Here we use a simple heuristic: if any evidence item is empty, mark speculative.
    all_content_present = all(len(e.content.strip()) > 20 for e in evidence_items)
    plausibility = "plausible" if all_content_present else "speculative"

    return (
        evidence_ledger,
        [r.to_dict() for r in reasoning_steps],
        plausibility,
        "OPEN",
    )


def decision_record(
    evidence_ledger: list,
    reasoning_ledger: list,
    plausibility_status: str,
    gate_status: str,
) -> DecisionRecord:
    """
    Compute pack_hash and produce a complete, verifiable DecisionRecord.

    The record is verifiable by any third party with:
        aiep-verify decision-record.json

    Raises AiepConstraintError if constitutional constraints CC-001–CC-005 are violated
    and aiep-validator is installed.
    """
    ph = pack_hash(evidence_ledger, reasoning_ledger, SCHEMA_VERSION)

    # CC-001–CC-005 runtime enforcement (requires aiep-validator)
    if _MONITOR_AVAILABLE and _MONITOR is not None:
        result = _MONITOR.check(
            stored_pack_hash=ph,
            evidence_ledger=evidence_ledger,
            reasoning_ledger=reasoning_ledger,
            plausibility_status=plausibility_status,
            gate_status=gate_status,
        )
        if not result.admissible:
            rules = ", ".join(v.rule for v in result.violations)
            raise AiepConstraintError(
                f"Record failed AIEP constraints [{rules}] — not committing. "
                f"validator_record_hash: {result.validator_record.validator_record_hash_val}"
            )

    # Determine verdict
    if plausibility_status == "plausible" and gate_status == "OPEN":
        verdict = "admissible"
    else:
        verdict = "rejected"

    # Negative proof hash if evidence is absent
    neg_hash = None
    if not evidence_ledger:
        ts = _now_iso()
        neg_hash = negative_proof_hash(
            expected_evidence_type="any",
            gap_window_start=ts,
            gap_window_end=ts,
            schema_version_id=SCHEMA_VERSION,
        )

    return DecisionRecord(
        schema_version_id=SCHEMA_VERSION,
        pack_hash_val=ph,
        evidence_ledger=evidence_ledger,
        reasoning_ledger=reasoning_ledger,
        plausibility_status=plausibility_status,
        gate_status=gate_status,
        verdict=verdict,
        committed_ts=_now_iso(),
        negative_proof_hash_val=neg_hash,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_short(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
