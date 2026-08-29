# Parallax 2.0 Current State

Date: 2026-08-28

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / W8 IMPLEMENTATION COMPLETE / W8-S1 + W8-S3 + W8-S4 DEPLOYMENT-VERIFIED / W8-S2 PRODUCTION INFRASTRUCTURE VERIFIED WITH AUTHENTICATED OT TIME REPLAY PENDING / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Wave 8 S4 is validated, merged to `main`, and client production-deployment-verified. It completes the planned Wave 8 human-centered implementation by giving desktop and mobile one deterministic, plain-language answer to **what Parallax is doing and what the user should do next**, derived only from existing conversation / Build plan / Engineering Run truth.

W8-S4 final qualified worker head:

`2b5a01212a4d3c3ddc1c0302c113512412259079`

W8-S4 application release merge:

`17b62ec2649224e2beeacd6c9b2ce23d01af8028`

W8-S2 remains independently production-deployed and infrastructure-verified. Its original authenticated OT Time defect replay is still pending and is not replaced by W8-S3 or W8-S4 release evidence. Wave 8 therefore has no further planned implementation slice, but its control remains open until that authenticated acceptance debt is resolved or explicitly dispositioned.

### Client

Current production client:

- application source: `17b62ec2649224e2beeacd6c9b2ce23d01af8028`;
- production deployment: `dpl_BAbUpv63PUFxmCHM6JDDkf2SsFNJ`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- target: `production`;
- state / ready state: `READY`;
- exact Git source: `17b62ec2649224e2beeacd6c9b2ce23d01af8028`;
- Git source verification: verified;
- aliases: `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, `parallax-git-main-lew7.vercel.app`;
- alias error: none.

W8-S4 client evidence:

- exact final head `2b5a01212a4d3c3ddc1c0302c113512412259079` passed P2 CI #1361 / run `33228221750`;
- Fast client checks passed typecheck, response-state tests, deterministic S4 workflow-guidance state tests, web export, production dependency audit capture, and the complete browser/Skia acceptance chain;
- the S4 browser contract proved desktop guidance precedes detailed Build plan / Progress, the utility rail remains secondary, desktop and 390px mobile guidance are semantically equivalent, technical identities remain hidden from ordinary guidance, desktop CTA height is at least 44px, mobile CTA height is at least 48px, and no browser errors were observed;
- cumulative browser acceptance retained W8-S3 plain language, normal/reduced-graphics parity, W8-S2 recovery, keyboard/composer clearance, governed scrolling, Project selection, canonical Project/Build binding, auth/session, Engineering Run handoff, and Live Build behavior;
- exact final-head Workstream Spec Validation #632 / run `33228221801` passed changed-spec contract and committed DSPy-plan validation;
- exact final-head Bounded Autonomy Pilot #913 / run `33228221792` passed client type/state/export and full API/protected regression coverage;
- exact final-head Preview `dpl_Fj9JKuQdy4nkxrVjUdXzNF1WRE22` was `READY`, source-pinned to `2b5a01212a4d3c3ddc1c0302c113512412259079`, with alias error none;
- expected-head merge produced application source `17b62ec2649224e2beeacd6c9b2ce23d01af8028`;
- exact production deployment `dpl_BAbUpv63PUFxmCHM6JDDkf2SsFNJ` is `READY`, source-pinned to the merge commit, with all expected production aliases attached;
- production errors-only build inspection shows a successful completed build;
- exact production deployment error/fatal runtime scan after cutover returned no matching logs;
- authenticated Vercel fetch of `parallax-ashy-one-20.vercel.app` returned HTTP 200 and the Parallax 2.0 application shell.

### API

Current production API remains the deployment-verified W8-S3 application:

- application source: `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- production deployment: `dpl_D2PAQhX7d2zzZbUZ8J4gAipzVu3M`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- target: `production`;
- state / ready state: `READY`;
- exact Git source: `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- established production domain: `parallax-api-tan.vercel.app`.

W8-S4 changed no API/runtime/provider/database/source-lineage implementation files. The main-merge API deployment attempt `dpl_7DHdsKtF1SYPmMpobRV71TC3FJ4o` was path-aware `CANCELED`, so it did **not** replace the verified API application identity above. Exact S4 qualification nevertheless retained full API regression, protected promotion/regression rejection, DSPy release compilation, and Bounded Autonomy coverage against the combined source tree.

Retained W8-S3 API production evidence remains valid:

- `https://parallax-api-tan.vercel.app/health` returns HTTP 200 with service status `ok`;
- `https://parallax-api-tan.vercel.app/ready` returns HTTP 200 with database/providers ready;
- unauthenticated `/v1/session` returns HTTP 401 `Authentication required`;
- post-cutover error/fatal runtime scan for the deployed W8-S3 API was clean.

## Wave 8 — Human-centered product experience and dependable guided execution

Control Tower: #374

Entry baseline:

`main@392c187d16a55688861db276d7d2150767667f2f`

Wave 8 implementation is complete through S4. No W8-S5 is planned. The control remains open only because W8-S2 still requires a normal authenticated production replay of its original defect case.

### W8-S1 — Mobile orientation, readable typography and plain-language UX

Workstream: #375

Release PR: #376

Application release merge:

`a784af75fc3076a56f9d8e52ff529ca8302e9ce6`

Production deployment:

`dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`

W8-S1 is **ACCEPTED / MAIN-MERGED / CLIENT PRODUCTION-DEPLOYMENT-VERIFIED**.

W8-S1 established:

- stable `Chat · Progress · Project` mobile navigation;
- `Define → Plan → Create → Check → Review` ordinary journey language;
- readable primary typography and at least 44px primary touch targets;
- mobile as a guided control surface rather than a compressed desktop workspace;
- `Build plan` and `Progress` as ordinary labels for technical Work Specification / Engineering Run concepts;
- progressive disclosure of IDs, states, failure codes, bindings, provider/source evidence and engineering detail;
- unchanged server-owned lifecycle and authority.

### W8-S2 — Automatic Project delivery readiness

Workstream: #377

Release PR: #379; draft PR #378 was superseded without changing implementation intent because the available GitHub ready-for-review mutation failed on an upstream unsupported GraphQL field.

Governing specification:

`P2-V0.21.1`

Application release merge:

`ee1b502269f7b4367576a02cdaab45c763eb6717`

W8-S2 is **ACCEPTED FOR RELEASE / MAIN-MERGED / PRODUCTION-DEPLOYED / INFRASTRUCTURE-VERIFIED / AUTHENTICATED DEFECT REPLAY PENDING**.

Retained architecture boundaries:

- exact Project-bound repository source bootstrap is independent of Vercel Preview-target readiness;
- protected PLAN/IMPLEMENT/BUILD/TEST/VERIFY work does not require manual static Vercel target registration;
- Vercel target discovery or bounded Project creation is deferred until verified delivery at REVIEW;
- dynamic readiness derives from canonical server-owned repository/team identity and fails closed on ambiguity, mismatch, duplicate targets, auth denial, or read-back mismatch;
- dynamic readiness has no production-promotion, merge, domain, environment-variable, deletion, credential-creation, source-acceptance-bypass, lifecycle-transition, or REVIEW-completion authority;
- client retry requests continuation of the same durable Engineering Run and cannot fabricate progress.

The authenticated OT Time replay remains the final W8-S2 production acceptance proof. Read-only production evidence confirmed Engineering Run `af617b0b-5297-427c-a40d-90d58f59a20a` remains canonical `PLAN`, revision `1`, with `last_failure_code` unset. No direct database mutation or authentication bypass will be used to manufacture success.

### W8-S3 — Plain-language completion across ordinary product surfaces

Workstream: #382

Release PR: #384

Application release merge:

`91be7cd9a7fa088f7cebd061d9f9147ac148282c`

Production deployments:

- client `dpl_CZuVyJKDHQuznvFgpdaBEuKzWtJe`;
- API `dpl_D2PAQhX7d2zzZbUZ8J4gAipzVu3M`.

W8-S3 is **ACCEPTED / MAIN-MERGED / CLIENT AND API PRODUCTION-DEPLOYMENT-VERIFIED**.

W8-S3 completed the ordinary plain-language contract across root shell, Project chooser/history, Progress, server-originated public messages, and reduced-graphics fallback while retaining machine-readable error codes, traces, Project binding, Work Specification / Engineering Run technical truth, source/provider evidence and REVIEW authority behind appropriate technical surfaces.

### W8-S4 — Guided next action

Workstream: #385

Release PR: #388; draft PR #387 was superseded without changing implementation intent because the available connector could not transition the draft PR to ready-for-review while protected release gates intentionally require a non-draft PR.

Governing specification:

`P2-V0.22.0`

Final qualified worker head:

`2b5a01212a4d3c3ddc1c0302c113512412259079`

Application release merge:

`17b62ec2649224e2beeacd6c9b2ce23d01af8028`

Production client deployment:

`dpl_BAbUpv63PUFxmCHM6JDDkf2SsFNJ`

W8-S4 is **ACCEPTED / MAIN-MERGED / CLIENT PRODUCTION-DEPLOYMENT-VERIFIED**.

The deployed S4 interaction layer:

- derives one shared deterministic ordinary guidance object from existing conversation, Build plan and Engineering Run truth;
- uses explicit precedence for approved-scope amendment, failure, pause, cancellation, REVIEW, COMPLETE, active work, plan review/creation and fresh conversation states;
- renders a primary desktop guided-workflow card before detailed Build plan / Progress;
- drives mobile guidance from the same mapper rather than a second lifecycle interpretation;
- provides the desktop utility rail only a secondary read-only `Next` summary from the same mapper;
- maps only to already-authorized callbacks such as create/review plan, continue/retry saved work, review Progress/Activity, continue approved scope, or start a new goal;
- fails closed when a real Engineering Run is unavailable instead of inventing a retry action;
- keeps REVIEW as a human-review boundary and COMPLETE distinct from deployment/merge;
- does not expose raw Project IDs, Engineering Run IDs, provider identities, raw lifecycle stage names or failure codes in ordinary guidance;
- adds no endpoint, schema, database mutation, lifecycle state, source/provider/model-routing authority, deployment/merge authority or REVIEW-completion authority.

S4 release qualification:

- Workstream Spec Validation #632 / `33228221801` — PASS;
- P2 CI #1361 / `33228221750` — PASS;
- Bounded Autonomy Pilot #913 / `33228221792` — PASS;
- full client browser/Skia acceptance — PASS;
- full API regression — PASS;
- protected promotion/regression rejection — PASS;
- DSPy release compilation — PASS;
- exact-head client Preview `dpl_Fj9JKuQdy4nkxrVjUdXzNF1WRE22` — READY;
- expected-head merge — PASS;
- exact-merge client production deployment `dpl_BAbUpv63PUFxmCHM6JDDkf2SsFNJ` — READY;
- post-cutover client build/runtime scan — clean;
- protected production client fetch — HTTP 200;
- API path-aware deployment attempt `dpl_7DHdsKtF1SYPmMpobRV71TC3FJ4o` — CANCELED, correctly preserving the S3 API deployment identity.

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

W8-S4 adds no database migration.

## Rollback

### Client

Current W8-S4 production client:

- application source `17b62ec2649224e2beeacd6c9b2ce23d01af8028`;
- deployment `dpl_BAbUpv63PUFxmCHM6JDDkf2SsFNJ`.

Immediate deployment-verified W8-S3 rollback reference:

- source `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- deployment `dpl_CZuVyJKDHQuznvFgpdaBEuKzWtJe`.

Earlier W8-S2 rollback reference:

- source `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- deployment `dpl_533dbrSSkCtpoL7C3KQna7fRKpG3`.

### API

Current production API remains W8-S3:

- application source `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- deployment `dpl_D2PAQhX7d2zzZbUZ8J4gAipzVu3M`.

Immediate deployment-verified W8-S2 rollback reference:

- source `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- deployment `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p`.

Earlier fully deployment-verified Wave 7 rollback reference:

- source `703934871e4df0f63828c7fd6e33d3e6a86b60b1`;
- deployment `dpl_GSkdmZDyXoh2RUdoPjC2WCeHeJVi`.

W8-S4 is client presentation only and adds no schema migration. Rollback requires no schema rollback. Any rollback must preserve canonical Project, Work Specification, Engineering Run, source-lineage, and protected evidence already written by production.

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
- this record-only commit does not replace application source `17b62ec2649224e2beeacd6c9b2ce23d01af8028` unless it actually changes and deploys application bytes;
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
- workflow guidance is presentation derived from canonical truth, not a client-owned lifecycle or new action authority;
- no deployment is recorded as deployment-verified without exact release identity and appropriate post-cutover evidence.

## Next governed implementation boundary

Wave 8 planned implementation is complete through S4. No S5 is planned. W8-S2 remains open only for its final authenticated production defect replay.

Immediate boundaries are:

1. through a normal authenticated Parallax session, retry OT Time Engineering Run `af617b0b-5297-427c-a40d-90d58f59a20a` or an exact canonical equivalent and confirm it advances beyond the former missing-static-target PLAN failure without weakening authentication;
2. after that evidence, mark W8-S2 defect verification complete and close #377; then Wave 8 Control #374 may be fully closed;
3. begin Wave 9 as a separate governed program focused on real-world app-builder proof rather than extending Wave 8 presentation work: the recommended first slice is a controlled end-to-end real application build benchmark from goal → specification → implementation → testing → REVIEW → deployment evidence;
4. complete safe deletion #290 only when a deliberately disposable authenticated production target is available;
5. treat hosted-to-private inference from Vercel as a separate architecture/security/network/deployment workstream if later desired;
6. handle Expo/tooling dependency findings as a bounded maintenance workstream rather than destabilizing the deployment-verified product with an unrelated major downgrade.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.5 — unchanged by W8-S4; existing authority and plain-language principles already govern S4.
- `ARCHITECTURE.md` v3.13 — unchanged by W8-S4; S4 adds no lifecycle, provider, source, deployment or REVIEW authority.
- `DESIGN-SYSTEM.md` v3.2 — unchanged by W8-S4; it already requires primary copy to explain outcomes, meaning and next actions and already protects mobile readability/progressive disclosure.
- `CURRENT-STATE.md` — updated after W8-S4 exact-head qualification, expected-head merge, exact client production deployment verification, clean post-cutover build/runtime checks, protected production fetch, and confirmation that the S4 API deployment attempt was path-aware canceled. W8-S2 authenticated OT Time replay and safe-deletion authenticated destructive smoke remain explicitly pending.