# Parallax 2.0 Current State

Date: 2026-08-28

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / W8-S1 DEPLOYMENT-VERIFIED / W8-S2 PRODUCTION INFRASTRUCTURE VERIFIED WITH AUTHENTICATED OT TIME REPLAY PENDING / W8-S3 DEPLOYMENT-VERIFIED / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Wave 8 S3 is validated, merged to `main`, and deployment-verified on both changed production surfaces. It completes the Wave 8 plain-language/readability correction across ordinary client, reduced-graphics, Project-selection, Progress, and server-originated public-message surfaces without changing canonical runtime authority.

W8-S3 final qualified worker head:

`7c21fe8ddc65d8a8931ccc4ac9c8e13b4bfd5b20`

W8-S3 application release merge:

`91be7cd9a7fa088f7cebd061d9f9147ac148282c`

W8-S2 remains independently production-deployed and infrastructure-verified. Its original authenticated OT Time defect replay is still pending and is not replaced by W8-S3 release evidence.

### Client

Current production client:

- application source: `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- production deployment: `dpl_CZuVyJKDHQuznvFgpdaBEuKzWtJe`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- target: `production`;
- state / ready state: `READY`;
- exact Git source: `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- Git source verification: verified;
- aliases: `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, `parallax-git-main-lew7.vercel.app`;
- alias error: none.

W8-S3 client evidence:

- exact final head `7c21fe8ddc65d8a8931ccc4ac9c8e13b4bfd5b20` passed P2 CI #1331 / run `33223747916`;
- Fast client checks passed typecheck, response-state tests, web export, production dependency audit capture, browser runtime install, and the full browser/Skia acceptance chain;
- the full browser chain includes the W8-S3 plain-language contract, normal visual behavior, 390px Wave 8 mobile UX, W8-S2 recovery, keyboard/composer clearance, governed scrolling, Project selection and fail-closed stale-Project behavior, canonical Code/Project binding, Google auth/session behavior, Engineering Run handoff, Live Build, and reduced-graphics parity;
- exact final-head Bounded Autonomy Pilot #885 / run `33223747944` passed client typecheck/state/export;
- exact final-head Preview `dpl_DiniY9XANBXm5QyQs582wVf6f1nF` was `READY`, source-pinned to `7c21fe8ddc65d8a8931ccc4ac9c8e13b4bfd5b20`, with alias error none and a clean build;
- production build completed successfully with no build failure;
- exact production deployment error/fatal runtime scan after cutover returned no matching logs;
- direct unauthenticated production client fetch redirects to Vercel SSO because deployment protection is enabled; that redirect is expected and is not treated as an application failure.

### API

Current production API:

- application source: `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- production deployment: `dpl_D2PAQhX7d2zzZbUZ8J4gAipzVu3M`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- target: `production`;
- state / ready state: `READY`;
- exact Git source: `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- Git source verification: verified;
- deployment aliases returned by Vercel: `parallax-api-lew7.vercel.app`, `parallax-api-git-main-lew7.vercel.app`;
- established production domain `parallax-api-tan.vercel.app` serves the post-cutover health/readiness checks.

W8-S3 API production evidence:

- exact final head `7c21fe8ddc65d8a8931ccc4ac9c8e13b4bfd5b20` passed P2 CI #1331 API + contract checks and the full API regression suite;
- exact final-head Bounded Autonomy Pilot #885 passed protected execution/autonomy tests and the full API regression suite;
- protected promotion evaluation passed Code, engineering, and Reason protected baselines plus regression-rejection checks;
- DSPy release compilation passed provider/local selection, SpecCritic + SpecCompiler execution, protected contract verification, status recording, and artifact upload;
- applicable API Preview `dpl_7AprkHGe26Xi9dRcP84rHKnpXYhj` was `READY` with the W8-S3 public-message route bytes; later final-head changes affected client/acceptance contracts while exact final-head API regression validated the combined tree;
- the exact production deployment completed all provider, delivery-permission, projected-source, Blob, lineage, agentic-runtime, projected-bootstrap, execution-snapshot, and run-event-schema preflights successfully before the production build completed;
- `https://parallax-api-tan.vercel.app/health` returns HTTP 200 with service status `ok`;
- `https://parallax-api-tan.vercel.app/ready` returns HTTP 200 with database `ok`, providers `ok`, and one admitted provider target;
- unauthenticated `/v1/session` returns HTTP 401 `Authentication required`, proving W8-S3 did not weaken or bypass normal application authentication;
- exact production deployment error/fatal runtime scan after cutover returned no matching logs.

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

W8-S1 established the durable presentation baseline:

- stable `Chat · Progress · Project` mobile navigation;
- `Define → Plan → Create → Check → Review` ordinary journey language;
- larger primary mobile typography and at least 44px primary touch targets;
- mobile as a guided control surface instead of a compressed desktop workspace;
- `Build plan` as the ordinary Work Specification label and `Progress` as the ordinary Engineering Run label;
- natural, outcome-oriented product copy by default;
- raw IDs, states, failure codes, bindings, provider/source evidence, and engineering detail remain secondary or intentionally technical;
- server-owned Project, Work Specification, Engineering Run, source, validation, provider, deployment, and REVIEW authority remain unchanged.

### W8-S2 — Automatic Project delivery readiness

Workstream: #377

Release PR: #379; draft PR #378 was superseded without changing implementation intent because the available GitHub ready-for-review mutation failed on an upstream unsupported GraphQL field.

Governing specification:

`P2-V0.21.1`

Final qualified worker head:

`97e95feadd2d49382563e9989cb282efdeda6192`

Application release merge:

`ee1b502269f7b4367576a02cdaab45c763eb6717`

Prior production deployments now retained as the immediate W8-S3 rollback references:

- client `dpl_533dbrSSkCtpoL7C3KQna7fRKpG3`;
- API `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p`.

W8-S2 is **ACCEPTED FOR RELEASE / MAIN-MERGED / PRODUCTION-DEPLOYED / INFRASTRUCTURE-VERIFIED / AUTHENTICATED DEFECT REPLAY PENDING**.

W8-S2 architecture retains these boundaries:

- exact Project-bound repository source bootstrap is independent of Vercel Preview-target readiness;
- protected PLAN/IMPLEMENT/BUILD/TEST/VERIFY work does not require manual static Vercel target registration;
- Vercel target discovery or bounded Project creation is deferred until verified delivery at REVIEW;
- existing statically registered targets keep their accepted delivery path;
- dynamic readiness verifies exact GitHub repository and Vercel team identity and fails closed on ambiguity, mismatch, duplicate targets, auth denial, or read-back mismatch;
- dynamic readiness has no production-promotion, merge, domain, environment-variable, deletion, credential-creation, source-acceptance-bypass, lifecycle-transition, or REVIEW-completion authority;
- client retry requests continuation of the same durable Engineering Run and cannot fabricate progress.

The authenticated OT Time replay remains the final W8-S2 production acceptance proof. A read-only production database check after W8-S2 cutover confirmed Engineering Run `af617b0b-5297-427c-a40d-90d58f59a20a` remains canonical `PLAN`, revision `1`, with `last_failure_code` unset. No direct database mutation was used to manufacture success; the next state change must occur through the normal authenticated Engineering Run API.

### W8-S3 — Plain-language completion across ordinary product surfaces

Workstream: #382

Release PR: #384; draft PR #383 was superseded without changing implementation intent because the available GitHub ready-for-review mutation failed on an upstream unsupported GraphQL field.

Governing presentation contracts:

- `P2-V0.20.3`;
- `PROJECT-CONSTITUTION.md` v1.5;
- `DESIGN-SYSTEM.md` v3.2.

Final qualified worker head:

`7c21fe8ddc65d8a8931ccc4ac9c8e13b4bfd5b20`

Application release merge:

`91be7cd9a7fa088f7cebd061d9f9147ac148282c`

Production deployments:

- client `dpl_CZuVyJKDHQuznvFgpdaBEuKzWtJe`;
- API `dpl_D2PAQhX7d2zzZbUZ8J4gAipzVu3M`.

W8-S3 is **ACCEPTED / MAIN-MERGED / CLIENT AND API PRODUCTION-DEPLOYMENT-VERIFIED**.

The deployed user experience now:

- uses natural root-shell fallback, empty, loading, completion, failure, and scope-change language;
- uses Ask/Build and Responding/Ready instead of raw Reason/Code and Live/Complete labels on ordinary surfaces;
- explains scope changes as `Your request changed`, with `Continue approved work` and `Start a new goal` where the approved-plan boundary allows them;
- removes shortened Project IDs and internal `reason/code` labels from ordinary desktop/mobile headers;
- keeps Project selection and conversation history understandable without requiring canonical-binding vocabulary while preserving exact Project ID behavior underneath;
- presents repository identity as familiar GitHub/repository context rather than provider-prefix syntax;
- removes protected-environment/run/build-flow jargon from ordinary Progress while keeping Engineering Run, Work Specification revision, bindings, states, failure codes, and evidence available in Technical details;
- applies the same natural-language/readability rules to the reduced-graphics fallback rather than treating degraded visual mode as exempt;
- replaces server-originated `Work Specification`, specification-amendment, model-provider/capacity, and protected-context-limit jargon with plain public messages while retaining machine-readable error codes, traces, phases, scope decisions, and `SPEC_AMENDMENT` authority;
- keeps the intentionally technical Activity/Live Build and Technical details surfaces precise.

W8-S3 release qualification:

- P2 CI #1331 / run `33223747916` — PASS;
- Bounded Autonomy Pilot #885 / run `33223747944` — PASS;
- full client browser/Skia acceptance — PASS;
- full API regression — PASS;
- protected promotion/regression rejection — PASS;
- DSPy release compilation — PASS;
- exact final-head client Preview `dpl_DiniY9XANBXm5QyQs582wVf6f1nF` — READY;
- client and API exact-merge production deployments — READY;
- post-cutover API health/readiness — PASS;
- post-cutover client/API error/fatal runtime scans — clean;
- unauthenticated API session boundary — preserved at HTTP 401.

W8-S3 expands presentation coverage only. It adds no endpoint, schema, event name, machine error code, persistence rule, model-routing rule, Project binding authority, source-lineage authority, Engineering Run lifecycle authority, merge authority, production-promotion authority, or REVIEW authority.

## Wave 7 retained baseline

Wave 7 Control Tower: #347

Wave 7 final application release merge:

`703934871e4df0f63828c7fd6e33d3e6a86b60b1`

Wave 7 S1–S6 remain **ACCEPTED / INTEGRATED / MAIN-MERGED / CHANGED-COMPONENT PRODUCTION-DEPLOYMENT-VERIFIED**.

Wave 7 continues to provide the retained runtime/productization baseline: ParallaxBench objective evaluation, Agent Run projection/control, Development Studio composition over canonical Engineering Run truth, bounded browser evidence, agentic observability/runtime economics/retention projection, and integrated proof across protected source, evaluation, browser, provider, and REVIEW boundaries.

Wave 8 does not replace or weaken those contracts.

## Local-first model routing

`P2-V0.19.8` local-first routing remains production-deployed and unchanged.

Vercel production remains intentionally hosted-only. With no admitted local-first production configuration, hosted model escalation remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted-to-private inference remains a separate architecture/security/network/deployment workstream.

## Production database and safe deletion

Supabase production migration `20260827173141` (`safe_conversation_project_deletion`) remains active and additive/backward-compatible.

Logical conversation/Project deletion remains production-deployed and infrastructure-verified. User-visible deletion is workspace deletion, not protected-evidence purge. Work Specifications, Engineering Runs, attempts/events, accepted source lineage, and immutable engineering/provider evidence remain retained; deleting a Project does not delete linked GitHub repositories, pull requests, or Vercel deployments.

Remaining safe-deletion debt: final authenticated destructive-behavior smoke against a deliberately disposable production conversation/Project. Authentication will not be weakened and real user content will not be deleted merely to manufacture evidence.

Stale safe-deletion record PR #296 remains closed without merge as superseded by later authoritative state records. Workstream #290 remains open and preserves the corrective merge/deployment evidence plus the still-pending authenticated destructive smoke.

W8-S3 adds no database migration.

## Rollback

### Client

Current W8-S3 production client:

- application source `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- deployment `dpl_CZuVyJKDHQuznvFgpdaBEuKzWtJe`.

Immediate deployment-verified W8-S2 rollback reference:

- source `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- deployment `dpl_533dbrSSkCtpoL7C3KQna7fRKpG3`.

Earlier W8-S1 rollback reference:

- source `a784af75fc3076a56f9d8e52ff529ca8302e9ce6`;
- deployment `dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`.

### API

Current W8-S3 production API:

- application source `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- deployment `dpl_D2PAQhX7d2zzZbUZ8J4gAipzVu3M`.

Immediate deployment-verified W8-S2 rollback reference:

- source `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- deployment `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p`.

Earlier fully deployment-verified Wave 7 rollback reference:

- source `703934871e4df0f63828c7fd6e33d3e6a86b60b1`;
- deployment `dpl_GSkdmZDyXoh2RUdoPjC2WCeHeJVi`.

W8-S3 changes presentation and public copy only and adds no schema migration. Rollback therefore requires no schema rollback. Any rollback must preserve canonical Project, Work Specification, Engineering Run, source-lineage, and protected evidence already written by production.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- parent integration/control record #31 serializes cross-wave release truth;
- app-builder roadmap #32 records program progression;
- Wave 7 Control Tower #347 governs the retained Wave 7 productization/runtime baseline;
- Wave 8 Control Tower #374 governs the human-centered UX/plain-language and guided execution program;
- every semantic AI/runtime change remains spec-first with stable acceptance IDs and authentic DSPy evidence;
- source readiness and hosting readiness are separate lifecycle concerns; provider infrastructure may not become an earlier lifecycle prerequisite merely because it will be required later;
- presentation may translate technical state into plain language but may not invent or conceal canonical state;
- deployment, integration, repository-record, and production identities remain separate facts;
- a record-only commit after this release does not replace application source `91be7cd9a7fa088f7cebd061d9f9147ac148282c` unless it actually changes and deploys application bytes;
- no deployment-verification claim is valid without exact release identity and post-cutover evidence appropriate to the changed component.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity, and accepted lineage remain server-owned;
- deterministic/protected validation outranks benchmark, model, agent, evaluator, routing, browser, observability, or integrated-proof judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- client reconnect/continuation may request existing bounded server authority but cannot redefine canonical run truth;
- hosted production model transport remains server-owned and local-first remains rejected in Vercel production;
- browser tools cannot create unrestricted JavaScript/network, credential, or destructive-action authority;
- absent economic evidence remains unknown, not zero;
- incomplete event evidence cannot be presented as complete observation;
- Preview remains the ordinary autonomous publication ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- logical workspace deletion cannot erase protected engineering/source/provider evidence;
- plain language may simplify presentation but may not hide failures, consequences, uncertainty, security boundaries, or required human approval;
- source bootstrap may not require hosting/Preview readiness before the lifecycle actually needs publication;
- dynamic hosting readiness must derive from canonical server-owned Project/provider identity and fail closed on ambiguity;
- no deployment is recorded as deployment-verified without exact release identity and appropriate post-cutover evidence.

## Next governed implementation boundary

Wave 8 S1 and W8-S3 are deployment-verified. W8-S2 code is released and production infrastructure is healthy; W8-S2 remains open only for its final authenticated production defect replay.

Immediate remaining boundaries are:

1. through a normal authenticated Parallax session, retry OT Time Engineering Run `af617b0b-5297-427c-a40d-90d58f59a20a` or an exact canonical equivalent and confirm it advances beyond the former missing-static-target PLAN failure without weakening authentication;
2. after that evidence, mark W8-S2 defect verification complete and close #377;
3. define any next Wave 8 slice under #374 before substantive implementation beyond W8-S3 rather than expanding authority implicitly;
4. complete safe deletion #290 only when a deliberately disposable authenticated production target is available;
5. treat hosted-to-private inference from Vercel as a separate architecture/security/network/deployment workstream if later desired;
6. handle Expo/tooling dependency findings as a bounded maintenance workstream rather than destabilizing the validated Wave 8 UX release with an unrelated major downgrade.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.5 — unchanged by W8-S3; Wave 8 S1's plain-language governing principle remains authoritative.
- `ARCHITECTURE.md` v3.13 — unchanged by W8-S3; W8-S2's source-readiness/hosting-readiness architecture and dynamic Vercel authority bounds remain authoritative.
- `DESIGN-SYSTEM.md` v3.2 — unchanged by W8-S3; Wave 8 S1's human-centered mobile/content standard already governs the S3 correction.
- `CURRENT-STATE.md` — updated after W8-S3 exact-head qualification, expected-head merge, separate client/API production deployment verification, post-cutover API health/readiness/authentication checks, and clean client/API runtime error scans. The W8-S2 authenticated OT Time replay and safe-deletion authenticated destructive smoke remain explicitly pending.