# Parallax 2.0 Current State

Release: Wave 4 Live Development stabilization is deployment-verified. The production API/runtime recovery is complete, the Warm Editorial client stabilization remains deployed, and a fresh real Project-bound autonomous production proof advanced through protected IMPLEMENT/BUILD/TEST/VERIFY to the explicit REVIEW/HUMAN_REQUIRED boundary with persisted exact-lineage GitHub/Vercel Preview delivery evidence.
Date: 2026-08-25
Status: **WAVE 4 PRODUCTION DEPLOYED / LIVE OBSERVABILITY ACTIVE / STABILIZATION VERIFIED / END-TO-END AUTONOMOUS PRODUCTION READINESS RESTORED / HUMAN REVIEW BOUNDARY PRESERVED / PREVIOUS API RELEASE RETAINED AS ROLLBACK CANDIDATE / SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**

## Current production truth

The deployment-verified production API/runtime binary is Vercel deployment `dpl_2L4R6g3em7LJc7XWdRp5rueGFRK1` from repository application head `main@62012c9017953945aa55d35550800347ed9f8007` (PR #212, Vercel Preview REST contract recovery). It is `READY`, mapped to `parallax-api-tan.vercel.app`, and post-cutover checks on 2026-08-25 confirmed:

- `/health` = HTTP 200 / `status=ok`;
- `/ready` = HTTP 200 / `status=ready`, `database=ok`, `providers=ok`, one registered provider target;
- unauthenticated access to a protected API route = HTTP 401 / `Authentication required`;
- deployment-scoped `error`/`fatal` runtime-log query covering the final proof window returned no entries.

The application head passed exact post-merge Parallax P2 CI #873. The pre-merge exact candidate also passed Parallax P2 CI #872 and Bounded Autonomy #524 before PR #212 was integrated.

The production client remains Vercel deployment `dpl_AHKAix8J11knSfSCRzCupM6ND7vn` from `main@f61ba4f65ea108994dbda8f507bf079fac534145`, the Wave 4 stabilization promotion containing the validated #170-#174 visual/runtime convergence package. It is `READY` and owns the production aliases `parallax-lew7.vercel.app`, `parallax-ashy-one-20.vercel.app`, and `parallax-git-main-lew7.vercel.app`. Later recovery commits were API-only and were correctly ignored by the client project rather than replacing the deployed visual stabilization.

The immediately preceding known-good API production deployment `dpl_LYTeixMa2rfWDatzeSRL6wBAuaXj` from `main@d9069d264d7ca47e831634c663890abf7ee02da8` remains identified by Vercel as a rollback candidate. Routine rollback remains non-destructive and follows the existing flag-first/application-deployment policy.

This `CURRENT-STATE.md` update is a record-only repository change. It does not change the deployment-verified application/runtime binary SHA above and must not be treated as a new production application release solely because the documentation commit advances `main`.

## Wave 4 stabilization and recovery outcome

Control-tower issue #169 serialized the production recovery and visual convergence effort. The original bounded workers #170-#174 were integrated, followed by a sequence of narrow production-recovery workstreams that removed successive real bottlenecks without broadening authority: runtime credentials, projected repository bootstrap latency, durable lineage object persistence latency, bounded failure classification, canonical repository provenance/delta delivery, exact-lineage Sandbox transfer, and the current Vercel Preview REST contract.

The recovery preserved these invariants throughout:

- no PAT fallback or materially broader provider credential scope;
- no arbitrary shell, filesystem, Git, HTTP or provider proxy surface;
- no production Vercel target selection from the runtime delivery path;
- exact canonical Project/run/source-lineage identity;
- protected BUILD/TEST/VERIFY execution on the accepted lineage only;
- bounded/redacted evidence rather than unrestricted logs or hidden reasoning;
- idempotent provider publication and replay-safe source delivery;
- explicit REVIEW/HUMAN_REQUIRED as the autonomous ceiling;
- no merge or production promotion authority granted to App Builder delivery.

## Fresh production autonomous proof

The final target-affecting proof used a fresh approved Work Specification and fresh Project-bound Engineering Run against the deployed production API. The proof intentionally created one harmless client-root artifact so the *registered delivery target itself* had to build rather than allowing Vercel's ignored-build rule to cancel the required Preview.

Canonical proof identities:

- Engineering Run: `ec24bdb2-543a-44f0-9f85-713f8fc36ddc`;
- Work Specification: `7b93c74f-8fa3-41e2-8e65-be15478e87c9`;
- final run state: `REVIEW`;
- final run revision: `6`;
- final failure code: none;
- accepted lineage: `src:180aab7555a15b71c320d859b888abffe263ffd11b424255d3e92da9ba360e63`;
- accepted content digest: `8bd10931f3ecd89da34831a8c7d5d1f25f13ba954e3cbde36ddc6c35ea72f7b3`.

Persisted protected attempts all passed exactly once for `SPECIFY`, `PLAN`, `IMPLEMENT`, `BUILD`, `TEST`, and `VERIFY`. BUILD/TEST/VERIFY evidence remained Vercel-Sandbox-backed, deny-all, exact-lineage bound, non-persistent, and did not fall back to a fresh repository checkout.

Persisted run-event sequence 1-10 is ordered and contains:

1. `RUN_CREATED`;
2. successful `SPECIFY`;
3. successful `PLAN`;
4. successful `IMPLEMENT`;
5. successful `SOURCE_LINEAGE_ACCEPTED`;
6. successful `BUILD`;
7. successful `TEST`;
8. successful `VERIFY`;
9. `REVIEW_REQUIRED` with outcome `HUMAN_REQUIRED`;
10. one successful `SOURCE_DELIVERY`.

The final proof did not transition the run to COMPLETE and did not perform operator review.

## Exact source-delivery proof

The successful source-delivery record for the final run created exactly the bounded provider publication expected by the existing App Builder contract:

- GitHub branch: `parallax/b1f6984d-ec24bdb2`;
- exact accepted-lineage commit: `7190079f5fab333f2d899edf644260bd3c95ed99`;
- proof-only pull request: #214;
- registered Vercel Preview project: `prj_wLXC5JjjetJf0H97kncRlqczD3OC` (`parallax` client project);
- delivery-recorded Preview deployment: `dpl_6qRbvuJchvNs1fRPHCpkEdEY5wvZ`;
- Preview URL: `parallax-kjk5uto0v-lew7.vercel.app`;
- Preview target: null / Preview-only;
- Preview source branch: `parallax/b1f6984d-ec24bdb2`;
- Preview source SHA: `7190079f5fab333f2d899edf644260bd3c95ed99`;
- status at immediate durable delivery read-back: `QUEUED`;
- independently verified terminal Preview state: `READY`, with no alias error.

The runtime's immediate source-delivery contract remains unchanged: it creates the bounded Preview, performs one authenticated read-back, rejects terminal ERROR/CANCELED states, and persists bounded delivery evidence. Control Tower then independently verifies that same recorded deployment ID reaches READY before release readiness is restored. No polling state machine or authority expansion was introduced merely to make the release proof pass.

Proof-only App Builder PRs #214, #213 and #209 were closed without merge after their evidence was captured. Their source branches/commits and provider evidence remain available for audit, but none was promoted to `main` or production.

## Production activation state

- production run-event migration/table: **APPLIED / PRESENT**;
- production run-event RLS/direct-client protections: **VERIFIED**;
- production `PARALLAX_RUN_EVENTS_ENABLED=1`: **YES**;
- protected live-observability routes active: **YES**;
- Warm Editorial stabilization client deployed: **YES**;
- runtime credential recovery deployed: **YES**;
- projected source bootstrap recovery deployed: **YES**;
- durable lineage bootstrap recovery deployed: **YES**;
- canonical provenance/delta source delivery deployed: **YES**;
- exact-lineage Sandbox transfer recovery deployed: **YES**;
- current Vercel Preview REST contract recovery deployed: **YES**;
- exact production API health/readiness/auth checks: **PASS**;
- final fresh autonomous run through IMPLEMENT/BUILD/TEST/VERIFY: **PASS**;
- persisted REVIEW/HUMAN_REQUIRED boundary: **PASS**;
- persisted successful SOURCE_DELIVERY: **PASS**;
- delivery-recorded exact Vercel Preview independently READY: **PASS**;
- deployment-scoped error/fatal log check for final proof window: **PASS / NONE FOUND**;
- end-to-end autonomous production readiness: **RESTORED / DEPLOYMENT-VERIFIED**.

## Durable architecture, design and authority

`ARCHITECTURE.md` remains authoritative for the Vercel Functions runtime OIDC/Connect boundary, canonical Project/run/source-lineage/provider authority, durable execution, exact-lineage protected Sandbox model and observation semantics. No durable architecture change was required during this final proof closeout.

`DESIGN-SYSTEM.md` remains authoritative for the Warm Editorial Observatory design direction. No design-system change was required during the final runtime-recovery proof closeout; the deployed client already corresponds to the validated Wave 4 stabilization promotion.

`PROJECT-CONSTITUTION.md` v1.4 standing single-user production promotion authority remains active. No governance-policy change was required. Standing authority did not waive exact-head CI, protected evaluation, least privilege, rollback, deployment evidence or post-deploy verification.

Production capability claims continue to require deployment evidence plus a real functional proof for the claimed path. This Wave 4 stabilization state now satisfies that boundary for the protected autonomous development loop through operator REVIEW.