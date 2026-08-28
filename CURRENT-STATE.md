# Parallax 2.0 Current State

Date: 2026-08-28

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / WAVE 8 S1 DEPLOYMENT-VERIFIED / WAVE 8 S2 MAIN-MERGED AND PRODUCTION-DEPLOYED / W8-S2 PRODUCTION INFRASTRUCTURE HEALTHY / W8-S2 AUTHENTICATED OT TIME REPLAY PENDING / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Wave 8 S2 is validated, merged to `main`, and production-deployed to both the Parallax client and API. The changed production infrastructure is healthy and exact release identity is verified. Full W8-S2 defect verification remains intentionally open until the original OT Time Engineering Run, or an exact canonical authenticated equivalent, is retried through normal production authentication and is observed advancing beyond the prior missing-Preview-target PLAN failure.

Wave 8 S2 qualified worker head:

`97e95feadd2d49382563e9989cb282efdeda6192`

Wave 8 S2 application merge:

`ee1b502269f7b4367576a02cdaab45c763eb6717`

The release is governed by `P2-V0.21.1`. It separates exact repository/source readiness from hosting/Preview readiness: protected source bootstrap and PLAN no longer require a pre-registered Vercel Preview target, while Vercel Project discovery or bounded creation is deferred until verified Preview publication is actually required at the existing REVIEW boundary.

### Client

Current production client:

- application source: `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- production deployment: `dpl_533dbrSSkCtpoL7C3KQna7fRKpG3`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- target: `production`;
- state: `READY`;
- exact Git source: `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- aliases: `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, `parallax-git-main-lew7.vercel.app`;
- alias error: none.

W8-S2 client evidence:

- exact worker head `97e95feadd2d49382563e9989cb282efdeda6192` passed release-strength browser/Skia acceptance, including the mobile recovery path;
- the recovery acceptance deliberately injects one HTTP 503, proves saved run state remains visible, exposes technical evidence only on demand, retries the same durable run revision, and reaches REVIEW; the test distinguishes that expected 503 from any other browser error;
- production client root returns HTTP 200 after cutover;
- production dependency audit records 0 critical and 0 high production vulnerabilities. Ten moderate findings are in the Expo/tooling dependency chain; the automated remediation proposes a major Expo downgrade, so no destabilizing dependency rewrite was folded into this release.

Wave 8 S1 human-centered mobile/plain-language behavior remains intact and authoritative for ordinary product presentation.

### API

Current production API:

- application source: `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- production deployment: `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- target: `production`;
- state: `READY`;
- exact Git source: `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- aliases: `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, `parallax-api-git-main-lew7.vercel.app`;
- alias error: none.

W8-S2 API production evidence:

- `/health` returns HTTP 200 with service status `ok`;
- `/ready` returns HTTP 200 with database `ok`, providers `ok`, and one admitted provider target;
- exact production deployment error/fatal runtime scan after cutover is clean;
- unauthenticated `/v1/session` returns HTTP 401 `Authentication required`, proving release verification did not weaken or bypass normal application authentication;
- exact merge-head Parallax P2 CI #1310 / run `33219992941` — PASS;
- exact merge-head Workstream Spec Validation #604 / run `33219992943` — PASS.

The authenticated OT Time replay remains the final W8-S2 production acceptance proof. It is not replaced by an unauthenticated service bypass.

## Wave 8 — Human-centered product experience and dependable guided execution

Control Tower: #374

Entry baseline:

`main@392c187d16a55688861db276d7d2150767667f2f`

### W8-S1 — Mobile orientation, readable typography and plain-language UX

Workstream: #375

Release PR: #376

Final qualified worker head:

`2754926d65ac46f12cf9a31d31d07de37038b155`

Application release merge:

`a784af75fc3076a56f9d8e52ff529ca8302e9ce6`

Production deployment:

`dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`

W8-S1 is **ACCEPTED / MAIN-MERGED / CLIENT PRODUCTION-DEPLOYMENT-VERIFIED**.

The deployed client:

- uses a stable `Chat · Progress · Project` mobile navigation model;
- presents the user journey as `Define → Plan → Create → Check → Review` instead of engineering-first internal stage language;
- keeps current project, position, current activity and next meaningful action understandable without reconstructing state across screens;
- uses larger primary mobile typography and at least 44px primary touch targets;
- treats mobile as a guided control surface rather than a compressed desktop workspace;
- defaults ordinary mobile and desktop product copy to natural, outcome-oriented language;
- keeps raw IDs, internal states, failure codes, bindings and engineering evidence behind technical-detail or intentionally technical Live Build/Activity surfaces;
- preserves server-owned Project, Work Specification, Engineering Run, source, validation, provider, deployment and REVIEW authority;
- preserves mobile keyboard/composer behavior and authenticated account-control separation at phone width.

### W8-S2 — Automatic Project delivery readiness

Workstream: #377

Release PR: #379; draft PR #378 was superseded without changing implementation intent because the available GitHub ready-for-review mutation failed on an upstream unsupported GraphQL field.

Governing specification:

`P2-V0.21.1`

Final qualified worker head:

`97e95feadd2d49382563e9989cb282efdeda6192`

Application release merge:

`ee1b502269f7b4367576a02cdaab45c763eb6717`

Production deployments:

- client `dpl_533dbrSSkCtpoL7C3KQna7fRKpG3`;
- API `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p`.

W8-S2 is **ACCEPTED FOR RELEASE / MAIN-MERGED / PRODUCTION-DEPLOYED / INFRASTRUCTURE-VERIFIED / AUTHENTICATED DEFECT REPLAY PENDING**.

The deployed architecture now:

- lets exact Project-bound repository source bootstrap occur independently of Vercel Preview-target readiness;
- allows protected PLAN/IMPLEMENT/BUILD/TEST/VERIFY work to proceed without manual static Vercel target registration;
- defers Vercel target discovery or bounded Project creation until verified delivery at REVIEW;
- preserves existing statically registered targets without changing their accepted delivery path;
- verifies exact GitHub repository identity and exact Vercel team identity before admitting a dynamically discovered or created target;
- fails closed on duplicate targets, unbounded discovery, provider/configuration ambiguity, repository/team mismatch, auth denial, and read-back mismatch;
- reconciles concurrent Vercel Project creation by exact repository identity and proves no production deployment side effect before admitting the target;
- gives dynamic readiness no production promotion, merge, domain, environment-variable, deletion, credential-creation, source-acceptance-bypass, lifecycle-transition, or REVIEW-completion authority;
- presents recoverable failure in plain language while keeping technical evidence secondary;
- keeps client retry non-authoritative: it requests continuation of the same durable Engineering Run rather than fabricating progress.

Exact-head release qualification for `97e95feadd2d49382563e9989cb282efdeda6192` passed:

- Workstream Spec Validation #603;
- Bounded Autonomy Pilot #866;
- P2 CI #1309 API + contract tests;
- client typecheck/state/export;
- production dependency audit capture;
- browser/Skia acceptance including W8-S2 recovery;
- protected promotion and regression rejection;
- DSPy release compilation.

The earlier exact API implementation Preview `dpl_8zRAfa7tkhb8T1sdrdMZN99aiQ5C` was `READY` at implementation head `496f4e4401413e11fe2e2a0e85ce6b6e3776c7f0`. The final head differs from that API-qualified head only in the browser acceptance script that classifies the expected injected recovery 503; no API source changed after that Preview qualification.

## Wave 7 retained baseline

Wave 7 Control Tower: #347

Wave 7 final application release merge:

`703934871e4df0f63828c7fd6e33d3e6a86b60b1`

Wave 7 S1–S6 remain **ACCEPTED / INTEGRATED / MAIN-MERGED / CHANGED-COMPONENT PRODUCTION-DEPLOYMENT-VERIFIED**.

Wave 7 established and retains:

- ParallaxBench objective evaluation;
- Agent Run projection/control contract;
- Development Studio composition over canonical Engineering Run truth;
- bounded safe browser evidence;
- agentic observability/runtime economics/retention projection;
- integrated product proof across protected source, evaluation, browser, provider and REVIEW boundaries.

Wave 8 does not replace or weaken those runtime/authority contracts.

## Local-first model routing

`P2-V0.19.8` local-first routing remains production-deployed and unchanged.

Vercel production remains intentionally hosted-only. With no admitted local-first production configuration, hosted model escalation remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted-to-private inference remains a separate architecture/security/network/deployment workstream.

## Production database and safe deletion

Supabase production migration `20260827173141` (`safe_conversation_project_deletion`) remains active and additive/backward-compatible.

Logical conversation/Project deletion remains production-deployed and infrastructure-verified. User-visible deletion is workspace deletion, not protected-evidence purge. Work Specifications, Engineering Runs, attempts/events, accepted source lineage and immutable engineering/provider evidence remain retained; deleting a Project does not delete linked GitHub repositories, pull requests or Vercel deployments.

Remaining safe-deletion debt: final authenticated destructive-behavior smoke against a deliberately disposable production conversation/Project. Authentication will not be weakened and real user content will not be deleted merely to manufacture evidence.

Safe-deletion record PR #296 predates the newer Wave 8 state record and touches this file. It must be reconciled against current `main` before any later merge so older record text cannot overwrite newer production truth.

## Rollback

### Client

Current W8-S2 production client:

- application source `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- deployment `dpl_533dbrSSkCtpoL7C3KQna7fRKpG3`.

Immediate deployment-verified W8-S1 rollback reference:

- source `a784af75fc3076a56f9d8e52ff529ca8302e9ce6`;
- deployment `dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`.

### API

Current W8-S2 production API:

- application source `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- deployment `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p`.

Immediate fully deployment-verified Wave 7 rollback reference:

- source `703934871e4df0f63828c7fd6e33d3e6a86b60b1`;
- deployment `dpl_GSkdmZDyXoh2RUdoPjC2WCeHeJVi`.

W8-S2 adds no database migration. Rollback therefore does not require schema rollback. Any rollback must preserve canonical Project, Work Specification, Engineering Run and durable source-lineage records already written by production.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- parent integration/control record #31 serializes cross-wave release truth;
- app-builder roadmap #32 records program progression;
- Wave 7 Control Tower #347 governs the retained Wave 7 productization/runtime baseline;
- Wave 8 Control Tower #374 governs the human-centered UX/plain-language and guided execution program;
- every semantic AI/runtime change remains spec-first with stable acceptance IDs and authentic DSPy evidence;
- source readiness and hosting readiness are separate lifecycle concerns; provider infrastructure may not become an earlier lifecycle prerequisite merely because it will be required later;
- presentation may translate technical state into plain language but may not invent or conceal canonical state;
- deployment, integration, repository-record and production identities remain separate facts;
- no deployment-verification claim is valid without exact release identity and post-cutover evidence appropriate to the changed component.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks benchmark, model, agent, evaluator, routing, browser, observability or integrated-proof judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- client reconnect/continuation may request existing bounded server authority but cannot redefine canonical run truth;
- hosted production model transport remains server-owned and local-first remains rejected in Vercel production;
- browser tools cannot create unrestricted JavaScript/network, credential or destructive-action authority;
- absent economic evidence remains unknown, not zero;
- incomplete event evidence cannot be presented as complete observation;
- Preview remains the ordinary autonomous publication ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- logical workspace deletion cannot erase protected engineering/source/provider evidence;
- plain language may simplify presentation but may not hide failures, consequences, uncertainty, security boundaries or required human approval;
- source bootstrap may not require hosting/Preview readiness before the lifecycle actually needs publication;
- dynamic hosting readiness must derive from canonical server-owned Project/provider identity and fail closed on ambiguity;
- no deployment is recorded as deployment-verified without exact release identity and appropriate post-cutover evidence.

## Next governed implementation boundary

Wave 8 S1 is complete and deployment-verified. Wave 8 S2 code is released and production infrastructure is healthy; W8-S2 remains open only for its final authenticated production defect replay.

Immediate remaining boundaries are:

1. through a normal authenticated Parallax session, retry OT Time Engineering Run `af617b0b-5297-427c-a40d-90d58f59a20a` or an exact canonical equivalent and confirm it advances beyond the former missing-static-target PLAN failure without weakening authentication;
2. after that evidence, mark W8-S2 deployment-verified and close #377;
3. define the next Wave 8 slice under #374 before substantive implementation beyond S2;
4. complete safe deletion #290 only when a deliberately disposable authenticated production target is available;
5. reconcile safe-deletion record PR #296 against this newer `CURRENT-STATE.md` before merging it;
6. treat hosted-to-private inference from Vercel as a separate architecture/security/network/deployment workstream if later desired.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.5 — unchanged by W8-S2; Wave 8 S1's plain-language governing principle remains authoritative.
- `ARCHITECTURE.md` v3.13 — updated by W8-S2 to make source readiness and hosting readiness distinct lifecycle concerns and to bound dynamic Vercel Project readiness authority.
- `DESIGN-SYSTEM.md` v3.2 — unchanged by W8-S2; Wave 8 S1's human-centered mobile and content standard remains authoritative.
- `CURRENT-STATE.md` — updated after W8-S2 merge and production deployment to record exact source/deployment identities, release qualification, healthy production infrastructure, rollback references, dependency-audit status, the preserved authentication boundary, and the still-pending authenticated OT Time defect replay.