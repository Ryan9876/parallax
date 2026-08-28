# Parallax 2.0 Architecture

Version: 3.13
Status: Authoritative

## Version relationship

Architecture v3.13 is a bounded architectural update to v3.12, not a platform rewrite. The complete v3.12 architecture at repository commit `09e9d096eb16adf083f5029fa6fc07ea1cb90923` is incorporated by reference. Every v3.12 durable contract not explicitly changed below remains authoritative, including canonical Project / Work Specification / Engineering Run authority, immutable accepted source lineage, single-writer canonical mutation, durable worker recovery, deny-all Sandbox validation, Wave 6 agentic orchestration/evaluation/routing/competition boundaries, Project-scoped tool/provider authority, protected evaluation, logical workspace deletion/retention, Preview/REVIEW ceilings, governed release evidence, accepted `P2-V0.19.8` local-first routing, and accepted Wave 7 productization contracts.

This version records W8-S2 (`P2-V0.21.1`): repository/source readiness and Preview-hosting readiness are separate lifecycle concerns. A Project-bound run may establish exact repository lineage and advance through protected planning/implementation/validation without a pre-registered Vercel Project. Vercel target discovery or bounded creation is deferred until verified Preview publication is actually required at the existing REVIEW boundary.

## W8-S2 — Delivery readiness at the correct lifecycle boundary

W8-S2 removes a hidden operational prerequisite without expanding ordinary build authority.

### Source readiness is immediate and repository-scoped

At autonomous-run composition, Parallax still resolves the canonical owner-scoped Project and its canonical GitHub repository binding. Repository bootstrap remains server-owned, exact-Project, exact-run and exact-repository scoped. If durable source lineage does not yet exist, Parallax reads the admitted repository through the existing scoped GitHub provider boundary and creates the immutable repository-root lineage. If the lineage already exists, it is reused.

Source bootstrap does **not** require a Vercel Project, Preview target or deployment lookup. Therefore absence of Preview registration cannot block PLAN, IMPLEMENT, BUILD, TEST or VERIFY merely because hosting is not yet needed.

The accepted Engineering Run state machine and single-writer transition rules are unchanged. W8-S2 changes composition timing, not canonical lifecycle authority.

### Preview readiness is deferred to verified delivery

`production_source_delivery_lazy` composes the normal repository bootstrap immediately and wraps verified delivery in a deferred resolver. The deferred resolver does not inspect, discover or create a Vercel Project until `VerifiedLineageDelivery.deliver(...)` is called after the protected coordinator has already reached the existing `REVIEW_REQUIRED` boundary.

Verified delivery retains the pre-existing requirements:

- the canonical run is at REVIEW;
- accepted IMPLEMENT evidence identifies the exact accepted non-root source lineage;
- VERIFY succeeded on that exact lineage under protected execution;
- the current durable source head still equals the verified lineage;
- the canonical Project/repository binding still matches;
- GitHub branch, commit and pull-request read-back match the exact verified source;
- Preview publication remains bounded evidence for operator review and does not complete REVIEW.

### Exact Vercel Project readiness

When verified delivery needs a Preview target, Parallax first uses the existing server-owned target registration if an exact canonical repository match exists. If the canonical repository has no registered target, W8-S2 may perform one new bounded provider action: ensure the exact Vercel Project container needed for Preview publication.

That readiness action is constrained by all of the following:

- server-owned credentials only;
- one server-owned Vercel team/provisioning profile;
- canonical Project identity and canonical GitHub repository only;
- GitHub repository identity is verified from the provider, including stable repository ID and default branch;
- Vercel discovery is bounded to at most 100 returned Projects and fails closed if the provider indicates additional pagination;
- zero exact GitHub-repository matches permits bounded creation;
- one exact match is reused after provider read-back;
- multiple exact matches fail closed as ambiguous;
- creation uses a deterministic name derived from repository name plus canonical Project identity;
- create conflicts are reconciled by re-discovery and exact read-back rather than blind retry;
- created/reused Projects must read back under the expected team and exact GitHub repository ID;
- a newly created Project is checked for absence of any production deployment side effect.

Dynamic readiness is reconstructed from canonical Project identity and provider truth on subsequent processes. The in-request augmented target registration is not new canonical Project state and is not trusted from client input.

### Readiness authority ceiling

The readiness client intentionally exposes only bounded Project metadata discovery/read/create operations plus a read-only check for unexpected production deployment side effects. It has no API surface for:

- production deployment creation or promotion;
- domain administration;
- environment-variable administration;
- provider credential creation;
- Project deletion;
- arbitrary Vercel team/project administration;
- GitHub repository expansion;
- merge;
- source acceptance bypass;
- Engineering Run transition;
- REVIEW completion.

The existing GitHub and Vercel provider action/audit contracts remain authoritative after readiness. The new `project.ensure` capability is Project-scoped and does not imply broader provider administration.

### Failure and retry semantics

Readiness/provider failure remains fail-closed. A failure may stop the current autonomous request, but it does not fabricate a new Engineering Run state, discard the approved Work Specification or erase durable source lineage. Primary product copy explains that the work remains saved and offers retry; raw provider/system evidence remains secondary technical detail.

Client retry is a request to continue the same durable run. Client recovery state is presentation state only and cannot advance, rewrite or reinterpret canonical Engineering Run truth.

No W8-S2 database migration is introduced by this architectural revision.

## Accepted Wave 7 cumulative architecture

Wave 7 now consists of six accepted cumulative layers:

1. **S1 — ParallaxBench**: read-only objective evaluation and protected comparison evidence.
2. **S2 — Agent Run projection/control**: typed projection over the existing canonical Engineering Run and already-authorized pause/resume/cancel operations.
3. **S3 — Development Studio / Agent Run Canvas**: client composition over fresh server-owned run truth, including replay-safe bounded continuation requests without client-side canonical authority.
4. **S4 — Safe Browser Tool Layer v1**: Project-scoped non-destructive browser evidence against server-admitted targets, with bounded navigation/inspection/assertion/screenshot behavior and no arbitrary JavaScript/network/destructive authority.
5. **S5 — Agentic observability/economics/retention**: query-time evidence aggregation with explicit `OBSERVED` / `ESTIMATED` / `UNKNOWN` semantics, bounded event coverage and no telemetry ledger or canonical deletion authority.
6. **S6 — Integrated Product Proof**: read-only composition that proves the accepted S1-S5 product path across materially different application objectives without acquiring upstream authority.

Final accepted cumulative Wave 7 integration:

`integration/wave7-productization@eb217315992ac0e20acd978433f3e4a17cdcf565`

This is an integration identity, not a production identity.

## W7-S6 — Integrated Product Proof

S6 adds `integrated_product_proof` as a bounded evidence-composition layer over accepted S1/S3/S4/S5 contracts. It owns no Project, Work Specification, Engineering Run, source-lineage, provider, browser-capability, deployment or REVIEW authority.

The server-owned immutable proof portfolio contains three materially different objective classes:

- `stateful-workflow`;
- `data-operations`;
- `public-utility`.

For each admitted scenario, the proof binds and verifies:

- canonical Project identity;
- approved Work Specification identity/revision/digest;
- Engineering Run identity and canonical server state;
- accepted source-lineage identity;
- exact Preview/release-lineage identity where Preview evidence is required;
- fresh S3 projection truth;
- S5 observability projection revision/fingerprint and explicit coverage state;
- canonical ParallaxBench result recomputation against the server-owned predeclared baseline;
- admitted S4 browser target/evidence only;
- bounded retry/recovery/replay evidence where required by the scenario;
- deterministic/protected failure precedence;
- predeclared non-protected value dimensions and portfolio-level regression rejection.

S6 proof output is evidence, not authority. It may conclude only within the existing autonomous ceiling and cannot complete operator REVIEW. `HUMAN_REQUIRED` remains the release boundary.

### Safe proof serialization

The integrated proof may expose bounded identities, result classifications, coverage state, deterministic validation outcome, predeclared metric/value summaries, recovery/replay indicators and safe browser assertion summaries.

It must not serialize or expose:

- source bytes or patches;
- credentials, cookies, authorization values or provider secrets;
- raw provider payloads;
- prompts, hidden reasoning or private scratchpad;
- unrestricted logs;
- browser observations containing sensitive content;
- sensitive/full target URLs where the accepted browser contract requires redaction;
- merge/deploy tokens or provider-administration material.

## Protected precedence and failure degradation

The following rules remain non-weakenable:

- deterministic/protected failure outranks benchmark/evaluator/browser/Preview success;
- incomplete S5 event coverage cannot be presented as complete observation;
- absent authoritative provider usage/cost remains `UNKNOWN`, not zero;
- missing or inadmissible browser evidence cannot be replaced with fabricated success;
- stale or mismatched Project/spec/run/source/Preview identity fails the proof rather than being normalized away;
- required recovery/replay evidence missing or inconsistent fails that proof criterion;
- one scenario's value improvement cannot compensate for correctness, safety, privacy or governance regression;
- no proof result can mutate canonical source, transition an Engineering Run, administer tools/providers, merge, deploy or complete REVIEW.

## Release-reconciliation architecture

Wave 7 development used a dedicated integration branch from the accepted entry baseline. During the wave, the mobile PLAN-handoff reliability fix originating in S3 was separately backported to `main` and deployment-verified before the full Wave 7 release.

By the time S6 completed, current `main` and the accepted Wave 7 integration branch therefore contained overlapping history for the same client behavior even though their final `apps` trees were byte-identical.

The governed release pattern is consequently **content reconciliation with dual ancestry**, not blind history replay:

1. start from the exact current `main` baseline;
2. preserve current deployment-verified client bytes and current authoritative records;
3. preserve accepted Wave 7 integration ancestry as a second parent;
4. adopt only the accepted Wave 7 workflow/API/test/spec trees not already represented by current main;
5. verify the exact candidate diff contains no accidental client, database, production-config, credential or authority regression;
6. rerun exact-head protected/release gates and Preview evidence before any main-release decision.

The first validated reconciled release candidate is:

`release/wave7-productization-v0206@e2743ee17264926adc675834ee38eee108af3111`

with parents:

- current main at construction: `a29a77fa5abe28c86b527a2a99f4023dc0c975f8`;
- accepted Wave 7 integration: `eb217315992ac0e20acd978433f3e4a17cdcf565`.

Its client tree remains byte-identical to current main. Its exact diff to that main baseline is limited to intended Wave 7 governed workflows, API/runtime/tests and `P2-V0.20.1`–`P2-V0.20.6` specification/compiled-plan records.

This reconciliation is not itself a production deployment and does not authorize a main merge.

## Release qualification retained

A Wave 7 release is not deployment-verified merely because the cumulative integration or reconciled release candidate is green.

Before a production claim, the governed path still requires:

- exact-head protected specification/evidence gates;
- full API/client/browser regression and protected promotion evaluation;
- independent DSPy release compilation;
- exact release identity;
- applicable Vercel Preview evidence;
- Control Tower authorization for the exact main-release candidate;
- a distinct production deployment/promotion decision;
- exact production deployment identity;
- post-cutover health/readiness checks for changed services;
- runtime error/fatal inspection;
- authoritative `CURRENT-STATE.md` reconciliation after deployment verification.

A path-aware Vercel cancellation for a component with no content delta is not recorded as a READY Preview. The unchanged component may instead rely on exact byte identity plus the repository's full component/build/browser release gates, while changed components still require applicable exact Preview evidence.

## Authority invariants retained

Wave 7 S1-S6, W8-S2 and release reconciliation grant none of the following authority unless already explicitly provided by an existing protected server contract:

- Project creation/ownership or cross-Project access;
- Work Specification approval/amendment;
- Engineering Run state truth or unapproved transition authority;
- accepted source-lineage creation/head advancement outside the single-writer boundary;
- filesystem/shell or arbitrary-command execution;
- unrestricted HTTP/network or arbitrary browser JavaScript authority;
- tool-capability creation/approval outside the exact server-owned W8-S2 readiness capability;
- provider spending/administration beyond the exact bounded Preview-container readiness action;
- GitHub merge authority;
- Vercel production promotion authority;
- approval, REVIEW completion or human-boundary bypass.

Canonical identity, deterministic validation, source acceptance, execution and release authority remain controlled by the existing protected Project/spec/run/lineage/provider contracts. Benchmark, model, agent, browser, projection, observability, readiness and integrated-proof output remains evidence or bounded infrastructure preparation, not canonical lifecycle authority.

## Production topology retained

The two long-lived application projects remain:

1. `parallax` — Expo/static web client;
2. `parallax-api` — FastAPI service.

`main` remains the production source branch. Vercel production remains hosted-only for model routing under `P2-V0.19.8`; enabling local-first configuration in Vercel production fails closed. Hosted-to-private inference remains a separate architecture/security/network/deployment workstream.

No Wave 7 S1-S6 or W8-S2 database migration is introduced by this architectural revision.

## Evidence for the previous accepted revision

Accepted S6 worker:

- exact worker head `e284d16972e80e40f7d5d7201f638fa72985d052`;
- Workstream Spec Validation #568 / run `33188024999` — PASS;
- Bounded Autonomy #807 / run `33187842726` — PASS;
- release-strength P2 CI #1241 / run `33188025079` — PASS;
- exact API Preview `dpl_B9HHdHHPYAoeSJhKs897kzTkdykR` — READY;
- PR #368 accepted/integrated as cumulative SHA `eb217315992ac0e20acd978433f3e4a17cdcf565`.

Reconciled release candidate:

- exact candidate `e2743ee17264926adc675834ee38eee108af3111`;
- Bounded Autonomy #808 / run `33189701035` — PASS;
- Workstream Spec Validation #571 / run `33189881795` — PASS;
- release-strength P2 CI #1244 / run `33189881717` — PASS;
- API Preview `dpl_E7yGJpknEU1thgE8UXR9v1wYgxUo` — READY, clean build and runtime error/fatal scans;
- client Preview canceled because there is no client content delta; client type/state/export/browser/Skia release gates passed in P2 #1244.

These facts validate the Wave 7 release candidate. They do not record a Wave 7 merge to `main` or production deployment.

W8-S2 validation/release evidence belongs in `CURRENT-STATE.md` only after the exact branch/release identity is fully validated and, for production claims, deployment-verified.
