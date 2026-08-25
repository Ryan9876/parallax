# Parallax 2.0 Current State

Release: Wave 4 Live Development is deployed; Wave 4 stabilization has now integrated all five recovery/convergence workstreams and passed the fully composed deterministic visual/runtime gate, but end-to-end autonomous production readiness remains suspended pending promotion and real post-cutover provider/runtime proof.
Date: 2026-08-24
Status: **WAVE 4 PRODUCTION DEPLOYED / LIVE OBSERVABILITY ACTIVE; ALL W4 STABILIZATION WORKERS ACCEPTED + INTEGRATED; FULLY COMPOSED VISUAL/RUNTIME GATE GREEN; RUNTIME CREDENTIAL FIX NOT YET DEPLOYED; END-TO-END AUTONOMOUS PRODUCTION READINESS NOT YET RE-VERIFIED; WAVE 3 API RELEASE RETAINED AS ROLLBACK CANDIDATE; SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**

## Current production truth

Wave 4 production API remains deployment `dpl_7gHytxPynJ3yoo2A51oZsyuDj8gM` from verified repository merge `main@8b5acd5c4042689d01317e7951695929e5ce44f9`. The production build completed its provider, projected-source, private Blob, lineage-composition, process-recreation/replay, rollback and run-event schema guards before publication. Live Observability remains active and the production `engineering_run_events` migration/table/RLS boundary remains verified.

A later real authenticated production user test exposed a production-blocking runtime defect: autonomous-run requests reached the production API and returned HTTP `503` with `source_bootstrap_failed stage=provider-repository error_class=ProviderActionFailed result_code=CREDENTIAL_UNAVAILABLE`. The defect occurs in the Vercel Functions runtime OIDC -> Vercel Connect -> repository-scoped GitHub credential path before substantive autonomous execution advances.

Workstream #170 corrected that runtime boundary and is integrated, but the correction is not yet deployed. Therefore deployment health and protected read availability are verified while **end-to-end autonomous production readiness is still not verified**.

The production client also remains on the earlier Wave 4 deployment and therefore does not yet contain the stabilization UI convergence now validated on `integration/w4-stabilization`.

The immediately preceding API deployment `dpl_2uiLj1VjJzvzZ26cAkkLzSTNxFez` from `main@e8d277de30a14b3ff1f288bcb22f651268031158` remains the ordered rollback candidate.

## Wave 4 stabilization integration

Control-tower issue #169 owns recovery and visual convergence on `integration/w4-stabilization`.

All bounded worker workstreams are now accepted and integrated:

- #170 / runtime credential recovery: **ACCEPTED + INTEGRATED** at `1f5b181da733c9cb440ad005dd579799e02ab421`;
- #171 / desktop shell convergence: **ACCEPTED + INTEGRATED** at `0ce8139347e9974f325fd29f80a915fa539713d3` after deterministic Project-selection/browser correction;
- #172 / Observability fidelity: **ACCEPTED + INTEGRATED** at `77fc19c013dedb0d552ab495e36bc8274fc9df90`;
- #173 / Live Build + mobile convergence: **ACCEPTED + INTEGRATED** at `d27fad3aee0557567c6fb2a19dc7fc5f357f2d63` after reconciliation onto #172;
- #174 / visual acceptance and release-proof gate: **ACCEPTED + INTEGRATED** at `534885e37aea6e42de1e1f480ce21d2e8f9738b5`.

The #174 package adds deterministic desktop/tablet/phone reference evidence, semantic clipping/overflow/layout assertions, accessibility/reduced-motion/reduced-graphics coverage, evidence-backed runtime-state fixtures, and a protected provider/runtime release proof that fails closed on `CREDENTIAL_UNAVAILABLE` and missing post-PLAN persisted evidence.

## Fully composed stabilization validation

After #174 integration, Control Tower created validation-only PR #186 with zero changed files and an exact-tree checkpoint matching `integration/w4-stabilization@534885e37aea6e42de1e1f480ce21d2e8f9738b5`.

`W4 Visual and Runtime Release Gate` run `32803015514` passed on the fully composed #170–#174 tree:

- Wave 4 spec/DSPy validation: **PASS**;
- release-proof self-test, including rejection of credential/observability failures: **PASS**;
- runtime/Observability/provider regression slice: **PASS**;
- client typecheck/state contracts: **PASS**;
- exact-head web export: **PASS**;
- inherited shell + Live Build browser acceptance: **PASS**;
- strict W4 material visual release gate: **PASS**;
- desktop/tablet/phone evidence artifact upload: **PASS**.

The earlier contextual-health rail clipping discovered by #174 no longer reproduces after #171 integration. The strict material gate was not weakened.

Evidence artifact: `w4-visual-release-evidence`, artifact `9547213147`, digest `sha256:46fe2564aec8aac0da13bd5a220784a96dcc15ea6d69bd1ff219995bea02fd16`.

The dispatch-only protected live provider/runtime proof was intentionally skipped in this deterministic validation because no authorized production-like API/run inputs were supplied. That proof remains mandatory after promotion/cutover before autonomous production readiness may be claimed.

## Release readiness boundary

Worker-level Wave 4 stabilization is complete. The remaining release work is integration/release authority, not another feature worker:

1. run the repository-wide exact-head release gates on the stabilization release candidate;
2. promote the validated stabilization release through the governed main/production path;
3. verify the new production `/ready` runtime Connect/OIDC check;
4. execute a fresh authenticated Project-bound autonomous run and prove repository bootstrap plus advancement beyond PLAN using persisted Observability/Live Build evidence;
5. inspect production runtime logs and client visual behavior;
6. update this record only after deployment evidence and the real functional proof establish the claimed production state.

Until those steps pass, Parallax production must not be described as restored for autonomous development, even though the stabilization source and deterministic visual/runtime release gates are green.

## Production activation state

- production run-event migration/table: **APPLIED / PRESENT**;
- production run-event RLS/direct-client protections: **VERIFIED**;
- production `PARALLAX_RUN_EVENTS_ENABLED=1`: **YES**;
- protected live-observability routes active: **YES**;
- #170 runtime credential correction integrated: **YES**;
- #170 runtime credential correction deployed: **NO**;
- desktop shell convergence integrated: **YES**;
- Observability fidelity integrated: **YES**;
- Live Build/mobile convergence integrated: **YES**;
- strict visual/release-proof gate integrated: **YES**;
- fully composed deterministic W4 visual/runtime gate: **PASS**;
- end-to-end autonomous production readiness re-verified after correction: **NO**.

## Durable architecture and authority

`ARCHITECTURE.md` v3.0 remains authoritative for the Vercel Functions runtime-OIDC/Connect boundary, Project/run/source-lineage/provider authority, durable execution and protected observation model.

`DESIGN-SYSTEM.md` remains authoritative for the Warm Editorial Observatory design direction. The stabilization implementation is now deterministically accepted against that family; production has not yet been updated to it.

`PROJECT-CONSTITUTION.md` v1.4 standing single-user production promotion authority remains active. It permits promotion of an already validated release without separate per-release approval while Parallax remains effectively single-user, but it does not waive exact-head CI, protected evaluation, migration order, rollback, least privilege, deployment evidence or post-deploy verification.

Production capability claims require deployment evidence plus a real functional proof for the claimed path. Source integration, a green Preview, health endpoints or route availability alone are not sufficient to claim end-to-end autonomous readiness.
