# Parallax 2.0 Current State

Date: 2026-08-28

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / WAVE 8 S1 DEPLOYMENT-VERIFIED / W8-S2 MAIN-MERGED + PRODUCTION-DEPLOYED + INFRASTRUCTURE-VERIFIED / OT TIME AUTHENTICATED RETRY OPEN / CLIENT READY / API READY / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Wave 8 S2 is validated, merged to `main`, production-deployed for both changed components, and infrastructure-verified. The final feature-level production proof remains intentionally open until the original authenticated OT Time Engineering Run is retried through the ordinary Parallax application boundary and advances beyond PLAN without the former missing-static-target failure.

Wave 8 S2 application merge:

`ee1b502269f7b4367576a02cdaab45c763eb6717`

Final qualified worker head:

`97e95feadd2d49382563e9989cb282efdeda6192`

Governing specification:

`P2-V0.21.1`

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

Wave 8 S2 client evidence:

- exact worker-head client Preview `dpl_5snYmwTHY4HYFFtdjSCKL8J6Wn3Y` at `97e95feadd2d49382563e9989cb282efdeda6192` — `READY`;
- production build completed and deployment completed successfully;
- production build errors-only scan contains no build failure;
- exact production deployment error/fatal runtime scan is clean;
- exact-head browser/Skia acceptance passed, including the W8-S2 recovery proof that preserves PLAN after a request-level readiness failure, hides raw evidence by default, exposes an accessible `Try again` action, and retries the same durable run revision through REVIEW;
- production dependency audit retained no high or critical production dependency vulnerability at the qualified implementation head.

### API

Current production API:

- application source: `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- production deployment: `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- target: `production`;
- state: `READY`;
- exact Git source: `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- production alias: `parallax-api-tan.vercel.app`;
- alias error: none.

Wave 8 S2 API production evidence:

- qualified API Preview `dpl_8zRAfa7tkhb8T1sdrdMZN99aiQ5C` at `496f4e4401413e11fe2e2a0e85ce6b6e3776c7f0` — `READY` with clean build/runtime scans;
- `496f4e4401413e11fe2e2a0e85ce6b6e3776c7f0 → 97e95feadd2d49382563e9989cb282efdeda6192` changed only the client W8-S2 browser acceptance script, so API bytes were unchanged across the final qualified worker-head correction;
- production provider preflight — PASS;
- production delivery-permission preflight — PASS;
- production projected-source preflight — PASS;
- production durable-lineage composition preflight — PASS;
- production agentic-runtime round-trip preflight — PASS;
- production projected-bootstrap/replay/process-recreation preflight — PASS;
- production execution-snapshot deny-all/offline-dependency preflight — PASS;
- production run-event schema guard — PASS;
- production build completed and deployment completed successfully;
- `GET https://parallax-api-tan.vercel.app/health` → HTTP 200;
- `GET https://parallax-api-tan.vercel.app/ready` → HTTP 200 with database `ok`, providers `ok`, and one statically registered provider target;
- exact production deployment error/fatal runtime scan is clean.

The readiness endpoint reporting one statically registered provider target is expected. W8-S2 does not pre-create every repository's Vercel Project during PLAN. For an unregistered canonical repository, exact Vercel Project discovery/creation is deferred until verified Preview delivery is actually required at the existing REVIEW boundary.

### W8-S2 remaining production proof

The original production defect target remains deliberately unmodified outside the canonical application flow:

- Project: `OT Time`;
- repository: `github:ryan9876/ot-time`;
- Engineering Run: `af617b0b-5297-427c-a40d-90d58f59a20a`;
- production database state after W8-S2 deployment verification: `PLAN`, revision `1`, no durable failure-code mutation.

Before W8-S2, authenticated autonomous continuation of that run returned HTTP 503 because source-delivery composition required a static Vercel Preview-target registration before PLAN could proceed.

The deployment connector cannot impersonate a Parallax application user or obtain the private application access credential. The production database will not be edited directly to manufacture success. Therefore W8-S2 is currently **production-deployed and infrastructure-verified, but final authenticated defect reproduction/retry verification remains open**.

Completion requires one ordinary authenticated retry of the same OT Time run (or an exact canonical equivalent) followed by evidence that:

1. the run advances beyond PLAN without `ProductionDeliveryConfigurationError` for a missing static Vercel target;
2. protected source/bootstrap and run-state evidence remain canonical;
3. any Vercel Project created later for Preview is the exact canonical repository/team target and creates no production deployment;
4. the run stops at the existing REVIEW/HUMAN_REQUIRED ceiling rather than gaining production authority.

## Wave 8 — Human-centered UX, plain-language experience and delivery readiness

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

W8-S1 remains **ACCEPTED / MAIN-MERGED / CLIENT PRODUCTION-DEPLOYMENT-VERIFIED**.

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

Release PR: #379. Draft PR #378 was superseded without merge because the available GitHub ready-for-review mutation failed on an upstream unsupported field; the replacement preserved the same branch implementation and exact-head validation path.

Governing spec:

`P2-V0.21.1`

Final qualified worker head:

`97e95feadd2d49382563e9989cb282efdeda6192`

Application release merge:

`ee1b502269f7b4367576a02cdaab45c763eb6717`

Production deployments:

- client `dpl_533dbrSSkCtpoL7C3KQna7fRKpG3` — `READY`;
- API `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p` — `READY`.

W8-S2 is **VALIDATED / MAIN-MERGED / PRODUCTION-DEPLOYED / INFRASTRUCTURE-VERIFIED / FINAL AUTHENTICATED OT TIME RETRY PENDING**.

W8-S2 now separates source readiness from hosting readiness:

- canonical GitHub source/bootstrap readiness is established immediately for the exact Project/run/repository;
- PLAN, IMPLEMENT, BUILD, TEST and VERIFY no longer require a pre-registered Vercel Preview target merely because hosting may be needed later;
- exact Vercel Project readiness is resolved only when verified Preview publication is needed at REVIEW;
- existing registered targets retain the established delivery path;
- an unregistered canonical repository may use only bounded server-owned Vercel list/read/create readiness against one admitted team/profile;
- GitHub stable repository identity and Vercel team/repository read-back must match exactly;
- discovery is bounded and ambiguity fails closed;
- creation/reconciliation verifies no production deployment side effect;
- readiness does not gain merge, production deployment/promotion, domain, environment-variable, credential-administration, deletion, source-acceptance-bypass, run-transition or REVIEW-completion authority;
- a failed autonomous request leaves the approved plan, canonical run and durable source truth intact, while client recovery copy explains what happened and offers retry without fabricating progress.

Exact-head release qualification on `97e95feadd2d49382563e9989cb282efdeda6192`:

- Workstream Spec Validation #603 / run `33219780087` — PASS;
- Bounded Autonomy Pilot #866 / run `33219780039` — PASS;
- Parallax P2 CI #1309 / run `33219780056` — PASS;
- full API regression — PASS;
- client typecheck/state/export — PASS;
- browser/Skia acceptance — PASS;
- protected promotion/regression evaluation — PASS;
- independent DSPy release compilation and protected-plan verification — PASS;
- exact client Preview — READY;
- applicable API Preview/content-equivalence qualification — PASS.

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

Stale record-only PR #296 was closed without merge after later authoritative `CURRENT-STATE.md` versions and workstream #290 already carried its infrastructure-verified/authenticated-smoke-pending truth. Workstream #290 remains open; its exact corrective merge/deployment evidence is preserved there.

## Rollback

### Client

Current W8-S2 production client:

- source `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- deployment `dpl_533dbrSSkCtpoL7C3KQna7fRKpG3`.

Immediate deployment-verified pre-W8-S2 client rollback reference:

- source `a784af75fc3076a56f9d8e52ff529ca8302e9ce6`;
- deployment `dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`.

### API

Current W8-S2 production API:

- source `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- deployment `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p`.

Immediate fully deployment-verified pre-W8-S2 API rollback reference:

- source `703934871e4df0f63828c7fd6e33d3e6a86b60b1`;
- deployment `dpl_GSkdmZDyXoh2RUdoPjC2WCeHeJVi`.

W8-S2 adds no database migration. Rollback does not require schema rollback. A rollback after W8-S2-created Preview Project containers would leave those provider containers intact rather than attempting destructive provider cleanup; they are not production deployments and remain bounded by canonical repository/provider identity.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- parent integration/control record #31 serializes cross-wave release truth;
- app-builder roadmap #32 records program progression;
- Wave 7 Control Tower #347 governs the retained Wave 7 productization/runtime baseline;
- Wave 8 Control Tower #374 governs the human-centered UX/plain-language and related governed productization program;
- every semantic AI/runtime change remains spec-first with stable acceptance IDs and authentic DSPy evidence;
- presentation may translate technical state into plain language but may not invent or conceal canonical state;
- deployment, integration, repository-record, infrastructure-verification and feature-level production-verification identities remain separate facts;
- no deployment-verification claim is valid without exact release identity and post-cutover evidence appropriate to the changed component/behavior.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks benchmark, model, agent, evaluator, routing, browser, observability or integrated-proof judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- source readiness and Preview-hosting readiness are separate concerns; absence of an early Preview target cannot itself redefine protected run state;
- dynamic Vercel readiness may establish only the exact bounded Preview Project container admitted by canonical Project/repository identity and cannot create production deployment authority;
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
- no feature is recorded as fully deployment-verified while a material authenticated production behavior gate remains outstanding.

## Next governed implementation boundary

W8-S1 is complete and deployment-verified. W8-S2 is merged, deployed and infrastructure-verified; its final authenticated production defect proof remains open.

Next actions, in order:

1. through the ordinary authenticated Parallax application, retry OT Time Engineering Run `af617b0b-5297-427c-a40d-90d58f59a20a` and capture durable run/provider evidence proving it advances beyond PLAN without the former missing-static-target error;
2. if that proof passes, reconcile this record from W8-S2 infrastructure-verified to fully deployment-verified and close #377 completed;
3. complete safe deletion #290 only when a deliberately disposable authenticated production target is available;
4. define any additional Wave 8 slice under #374 before substantive implementation;
5. treat hosted-to-private inference from Vercel as a separate architecture/security/network/deployment workstream if later desired.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.5 — unchanged by W8-S2; plain language remains the durable default product-language principle.
- `ARCHITECTURE.md` v3.13 — updated by W8-S2 to make source readiness independent of Preview-hosting readiness and to define the bounded exact-repository Vercel Project readiness authority/failure/retry contract.
- `DESIGN-SYSTEM.md` v3.2 — unchanged by W8-S2; the Wave 8 human-centered mobile/content standard remains authoritative.
- `CURRENT-STATE.md` — reconciled after W8-S2 production cutover to record exact validated worker head, merge, production deployments, release gates, post-cutover health/readiness/runtime evidence, rollback references, stale-record coordination, and the still-open authenticated OT Time retry boundary.