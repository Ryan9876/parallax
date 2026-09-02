from pathlib import Path


ARCHITECTURE_INSERT = """Architecture v3.48 recognizes the universal canonical Git empty-tree SHA `4b825dc642cb6eb9a060e54bf8d69288fbee4904` as the exact deterministic empty-tree identity during replay of an existing Parallax two-commit greenfield baseline. Existing-baseline replay therefore requires the cleanup commit's exact `tree.sha` to equal that canonical identity and does not require GitHub to materialize the object through a Trees GET, because authenticated production evidence proves that endpoint may return 404 for the canonical empty tree even while the verified cleanup commit references it. Any other cleanup tree SHA fails `GREENFIELD_BASELINE_MISMATCH` before provider tree read-back and no arbitrary missing tree or 404 is normalized as empty. New empty-repository initialization remains stricter: Parallax still creates the cleanup tree from the verified bootstrap tree by deleting only the fixed marker, reads back the provider-returned created tree, proves it contains zero entries before cleanup commit/ref mutation, and then requires the resulting cleanup commit to reference the canonical empty-tree identity. Exact repository/default-ref binding, actor name/email and timezone-aware chronology requirements, commit messages and parent cardinality, bootstrap marker path/type/mode/blob/content/provenance, non-force ref update, GET-only existing-baseline replay, source-lineage, lifecycle and human REVIEW authority remain unchanged. Architecture v3.47 remains the provider-owned chronology foundation.\n\n"""

CURRENT_39 = """## P2-V0.23.39 — canonical empty-tree replay compatibility — VALIDATED / PR PENDING

Workstream: #562. Parent: #560 / #558 / W9-S1. Governing specification: `P2-V0.23.39`. Architecture: `ARCHITECTURE.md` v3.48.

P2-V0.23.39 makes existing exact two-commit greenfield baseline replay compatible with GitHub's canonical empty-tree object semantics without widening trust. Replay accepts emptiness only when the verified cleanup commit's exact tree SHA is the universal Git empty-tree identity `4b825dc642cb6eb9a060e54bf8d69288fbee4904`; it then omits the redundant Trees GET that production proved GitHub may answer 404. Any non-canonical cleanup tree fails `GREENFIELD_BASELINE_MISMATCH` before tree read-back, so no arbitrary 404 or missing object is normalized as empty. New empty-repository initialization remains unchanged in authority and still reads back the provider-returned cleanup tree and proves zero entries before cleanup commit/ref mutation.

Validated pre-PR evidence:

- protected DSPy SpecCritic/SpecCompiler and strict spec gate `33639991993`: SUCCESS, with exact compiled plan persisted;
- bounded implementation validation `33640788281`: SUCCESS, including strict persisted DSPy-plan validation, focused greenfield regressions, API compileall and the full API regression suite;
- exact validated implementation commit before record reconciliation: `79e5a570fc21ff95e5091e32a99a9467f76b10fb`;
- regressions prove canonical empty-tree replay performs no provider GET for `/git/trees/4b825dc642cb6eb9a060e54bf8d69288fbee4904`, remains GET-only overall and returns `initialized=false`; non-canonical cleanup-tree identity fails closed without interpreting a missing provider tree as empty; existing initialization regression continues to prove provider-created cleanup-tree read-back must contain zero entries before later commit/ref mutation.

P2-V0.23.39 is **not merged or production-deployed** at this record point. Production acceptance still requires protected PR gates, exact merged-source deployment verification, normal production preflights/health/readiness/runtime checks and continuation of the same frozen W9-S1 Engineering Run beyond the canonical empty-tree `SOURCE_NOT_FOUND` blocker under the unchanged human REVIEW boundary.

"""

CURRENT_38 = """## P2-V0.23.38 — provider-owned greenfield commit timestamp compatibility — PRODUCTION-BEHAVIOR-ACCEPTED / LATER CANONICAL EMPTY-TREE PROVIDER READBACK BLOCKER EXPOSED

Workstream: #560. Release PR: #561. Parent: #558 / W9-S1. Governing specification: `P2-V0.23.38`. Architecture: `ARCHITECTURE.md` v3.47.

P2-V0.23.38 narrows deterministic greenfield actor verification to authority-bearing identity while treating provider commit chronology as validated metadata. Exact author and committer name/email remain mandatory Parallax-owned constants. Provider-returned dates must be non-empty, parseable and timezone-aware, but they no longer have to equal the fixed server request preference and do not participate in repository, baseline, source-lineage, lifecycle, REVIEW or production authority. Exact message, parent, tree, marker path/type/mode/blob/content/provenance, canonical ref and read-only replay invariants remain unchanged.

Release and production evidence:

- protected DSPy/spec and bounded implementation validation completed successfully before PR, including exact persisted compiled-plan validation, focused regressions, compileall and the full API regression suite;
- PR #561 exact head `638f9a3f3169e557fdfdf42138d0bc6be9f08c01`; Bounded Autonomy Pilot `33638850763`, Workstream Spec Validation `33638850793`, and Parallax P2 CI `33638851131`: SUCCESS;
- squash merge / exact production application source `c4adba3743a9280f65ce94b8323508f6c2914e6a`;
- post-merge Workstream Spec Validation `33639057258` and Parallax P2 CI `33639057336`: SUCCESS;
- exact production deployment `dpl_CLvkbd6zq23fREa74AApn3Rr5MSo`: READY from that merged source with canonical `parallax-api-tan.vercel.app` alias;
- production provider, delivery-permission, projected-source, Blob, lineage, agentic-runtime, projected-bootstrap, execution-snapshot, candidate-validation and run-event-schema preflights passed; canonical `/health` and `/ready` returned HTTP 200 and exact-deployment runtime/error scans were clean before acceptance replay.

Frozen W9-S1 replay `33639577412` continued the same Engineering Run `a64d56b7-ad42-42ad-9562-891783363f4a` at REVIEW revision 6. `GREENFIELD_BASELINE_MISMATCH`, `PROVIDER_CONFLICT`, and `TARGET_DISCOVERY_UNBOUNDED` did not recur, proving the provider-owned timestamp correction worked in production. Exact production logs then advanced to the cleanup-tree check: cleanup commit `b1c8d7102ca0567c20cd2fc05289eba945b01138` read successfully and referenced canonical empty-tree SHA `4b825dc642cb6eb9a060e54bf8d69288fbee4904`, but GitHub returned 404 for `GET /git/trees/4b825dc642cb6eb9a060e54bf8d69288fbee4904?recursive=1`. Verified source delivery therefore failed later and bounded as `SOURCE_NOT_FOUND`; no new durable mutation occurred, the run remained REVIEW revision 6 and human REVIEW authority remained unchanged.

"""


def update_architecture() -> None:
    path = Path("ARCHITECTURE.md")
    text = path.read_text()
    if text.count("Version: 3.47") != 1:
        raise SystemExit("architecture version anchor mismatch")
    text = text.replace("Version: 3.47", "Version: 3.48", 1)
    anchor = "## Version relationship\n\nArchitecture v3.47"
    if text.count(anchor) != 1:
        raise SystemExit("architecture relationship anchor mismatch")
    text = text.replace(anchor, "## Version relationship\n\n" + ARCHITECTURE_INSERT + "Architecture v3.47", 1)
    path.write_text(text)


def update_current_state() -> None:
    path = Path("CURRENT-STATE.md")
    text = path.read_text()
    old_status_tail = "P2-V0.23.38 PROVIDER-OWNED GREENFIELD TIMESTAMP COMPATIBILITY VALIDATED / PR PENDING**"
    new_status_tail = (
        "P2-V0.23.38 PROVIDER-OWNED GREENFIELD TIMESTAMP COMPATIBILITY PRODUCTION-BEHAVIOR-ACCEPTED / "
        "LATER CANONICAL EMPTY-TREE PROVIDER READBACK BLOCKER EXPOSED / "
        "P2-V0.23.39 CANONICAL EMPTY-TREE REPLAY COMPATIBILITY VALIDATED / PR PENDING**"
    )
    if text.count(old_status_tail) != 1:
        raise SystemExit("current-state status anchor mismatch")
    text = text.replace(old_status_tail, new_status_tail, 1)

    start = text.index("## P2-V0.23.38")
    end = text.index("## P2-V0.23.37", start)
    text = text[:start] + CURRENT_39 + CURRENT_38 + text[end:]
    path.write_text(text)


def main() -> None:
    update_architecture()
    update_current_state()


if __name__ == "__main__":
    main()
