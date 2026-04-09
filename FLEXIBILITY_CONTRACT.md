# AIEP GENOME — Flexibility Contract v1.0

**Document:** AIEP-FC-001  
**Status:** Binding Architectural Constraint  
**Version:** 1.0.0  
**Applies to:** All AIEP GENOME SDK builds and downstream SaaS systems

See `AIEP_GENOME_Flexibility_Contract_v1.0.docx` for the full binding specification.

## Quick Reference

```
Layer 0 — Kernel        FROZEN   kernel/LOCKFILE.json
Layer 1 — Capability    VERSIONED governance/capability/
Layer 2 — Policy        GOVERNED  governance/policy_engine/
Layer 3 — Enterprise    FREE      enterprise/
```

## The Flexibility Test (FC §11)

A requested change is valid without version fracture if it can be expressed as:
- A policy change (Layer 2)
- A capability selection (Layer 1)  
- An adapter swap (FC §6)
- An enterprise-layer enhancement (Layer 3)

If it requires editing kernel logic → it is a new protocol version.

## Determinism Proof

`Output = f(A, C, P)` — see `examples/governance_trace_v1/` for six locked reference hashes
proving determinism at all three flexible layers.

## Reference Hashes (governance_trace_v1)

| Layer | Hash type | Value |
|-------|-----------|-------|
| L0 | evidence_commitment | `1e73514dd9ec110ec3b647295df4ba6341522701db11f46c0742e46f6b79adab` |
| L0 | pack_hash | `fb73d77f0d84babd7b775406dd11bfad4ce4accef98c41fa7840ef3e5313404b` |
| L0 | negative_proof_hash | `6413c93503255f608311e1fae9a2caacb2079b1b87137fc3f81eae64baf46d5d` |
| L1 | capability_hash | `80b0a0ee9254de1694acb33b46d7e7a5d279ee68bf29cab67fa757d81b13dd3c` |
| L2 | policy_hash | `d326f997a85041af0c15f1caeea44d0a9d63f4418699c6298255e3c040ebc3ca` |
| Combined | H(ev ‖ cap ‖ pol) | `455b712ece1793097089e4d11cdbd6ae48a81aa889ef5e33eaccaeae8923b311` |
