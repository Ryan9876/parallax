# Parallax 2.0 Current State

Date: 2026-08-29

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / W8 IMPLEMENTATION COMPLETE / W8-S1 + W8-S3 + W8-S4 DEPLOYMENT-VERIFIED / QA PASSWORD FALLBACK CLIENT PRODUCTION-DEPLOYMENT-VERIFIED + QA PASSWORD ENROLLMENT/SIGN-IN VERIFIED / W8-S2 PRODUCTION INFRASTRUCTURE VERIFIED WITH AUTHENTICATED OT TIME REPLAY PENDING / W9-S1 + W9-S2 API PRODUCTION-DEPLOYMENT-VERIFIED WITH W9-S1 CONTROLLED REAL-WORLD TRIAL PENDING CREDENTIAL-SAFE INTERACTIVE BROWSER SESSION / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Parallax production now includes the deployment-verified W9-S1 real-world benchmark-admission layer and the W9-S2 governed skill-intake/capability-catalog backend in the API while retaining the existing deployment-verified client, QA authentication fallback, Wave 8 guided experience and earlier Waves 1–7 runtime/productization baseline.

W9-S2 does not make internet-discovered content executable. External skill/tool observations remain quarantined metadata until exact approval and existing registry admission succeed; tool/provider authority remains separately Project-scoped. The released S2 slice adds no live arbitrary crawler, package/MCP installation, database migration or user-facing marketplace.

W9-S1 does **not** mean the first real-world Decision Ledger benchmark has passed. The evaluation/admission capability is released and the dedicated QA account has now completed private password enrollment plus successful production password sign-in. The controlled authenticated reference trial itself has not started because this continuation's available tool surface does not provide a credential-safe interactive Parallax browser session that can inherit the privately authenticated QA cookie/session. No password/token extraction, authentication bypass, direct database/admin session mutation or out-of-band benchmark source mutation is being used to manufacture evidence.

### Client

Current production client:

- application source: `4f812bd2cd6a5939c3d39ede457c091bac7b6e0f`;
- production deployment: `dpl_CbuQzRDz3iJgF8rnqEpivmfmpQaM`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- target: `production`;
- state / ready state: `READY`;
- exact Git source: `4f812bd2cd6a5939c3d39ede457c091bac7b6e0f`;
- aliases: `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, `parallax-git-main-lew7.vercel.app`;
- alias error: none.

W9-S1 changes no client application bytes. Current client truth therefore remains the independently deployment-verified QA-fallback release rather than being relabeled as an S1 client deployment.

### QA authenticated-browser fallback

Workstream: #389

Release PR: #390

Governing specification: `P2-V0.22.1`

Qualified worker head: `d470208b98a148512fbeb300255e97a9bd9e6514`

Application release merge: `4f812bd2cd6a5939c3d39ede457c091bac7b6e0f`

Production client deployment: `dpl_CbuQzRDz3iJgF8rnqEpivmfmpQaM`

The QA fallback is **MAIN-MERGED / CLIENT PRODUCTION-DEPLOYMENT-VERIFIED / PRIVATE PASSWORD ENROLLMENT + PASSWORD SIGN-IN VERIFIED**:

- exact-head Workstream Spec Validation `33229323953` — PASS;
- exact-head Bounded Autonomy `33229323990` — PASS;
- exact-head P2 CI `33229323928` — PASS;
- exact-head Preview `dpl_7yKbmEUPT3NnDQ6BBej6UJHoC8fe` — READY;
- exact-merge production deployment `dpl_CbuQzRDz3iJgF8rnqEpivmfmpQaM` — READY;
- normal `/` remains Google-only;
- live `/?qa=1` exposes the bounded secondary QA email/password/recovery controls while retaining Google as primary;
- passwords, recovery tokens and Supabase access tokens are not persisted by the client and are not recorded in project records;
- post-cutover client runtime-error scan was clean;
- production Supabase auth evidence records password update (`PUT /user`) — HTTP 200 at `2026-08-29T02:57:49Z`;
- production password sign-in (`POST /token`, `grant_type=password`) — HTTP 200 at `2026-08-29T02:58:29Z`;
- repeated production password sign-in — HTTP 200 at `2026-08-29T03:00:43Z`, followed by authenticated user retrieval — HTTP 200.

The prior password-enrollment blocker is therefore resolved. No password, recovery token, access token or refresh token was read into this continuation. The remaining automation constraint is session transport: this tool surface cannot inherit the private authenticated browser cookie/session without exposing credentials or bypassing the existing authentication design. This still prevents this continuation from performing the W8-S2 OT Time production replay or starting the W9-S1 trial, but it is no longer an account-enrollment failure.

### API

Current production API:

- application source: `fcb6abf4f794e038bcf48daac8d3400f006a18d8`;
- production deployment: `dpl_57xiHUKBm3qK4HAA47kYzc9mJM13`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- target: `production`;
- state / ready state: `READY`;
- exact Git source verification: verified;
- aliases: `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, `parallax-api-git-main-lew7.vercel.app`;
- alias error: none.

W9-S2 post-cutover verification:

- production build cloned exact merge `fcb6abf4f794e038bcf48daac8d3400f006a18d8`;
- production provider preflight — PASS;
- scoped delivery-permission preflight — PASS;
- projected-source preflight — PASS;
- private Blob/immutable-lineage composition preflight — PASS;
- agentic-runtime round-trip preflight — PASS;
- projected-bootstrap process-recreation/replay/no-stage-mutation checks — PASS;
- deny-all execution-snapshot/offline dependency check — PASS;
- production run-event schema guard — PASS;
- build completed successfully and outputs deployed;
- `https://parallax-api-tan.vercel.app/health` — HTTP 200, service `ok`;
- `https://parallax-api-tan.vercel.app/ready` — HTTP 200, database/providers `ok`, one provider target;
- exact-deployment error/fatal runtime scan — no matching logs.

W9-S1 post-cutover verification:

- production build cloned exact merge `ee6af25d09c495f2550f39a7d7f90f527dc7e447`;
- production provider preflight — PASS;
- scoped delivery-permission preflight — PASS;
- projected-source preflight — PASS;
- private Blob/immutable-lineage composition preflight — PASS;
- agentic-runtime round-trip preflight — PASS;
- projected-bootstrap process-recreation/replay/no-stage-mutation checks — PASS;
- deny-all execution-snapshot/offline dependency check — PASS;
- production run-event schema guard — PASS;
- build completed successfully and outputs deployed;
- `https://parallax-api-tan.vercel.app/health` — HTTP 200, service `ok`;
- `https://parallax-api-tan.vercel.app/ready` — HTTP 200, database/providers `ok`, one provider target;
- exact-deployment error/fatal runtime scan — no matching logs.

Immediate API rollback reference is the deployment-verified W9-S1 API:

- source `ee6af25d09c495f2550f39a7d7f90f527dc7e447`;
- deployment `dpl_9fWd2fZLsfXyexSC8hohvS9X5iDa`.

## Wave 9 S1 — Real-world greenfield benchmark admission

Control Tower: #391

Workstream: #392

Release PR: #394; draft #393 was superseded without changing implementation intent because the available ready-for-review connector remains incompatible with GitHub's current GraphQL schema.

Governing specification: `P2-V0.23.0`

Final qualified worker head:

`1d053823d08d8e5050e77c624dafcd09199fe942`

Application release merge:

`ee6af25d09c495f2550f39a7d7f90f527dc7e447`

Production API deployment:

`dpl_9fWd2fZLsfXyexSC8hohvS9X5iDa`

W9-S1 is **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED / QA PASSWORD ENROLLMENT + PASSWORD SIGN-IN VERIFIED / CONTROLLED REAL-WORLD TRIAL PENDING CREDENTIAL-SAFE INTERACTIVE BROWSER SESSION**.

### Frozen Decision Ledger benchmark

Template: `decision-ledger@1.0.0`

Fixture digest:

`15b098df3956ffe71833778e18a301a8e77fae9f37705223256703619f684900`

The frozen benchmark contains exactly `DL-01` through `DL-12` and requires:

- create/view/edit/delete decision records;
- title, status, decision date, owner, context, final decision, options considered and tags;
- Proposed / Accepted / Superseded status meaning that is not color-only;
- browser-persistent state without an external account or third-party backend;
- search, status/tag filtering and deterministic understandable ordering;
- JSON export/import with safe failure that preserves existing valid data;
- recoverable empty, validation, destructive-confirmation and import-failure UX;
- usable 390px mobile and 1440px desktop layouts;
- keyboard reachability, accessible labels and non-color-only meaning;
- automated CRUD/persistence/search/filter/import coverage plus production build;
- no embedded secrets, real user data, tracking credential or benchmark-specific runtime branch;
- ordinary accepted-source → Preview → REVIEW behavior with protected validation evidence.

### ParallaxBench real-world admission contract

W9-S1 extends existing ParallaxBench rather than introducing another benchmark engine or aggregate score.

The deployed evaluation-only contract provides:

- bounded immutable real-world objective templates with stable ID/version and deterministic material digest;
- bounded immutable requirement records with stable requirement tokens and per-requirement digests;
- duplicate template identity with different content failing closed;
- canonical binding only to exact Project identity plus an **APPROVED** Work Specification with exact ID/revision/digest and unique acceptance IDs;
- repository-shape matching;
- deterministic requirement-token admission: every frozen `DL-01` through `DL-12` token must appear exactly once across approved canonical acceptance text;
- missing or duplicate requirement tokens failing closed;
- no unconstrained model/evaluator semantic substitution or silent Work Specification repair;
- successful binding producing the existing `BenchmarkCase` contract, including the complete canonical acceptance-ID set and frozen fixture digest;
- existing protected correctness, evidence-state, comparison and safe-serialization precedence retained unchanged.

Benchmark template identity remains evaluation evidence only. It grants no Project creation, Work Specification approval, Engineering Run transition, source acceptance, provider/tool capability, repository mutation, browser/network capability, merge, production promotion, approval or REVIEW-completion authority.

### Authentic DSPy and qualification evidence

Authentic pre-implementation DSPy evidence:

- P2 CI run `33229188492` executed SpecCritic + SpecCompiler for exact `P2-V0.23.0`;
- repository-approved local fallback model `ollama_chat/qwen2.5:0.5b` was used because no provider key was available in CI;
- exact generated plan committed as `specs/compiled/P2-V0.23.0.plan.json`;
- plan blob `90c2b678d62efc09d872dd716296f6d7581f1341`;
- temporary evidence-only workflow retarget was removed;
- `.github/workflows/ci.yml` restored byte-for-byte to blob `79caf538e381b7c6f14471f80c3c3df4acad5f26`;
- clean changed-spec protected plan gate `33229680275` — PASS.

Final exact-head qualification at `1d053823d08d8e5050e77c624dafcd09199fe942`:

- Workstream Spec Validation `33230085106` — PASS;
- Bounded Autonomy `33230085121` — PASS;
- P2 CI `33230085107` — PASS;
- full API regression — PASS;
- full client type/state/export/browser/Skia regression against the current-base synthetic merge candidate — PASS;
- protected promotion/regression rejection — PASS;
- normal DSPy release compilation — PASS;
- API semantic Preview `dpl_FduDSzUA7NFwGMdQxTM57NADA2EH` — READY / clean build;
- final architecture-only candidate Preview attempt was path-aware canceled because API application bytes were unchanged from the verified semantic Preview.

The expected-head merge preserved current main QA-auth work and S1 ancestry:

- parent `24d487eee87894597f434298dbd00a0eef5fb6c4` — pre-S1 current main / QA-auth state record;
- parent `1d053823d08d8e5050e77c624dafcd09199fe942` — final qualified W9-S1 head;
- merge `ee6af25d09c495f2550f39a7d7f90f527dc7e447` — GitHub-verified.

### Controlled real-world reference trial

The real Decision Ledger trial has **not started**.

A source-empty independent target candidate has been identified:

`Ryan9876/sickbeard`

GitHub's commit-history endpoint still reports the repository as empty. It therefore contains no reference solution or manually seeded application source. It has not been mutated, initialized or bound to a Parallax Project by this workstream.

The previously recorded private QA password-enrollment prerequisite is now satisfied by production evidence. The remaining limitation is this continuation's tool surface: it does not expose a credential-safe interactive Parallax browser session that can inherit the privately authenticated QA session. The workstream will not obtain that access by extracting the QA password or Supabase tokens, direct database/admin session mutation, authentication bypass, or a benchmark-only auth path.

When a managed interactive browser context can use the privately authenticated QA session, the S1 trial must:

1. use the frozen objective and exact `DL-01` through `DL-12` tokens;
2. create/select a normal Parallax Project bound to the independent greenfield repository;
3. generate the ordinary Work Specification / Build plan;
4. record pre-approval clarification separately if needed;
5. obtain only the ordinary required plan approval;
6. run the normal Engineering Run through protected PLAN / IMPLEMENT / BUILD / TEST / VERIFY and Preview / REVIEW behavior;
7. make any corrective request only through Parallax, never through out-of-band source editing;
8. bind the actual approved canonical Project/Work Specification through the released S1 admission contract;
9. capture exact Project/spec/run/source/Preview/protected identities plus interventions/retries/time/cost/UX only where trustworthy;
10. record failure or `HUMAN_REQUIRED` honestly if that is the observed product boundary.

A failed/HUMAN_REQUIRED trial is useful S1 evidence once the real trial has actually begun. An unavailable credential-safe browser session before trial start is not mislabeled as a completed benchmark.

Any semantic Parallax defect discovered by the trial must be recorded before implementation and receives a separately governed future workstream/specification. No such fix is included in W9-S1.

## Wave 9 S2 — Governed skill intake and capability catalog

Control Tower: #391

Workstream: #395

Release PR: #397

Governing specification: `P2-V0.23.1`

Final qualified worker head:

`0965969da3224ebe62e8a33348440b5753e76d6e`

Application release merge:

`fcb6abf4f794e038bcf48daac8d3400f006a18d8`

Production API deployment:

`dpl_57xiHUKBm3qK4HAA47kYzc9mJM13`

W9-S2 is **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

### Released capability boundary

The deployed backend contract adds:

- deterministic bounded `SkillCandidate` identity for skill/tool observations;
- quarantine by default with explicit provenance, source-tier, license and static-policy reason codes;
- exact replay idempotency and changed-content conflict handling instead of silent replacement;
- Project-private catalog isolation;
- safe catalog metadata that excludes raw source bodies, credentials, provider secrets, unrestricted execution handles and hidden reasoning;
- exact `SkillCandidateApproval` binding to candidate identity, source/content digest, intake-policy digest and exact `PortableSkill` digest;
- final admission through the pre-existing `SkillRegistry.admit` contract;
- runtime retrieval limited to catalog-admitted skills followed by the existing deterministic `SkillSelector`;
- server-owned source definitions for the official Agent Skills ecosystem and official MCP Registry metadata roots;
- a bounded source-adapter interface proven with synthetic fixtures and no candidate-content execution.

The release does **not** add live arbitrary internet crawling, generic shell/network execution, package installation, MCP server startup, tool-capability mutation, provider administration, merge/deployment authority, REVIEW authority, database persistence/migration or a user-facing skill marketplace. Tool candidates remain metadata only; a skill's requested capability cannot grant itself that capability.

### Authentic DSPy and exact-head qualification

Authentic pre-implementation DSPy evidence:

- evidence workflow run `33229695444` executed SpecCritic + SpecCompiler for exact `P2-V0.23.1`;
- repository-approved local fallback model `ollama_chat/qwen2.5:0.5b` was used because no provider key was available in the evidence workflow;
- exact generated plan committed as `specs/compiled/P2-V0.23.1.plan.json`;
- plan blob `41afe19e7104c756dff94d0c1c11fc04d56fd7f3`;
- the temporary S2 evidence workflow was removed before semantic implementation qualification.

Final exact-head qualification at `0965969da3224ebe62e8a33348440b5753e76d6e`:

- Workstream Spec Validation `33230538004` — PASS;
- Bounded Autonomy `33230537997` — PASS;
- P2 CI `33230537996` — PASS;
- full API regression — `966 passed, 1 skipped, 4 existing collection warnings`;
- full client type/state/export/browser/Skia regression — PASS;
- protected promotion/regression rejection — PASS;
- normal DSPy release compilation — PASS;
- exact API Preview `dpl_DzZAGtehR5cU9pMPbEanXH7DgeLH` — READY.

Expected-head merge #397 produced GitHub-verified main commit `fcb6abf4f794e038bcf48daac8d3400f006a18d8`. Production deployment `dpl_57xiHUKBm3qK4HAA47kYzc9mJM13` cloned that exact commit and completed the existing provider, scoped-delivery, projected-source, private-Blob/lineage, agentic-runtime, process-recreation/replay, deny-all execution-snapshot and schema preflights before deployment. Post-cutover `/health` and `/ready` are HTTP 200 and the exact-deployment error/fatal scan is clean.

W9-S2 changes no client application bytes, so current deployment-verified client identity remains unchanged.

## Wave 8 retained state

Wave 8 Control Tower: #374

Wave 8 planned implementation is complete through S4. No W8-S5 is planned. The control remains open only for the W8-S2 authenticated OT Time replay.

### W8-S1

- release merge `a784af75fc3076a56f9d8e52ff529ca8302e9ce6`;
- production client `dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`;
- status: **ACCEPTED / MAIN-MERGED / CLIENT PRODUCTION-DEPLOYMENT-VERIFIED**.

W8-S1 established mobile `Chat · Progress · Project`, plain journey language, readable typography, at least 44px primary touch targets, progressive disclosure and unchanged server-owned lifecycle authority.

### W8-S2

- workstream #377;
- spec `P2-V0.21.1`;
- release merge `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- status: **ACCEPTED FOR RELEASE / MAIN-MERGED / PRODUCTION-DEPLOYED / INFRASTRUCTURE-VERIFIED / AUTHENTICATED DEFECT REPLAY PENDING**.

W8-S2 separates exact repository bootstrap from deferred Preview-hosting readiness. PLAN/IMPLEMENT/BUILD/TEST/VERIFY no longer require manual static Vercel target registration. Exact bounded Vercel Project discovery/creation occurs only when verified delivery needs it, remains Project/repository/team scoped and adds no merge, production-promotion, domain, environment-variable, credential, source-acceptance, lifecycle-transition or REVIEW-completion authority.

Original OT Time run still requiring authenticated replay:

`af617b0b-5297-427c-a40d-90d58f59a20a`

Read-only evidence retained the run at canonical PLAN revision 1 before the replay. No direct database mutation or auth bypass will be used to manufacture success.

### W8-S3

- release merge `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- client `dpl_CZuVyJKDHQuznvFgpdaBEuKzWtJe`;
- API `dpl_D2PAQhX7d2zzZbUZ8J4gAipzVu3M`;
- status: **ACCEPTED / MAIN-MERGED / CLIENT AND API PRODUCTION-DEPLOYMENT-VERIFIED**.

W8-S3 completed ordinary plain-language treatment across shell, Project history, Progress and server-originated public messages while retaining machine-readable technical evidence and authority boundaries.

### W8-S4

- workstream #385;
- spec `P2-V0.22.0`;
- final qualified head `2b5a01212a4d3c3ddc1c0302c113512412259079`;
- release merge `17b62ec2649224e2beeacd6c9b2ce23d01af8028`;
- production client `dpl_BAbUpv63PUFxmCHM6JDDkf2SsFNJ`;
- status: **ACCEPTED / MAIN-MERGED / CLIENT PRODUCTION-DEPLOYMENT-VERIFIED**.

S4 provides one deterministic plain-language next-action mapper shared by desktop/mobile/secondary utility surfaces, derived only from canonical conversation/Build plan/Engineering Run truth. It adds no client-owned lifecycle, endpoint, schema, provider/source authority, deployment/merge authority or REVIEW-completion authority.

## Wave 7 retained baseline

Wave 7 Control Tower: #347

Final application release merge:

`703934871e4df0f63828c7fd6e33d3e6a86b60b1`

Waves 1–7 remain **DEPLOYMENT-VERIFIED**. Wave 7 continues to provide the retained ParallaxBench evaluation, Agent Run projection/control, Development Studio, bounded safe-browser evidence, agentic observability/economics/retention projection, integrated product proof and protected source/provider/REVIEW boundaries.

W8 and W9-S1 extend but do not replace or weaken those contracts.

## Production database and safe deletion

Supabase production migration `20260827173141` (`safe_conversation_project_deletion`) remains active and additive/backward-compatible.

Logical conversation/Project deletion remains production-deployed and infrastructure-verified. User-visible deletion is workspace deletion, not protected-evidence purge. Work Specifications, Engineering Runs, attempts/events, accepted source lineage and immutable engineering/provider evidence remain retained; deleting a Project does not delete linked GitHub repositories, pull requests or Vercel deployments.

Remaining safe-deletion debt: final authenticated destructive-behavior smoke against a deliberately disposable production conversation/Project. Authentication will not be weakened and real user content will not be deleted merely to manufacture evidence.

Workstream #290 remains open.

W9-S1 adds no database migration.

## Local-first model routing

`P2-V0.19.8` local-first routing remains production-deployed and unchanged.

Vercel production remains intentionally hosted-only. Hosted model escalation remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted-to-private inference remains a separate architecture/security/network/deployment workstream.

## Rollback

### Client

Current QA-fallback production client:

- source `4f812bd2cd6a5939c3d39ede457c091bac7b6e0f`;
- deployment `dpl_CbuQzRDz3iJgF8rnqEpivmfmpQaM`.

Immediate deployment-verified pre-QA fallback reference:

- source `17b62ec2649224e2beeacd6c9b2ce23d01af8028`;
- deployment `dpl_BAbUpv63PUFxmCHM6JDDkf2SsFNJ`.

Earlier W8-S3 reference:

- source `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- deployment `dpl_CZuVyJKDHQuznvFgpdaBEuKzWtJe`.

### API

Current W9-S1 production API:

- source `ee6af25d09c495f2550f39a7d7f90f527dc7e447`;
- deployment `dpl_9fWd2fZLsfXyexSC8hohvS9X5iDa`.

Immediate deployment-verified rollback reference:

- source `91be7cd9a7fa088f7cebd061d9f9147ac148282c`;
- deployment `dpl_D2PAQhX7d2zzZbUZ8J4gAipzVu3M`.

Earlier W8-S2 reference:

- source `ee1b502269f7b4367576a02cdaab45c763eb6717`;
- deployment `dpl_EkapMujhx4DUAAvLowKsYZ2zxR4p`.

Rollback requires no W9-S1 schema rollback because S1 adds no database migration. Any rollback must preserve canonical Project, Work Specification, Engineering Run, accepted source lineage and protected evidence already written by production.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- parent integration/control #31 serializes cross-wave release truth;
- Wave 7 Control #347 governs the retained productization/runtime baseline;
- Wave 8 Control #374 governs human-centered UX/plain-language/guided execution and remains open only for W8-S2 authenticated replay;
- Wave 9 Control #391 governs real-world app-builder validation;
- W9-S1 #392 remains open only for the controlled authenticated Decision Ledger reference trial; QA enrollment/sign-in is verified, while a credential-safe managed interactive browser session remains required to start that trial;
- every semantic AI/runtime/evaluation change remains spec-first with stable acceptance IDs and authentic DSPy evidence;
- benchmark fixtures and evaluator output are evidence, not lifecycle/provider/source authority;
- source readiness and hosting readiness remain separate lifecycle concerns;
- presentation may translate technical state into plain language but may not invent canonical state;
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
- workflow guidance is presentation derived from canonical truth, not a client-owned lifecycle or new action authority;
- real-world benchmark admission may bind canonical evidence but cannot create, repair or mutate that canonical evidence;
- benchmark identity or expected outcome may not become a runtime/provider/source-delivery/client branch selector;
- no deployment is recorded as deployment-verified without exact release identity and appropriate post-cutover evidence.

## Next governed boundary

For the user's instruction to continue through **W9-S1 only**, no further Wave 9 implementation slice is authorized here.

The only remaining S1 completion action is the controlled real-world Decision Ledger trial from a credential-safe managed interactive browser context using the already-enrolled QA account. Use the ordinary product workflow against the independent greenfield repository and record either the trustworthy reference result or the honest failed/HUMAN_REQUIRED product boundary. Do not expose the QA password/tokens, bypass authentication, mutate session state through database/admin authority, or implement a benchmark-discovered semantic product fix inside S1; record any such defect for separate future governance.

Independent open debts remain:

1. W8-S2 authenticated OT Time replay;
2. safe deletion #290 authenticated destructive smoke;
3. hosted-to-private inference only if separately governed later;
4. unrelated dependency/toolchain maintenance only as a bounded maintenance workstream.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.5 — unchanged by this W9-S1 state reconciliation; existing authority, evidence and human-review rules already govern the benchmark boundary.
- `ARCHITECTURE.md` v3.14 — unchanged by this state reconciliation; W9-S1's immutable real-world objective templates, deterministic canonical Project/approved Work Specification admission, existing `BenchmarkCase` compatibility, evaluation-only authority and reference-observation boundary remain authoritative.
- `DESIGN-SYSTEM.md` v3.2 — unchanged; this reconciliation adds no user-facing design-system rule.
- `CURRENT-STATE.md` — updated to replace the stale QA password-enrollment blocker with verified production password-enrollment/sign-in evidence, retain the unstarted Decision Ledger trial truth, and record the remaining credential-safe managed-browser session requirement. No application code, schema, deployment or durable architecture contract changed.