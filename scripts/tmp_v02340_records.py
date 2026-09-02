from pathlib import Path

architecture = Path("ARCHITECTURE.md")
text = architecture.read_text(encoding="utf-8")
assert text.startswith("# Parallax 2.0 Architecture\n\nVersion: 3.48\nStatus: Authoritative\n")
text = text.replace("Version: 3.48\n", "Version: 3.49\n", 1)
anchor = "Architecture v3.48 recognizes the universal canonical Git empty-tree SHA"
assert anchor in text
section = """Architecture v3.49 separates protected static-web structural execution success from Work Specification acceptance verification. For an exact durable PLAN whose closed-catalog execution contract resolves to `static-web-v1` / `GREENFIELD_STATIC_WEB`, successful TEST and VERIFY persist the fixed server-owned scope `STRUCTURAL_ONLY`: the exact protected acceptance map remains targeted and explicitly unverified while `acceptance_ids_verified` is empty. `EngineeringRunService` independently re-resolves and verifies the persisted PLAN execution-contract identity before admitting that envelope, so stage payloads, candidate source, user text, model output, or a forged `static-web-v1` label cannot self-authorize partial verification. `AutonomyCoordinator` derives the writer-side scope from the same already-resolved PLAN-bound execution contract used for same-lineage execution. Runtime evaluation independently authenticates the durable PLAN identity, validates the exact structural partition, and binds the verification scope into its evidence digest; structural command success can therefore remain valid same-lineage execution evidence without being reinterpreted as behavioral acceptance proof. Python and .NET TEST/VERIFY retain exact full-acceptance verification semantics. The immutable execution-contract/profile digests, static-web validator commands, source-lineage authority, provider/Git/Preview authority, lifecycle authority, and human REVIEW completion contract are unchanged. No browser or behavioral verifier is added in v3.49; remaining static-web acceptance criteria stay explicit until human REVIEW or a separately governed future verifier proves them. Architecture v3.48 remains the canonical empty-tree replay foundation.

"""
text = text.replace(anchor, section + anchor, 1)
architecture.write_text(text, encoding="utf-8")

current = Path("CURRENT-STATE.md")
text = current.read_text(encoding="utf-8")
lines = text.splitlines()
status_index = next(i for i, line in enumerate(lines) if line.startswith("Status: **"))
if "P2-V0.23.40 HONEST STATIC-WEB ACCEPTANCE EVIDENCE" not in lines[status_index]:
    assert lines[status_index].endswith("**")
    lines[status_index] = (
        lines[status_index][:-2]
        + " / P2-V0.23.40 HONEST STATIC-WEB ACCEPTANCE EVIDENCE IMPLEMENTATION-VALIDATED / PR PENDING**"
    )
text = "\n".join(lines) + "\n"
anchor = "## P2-V0.23.39 — canonical empty-tree replay compatibility"
assert anchor in text
section = """## P2-V0.23.40 — honest static-web acceptance evidence — IMPLEMENTATION-VALIDATED / PR PENDING

Workstream: #565. Parent: #391 / W9-S1. Governing specification: `P2-V0.23.40`. Architecture: `ARCHITECTURE.md` v3.49. Production remains P2-V0.23.39 until merge and deployment verification.

The first real W9-S1 Decision Ledger build exposed a systemic evidence defect rather than only an application defect: `static-web-v1` proves bounded structural properties such as root/file safety, `index.html`, JavaScript syntax and local references, but protected TEST/VERIFY previously stamped the full Work Specification acceptance map as verified whenever those structural commands succeeded. P2-V0.23.40 contracts that claim. PLAN-bound static-web TEST/VERIFY now persist `STRUCTURAL_ONLY`, target the exact protected acceptance map, verify none of it behaviorally, and explicitly mark the full map unverified. The run can still reach human REVIEW because structural execution succeeded, but structural evidence alone cannot complete REVIEW.

Validated implementation evidence:

- refined protected DSPy SpecCritic/SpecCompiler gate `33651595933`: SUCCESS, with the exact compiled plan persisted;
- serialized bounded implementation validation `33663382152`: SUCCESS, including strict DSPy-plan validation, API compileall, focused P2-V0.23.40 regressions, the full API regression suite, patch hygiene and durable semantic commit;
- exact validated semantic head `4f1c1a0956c4d01fb5363c79faa44140d8a60976`;
- runtime evaluation now independently authenticates the persisted PLAN execution contract before consuming `STRUCTURAL_ONLY`, validates the exact targeted/verified/unverified partition, and binds scope into the evidence digest instead of converting structural success back into behavioral proof;
- Python/.NET full-verification semantics, execution-contract/profile digests, commands, provider/model/network authority, source-lineage authority, Git/Preview authority, lifecycle transitions and human REVIEW completion authority remain unchanged.

This state is implementation-validated only. P2-V0.23.40 has not yet been merged or deployed, and no production acceptance claim is recorded here.

"""
text = text.replace(anchor, section + anchor, 1)
current.write_text(text, encoding="utf-8")
