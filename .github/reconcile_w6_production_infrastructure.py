from __future__ import annotations

from pathlib import Path
import re


path = Path("CURRENT-STATE.md")
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    if old not in text:
        raise SystemExit(f"{label} anchor drifted")
    text = text.replace(old, new, 1)


replace_once(
    "Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE DELETION CORRECTIVE P2-V0.18.12 PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED / FINAL SAFE-DELETION ACCEPTANCE PENDING AUTHENTICATED POST-CUTOVER SMOKE / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S6 + W6-R1 #304 ACCEPTED AND INTEGRATED / CUMULATIVE RUNTIME-ACTIVATED WAVE 6 CHECKPOINT VALIDATED / WAVE 6 NOT DEPLOYED / PRODUCTION PROMOTION REQUIRES SEPARATE GOVERNED RELEASE + POST-CUTOVER PROOF**",
    "Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE DELETION CORRECTIVE P2-V0.18.12 PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED / FINAL SAFE-DELETION ACCEPTANCE PENDING AUTHENTICATED POST-CUTOVER SMOKE / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S6 + W6-R1 #304 PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED / PRODUCTION AGENTIC CANARY + DURABLE REPLAY PRECHECKS PASS / FINAL WAVE 6 RELEASE ACCEPTANCE PENDING AUTHENTICATED PROJECT-BOUND ENGINEERING RUN / #312 OPEN**",
    "status",
)

replace_once(
    "Production remains the deployment-verified Wave 5 generalized application-delivery platform plus the accepted stabilization chain through mobile #261/#262, response-stream #271/#272 and P2-V0.18.10 model transport.",
    "Production is cumulative through the Wave 6 API infrastructure activation on exact application source `main@831fef94aa1c94ff1178b1a325e8774d49fd8752`, while retaining the deployment-verified Wave 5 generalized application-delivery baseline and the accepted stabilization chain through mobile #261/#262, response-stream #271/#272, P2-V0.18.10 model transport and safe-deletion hardening. The client had no Wave 6 source delta and retains its prior verified production artifact under the existing path-aware ignored-build contract.",
    "production truth",
)

replace_once(
    "PR #294 merged to `main` as `109444dcd7e13bfe842dea71355607941258b073` after the exact corrective implementation head passed all required gates. Vercel deployed the corrective API SHA to production and the production alias is serving it. The client had no source delta, so its main deployment was intentionally canceled by the configured Ignored Build Step and the existing verified client artifact remains active.",
    "PR #294 merged to `main` as `109444dcd7e13bfe842dea71355607941258b073` after the exact corrective implementation head passed all required gates. Vercel deployed that corrective API SHA and it remained the verified API rollback artifact until the Wave 6 production cutover. The client had no source delta, so its main deployment was intentionally canceled by the configured Ignored Build Step and the existing verified client artifact remains active.",
    "safe-deletion production history",
)

wave_pattern = re.compile(
    r"Wave 6 S1-S6 plus runtime-activation closure W6-R1 are accepted development architecture and are \*\*not\*\* production deployments\..*?before Wave 6 can be called deployed or deployment-verified\.",
    re.DOTALL,
)
wave_truth = """Wave 6 S1-S6 plus runtime-activation closure W6-R1 are now **production-deployed and infrastructure-verified, but not yet release-verified**. The accepted W6-R1 worker `6244cefd8c7cc2dec923f815838e14747f47aef0` was integrated through `07f45319d166d52298b2b056cdab4c48c1accf25`, authoritative records were reconciled at `f55c07c188df7cd370d10a3f5478001a139061a0`, and the governed release sequence reached production through PR #313 plus bounded fail-closed corrections PR #315, PR #318 and PR #321. Exact production application source is `main@831fef94aa1c94ff1178b1a325e8774d49fd8752`; Vercel API deployment `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw` is READY and owns the production API aliases.

The server-owned `PARALLAX_AGENTIC_RUNTIME_ENABLED=1` activation is version-controlled with the release. Production pre-cutover proof passed provider/source, delivery-permission, projected-source, private Blob, durable lineage, exact selected-candidate artifact round-trip, projected bootstrap with engineering-runtime/process-recreation/replay/no-stage-mutation proofs, execution snapshot and run-event schema guards. `/health` and `/ready` are HTTP 200, unauthenticated protected access remains HTTP 401, and the exact deployment error/fatal scan is clean. The remaining #312 acceptance gate is deliberately not bypassed: an authenticated application principal must execute a disposable Project-bound Engineering Run through live agentic PLAN/IMPLEMENT, exact-lineage BUILD/TEST/VERIFY, Preview and REVIEW stop behavior."""
text, count = wave_pattern.subn(wave_truth, text, count=1)
if count != 1:
    raise SystemExit("Wave 6 current-truth anchor drifted")

production_block = """### Production API — Wave 6 infrastructure activation

- Vercel project: `parallax-api`;
- production deployment: `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw`;
- state: `READY`;
- target: `production`;
- exact application Git SHA: `831fef94aa1c94ff1178b1a325e8774d49fd8752`;
- public production alias: `parallax-api-tan.vercel.app`;
- activation: version-controlled `PARALLAX_AGENTIC_RUNTIME_ENABLED=1`.

Governed release/correction evidence:

- release candidate PR #313 exact head `3d90bbedfeca16a1d0dcf4e564dde6832fa0085d`; Workstream #498, Bounded #704 and full-release P2 CI #1109 — **PASS**;
- source-tree preflight parity PR #315 exact head `2843936d5dad69c57a26b6f4c293d27deb832c9c`; Bounded #708 and full-release P2 CI #1114 — **PASS**;
- direct-script source-root correction PR #318 exact head `cb7cb6f51f1eb2a86da39c3398d6fb4a19af437e`; Bounded #709 and full-release P2 CI #1116 — **PASS**;
- service-runtime dependency correction PR #321 exact head `ce55f9c4fabd82774954007483997b9d52878e2c`; Bounded #711 and full-release P2 CI #1119 — **PASS**;
- exact-head Vercel Preview for PR #321: `dpl_63ZxgWDYb7JKsRGeUetUy3VXkZzk` — **READY**.

Exact production build proof on `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw`:

- provider preflight PASS with 538 source-tree entries and private Blob read/write verification;
- delivery-permission preflight PASS for one exact repository target;
- projected-source preflight PASS with 492 lineage-eligible files / 5,013,766 UTF-8 bytes;
- durable lineage composition PASS with metadata rollback verification;
- Wave 6 selected-candidate artifact canary PASS with exact immutable round trip (`artifact=366be26db9bf…`);
- projected bootstrap PASS with engineering runtime, process recreation, replay, no-stage-mutation, metadata rollback and Project rollback verified;
- execution-snapshot preflight PASS with deny-all restore, offline dependencies and no repository source present;
- run-event schema guard PASS;
- `GET /health` → HTTP 200;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- unauthenticated `GET /v1/access/me` → HTTP 401 with `Authentication required`;
- exact deployment error/fatal runtime scan: no matching logs.

Release state: **DEPLOYED / INFRASTRUCTURE-VERIFIED / AUTHENTICATED RUNTIME SMOKE PENDING**. Earlier failed production attempts were fail-closed build-time probes and did not cut over the production alias. #312 remains open until the authenticated Project-bound Engineering Run is proven.

"""
marker = "### Safe-deletion release identity\n"
if production_block not in text:
    if marker not in text:
        raise SystemExit("safe-deletion release marker missing")
    text = text.replace(marker, production_block + marker, 1)

old_safe_api = """### Production API — corrective P2-V0.18.12

- Vercel project: `parallax-api`;
- production deployment: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `109444dcd7e13bfe842dea71355607941258b073`;
- public production alias: `parallax-api-tan.vercel.app`.

Post-cutover verification on the corrective deployment established:

- production alias is serving deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- `GET /health` → HTTP 200 with `status=ok`;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- exact corrective deployment runtime scan found no `error`/`fatal` records;
- unauthenticated `GET /v1/conversations` → HTTP 401 with `Authentication required`, confirming the protected route remains behind the authentication boundary.

The final authenticated destructive-behavior smoke is intentionally still open: the available deployment connector cannot present a Parallax application user session, and production verification must not be faked by weakening auth or deleting real user data without a deliberate test target.
"""
new_safe_api = """### Prior production API rollback — corrective P2-V0.18.12

- Vercel project: `parallax-api`;
- rollback deployment: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- state: `READY`;
- historical target: `production`;
- exact Git SHA: `109444dcd7e13bfe842dea71355607941258b073`;
- prior public alias: `parallax-api-tan.vercel.app` (now served by the Wave 6 production deployment).

Before Wave 6 cutover, post-cutover verification on this corrective deployment established HTTP 200 health/readiness, database/provider readiness, a clean exact-deployment error/fatal scan and HTTP 401 for unauthenticated protected access. It remains the immediate verified API rollback artifact.

The final authenticated destructive safe-deletion smoke remains intentionally open: the available deployment connector cannot present a Parallax application user session, and production verification must not be faked by weakening auth or deleting real user data without a deliberate test target.
"""
replace_once(old_safe_api, new_safe_api, "prior API production block")

old_identity = """Control Tower: #263.  
Authoritative integration branch: `integration/wave6-agentic-control-plane`.  
Current accepted runtime-activated integration head: `07f45319d166d52298b2b056cdab4c48c1accf25`.  
Current production baseline: `main@a455b223ad4707aa7fe2ccd3470a5e7640c40da2`.  
Wave 6 production deployment: **none**.  
Production activation flag state: **not claimed enabled**."""
new_identity = """Control Tower: #263.
Authoritative integration branch: `integration/wave6-agentic-control-plane`.
Accepted runtime-activated application integration head: `07f45319d166d52298b2b056cdab4c48c1accf25`.
Reconciled Wave 6 integration/record head: `f55c07c188df7cd370d10a3f5478001a139061a0`.
Current production application source: `main@831fef94aa1c94ff1178b1a325e8774d49fd8752`.
Wave 6 production API deployment: `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw` — **READY / INFRASTRUCTURE-VERIFIED**.
Production activation flag state: **enabled through version-controlled `PARALLAX_AGENTIC_RUNTIME_ENABLED=1`**.
Final Wave 6 release verification: **PENDING AUTHENTICATED PROJECT-BOUND ENGINEERING RUN**."""
replace_once(old_identity, new_identity, "Wave 6 identity")

release_evidence = """### Production release #312 evidence

- release candidate PR #313 exact head: `3d90bbedfeca16a1d0dcf4e564dde6832fa0085d`;
- qualified release merge: `a5c700762bcf8ebbd5605d7e5d47756bab10fb4e`;
- source-tree parity correction #314 / PR #315 merge: `8bd124244f9bb8175c417e4c4084cc15d9bea066`;
- API source-root correction #316 / PR #318 merge: `bafda5b3d42ca3662a075cefb8c83bd9b017392e`;
- service-runtime canary correction #319 / PR #321 exact worker: `ce55f9c4fabd82774954007483997b9d52878e2c`;
- production application merge: `831fef94aa1c94ff1178b1a325e8774d49fd8752`;
- final correction Bounded Autonomy #711 — **PASS**;
- final correction Parallax P2 CI #1119 — **PASS**, including browser/Skia, protected promotion evaluation and DSPy release compilation/protected-plan verification;
- production deployment: `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw` — **READY**;
- immediate API rollback: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex` at `109444dcd7e13bfe842dea71355607941258b073`;
- authenticated Project-bound Engineering Run smoke: **PENDING**.

"""
accepted_anchor = "### Accepted cumulative S1-S6 + W6-R1 evidence\n"
if release_evidence not in text:
    if accepted_anchor not in text:
        raise SystemExit("Wave 6 accepted evidence anchor missing")
    text = text.replace(accepted_anchor, release_evidence + accepted_anchor, 1)

replace_once(
    "8. #304 / W6-R1 Runtime Activation — **COMPLETE / VALIDATED / ACCEPTED / INTEGRATED / NOT DEPLOYED**.",
    "8. #304 / W6-R1 Runtime Activation — **COMPLETE / VALIDATED / ACCEPTED / INTEGRATED / PRODUCTION-DEPLOYED / INFRASTRUCTURE-VERIFIED / FINAL AUTHENTICATED RELEASE SMOKE PENDING**.",
    "W6-R1 semantic status",
)

old_gate = """### Next release gate

Wave 6 is **validated and integrated but not deployed**. The next action is a separate governed production-release candidate, not a merge of validation PR #275. Before production promotion Control Tower must:

1. reconcile the release candidate to the exact current production `main` head and resolve any intervening production changes without weakening Wave 6 contracts;
2. rerun required exact-head protected gates on the release candidate;
3. verify production prerequisites for durable source lineage, Vercel Sandbox, private selected-candidate artifacts, hosted model transport and source delivery;
4. explicitly authorize and configure `PARALLAX_AGENTIC_RUNTIME_ENABLED=1` only as part of the governed release;
5. merge/promote only the exact accepted release head;
6. verify production health/readiness plus an authenticated Project-bound Engineering Run that exercises agentic PLAN/IMPLEMENT, exact-lineage BUILD/TEST/VERIFY, Preview and REVIEW stop behavior;
7. verify replay/process recreation does not duplicate canonical mutation or Preview publication;
8. inspect exact-deployment logs/error signals and record rollback identities before calling Wave 6 deployment-verified."""
new_gate = """### Final release-verification gate

Wave 6 is **production-deployed and infrastructure-verified but not yet release-verified**. Infrastructure, durable replay prechecks, health/readiness and exact-deployment logs are green. The remaining #312 gate is intentionally application-authenticated and must not be replaced by a verification-only bypass.

Before closing #312 and calling Wave 6 release-verified:

1. authenticate through an existing production application bearer or authorized user session;
2. use a deliberately disposable Project-bound conversation with an approved Work Specification and valid repository/source binding;
3. execute the ordinary `/v1/engineering-runs/{run_id}/autonomous` path and prove live agentic PLAN/IMPLEMENT followed by exact-lineage BUILD/TEST/VERIFY, Preview publication and stop at REVIEW;
4. replay the same protected operation identity and confirm no duplicate canonical source mutation or duplicate Preview publication;
5. inspect run events, attempt evidence and accepted source lineage to prove canonical state/evidence consistency;
6. rescan the exact production deployment for runtime error/fatal signals after the smoke;
7. record the authenticated smoke identity/evidence, close #312 and reconcile this record from infrastructure-verified to release-verified.

No temporary auth bypass, synthetic owner endpoint, secret disclosure or weakening of REVIEW/Preview authority is permitted to satisfy this gate."""
replace_once(old_gate, new_gate, "Wave 6 release gate")

old_rollback = """### API

Corrective production API:

- deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- source `109444dcd7e13bfe842dea71355607941258b073`.

Previous #291 API rollback candidate:

- deployment `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP`;
- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

Pre-#291 accepted API reference remains `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9` at `e6fc6900239df436545318e6ab7f532d0d3789bc`.

Because migration `20260827173141` is additive, application rollback does not require an emergency down-migration. Do not drop deletion tombstones or partial uniqueness indexes while deletion data may depend on them."""
new_rollback = """### API

Current Wave 6 production API:

- deployment `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw`;
- application source `831fef94aa1c94ff1178b1a325e8774d49fd8752`;
- activation `PARALLAX_AGENTIC_RUNTIME_ENABLED=1` is version-controlled and rolls back with the application release identity.

Immediate pre-Wave-6 verified API rollback:

- deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- source `109444dcd7e13bfe842dea71355607941258b073`.

Previous #291 API rollback candidate remains `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP` at `a6d7a6fd4d556d5544ede9c43b93972a8c590011`. Pre-#291 accepted API reference remains `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9` at `e6fc6900239df436545318e6ab7f532d0d3789bc`.

Because migration `20260827173141` is additive, application rollback does not require an emergency down-migration. Do not drop deletion tombstones or partial uniqueness indexes while deletion data may depend on them."""
replace_once(old_rollback, new_rollback, "API rollback")

replace_once(
    "- `CURRENT-STATE.md` — updated after exact W6-R1 worker gates, integration merge and fresh cumulative integration-head validation to distinguish validated/integrated from deployed/deployment-verified state.",
    "- `CURRENT-STATE.md` — updated after the governed Wave 6 production release, bounded fail-closed production corrections, exact `main@831fef94aa1c94ff1178b1a325e8774d49fd8752` READY deployment and infrastructure/replay verification; authenticated Project-bound runtime smoke remains explicitly open.",
    "authoritative record note",
)

# Normalize trailing whitespace only on lines changed by this reconciliation.
# Existing historical Markdown hard-break spacing elsewhere remains untouched.
path.write_text(text, encoding="utf-8")
