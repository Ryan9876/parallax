from __future__ import annotations

from pathlib import Path

architecture = Path("ARCHITECTURE.md")
text = architecture.read_text(encoding="utf-8")
if text.count("Version: 3.49") != 1:
    raise SystemExit("ARCHITECTURE.md does not have the expected v3.49 baseline")
text = text.replace("Version: 3.49", "Version: 3.50", 1)
anchor = "## Version relationship\n\n"
if text.count(anchor) != 1:
    raise SystemExit("ARCHITECTURE.md version relationship anchor drifted")
paragraph = (
    "Architecture v3.50 adds an explicit bounded human correction loop at the existing REVIEW ceiling without changing the approved Work Specification or source-authority model. "
    "An authenticated Project-bound Engineering Run may move only from exact REVIEW back to PLAN when the operator supplies one normalized bounded finding linked to one or more existing immutable acceptance IDs, with optimistic run revision and idempotent operation identity. "
    "The server persists a deterministic REVIEW-rework context digest and exact accepted same-run IMPLEMENT lineage/workspace identity; fresh PLAN evidence must bind that digest and the current durable lineage before replacement IMPLEMENT can proceed. "
    "Human findings remain non-authoritative generation context and cannot select files, patches, commands, tools, providers, credentials, networks, execution profiles, Git refs, Preview targets, merge or production destinations. "
    "A narrowly admitted worker re-arm clears the rejected READY_FOR_INTEGRATION candidate/plan checkpoint only for the exact unleased same-run worker and reviewed accepted lineage, then reuses the existing RECOVERING/REASSIGNED lifecycle; ordinary acquisition and automatic recovery gain no terminal-worker restart authority. "
    "The authenticated desktop, compact-mobile and reduced-graphics clients expose the same acceptance-linked Request changes action and hand the returned PLAN revision into the unchanged bounded autonomous continuation path. "
    "Interrupted run-transition/worker-reset requests remain replay-safe under the same operation key, and the regenerated cycle still follows PLAN -> IMPLEMENT -> BUILD -> TEST -> VERIFY -> REVIEW. "
    "P2-V0.23.40 static-web STRUCTURAL_ONLY truthfulness, SafeImplementationEngine, candidate validation/evaluation, source-lineage authority, provider/model/retry ceilings, Git/deployment authority and human REVIEW completion authority remain unchanged. "
    "Architecture v3.49 remains the structural-verification foundation.\n\n"
)
text = text.replace(anchor, anchor + paragraph, 1)
architecture.write_text(text, encoding="utf-8")
