from pathlib import Path
import re

path = Path("CURRENT-STATE.md")
text = path.read_text()

# Reconcile the headline without rewriting unrelated historical state.
lines = text.splitlines()
try:
    status_index = next(i for i, line in enumerate(lines) if line.startswith("Status: **"))
except StopIteration as exc:
    raise SystemExit("CURRENT-STATE status line not found") from exc

status = lines[status_index]
replacements = {
    "P2-V0.23.23 BOUNDED VALIDATOR REPAIR DEPLOYED-READY / PRODUCTION BEHAVIOR ACCEPTANCE PENDING": "P2-V0.23.23 BOUNDED VALIDATOR REPAIR PRODUCTION-BEHAVIOR-VERIFIED",
    "P2-V0.23.25 SAFE NESTED SOURCE CREATION + TRANSPORT RECONCILIATION PRODUCTION-DEPLOYMENT-VERIFIED / REAL-PATH BEHAVIOR ACCEPTANCE PENDING": "P2-V0.23.25 SAFE NESTED SOURCE CREATION + TRANSPORT RECONCILIATION PRODUCTION-BEHAVIOR-ACCEPTED",
    "P2-V0.23.26 SERVER-CANONICALIZED IMPLEMENTATION CONTENT EDITS PRODUCTION-DEPLOYMENT-VERIFIED / REAL-PATH BEHAVIOR ACCEPTANCE PENDING": "P2-V0.23.26 SERVER-CANONICALIZED IMPLEMENTATION CONTENT EDITS PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED",
    "P2-V0.23.27 INCREMENTAL IMPLEMENT CONVERGENCE PRODUCTION-DEPLOYMENT-VERIFIED / REAL-PATH BEHAVIOR ACCEPTANCE PENDING": "P2-V0.23.27 INCREMENTAL IMPLEMENT CONVERGENCE PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED",
}
for old, new in replacements.items():
    if old not in status:
        raise SystemExit(f"status seam missing: {old}")
    status = status.replace(old, new, 1)

release_status = "P2-V0.23.28 PLAN-PREFIX IMPLEMENT CONVERGENCE PRODUCTION-DEPLOYMENT-VERIFIED / AUTHENTICATED REAL-PATH ACCEPTANCE PENDING"
if release_status not in status:
    if not status.endswith("**"):
        raise SystemExit("status line closing marker missing")
    status = status[:-2] + " / " + release_status + "**"
lines[status_index] = status
text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")

# Historical acceptance reconciliations now proven by the authenticated run lineage.
heading_replacements = {
    "## P2-V0.23.27 — incremental IMPLEMENT convergence — PRODUCTION-DEPLOYMENT-VERIFIED / REAL-PATH BEHAVIOR ACCEPTANCE PENDING": "## P2-V0.23.27 — incremental IMPLEMENT convergence — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED",
    "## P2-V0.23.26 — server-canonicalized implementation content edits — PRODUCTION-DEPLOYMENT-VERIFIED / REAL-PATH BEHAVIOR ACCEPTANCE PENDING": "## P2-V0.23.26 — server-canonicalized implementation content edits — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED",
    "## P2-V0.23.25 — safe nested source creation and ambiguous transport reconciliation — PRODUCTION-DEPLOYMENT-VERIFIED / REAL-PATH BEHAVIOR ACCEPTANCE PENDING": "## P2-V0.23.25 — safe nested source creation and ambiguous transport reconciliation — PRODUCTION-BEHAVIOR-ACCEPTED",
    "## P2-V0.23.23 — bounded validator repair — DEPLOYED-READY / PRODUCTION BEHAVIOR ACCEPTANCE PENDING": "## P2-V0.23.23 — bounded validator repair — PRODUCTION-BEHAVIOR-VERIFIED",
}
for old, new in heading_replacements.items():
    if old not in text:
        raise SystemExit(f"heading seam missing: {old}")
    text = text.replace(old, new, 1)

patterns = [
    (
        r"Deployment verification is complete, but workstream #527 remains open.*?session ownership\.\n\n",
        "Authenticated real-path acceptance for P2-V0.23.27 completed on Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc`. The run reached durable sequence #86: PLAN completed at #79, the worker persisted CHECKPOINTED at #85, and IMPLEMENT attempt 6 failed at #86 with `AUTONOMOUS_IMPLEMENT_FAILED`. Exact production logs showed source-lineage reads succeeding and Luna then Terra completing hosted generations, but no Sol/final validator-repair generation and no disposable BUILD/TEST/VERIFY after Terra. This satisfied #527's explicit completion alternative by exposing a later bounded cross-work-unit blocker after incremental convergence rather than reverting to whole-proposal regeneration. Workstream #527 is closed completed; successor #530 / P2-V0.23.28 owns the later blocker.\n\n",
    ),
    (
        r"Deployment verification is complete, but workstream #519 remains open.*?session ownership\.\n\n",
        "Authenticated real-path acceptance for P2-V0.23.26 is complete. The same Engineering Run progressed through the server-canonicalized `{path, content}` boundary without reintroducing model-owned unified-diff parsing/canonicalization failure and exposed a later protected proposal-admission blocker before BUILD. This satisfies #519's explicit completion alternative; workstream #519 is closed completed, with the later blocker governed by P2-V0.23.27 and P2-V0.23.28.\n\n",
    ),
    (
        r"Deployment verification is complete, but workstream #514 remains open.*?manufactured synthetically\.\n\n",
        "Authenticated real-path acceptance for P2-V0.23.25 is complete. Subsequent retries of the same Engineering Run progressed beyond the former nested-parent `unsafe_target` rejection; on the later P2-V0.23.26 acceptance attempt no `unsafe_target` event recurred and execution continued through source-lineage reads and hosted generation into later proposal admission. Workstream #514 is closed completed. The response-loss ambiguity did not recur in the acceptance attempt, and no duplicate mutation request was manufactured.\n\n",
    ),
    (
        r"The merge automatically closed #510 through PR linkage, but #510 was reopened.*?session ownership\.\n\n",
        "Production behavior acceptance for P2-V0.23.23 is complete through the authenticated P2-V0.23.24 proof. After distinct-agent validation exhaustion, Parallax emitted `parallax_final_validator_repair_dispatch` and performed a real fresh Terra hosted completion before a later protected validation rejection. The affected run therefore no longer failed solely because the distinct admitted-agent set was exhausted. Workstream #510 is closed completed; later proposal-quality/admission blockers were governed separately.\n\n",
    ),
]
for pattern, replacement in patterns:
    text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"acceptance reconciliation seam not matched: {pattern}")

anchor = "## P2-V0.23.27 — incremental IMPLEMENT convergence — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED\n"
if anchor not in text:
    raise SystemExit("P2-V0.23.27 insertion anchor missing")

section = """## P2-V0.23.28 — plan-prefix IMPLEMENT convergence and durable failure diagnostics — PRODUCTION-DEPLOYMENT-VERIFIED / AUTHENTICATED REAL-PATH ACCEPTANCE PENDING

Workstream: #530. Release PR: #531. Governing specification: `P2-V0.23.28`. Architecture: `ARCHITECTURE.md` v3.39.

P2-V0.23.28 removes the later cross-work-unit IMPLEMENT blocker exposed by the authenticated P2-V0.23.27 retry. Before a locally converged work unit is completed, the protected runtime now preflights its canonical patches together with the already completed non-authoritative plan prefix through the unchanged `ProposalSafetyPreflight` / `SafeImplementationEngine` boundary. A plan-prefix rejection keeps only the current work unit inside the existing finite distinct-agent recovery and single final validator-repair path; previously completed work-unit intent remains unchanged and non-authoritative, current-generation additions are not retained, and repair guidance receives only bounded target names plus fixed sanitized reason codes. Final exact-acceptance and whole-plan safe preflight remains mandatory defense in depth before disposable BUILD/TEST/VERIFY. The durable IMPLEMENT failure sanitizer now admits only the closed bounded `candidate_generation_failure` diagnostic envelope, preserving fixed reason vocabularies/counts/generations and false authority claims while dropping source/generated content, diffs, exception text, provider payloads, credentials, environment values and any true mutation/lineage/Git/deployment/REVIEW claim.

Validated release and deployment evidence:

- protected DSPy spec preparation run `33429823111`: SUCCESS;
- focused implementation run `33430746804`: SUCCESS, including 23 focused convergence/preflight/activation regressions;
- architecture validation run `33431116950`: SUCCESS;
- exact green PR head: `ce8b05ee697ce2ad987f1ebb73b1f207a141e6fd`;
- PR Bounded Autonomy Pilot `33431252351`: SUCCESS;
- PR Workstream Spec Validation `33431252363`: SUCCESS;
- PR Parallax P2 CI `33431252314`: SUCCESS;
- squash merge / exact application source: `a5346ee8da6f6b38e09f678a00fe1f973edd79a0`;
- post-merge Workstream Spec Validation `33432401374`: SUCCESS, including changed-spec protected plan evidence;
- post-merge Parallax P2 CI `33432401421`: SUCCESS, including full API regression, client checks, protected promotion evaluation, and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production API deployment `dpl_4DjbFpezU1NGJNsiCKXNRqbA7DA2`: target production, state `READY`, exact application source, canonical alias `parallax-api-tan.vercel.app`;
- backend-only production client attempt `dpl_AQ2qoQxiLjFhuWUow38cyWe6EAjW` was canceled/ignored by path-aware Vercel deployment logic, so the prior READY client remains authoritative;
- production build preflights passed provider registration/private Blob and exact delivery-permission checks before the deployment became READY;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact API deployment warning/error/fatal runtime scan after readiness was clean.

Deployment verification is complete. Workstream #530 remains open only for its final authenticated real-path acceptance: retry Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc` (or equivalent exact work) through the normal signed-in product path. Acceptance requires the run to enter disposable BUILD after plan-prefix-aware convergence, or to expose a still-later bounded blocker while preserving the new sanitized `candidate_generation_failure` evidence. This evidence must not be manufactured by bypassing user authentication or session ownership.

No model/provider/credential addition, retry-budget increase, hosted timeout increase, hidden provider retry, direct model filesystem authority, source-lineage authority expansion, Git/deployment authority expansion, lifecycle-transition authority expansion, automatic REVIEW completion, or queue redesign was added.

"""
if section not in text:
    text = text.replace(anchor, section + anchor, 1)

path.write_text(text)
