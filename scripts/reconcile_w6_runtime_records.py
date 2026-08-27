from pathlib import Path
import re

ARCH = Path("ARCHITECTURE.md")
STATE = Path("CURRENT-STATE.md")
arch = ARCH.read_text()
state = STATE.read_text()

if "Version: 3.8" not in arch:
    raise SystemExit("expected ARCHITECTURE v3.8 baseline")
arch = arch.replace("Version: 3.8", "Version: 3.9", 1)

anchor = "  ├─ integrated agentic reference proof + Wave 5 comparison\n"
if arch.count(anchor) != 1:
    raise SystemExit("unexpected system-shape anchor count")
arch = arch.replace(anchor, anchor + "  ├─ live agentic runtime activation + durable selected-candidate replay\n", 1)

old_overview = (
    "Wave 3 remains the deployment-verified app-builder execution architecture at the pre-production Wave 4 release boundary. "
    "Wave 4 Live Build/Observability source is integrated but production run-event persistence and protected observation remain explicitly migration/activation gated until release evidence records otherwise. "
    "Wave 5 generalized application delivery is deployment-verified. Wave 6 S1-S6 are accepted on the governed Wave 6 integration branch but are not production deployments. "
    "The release audit identified that ordinary Engineering Runtime composition does not yet activate the accepted S1-S5 agentic control plane, so runtime activation closure #304 / P2-V0.19.7 is required before any Wave 6 production promotion. "
    "Preview publication remains the ordinary autonomous provider ceiling; production merge/promotion remains outside ordinary autonomous Project execution."
)
new_overview = (
    "Wave 3 remains the deployment-verified app-builder execution architecture at the pre-production Wave 4 release boundary. "
    "Wave 4 Live Build/Observability source is integrated but production run-event persistence and protected observation remain explicitly migration/activation gated until release evidence records otherwise. "
    "Wave 5 generalized application delivery is deployment-verified. Wave 6 S1-S6 plus W6-R1 runtime activation are accepted on the governed Wave 6 integration branch but are not production deployments. "
    "W6-R1 attaches the accepted S1-S5 decision plane to the ordinary Engineering Runtime behind a server-owned activation switch while retaining the existing single-writer source-lineage, deterministic-validation, provider and REVIEW boundaries. "
    "Preview publication remains the ordinary autonomous provider ceiling; production merge/promotion remains outside ordinary autonomous Project execution and still requires separate release qualification."
)
if arch.count(old_overview) != 1:
    raise SystemExit("stale architecture overview not found")
arch = arch.replace(old_overview, new_overview, 1)

start = arch.find("## Wave 6 integrated reference proof\n")
end = arch.find("## Project-scoped tool authority\n", start)
if min(start, end) < 0:
    raise SystemExit("Wave 6 architecture anchors missing")
arch_section = '''## Wave 6 integrated reference proof

Wave 6 S6 composes the accepted S1-S5 protocol, orchestration, independent-evaluation, routing/economic and competition/synthesis evidence with existing protected worker/source/delivery evidence into one deterministic read-only reference proof. It is accepted on the governed Wave 6 integration branch and creates no independent execution or authority path.

The proof binds exact canonical Project ID, Engineering Run ID, Work Specification ID/revision/digest and stable acceptance IDs through S2 team/schedule identity, S3 candidate/evaluator policy, S4 routing evidence, S5 competition evidence, exact candidate/source-lineage identity and bounded verified Preview delivery evidence. Identity or lineage substitution fails closed.

Protected deterministic failure and `HUMAN_REQUIRED` take precedence over quality/economic/benchmark claims. A supported integrated proof requires a READY Preview, preserved correctness/safety/privacy/governance guardrails and a material Wave 5 comparison improvement on an appropriate fixture. Benchmark dimensions distinguish observed, unknown and incomparable state; missing values are never treated as free, fast or successful.

Proof/recovery fingerprints are deterministic and replay-safe. Bounded worker reassignment evidence may be included, but the proof itself cannot acquire a worker lease, mutate source, accept lineage, invoke providers, route spending, transition an Engineering Run, merge, production-deploy, approve release, complete REVIEW or resolve a protected human boundary. Safe serialization excludes source bytes, patches, credentials, raw provider payloads, prompts, hidden reasoning, arbitrary commands and arbitrary URLs.

## Wave 6 live runtime activation

W6-R1 / `P2-V0.19.7` activates the accepted Wave 6 control-plane decisions inside the ordinary protected Engineering Run composition. The route selects this composition only when the server-owned `PARALLAX_AGENTIC_RUNTIME_ENABLED` switch is enabled. Disabled mode preserves the pre-Wave-6 runtime. Enabled mode requires durable source lineage and fails closed rather than silently falling back to a second or ungoverned implementation path.

PLAN remains an `EngineeringRunService` transition. The live agentic planner emits the existing required `work_items` and `validation_checks` evidence while adding the deterministic server-owned team/work-graph decision bound to exact Project/run/Work Specification/acceptance identity. Operator-selected agents are not authority input. The smallest adequate admitted team is selected within S2 bounds; multiple agents by themselves do not justify candidate-competition spend.

Agent outputs remain labor/evidence. Selected proposal evidence enters the existing `ProtectedImplementationRuntime` and `SafeImplementationEngine`; only that runtime may validate the protected workspace, advance immutable source lineage through compare-and-swap, and hand the accepted exact lineage to BUILD/TEST/VERIFY. S3 deterministic-validation precedence, S4 routing eligibility, S5 candidate selection, provider limits, Preview ceiling and REVIEW/HUMAN_REQUIRED boundaries remain unchanged.

The live control plane binds S2 dispatch to the accepted durable worker execution/lease/checkpoint/recovery contract. Recoverable process loss may reassign only after the prior lease is expired or durable recovery state explicitly admits reassignment, and the new lease generation becomes the only accepted generation. A competing active worker fails closed rather than being taken over.

After candidate selection, Parallax persists the exact selected generation as a private immutable content-addressed candidate artifact and checkpoints the worker as `READY_FOR_INTEGRATION`, releasing the worker mutation lease. Process recreation may replay that exact candidate only when Project, run, Work Specification revision/digest, acceptance set, plan, base source lineage, base revision and source-context digest all still match and the proposal still passes current protected workspace validation. Drift, tampering, stale authority claims or missing durable evidence fail closed. Candidate replay does not accept source lineage, transition the Engineering Run, complete REVIEW or deploy production.

The ordinary source-lineage and provider idempotency boundaries remain authoritative after replay. A restored selected candidate therefore cannot duplicate canonical mutation or Preview publication merely because the API process was recreated.

'''
arch = arch[:start] + arch_section + arch[end:]
ARCH.write_text(arch)

status = "Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE DELETION CORRECTIVE P2-V0.18.12 PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED / FINAL SAFE-DELETION ACCEPTANCE PENDING AUTHENTICATED POST-CUTOVER SMOKE / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S6 + W6-R1 RUNTIME ACTIVATION ACCEPTED AND INTEGRATED / EXACT INTEGRATION HEAD 07F45319 VALIDATED / WAVE 6 NOT DEPLOYED / AUTHORITATIVE RECORDS RECONCILED / PRODUCTION PROMOTION BLOCKED PENDING SEPARATE RELEASE QUALIFICATION + GOVERNED PROMOTION**"
state, n = re.subn(r"^Status: \*\*.*?\*\*$", status, state, count=1, flags=re.MULTILINE)
if n != 1:
    raise SystemExit("status replacement failed")

truth = '''Wave 6 S1-S6 plus W6-R1 runtime activation are accepted/integrated development architecture and are **not** production deployments. W6-R1 exact worker head `6244cefd8c7cc2dec923f815838e14747f47aef0` passed Workstream Spec Validation #492, Bounded Autonomy #699 and P2 CI #1103 (`781 passed, 1 skipped`; client checks also passed). PR #306 merged that exact head into `integration/wave6-agentic-control-plane` as `07f45319d166d52298b2b056cdab4c48c1accf25`. Fresh integration-head Workstream #493, Bounded Autonomy #700 and P2 CI #1104 all passed. Validation-only PR #308 was closed without merge to `main`.

Ordinary `EngineeringRuntimeComposition` can now activate the accepted agentic decision plane under the server-owned `PARALLAX_AGENTIC_RUNTIME_ENABLED` switch. Disabled mode preserves the existing runtime. Enabled mode requires durable source lineage; PLAN preserves the protected evidence contract, agent candidates remain non-authoritative until selected, selected evidence still enters the existing safe IMPLEMENT/source-lineage boundary, durable worker recovery gates dispatch/reassignment, and process recreation can replay only an exact immutable selected-candidate artifact whose protected bindings still match. Preview remains the autonomous provider ceiling and REVIEW/HUMAN_REQUIRED remain protected boundaries.

Production remains unchanged at `main@a455b223ad4707aa7fe2ccd3470a5e7640c40da2`. This record reconciles the completed W6-R1 integration state; it does not authorize or imply deployment. Wave 6 production promotion remains blocked pending a separate exact-head release-qualification decision and governed production promotion/verification.
'''
pattern = re.compile(r"Wave 6 S1-S6 are accepted development architecture and are \*\*not\*\* production deployments\..*?No Wave 6 production promotion is authorized until that closure is integrated and release-qualified\.\n", re.DOTALL)
state, n = pattern.subn(truth, state, count=1)
if n != 1:
    raise SystemExit("production truth replacement failed")

start = state.find("## Wave 6 — Agentic Development Control Plane\n")
end = state.find("## Rollback\n", start)
if min(start, end) < 0:
    raise SystemExit("Wave 6 state anchors missing")
state_section = '''## Wave 6 — Agentic Development Control Plane

Control Tower: #263.  
Authoritative integration branch: `integration/wave6-agentic-control-plane`.  
Current accepted integration head: `07f45319d166d52298b2b056cdab4c48c1accf25`.  
Current production baseline: `main@a455b223ad4707aa7fe2ccd3470a5e7640c40da2`.  
Wave 6 production deployment: **none**.

### Accepted cumulative S1-S6 foundation

1. #264 / S1 Agent Adapter & Evidence Protocol — **COMPLETE / ACCEPTED / INTEGRATED**;
2. #265 / S2 Dynamic Development Team Orchestration — **COMPLETE / ACCEPTED / INTEGRATED**;
3. #266 / S3 Independent Evaluation & Quality Judgment — **COMPLETE / ACCEPTED / INTEGRATED**;
4. #267 / S4 Outcome Routing & Development Economics — **COMPLETE / ACCEPTED / INTEGRATED**;
5. #281 repository source-tree capacity prerequisite — **COMPLETE / ACCEPTED / INTEGRATED**;
6. #268 / S5 Candidate Competition & Synthesis — **COMPLETE / ACCEPTED / INTEGRATED**;
7. #269 / S6 Agentic Development Integrated Reference Proof — **COMPLETE / ACCEPTED / INTEGRATED**.

The cumulative S1-S6 integration checkpoint before runtime activation was `01dda9f0328ca3f6ce2cf31f9c236c4603cef638`. S6 exact worker gates Workstream #485, Bounded Autonomy #692 and P2 CI #1096 passed, followed by cumulative integration Workstream #486, Bounded Autonomy #693 and P2 CI #1097. Temporary main-targeted validation PR #302 closed without merge.

### W6-R1 runtime activation closure — #304 / P2-V0.19.7

W6-R1 is **IMPLEMENTED / VALIDATED / INTEGRATED**.

- approved specification: `P2-V0.19.7` with stable AC-01..AC-10;
- authentic DSPy SpecCritic + SpecCompiler evidence: run `33111365094`;
- exact compiled plan committed at `specs/compiled/P2-V0.19.7.plan.json`;
- pre-semantic protected `--require-dspy` gate: run `33111782426` — **PASS**;
- exact validated implementation head: `6244cefd8c7cc2dec923f815838e14747f47aef0`;
- canonical PR #306: **MERGED TO INTEGRATION ONLY**;
- resulting integration head: `07f45319d166d52298b2b056cdab4c48c1accf25`;
- worker Workstream Spec Validation #492 — **PASS**;
- worker Bounded Autonomy Pilot #699 — **PASS**;
- worker Parallax P2 CI #1103 — **PASS** (`781 passed, 1 skipped`);
- fresh integration Workstream Spec Validation #493 — **PASS**;
- fresh integration Bounded Autonomy Pilot #700 — **PASS**;
- fresh integration Parallax P2 CI #1104 — **PASS**;
- validation-only PR #308: **CLOSED WITHOUT MERGE TO MAIN**.

### Integrated runtime behavior

The ordinary protected Engineering Run path now has a server-owned Wave 6 activation composition. `PARALLAX_AGENTIC_RUNTIME_ENABLED` is the sole runtime switch: disabled mode retains the existing composition; enabled mode requires durable lineage and fails closed rather than falling back to an alternate writer.

PLAN records a deterministic server-owned team/work-graph decision while retaining the existing required PLAN evidence. Agent results remain proposal/evidence only. Selected candidates still pass through `ProtectedImplementationRuntime`, the safe patch engine and durable source-lineage compare-and-swap before exact-lineage BUILD/TEST/VERIFY. Controller evidence is bounded and cannot claim Engineering Run transition, source acceptance, REVIEW completion or deployment authority.

S2 dispatch is bound to durable worker leases/checkpoints/recovery. Expired process ownership may reassign only through the accepted recovery state and a new lease generation; competing active ownership fails closed. Multi-agent team selection does not itself trigger extra candidate competition spend.

The selected candidate is persisted as an immutable private content-addressed artifact before worker transition to `READY_FOR_INTEGRATION`. Process recreation may restore that exact candidate only if Project/run/spec/acceptance/plan/base-lineage/base-revision/source-context bindings still match and current protected proposal validation succeeds. Replay never bypasses canonical lineage acceptance or provider idempotency.

### Release state

Wave 6 remains **not deployed**. W6-R1 closed the material runtime-activation defect found by the release audit. This authoritative record reconciliation establishes the durable project truth at the exact validated integration state. The next gate is a separate release qualification against the reconciled integration head, followed only then by an explicit governed production-promotion decision and post-cutover verification.

No W6-R1 result grants autonomous production promotion, production merge, REVIEW completion or expansion of provider/model/credential authority.

'''
state = state[:start] + state_section + state[end:]
STATE.write_text(state)
