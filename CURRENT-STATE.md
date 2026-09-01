# Parallax 2.0 Current State

Date: 2026-09-01

Status: **WAVES 1–8 DEPLOYMENT-VERIFIED / PYTHON AND .NET SOURCE-ONLY FULL EXPERIENCE PRODUCTION-ACCEPTED / P2-V0.23.10 LUNA-FIRST HOSTED SELECTION PRODUCTION-ACCEPTED / P2-V0.23.13 FAILED-IMPLEMENT HUMAN REPLAN PRODUCTION-ACCEPTED / P2-V0.23.14 RECOVERED-WORKER PLAN REBIND PRODUCTION-ACCEPTED / P2-V0.23.15 STRUCTURED-OUTPUT ROUTING CLASSIFICATION PRODUCTION-ACCEPTED / P2-V0.23.16 WEBGL PREFLIGHT REDUCED-GRAPHICS FALLBACK PRODUCTION-ACCEPTED / P2-V0.23.17 DEDICATED QA REPOSITORY PRODUCTION-PROVEN / P2-V0.23.18 EXACT MODEL PATCH CANONICALIZATION PRODUCTION-ACCEPTED / P2-V0.23.19 DEDICATED QA TRUST CONTRACTION PRODUCTION-VERIFIED / P2-V0.23.20 EXACT GITHUB EMPTY-REF COMPATIBILITY PRODUCTION-DEPLOYMENT-VERIFIED / P2-V0.23.21 BOUNDED GREENFIELD INSPECTION DIAGNOSTICS PRODUCTION-VERIFIED / RISK-TIERED CI/CD VALIDATION MAIN-VERIFIED / P2-V0.23.22 REQUEST-BOUNDED AUTONOMOUS BUILDS PRODUCTION-VERIFIED / P2-V0.23.23 BOUNDED VALIDATOR REPAIR PRODUCTION-BEHAVIOR-VERIFIED / P2-V0.23.24 FRESH FINAL VALIDATOR REPAIR PRODUCTION-BEHAVIOR-VERIFIED / P2-V0.23.25 SAFE NESTED SOURCE CREATION + TRANSPORT RECONCILIATION PRODUCTION-BEHAVIOR-ACCEPTED / P2-V0.23.26 SERVER-CANONICALIZED IMPLEMENTATION CONTENT EDITS PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED / P2-V0.23.27 INCREMENTAL IMPLEMENT CONVERGENCE PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED / P2-V0.23.28 PLAN-PREFIX IMPLEMENT CONVERGENCE PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED / P2-V0.23.29 COHERENT IMPLEMENT SOURCE UNIT PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED / P2-V0.23.30 SOURCE-ANCHORED CANDIDATE VALIDATION PROFILE PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED / P2-V0.23.31 EXPLICIT EXECUTION CONTRACT + END-TO-END ACCEPTANCE REPLAY PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED / P2-V0.23.32 BOUNDED CANDIDATE VALIDATION REPAIR + EXPLICIT CANARY IDENTITY PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED / P2-V0.23.33 CANONICAL DURABLE PLAN IDENTITY ACROSS CANDIDATE REPAIR PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED**

## P2-V0.23.33 — canonical durable PLAN identity across candidate repair — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED

Workstream: #546. Release PR: #547. Governing specification: `P2-V0.23.33`. Architecture: `ARCHITECTURE.md` v3.44.

P2-V0.23.33 separates the canonical protected PLAN identity from subordinate disposable candidate-local producer selection during one IMPLEMENT attempt. The exact `primary_plan` accepted at protected PLAN remains the only durable worker-checkpoint `plan_ref`; bounded candidate rounds retain candidate-local producer/scheduling/dispatch identity but cannot become a durable PLAN replacement. The server-owned compatibility guard preserves exact Project, run, Work Specification, acceptance contract, work graph, limits, and canonical agent admission. Candidate ceilings, Luna/Terra/Sol roster, 60-second hosted timeout, zero hidden provider retries, SafeImplementationEngine, source-lineage authority, disposable validation, Git/deployment/lifecycle authority, and human REVIEW authority remain unchanged.

Validated release and deployment evidence:

- protected SpecCritic/SpecCompiler preparation `33502875202`: SUCCESS;
- focused implementation/full regression and architecture v3.44 reconciliation `33503125360`: SUCCESS;
- exact green PR head `cef9a78892c9e97f7697f2c9ff12df2669c4d474`;
- PR #547 Bounded Autonomy `33503410878`, Workstream Spec Validation `33503410859`, and P2 CI `33503410923`: SUCCESS;
- merge / exact application source `4e5b1e3d3962221b655630891bb7cae25cb66f01`;
- post-merge Workstream Spec Validation `33503578717` and P2 CI `33503578716`: SUCCESS, including fresh promotion-boundary DSPy compilation;
- production deployment `dpl_6ahCYmgKUyaFCZJVAEB2cMfQNGMD`: `READY`, exact source `4e5b1e3d3962221b655630891bb7cae25cb66f01`, canonical alias `parallax-api-tan.vercel.app`;
- production preflights and real static-web candidate BUILD/TEST/VERIFY canary: PASS;
- production `/health` and `/ready`: HTTP 200; initial exact-deployment warning/error/fatal verification window clean.

The first dedicated-QA replay `33503995863` / job `99843617504` was invalid as release acceptance because its objective required two `.svg` targets outside both the governed text-patch allowlist and the `static-web-v1` replacement contract. Parallax correctly rejected them as `UNSAFE_TARGET`; product authority was not widened. QA PR #2 corrected only the fixture and was squash-merged as `246229a807c193ae7a44ed9a1217624d977e9131`.

Corrected authenticated replay `33506848853` / job `99852814534` exercised Engineering Run `c7c6a645-aa4e-4440-b4d3-19ff1bbc8a82` on the exact P2-V0.23.33 production deployment. Protected PLAN succeeded; durable worker checkpoints progressed through `AGENT_DISPATCH`, `AGENT_RESULT`, `AGENT_PROPOSAL`, and `CANDIDATE_SELECTED`; IMPLEMENT attempt `4240d596-41f1-42c1-be8e-dbde9a490a73` PASSED with exactly `index.html`, `styles.css`, and `app.js`; and immutable source lineage `src:eded58029c39114fd67a2aaa11b4d5a01551c170031f78a9f306e015d525b9fb` was accepted. The prior candidate-repair PLAN-ref failure did not recur. Execution then advanced to BUILD, where attempt `d987c5f5-93ed-49ee-97bb-2c8ea1b470ec` failed bounded as `AUTONOMOUS_BUILD_FAILED`. This is a genuinely later blocker and satisfies #546.

Successor #548 / P2-V0.23.34 owns the later blocker. Candidate validation already consumes the immutable PLAN-bound `static-web-v1` execution contract, but `SameLineageVercelSandboxExecutor.execute_on_lineage()` re-runs legacy `select_validation_profile()` against post-IMPLEMENT source. Marker-free static source intentionally has no Node/Python/.NET execution marker, so source-shape re-inference rejects an already-authorized static-web lineage. P2-V0.23.34 will preserve the persisted closed-catalog PLAN execution contract through same-lineage BUILD/TEST/VERIFY instead of re-inferring authority from generated source.

No database migration, generic Node/Python admission, arbitrary repository command path, provider/model/credential addition, retry/timeout increase, hidden provider retry, source-lineage authority expansion, Git/deployment/lifecycle expansion, automatic REVIEW completion, or UI redesign was added.

## P2-V0.23.31 — explicit execution contract and end-to-end acceptance replay — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED

Workstream: #539. Release PR: #541. Governing specification: `P2-V0.23.31`. Architecture: `ARCHITECTURE.md` v3.42.

P2-V0.23.31 replaces source-shape inference as the remaining marker-free greenfield execution authority with one immutable server-owned execution contract bound during protected PLAN to the exact accepted source lineage and work-specification identity. Established Parallax Python and bounded root .NET source retain their governed validation profiles; a marker-free greenfield lineage binds only the narrow `static-web-v1` contract. Generic Python and generic Node source remain fail-closed. The static-web validator is server-owned code outside candidate source, uses only deterministic HTML/local-reference and JavaScript syntax checks, and runs through the existing pinned disposable candidate sandbox. Candidate-authored markers, package scripts, command text, network policy, execution snapshots and validator source cannot change the bound authority. IMPLEMENT verifies the persisted execution contract before generation/candidate validation. Contract/profile admission failures persist only a closed server-owned phase, fixed failure kind and fixed reason-code vocabulary; raw source, generated content, exception/provider payloads and environment material remain excluded.

Validated release and deployment evidence:

- protected P2-V0.23.31 spec-first preparation / DSPy compile-and-verify run `33452271536`: SUCCESS;
- exact validated release branch head: `a1ce6564076cad7399939266cd9d1cc1b6eb7fe2`;
- release-branch completion run `33453570435`: SUCCESS, including focused execution-contract regressions, full API regression, compatibility repair, bounded diagnostic admission and architecture v3.42 reconciliation;
- PR #541 Bounded Autonomy Pilot `33453718040`: SUCCESS;
- PR #541 Workstream Spec Validation `33453717927`: SUCCESS, including committed protected DSPy plan evidence;
- PR #541 Parallax P2 CI `33453717932`: SUCCESS, including full API regression, client checks, protected promotion evaluation and DSPy release evidence;
- merge / exact application source: `27bb6b2af73dbae1809cbb168dc760cf81c977ba`;
- post-merge Workstream Spec Validation `33453948745`: SUCCESS, including changed-spec protected plan evidence;
- post-merge Parallax P2 CI `33453948968`: SUCCESS, including full API regression, client checks, protected promotion evaluation and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production API deployment `dpl_FDuJ3JKRHnvHf14mzJX59cVGasAY`: target production, state `READY`, exact application source `27bb6b2af73dbae1809cbb168dc760cf81c977ba`, canonical alias `parallax-api-tan.vercel.app`;
- production build preflights passed provider registration/private Blob, exact delivery permission, projected source (697 lineage-eligible files / 7,208,638 UTF-8 bytes), private Blob SDK, lineage composition, agentic runtime, projected bootstrap, execution-snapshot verification, and Engineering Run event schema guard;
- production candidate-validation canary: PASS under `node-v1`, with exact disposable `BUILD`, `TEST`, and `VERIFY` all protected-successful; immutable candidate digest `f2e8320d210228539bd8c44a9a2d62dccea66d4e7d29f81389b71ba148a483a4`;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact production deployment warning/error/fatal runtime scan after readiness was clean;
- backend-only client production attempt `dpl_AHh6NNdySuwEQQd7EzRgW2XokJFd` was canceled/ignored by path-aware deployment logic, so the prior READY client remains authoritative.

Authenticated real-path acceptance for P2-V0.23.31 is complete under the workstream’s explicit later-bounded-blocker alternative. On exact production deployment `dpl_FDuJ3JKRHnvHf14mzJX59cVGasAY`, the signed-in retry of Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc` restored normal session ownership, resumed the protected path, read authoritative source lineage, created and exercised a real disposable Vercel candidate sandbox, and reached protected candidate BUILD under the persisted `static-web-v1` execution contract. Production emitted `parallax_candidate_validation_failed candidate=candidate-primary stage=BUILD timed_out=False` before durable IMPLEMENT failure sequence #89. The prior `VALIDATION_PROFILE_ERROR` did not recur. This proves the explicit execution-contract and real candidate-validation boundary is active and exposes a genuinely later bounded blocker: repairable candidate-authored static-web BUILD failure was still terminal rather than consuming the already-bounded alternative-candidate slot. Workstream #539 is closed completed; successor #543 / P2-V0.23.32 owns bounded validation-guided replacement.

No generic ecosystem admission, provider/model/credential addition, retry-budget increase, hosted timeout increase, hidden provider retry, model filesystem authority, source-lineage authority expansion, Git/deployment authority expansion, lifecycle-transition authority expansion, automatic REVIEW completion or queue redesign was added.

## P2-V0.23.32 — bounded candidate validation repair and explicit canary contract identity — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED

Workstream: #543. Release PR: #544. Governing specification: `P2-V0.23.32`. Architecture: `ARCHITECTURE.md` v3.43.

P2-V0.23.32 converts one repairable `static-web-v1` disposable candidate BUILD/TEST/VERIFY rejection into a single bounded validation-guided replacement while preserving the existing two-candidate ceiling. Only an exact one-line reason from the server-owned static-web validator’s closed vocabulary can become `validation_reason_code`; only candidate-authored content/structure reasons are repairable. The rejected candidate is discarded, the replacement consumes the existing second candidate / alternative-round capacity, starts again from authoritative accepted/base source under the same approved Work Specification and immutable PLAN-bound execution contract, and reruns unchanged proposal safety, SafeImplementationEngine, real disposable BUILD/TEST/VERIFY, independent evaluation and routing. A second validation rejection is terminal and cannot create a third candidate. Raw validator output, rejected source/generated content, exception/provider payloads, filesystem roots, credentials and environment values remain excluded from repair guidance and durable evidence. If validation repair consumes the second candidate slot, ordinary competitive challenger creation is skipped. Model/provider roster, 60-second hosted timeout, zero hidden provider retries, validator-repair budget, source-lineage authority, Git/deployment/lifecycle authority and the human REVIEW ceiling remain unchanged.

Validated release and deployment evidence:

- corrected protected DSPy SpecCritic + SpecCompiler preparation `33458383302`: SUCCESS;
- focused implementation and regression validation `33459028277`: SUCCESS;
- architecture v3.43 reconciliation and governed-spec revalidation `33465359072`: SUCCESS;
- exact green PR head: `1db8760f8c2ab448c1bea6576b73a37ec7039d99`;
- PR #544 Bounded Autonomy Pilot `33465602604`: SUCCESS;
- PR #544 Workstream Spec Validation `33465602578`: SUCCESS;
- PR #544 Parallax P2 CI `33465602587`: SUCCESS, including API regression, client checks, protected promotion evaluation and committed DSPy release evidence;
- squash merge / exact application source: `421b81113a0bbe27df7a312ceec49cdc2c55899b`;
- post-merge Workstream Spec Validation `33465737419`: SUCCESS;
- post-merge Parallax P2 CI `33465737383`: SUCCESS, including full API regression, client checks, protected promotion evaluation and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production API deployment `dpl_BgLMFQY3k2q1ZSF3yL6bjJbCedCs`: target production, state `READY`, exact application source `421b81113a0bbe27df7a312ceec49cdc2c55899b`, region `iad1`, canonical alias `parallax-api-tan.vercel.app`;
- production build preflights passed provider/private Blob, exact delivery permission, projected source (700 lineage-eligible files / 7,261,577 UTF-8 bytes), private Blob SDK, lineage composition, agentic runtime, projected bootstrap, execution snapshots and Engineering Run event schema guard;
- production candidate-validation canary: PASS through real disposable `BUILD`, `TEST`, and `VERIFY`, explicitly reporting `contract=static-web-v1`, `binding=GREENFIELD_STATIC_WEB`, `ecosystem=static-web`, `profile=node-v1`, `stages=BUILD,TEST,VERIFY`, candidate digest `f2e8320d210228539bd8c44a9a2d62dccea66d4e7d29f81389b71ba148a483a4`;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact deployment warning/error/fatal runtime scan after readiness was clean.

Authenticated real-path acceptance for P2-V0.23.32 is complete under the workstream’s explicit later-bounded-blocker alternative. Trusted dedicated-QA replay `33481570167` / job `99772133148` exercised Engineering Run `171a4d64-6cf1-4c13-bac9-ddea01bb0b22` through ordinary production endpoints on exact deployment `dpl_BgLMFQY3k2q1ZSF3yL6bjJbCedCs`. The real marker-free path preserved Project, Work Specification, accepted source lineage and the immutable `static-web-v1` contract, reached primary candidate convergence with durable `CANDIDATE_PARTIAL_PROGRESS`, then later `AGENT_RESULT` and `AGENT_PROPOSAL`, and advanced into the P2-V0.23.32 validation-repair branch. Exact runtime logs show bounded Luna then Terra hosted calls during the primary proposal convergence and then `parallax_candidate_admission_failed candidate=candidate-repair phase=PROPOSAL_ASSEMBLY failure_kind=AGENTIC_CONTRACT_ERROR`; no additional repair hosted call is evidenced. The prior terminal unrepaired primary BUILD boundary therefore did not recur. This exposes a genuinely later bounded blocker: the candidate-local challenger `TeamPlan` used for alternate producer/dispatch identity is incorrectly projected into the durable worker checkpoint `plan_ref`, which is allowed to change only through an explicit human-authorized protected PLAN refresh. Workstream #543 is closed completed; successor #546 / P2-V0.23.33 owns the canonical-PLAN versus candidate-local selection identity correction. Terra in this replay is primary incremental convergence evidence, not the candidate-repair hosted generation itself.

No database migration, generic Node/Python ecosystem admission, arbitrary repository command path, new provider/model/credential, retry-budget increase, hosted timeout increase, hidden provider retry, source-lineage authority expansion, Git/deployment authority expansion, lifecycle-transition authority expansion, automatic REVIEW completion or UI redesign was added.

## P2-V0.23.30 — source-anchored candidate validation profile — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED

Workstream: #536. Release PR: #537. Governing specification: `P2-V0.23.30`. Architecture: `ARCHITECTURE.md` v3.41.

P2-V0.23.30 contracts disposable candidate-validation authority to the immutable `ValidationProfile` selected from the authoritative accepted/base workspace before any non-authoritative candidate mutation. Candidate source bytes still determine what is transferred into the disposable sandbox and what BUILD/TEST/VERIFY evaluates, but candidate edits to manifests, project files, Python markers, validation tests or other source-shape markers can no longer switch or invalidate the protected validation ecosystem, command set, dependency-preparation policy or execution-snapshot family for that attempt. A validation ecosystem/profile transition requires a separately governed capability rather than model-authored source. `ValidationProfileError` / `ExecutionPolicyError` candidate-admission failures now map only to fixed sanitized `VALIDATION_PROFILE_ERROR` evidence without exception text. SafeImplementationEngine, deny-all validation networking, dependency preparation, immutable source lineage, independent evaluation, Git/deployment/lifecycle authority, Luna/Terra/Sol routing, hosted timeout, retry ceilings and the human REVIEW boundary remain unchanged.

Validated release and deployment evidence:

- protected DSPy spec preparation run `33441277401`: SUCCESS;
- corrected focused implementation run `33441815830`: SUCCESS;
- exact green PR head: `632398afbcb9f9e28a6f87bcb6c359dbd0e26918`;
- PR Bounded Autonomy Pilot `33441973989`: SUCCESS;
- PR Workstream Spec Validation `33441973980`: SUCCESS;
- PR Parallax P2 CI `33441974505`: SUCCESS;
- squash merge / exact application source: `9768f6a3cc2d9e8c7af41523a03f1b4f528d5926`;
- post-merge Workstream Spec Validation `33442203063`: SUCCESS, including changed-spec protected plan evidence;
- post-merge Parallax P2 CI `33442203117`: SUCCESS, including full API regression, client checks, protected promotion evaluation and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production API deployment `dpl_Gygn6JBjVdPhbSkLvSKvuXrh7SGm`: target production, state `READY`, exact application source, canonical alias `parallax-api-tan.vercel.app`;
- production build preflights passed provider registration/private Blob, exact delivery permission, projected source (687 lineage-eligible files / 7,137,038 UTF-8 bytes), private Blob SDK, lineage composition, agentic runtime, projected bootstrap, execution snapshots and Engineering Run event schema guard;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact API deployment warning/error/fatal runtime scan after readiness was clean.

Authenticated real-path acceptance for P2-V0.23.30 is complete under the workstream’s explicit later-bounded-blocker alternative. On exact production deployment `dpl_Gygn6JBjVdPhbSkLvSKvuXrh7SGm`, the signed-in retry of Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc` restored session ownership, resumed successfully, read authoritative source lineage, and exercised a real Vercel sandbox lifecycle. The subsequent IMPLEMENT request completed Luna and Terra generation and advanced candidate admission to `DISPOSABLE_CANDIDATE_VALIDATION`, where the protected runtime emitted the new bounded diagnostic `failure_kind=VALIDATION_PROFILE_ERROR`. This proves the P2-V0.23.30 classification/profile-pinning boundary is active and exposes a still-later architectural blocker: execution/validation capability remains inferred from source shape rather than being bound as an explicit project/run execution contract. Workstream #536 is closed completed; successor #539 / P2-V0.23.31 owns explicit execution-contract binding plus deterministic end-to-end acceptance replay so production users are no longer the primary fault-discovery loop.

No broader validation ecosystem admission, provider/model/credential addition, retry-budget increase, hosted timeout increase, hidden provider retry, direct model filesystem authority, source-lineage authority expansion, Git/deployment authority expansion, lifecycle-transition authority expansion, automatic REVIEW completion or queue redesign was added.

## P2-V0.23.29 — coherent IMPLEMENT source unit and candidate-assembly contraction — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED

Workstream: #533. Release PR: #534. Governing specification: `P2-V0.23.29`. Architecture: `ARCHITECTURE.md` v3.40.

P2-V0.23.29 contracts ordinary production IMPLEMENT source authoring from heuristic acceptance-keyword client/server/data co-authoring to one coherent implementation work unit spanning the exact approved acceptance contract. Acceptance wording no longer creates independent canonical-source authors merely because different criteria mention client, server, browser, persistence, or similar domains. The smallest-capable-team planner selects one initial admitted implementation agent, while the unchanged Luna/Terra/Sol roster remains eligible through the existing finite candidate-recovery sequence and single final validator repair. P2-V0.23.27 incremental patch convergence and P2-V0.23.28 plan-prefix safety remain defense in depth. Exact acceptance validation, `SafeImplementationEngine`, disposable BUILD/TEST/VERIFY, independent evaluation, immutable source lineage, delivery, lifecycle, Git/deployment, and human REVIEW authority remain unchanged. Candidate admission/validation operational logs expose only bounded sanitized candidate identity, phase/fixed failure kind or protected stage/timeout classification; source/generated content, diffs, exception text, provider payloads, credentials, and filesystem roots remain excluded.

Validated release and deployment evidence:

- protected DSPy spec preparation run `33435042035`: SUCCESS;
- focused implementation run `33435434052`: SUCCESS, including coherent-topology, recovery-budget, activation, incremental-convergence, and plan-prefix regressions;
- exact green PR head: `c040895ff13885057c22a1193cf4af8a4bccbd04`;
- PR Bounded Autonomy Pilot `33435787802`: SUCCESS;
- PR Workstream Spec Validation `33435787778`: SUCCESS;
- PR Parallax P2 CI `33435787884`: SUCCESS;
- squash merge / exact application source: `282e2c2801217a63efad50f1f91e6b1e5f267ba6`;
- post-merge Workstream Spec Validation `33436229851`: SUCCESS, including changed-spec protected plan evidence;
- post-merge Parallax P2 CI `33436229844`: SUCCESS, including full API regression, client checks, protected promotion evaluation, and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production API deployment `dpl_9Csq52Q1ihkenrw3UZW8ZfRrLdka`: target production, state `READY`, exact application source, canonical alias `parallax-api-tan.vercel.app`;
- production build preflights passed provider registration/private Blob, exact delivery permission, projected source, private Blob SDK, lineage composition, agentic runtime, projected bootstrap, and execution-snapshot verification;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact API deployment warning/error/fatal runtime scan after readiness was clean.

Authenticated real-path acceptance for P2-V0.23.29 is complete under the workstream’s explicit later-bounded-blocker alternative. On exact production deployment `dpl_9Csq52Q1ihkenrw3UZW8ZfRrLdka`, the signed-in retry of Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc` resumed successfully; source-lineage reads succeeded; Luna completed and Terra completed; the coherent proposal advanced into server-owned candidate admission; and runtime emitted `candidate=candidate-primary phase=DISPOSABLE_CANDIDATE_VALIDATION failure_kind=VALUE_CONTRACT_ERROR` before any disposable BUILD/TEST/VERIFY sandbox. This is materially later than the superseded post-generation/pre-sandbox multi-work-unit assembly pattern and satisfies #533’s completion alternative by exposing a later bounded validation-profile authority blocker. Workstream #533 is closed completed; successor #536 / P2-V0.23.30 owns the accepted-source profile-pinning correction.

No provider/model/credential addition, retry-budget increase, hosted timeout increase, hidden provider retry, direct model filesystem authority, source-lineage authority expansion, Git/deployment authority expansion, lifecycle-transition authority expansion, automatic REVIEW completion, queue redesign, or generic WorkGraph/TeamPlan removal was added.

## P2-V0.23.28 — plan-prefix IMPLEMENT convergence and durable failure diagnostics — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED

Workstream: #530. Release PR: #531. Governing specification: `P2-V0.23.28`. Architecture: `ARCHITECTURE.md` v3.39.

P2-V0.23.28 removes the later cross-work-unit IMPLEMENT blocker exposed by the authenticated P2-V0.23.27 retry. Before a locally converged work unit is completed, the protected runtime now preflights its canonical patches together with the already completed non-authoritative plan prefix through the unchanged `ProposalSafetyPreflight` / `SafeImplementationEngine` boundary. A plan-prefix rejection keeps only the current work unit inside the existing finite distinct-agent recovery and single final validator-repair path; previously completed work-unit intent remains unchanged and non-authoritative, current-generation additions are not retained, and repair guidance receives only bounded target names plus fixed sanitized reason codes. Final exact-acceptance and whole-plan safe preflight remains mandatory defense in depth before disposable BUILD/TEST/VERIFY. The durable IMPLEMENT failure sanitizer now admits only the closed bounded `candidate_generation_failure` diagnostic envelope, preserving fixed reason vocabularies/counts/generations and false authority claims while dropping source/generated content, diffs, exception text, provider payloads, credentials, environment values and any true mutation/lineage/Git/deployment/REVIEW claim.

Validated release and deployment evidence:

- protected DSPy spec preparation run `33429823111`: SUCCESS;
- focused implementation run `33430746804`: SUCCESS, including 23 focused convergence/preflight/activation regressions;
- architecture validation run `33431116950`: SUCCESS;
- exact green PR head: `ce8b05ee697ce2ad987f1ebb73b1f207a141e6fd`;
- PR Bounded Autonomy Pilot `33431252351`: SUCCESS;
- PR Workstream Spec Validation `33431252363`: SUCCESS;
- PR Parallax P2 CI `33431252314`: SUCCESS;
- squash merge / exact application source: `a5346ee8da6f6b38e09f678a00fe1f973edd79a0`;
- post-merge Workstream Spec Validation `33432401374`: SUCCESS, including changed-spec protected plan evidence;
- post-merge Parallax P2 CI `33432401421`: SUCCESS, including full API regression, client checks, protected promotion evaluation, and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production API deployment `dpl_4DjbFpezU1NGJNsiCKXNRqbA7DA2`: target production, state `READY`, exact application source, canonical alias `parallax-api-tan.vercel.app`;
- backend-only production client attempt `dpl_AQ2qoQxiLjFhuWUow38cyWe6EAjW` was canceled/ignored by path-aware Vercel deployment logic, so the prior READY client remains authoritative;
- production build preflights passed provider registration/private Blob and exact delivery-permission checks before the deployment became READY;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact API deployment warning/error/fatal runtime scan after readiness was clean.

Authenticated real-path acceptance for P2-V0.23.28 is complete under the workstream’s explicit later-blocker alternative. On exact production deployment `dpl_4DjbFpezU1NGJNsiCKXNRqbA7DA2`, the signed-in retry of Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc` resumed successfully; source-lineage reads succeeded; Luna completed and Terra completed; no Sol/final validator-repair dispatch and no disposable BUILD/TEST/VERIFY followed before IMPLEMENT failed again while the production API remained healthy. This exposed a still-later post-generation/pre-sandbox source-assembly blocker rather than recurring the prior plan-prefix rejection. The completion alternative is therefore satisfied, workstream #530 is closed completed, and successor #533 / P2-V0.23.29 owns the coherent source-authoring correction.

No model/provider/credential addition, retry-budget increase, hosted timeout increase, hidden provider retry, direct model filesystem authority, source-lineage authority expansion, Git/deployment authority expansion, lifecycle-transition authority expansion, automatic REVIEW completion, or queue redesign was added.

## P2-V0.23.27 — incremental IMPLEMENT convergence — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED

Workstream: #527. Release PR: #528. Governing specification: `P2-V0.23.27`. Architecture: `ARCHITECTURE.md` v3.38.

P2-V0.23.27 changes only the resilient live IMPLEMENT proposal-admission boundary from whole-proposal regeneration to bounded incremental convergence. The protected server classifies safe-preflight failures into a fixed sanitized reason-code vocabulary, independently validates canonical patches against the authoritative workspace, retains only independently safe non-overlapping patches as non-authoritative candidate intent, isolates rejected patches, and supplies subsequent bounded repair generations only retained target names plus sanitized rejection codes. Retained targets cannot be overwritten, ancestor/descendant conflicts fail before retention, and current-generation additions are discarded if the combined retained proposal fails unchanged whole-proposal safe preflight. Convergence still requires the combined proposal to pass `SafeImplementationEngine`; disposable BUILD/TEST/VERIFY, independent evaluation, commit-time safe-engine validation, source-lineage acceptance, delivery authority, lifecycle authority, Git/deployment authority, and the human REVIEW ceiling remain unchanged.

Validated release and deployment evidence:

- protected spec-first preparation and DSPy compile/verify run `33418091097`: SUCCESS;
- focused runtime implementation/regression run `33419284259`: SUCCESS;
- focused incremental-convergence behavior and architecture run `33419461306`: SUCCESS;
- exact green PR head: `e955774274bdca0697378cf7ceeb007bab9d6efd`;
- PR Parallax P2 CI `33419601581`: SUCCESS;
- PR Bounded Autonomy Pilot `33419601582`: SUCCESS;
- PR Workstream Spec Validation `33419601635`: SUCCESS;
- merge / exact application source: `a6b61f0e278cf366e3bd7cd43a2c7c4409607c00`;
- post-merge Workstream Spec Validation `33420204270`: SUCCESS;
- post-merge Parallax P2 CI `33420204150`: SUCCESS, including full API regression, client checks, protected promotion evaluation, and promotion-boundary DSPy compilation/verification;
- production API deployment `dpl_9wJkX4CXrhgbAn9ECQPiXYMEsm83`: target production, state `READY`, exact application source, canonical alias `parallax-api-tan.vercel.app`;
- production client deployment `dpl_6CKUg7iZJRmGmWQpoPXQmh4PJRXw` for the backend-only merge was canceled/ignored by Vercel, so the prior READY client remains authoritative;
- production build preflights passed: provider registration/private Blob, exact delivery permission, projected source (678 files / 7,022,596 UTF-8 bytes), private Blob SDK, lineage composition, agentic runtime, projected bootstrap, execution snapshots, and Engineering Run event schema guard;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact API deployment warning/error/fatal runtime scan after readiness was clean, and project runtime-error aggregation found no errors in the selected verification window.

Authenticated real-path acceptance for P2-V0.23.27 completed on Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc`. The run reached durable sequence #86: PLAN completed at #79, the worker persisted CHECKPOINTED at #85, and IMPLEMENT attempt 6 failed at #86 with `AUTONOMOUS_IMPLEMENT_FAILED`. Exact production logs showed source-lineage reads succeeding and Luna then Terra completing hosted generations, but no Sol/final validator-repair generation and no disposable BUILD/TEST/VERIFY after Terra. This satisfied #527's explicit completion alternative by exposing a later bounded cross-work-unit blocker after incremental convergence rather than reverting to whole-proposal regeneration. Workstream #527 is closed completed; successor #530 / P2-V0.23.28 owns the later blocker.

No model/provider/credential addition, retry-budget increase, hosted timeout increase, hidden provider retry, direct model filesystem authority, source-lineage authority expansion, Git/deployment authority expansion, lifecycle-transition authority expansion, automatic REVIEW completion, or queue redesign was added.

## P2-V0.23.26 — server-canonicalized implementation content edits — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED

Workstream: #519. Release PR: #525. Governing specification: `P2-V0.23.26`. Architecture: `ARCHITECTURE.md` v3.37.

P2-V0.23.26 removes model-owned unified-diff mechanics from hosted IMPLEMENT generation while preserving the existing canonical safe-patch and source-lineage authority. Hosted DSPy generation now returns exact acceptance coverage plus bounded typed `{path, content}` file intent. The protected server binds existing targets to authoritative source SHA/content, classifies absent selected paths only as empty-base new-file intent, deterministically renders strict single-file unified diffs including no-final-newline markers, and then constructs the unchanged downstream `ImplementationProposal`. Duplicate and no-op content intents fail before candidate admission. Existing path, secret, symlink, extension, size, hierarchy, stale-source, collision, source-lineage, disposable BUILD/TEST/VERIFY, delivery, lifecycle, Git/deployment, and human REVIEW controls remain authoritative.

Validated release and deployment evidence:

- spec-first preparation run `33391451812`: SUCCESS, including protected DSPy SpecCritic/SpecCompiler plan generation and verification;
- focused implementation run `33392060970`: SUCCESS;
- exact green PR head: `8156832c51373f743a0afab2aa69f33e022c60c9`;
- PR Bounded Autonomy Pilot `33392511170`: SUCCESS;
- PR Workstream Spec Validation `33392511127`: SUCCESS;
- PR Parallax P2 CI `33392511167`: SUCCESS;
- squash merge / exact application source: `15a02cdeac4f36b1ca6701bccc4d209b747e8dca`;
- post-merge Workstream Spec Validation `33392742869`: SUCCESS;
- post-merge Parallax P2 CI `33392742926`: SUCCESS;
- production API deployment `dpl_GzfqpAS5Sex1sZNSfXHKnhEosJph`: target production, state `READY`, exact application source, canonical alias `parallax-api-tan.vercel.app`;
- production client deployment for the same backend-only source was intentionally ignored/skipped by Vercel, so the prior READY client remains authoritative;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact API deployment warning/error/fatal runtime scan after readiness was clean, and project runtime-error aggregation found no errors in the selected verification window.

Authenticated real-path acceptance for P2-V0.23.26 is complete. The same Engineering Run progressed through the server-canonicalized `{path, content}` boundary without reintroducing model-owned unified-diff parsing/canonicalization failure and exposed a later protected proposal-admission blocker before BUILD. This satisfies #519's explicit completion alternative; workstream #519 is closed completed, with the later blocker governed by P2-V0.23.27 and P2-V0.23.28.

No model/provider/credential addition, retry-budget increase, timeout increase, hidden transport retry, arbitrary recursive filesystem authority, Git/deployment authority expansion, lifecycle-transition authority expansion, automatic REVIEW completion, or queue redesign was added.

## P2-V0.23.25 — safe nested source creation and ambiguous transport reconciliation — PRODUCTION-BEHAVIOR-ACCEPTED

Workstream: #514. Release PR: #515. Governing specification: `P2-V0.23.25`. Architecture: `ARCHITECTURE.md` v3.36.

P2-V0.23.25 removes two blockers exposed by authenticated Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc`. First, validated new text-file patches may now carry bounded missing-parent intent inside the workspace: preparation remains side-effect-free, commit creates only the recorded safe parent segments after containment/type/symlink rechecks, rollback removes only recorded directories that remain empty, and file-target ancestry conflicts fail before mutation. Existing traversal, secret, extension, size, stale-base, canonicalization, source-lineage, Git/deployment, lifecycle, and human REVIEW controls remain authoritative. Second, when an autonomy POST fails only as a response-less transport exception, the client performs one read-only latest-run reconciliation and accepts recovered progress only for the same Engineering Run at a strictly newer authoritative revision; otherwise it preserves the error and does not send a duplicate POST from an uncertain revision.

Validated release and deployment evidence:

- spec-first preparation run `33383836394`: SUCCESS, including SpecCritic + SpecCompiler and committed protected DSPy plan;
- focused implementation run `33384739256`: SUCCESS after a TypeScript narrowing correction; nested-source safety/canonicalization, client type/state tests, and protected authority-surface checks passed;
- full API regression alignment run `33386954353`: SUCCESS; the superseded legacy missing-parent assertion was updated to the governed commit-time creation contract and the temporary workflow removed;
- exact green PR head: `3a03664ec3a060cee0859d3e0d0a7c3c61773336`;
- PR Parallax P2 CI `33387321232`: SUCCESS;
- PR Workstream Spec Validation `33387321262`: SUCCESS;
- PR Client Visual Validation `33387321240`: SUCCESS;
- PR Bounded Autonomy `33387321274`: SUCCESS;
- squash merge / exact application source: `3d53599c4659162cfe45bbc4809f3f329d0abb73`;
- post-merge Workstream Spec Validation `33387562760`: SUCCESS, including changed-spec protected plan evidence;
- post-merge Parallax P2 CI `33387562779`: SUCCESS, including full API regression, client checks, protected promotion evaluation, and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and plan verification;
- production client deployment `dpl_HA9KJ1kqy9xUKdQsi8of2zGDiEP4`: target production, state `READY`, exact application source;
- production API deployment `dpl_264xsb2C1yyaYb2aBFFVYzfj5t6G`: target production, state `READY`, exact application source, canonical alias `parallax-api-tan.vercel.app`;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- production build preflights passed, including lineage composition (672 files / 6,913,615 bytes), agentic runtime, projected bootstrap, execution snapshots, and run-event schema guard;
- exact API deployment warning/error/fatal runtime scan immediately after readiness was clean;
- temporary P2-V0.23.25 regression-alignment workflow is absent from `main`.

Authenticated real-path acceptance for P2-V0.23.25 is complete. Subsequent retries of the same Engineering Run progressed beyond the former nested-parent `unsafe_target` rejection; on the later P2-V0.23.26 acceptance attempt no `unsafe_target` event recurred and execution continued through source-lineage reads and hosted generation into later proposal admission. Workstream #514 is closed completed. The response-loss ambiguity did not recur in the acceptance attempt, and no duplicate mutation request was manufactured.

No additional model retry budget, hosted-model timeout, hidden transport retry, provider/model roster, credential authority, recursive filesystem authority, source writer, Git/deployment authority, lifecycle-transition authority, automatic REVIEW completion, or queue redesign was added.

## P2-V0.23.24 — fresh final validator repair generation — PRODUCTION-BEHAVIOR-VERIFIED

Workstream: #512. Release PR: #513. Governing specification: `P2-V0.23.24`. Architecture: `ARCHITECTURE.md` v3.35.

P2-V0.23.24 corrects the authenticated production failure discovered after P2-V0.23.23. The prior final validator-repair assignment was selected correctly, but its Terra request was identical to an earlier validator-guided request, allowing DSPy in-process caching to replay the already-rejected proposal in about 7 ms rather than performing the intended fresh hosted generation. The final `CANDIDATE_VALIDATION_REPAIR` request now receives the existing safe validator guidance plus a final-repair-only server-owned constraint containing a bounded deterministic context token derived from authoritative run revision, work-unit identity, and repair generation. That changes only request/cache identity; it carries no rejected output or source material and grants no new authority.

Validated release and deployment evidence:

- exact reviewed PR head: `7c3dc0864f834c9ee58715e087ff5cbfd38646f0`;
- spec-first preparation run `33367240179`: SUCCESS and committed protected DSPy plan;
- focused implementation gate `33368039034`: SUCCESS;
- PR Parallax P2 CI `33368162041`: SUCCESS;
- PR Bounded Autonomy `33368162065`: SUCCESS;
- PR Workstream Spec Validation `33368162106`: SUCCESS;
- squash merge / exact application source: `6295948d1f8230e769ba67a81b4a0f5ee61f9433`;
- post-merge Workstream Spec Validation `33382027091`: SUCCESS;
- post-merge Parallax P2 CI `33382027044`: SUCCESS, including full API regression, client checks, protected promotion evaluation, and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production API deployment: `dpl_Am5D5JkShtNHnXYuFcDBfnrYK7i2`, target production, state `READY`, canonical alias `parallax-api-tan.vercel.app`;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- one-repair ceiling remains exactly one per work unit; global DSPy caching, 60-second hosted-model timeout, zero hidden transport retries, model/provider roster, safe patch validation/canonicalization, source-lineage authority, Git/deployment authority, lifecycle authority, and human REVIEW ceiling are unchanged.

Production behavior acceptance completed on the affected authenticated Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc`. On exact deployment `dpl_Am5D5JkShtNHnXYuFcDBfnrYK7i2`, the retry returned HTTP 200 and emitted `parallax_final_validator_repair_dispatch generation=7 context=7176413ebb4b332036c3fcee`; immediately afterward Parallax started a real Vercel AI Gateway Terra completion at 10:34:35 UTC. That hosted call completed at 10:35:12 UTC and was classified `validation_failed` after about 36.7 seconds. This proves the final repair request is cache-distinct and genuinely fresh rather than the prior approximately 7 ms DSPy cache replay. The fresh proposal still failed protected validation, which is a separate implementation-capability blocker and does not invalidate P2-V0.23.24 acceptance. Workstream #512 is closed completed with the evidence recorded.

No database migration, new queue, model/provider/credential, source writer, Git mutation authority, deployment authority, lifecycle-transition authority, automatic REVIEW completion, or additional retry budget was added.

## P2-V0.23.23 — bounded validator repair — PRODUCTION-BEHAVIOR-VERIFIED

Workstream: #510. Release PR: #511. Governing specification: `P2-V0.23.23`. Architecture: `ARCHITECTURE.md` v3.34.

P2-V0.23.23 closes the finite candidate-recovery gap exposed after P2-V0.23.22 removed the former 300-second request timeout. A work unit that exhausts its distinct admitted implementation agents may now receive exactly one additional validator-guided proposal generation only when a prior candidate was server-classified `VALIDATION_EXHAUSTED`. The retry deterministically reuses the most recent validator-rejected admitted agent for that work unit, receives the existing static safe-patch repair guidance, and then passes through the unchanged typed proposal schema, exact acceptance ownership, strict patch canonicalization/verifier, disposable BUILD/TEST/VERIFY, independent evaluation, canonical source writer, delivery authority, durable lifecycle authority, and human REVIEW ceiling. Provider-only failures cannot authorize the retry; a provider failure on the repair consumes the one-repair budget. The 60-second hosted-model timeout and zero hidden transport retries remain unchanged.

Validated release and deployment evidence:

- exact reviewed PR head: `e814e0b7878f146ea6d84257760eb119f3551b13`;
- PR Bounded Autonomy `33365009741`: SUCCESS;
- PR Workstream Spec Validation `33365009754`: SUCCESS;
- PR Parallax P2 CI `33365009828`: SUCCESS;
- squash merge / exact application source: `256254a0922e7bea113a5902c353c4038bd0cf99`;
- post-merge Workstream Spec Validation `33365184589`: SUCCESS;
- post-merge Parallax P2 CI `33365184587`: SUCCESS, including full API regression, client checks, protected promotion evaluation, and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production API deployment: `dpl_3NuuSdj1aZCx3N2Y5c1ru9UFAAv1`, target production, state `READY`, canonical alias `parallax-api-tan.vercel.app`;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- production provider, exact delivery permission, projected-source, private Blob SDK, lineage composition, agentic runtime, projected bootstrap, execution-snapshot, and run-event schema preflights all passed;
- exact-deployment error/fatal runtime scan after readiness was clean;
- the client deployment generated by this backend-only merge was canceled/ignored, so the existing client production release remains authoritative.

Production behavior acceptance for P2-V0.23.23 is complete through the authenticated P2-V0.23.24 proof. After distinct-agent validation exhaustion, Parallax emitted `parallax_final_validator_repair_dispatch` and performed a real fresh Terra hosted completion before a later protected validation rejection. The affected run therefore no longer failed solely because the distinct admitted-agent set was exhausted. Workstream #510 is closed completed; later proposal-quality/admission blockers were governed separately.

No database migration, source-authority widening, new model/provider/credential, Git mutation authority, deployment authority, lifecycle-transition authority, automatic REVIEW completion, or retry loop was added.


## P2-V0.23.22 — request-bounded autonomous builds — PRODUCTION-VERIFIED

Workstream: #508. Release PR: #509. Governing specification: `P2-V0.23.22`. Architecture: `ARCHITECTURE.md` v3.33.

P2-V0.23.22 removes the production 300-second autonomous-build failure mode exposed by Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc`. Production `/autonomous` now performs at most one protected lifecycle transition per HTTP request. The client continues only from the newly returned authoritative revision, uses a deterministic revision-bound operation key, stops at terminal or human boundaries, and enforces an eight-request hard ceiling. VERIFY -> REVIEW remains correctly classified as `REVIEW_REQUIRED`. Implementation generation now uses typed DSPy output fields under explicit JSON adaptation, while the strict server-owned implementation proposal validator remains authoritative. Hosted Vercel AI Gateway calls use a 60-second request timeout with zero hidden transport retries; explicit admitted candidate recovery remains the governed retry path.

Release and production evidence:

- exact green PR head: `261c38f0b7ebe27b1058c5c16d727520cb7202ec`;
- squash-merged application source: `e51793cceddb640f122f458554c7082c70b585fb`;
- production API deployment: `dpl_BgZQVz3S2QeTTP7uxcE6ARuVHPUD`, target production, state `READY`, canonical alias `parallax-api-tan.vercel.app`;
- production client deployment: `dpl_AYNh9LqhPm8qFrXfnqRJeXwsTeYA`, target production, state `READY`, exact same application source;
- post-merge Parallax P2 CI `33361126044`: SUCCESS, including full API regression, client checks, protected promotion evaluation and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- post-merge Workstream Spec Validation `33361126056`: SUCCESS;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- production provider, exact delivery permission, projected source, private Blob SDK, lineage composition, agentic runtime, projected bootstrap, execution-snapshot and run-event schema preflights all passed;
- dedicated production replay `33361676731`: SUCCESS;
- Python job `99394089315`: Engineering Run `75380966-77d7-4db0-a31c-6500f313563c` advanced across five bounded HTTP 200 requests: PLAN -> IMPLEMENT (9s), IMPLEMENT -> BUILD (21s), BUILD -> TEST (10s), TEST -> VERIFY (11s), VERIFY -> REVIEW (13s); final state REVIEW; authenticated source-only ZIP 7 entries / 1,418 bytes;
- OT Time/.NET job `99394089261`: Engineering Run `11657ce8-9463-4a21-b458-694412c21981` advanced across five bounded HTTP 200 requests: PLAN -> IMPLEMENT (10s), IMPLEMENT -> BUILD (47s), BUILD -> TEST (24s), TEST -> VERIFY (30s), VERIFY -> REVIEW (32s); final state REVIEW; authenticated source-only ZIP 32 entries / 74,823 bytes;
- longest observed production autonomy request was 47 seconds, far below the former 300-second function boundary;
- runtime scans across acceptance found no HTTP 504 and no `FUNCTION_INVOCATION_TIMEOUT`; all ten accepted `/autonomous` requests were HTTP 200;
- both source-only acceptance paths recorded `source_publication=false` and `app_deployment=false`.

The dedicated QA scripts now exercise the same revision-bound, maximum-eight-request continuation contract as the product client. An initial replay correctly proved PLAN -> IMPLEMENT but exposed a QA-only assertion that treated the response `steps` evidence array as a lifecycle-transition count; that harness assertion was removed without changing product runtime behavior. QA Harness CI then passed. The temporary push trigger used to initiate the final production replay was restored immediately; standing `Ryan9876/parallax-qa/.github/workflows/production-replay.yml` is manual-only with canonical blob SHA `cfb41caffd5e16531b28d55f65eb730cb8fcc082` at QA main commit `695759cd11ab38b30fb4cf0a1968c8b340f231d1`.

No new queue, credential, source writer, Git mutation authority, deployment authority, lifecycle authority, or REVIEW completion authority was added. Canonical source lineage, durable worker recovery, strict patch validation/canonicalization, disposable BUILD/TEST/VERIFY, protected evaluation, delivery policy and the human REVIEW ceiling remain authoritative.


## CI/CD development pipeline optimization — MAIN-VERIFIED

PR #503 changed the engineering validation topology to reduce development latency without relaxing protected promotion or production governance. Exact merge source `85d6edc2d8d9e23c97429aa0e0d6a263174180c6` is on `main`. This is a workflow/policy release; it does not claim a newer application deployment or change product runtime authority.

Validated behavior:

- independent API, client, protected-promotion evaluation and DSPy validation jobs no longer serialize behind the API suite, so one CI attempt can expose independent failures together;
- ordinary pull requests validate committed DSPy plan evidence deterministically, while fresh SpecCritic/SpecCompiler execution is reserved for `main` push/manual promotion boundaries;
- browser/Skia acceptance and dependency audit are path-scoped to client changes instead of running for unrelated API/spec/governance work;
- Bounded Autonomy retains its protected execution/autonomy tests but no longer duplicates the full API and client suites; legacy status contexts are preserved without duplicate execution;
- full API regression coverage, protected Code/Engineering/Reason benchmark rejection, committed DSPy evidence, production QA/replay requirements, deployment authority and the REVIEW ceiling are unchanged.

Validation evidence:

- PR #503 exact head `e7bdfa245754acb006ca5275339f3dbb56a23140`;
- PR Parallax P2 CI `33347033544`: SUCCESS; API/contracts, fast client, protected promotion evaluation and deterministic committed-plan DSPy validation all passed independently;
- PR Bounded Autonomy `33347033542`: SUCCESS; focused protected autonomy checks passed and compatibility client context completed without rerunning the client suite;
- PR Client Visual Validation `33347033522`: SUCCESS after correcting the split workflow to use the repository's established client dependency installation;
- post-merge main Parallax P2 CI `33347210262`: SUCCESS, including full API regression, client checks, protected promotion evaluation and fresh promotion-boundary DSPy SpecCritic/SpecCompiler validation;
- post-merge main Client Visual Validation `33347210250`: SUCCESS.

The observed PR fast-client job completed in about 68 seconds versus about 169 seconds for the prior client job that also installed Chromium and ran browser/Skia acceptance. The larger architectural benefit is that unrelated failures no longer force later independent gates to be discovered on separate reruns.

## P2-V0.23.17 / P2-V0.23.18 — dedicated QA proof and exact model patch canonicalization — PRODUCTION-ACCEPTED

P2-V0.23.17 / Architecture v3.29 moved standing production-QA identity to the dedicated `Ryan9876/parallax-qa` repository and bound authorization to an exact signed `(repository, repository_id, workflow_ref)` tuple. The dedicated repository path is behaviorally production-proven. P2-V0.23.19 / Architecture v3.31 completed that staged cutover: the two migration-only `Ryan9876/parallax` QA tuples are retired, leaving only the exact dedicated repository tuple as standing production-QA trust.

P2-V0.23.18 / Architecture v3.30 adds a server-owned exact patch-intent canonicalization boundary only for protected model-generated IMPLEMENT proposals. Mechanical unified-diff headers, counts, positions and an anchored stale model base digest may be recovered only when exact current protected source proves the edit intent. Ambiguous, fuzzy, semantic, unanchored stale-base, unsafe-target, secret-sensitive, size-limit and other protected failures remain fail-closed, and every recovered patch is re-parsed by the unchanged strict `TextPatchEngine` before candidate admission or mutation.

Release and production evidence:

- workstream: #501; release PR: #502;
- exact green PR head: `8fbcb6ff320289f0d13e9a56f10201768a32199c`;
- application merge / deployed API source: `8e9efa4afec667b644a6a94063a463d72d10cd58`;
- production deployment: `dpl_2zTNwf1m59cZmNRAWqWXdZ1pw9tw`, target production, state `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- post-merge Workstream Spec Validation `33348830525`: SUCCESS;
- post-merge Parallax P2 CI `33348830492`: SUCCESS, including full API regression, client checks, protected promotion evaluation and promotion-boundary DSPy validation;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact dedicated-repository acceptance workflow `Ryan9876/parallax-qa` run `33349444286`: SUCCESS;
- dedicated Python source-only job: SUCCESS;
- dedicated P2-V0.23.18 OT Time existing-file acceptance job `99359771040`: SUCCESS;
- OT Time Engineering Run `a3a6f6bc-b341-4cb4-98b8-dbc3219ed49b` advanced PLAN -> IMPLEMENT -> BUILD -> TEST -> VERIFY -> REVIEW, revision 6, with `last_failure_code=null`;
- IMPLEMENT passed using `safe-source-implementation-v1` against an existing `README.md` edit rather than the prior new-file smoke path;
- authenticated source-only ZIP handoff verified 31 entries / 74,567 bytes and contained the exact accepted README marker;
- source publication: false; application deployment by the generated workload: false.

This closes the P2-V0.23.18 workload-sensitive candidate-validation blocker without widening model count, retry ceilings, source-lineage authority, Git/deployment authority, or the human REVIEW boundary. Its planned follow-up trust contraction is now complete under P2-V0.23.19.

## P2-V0.23.19 — dedicated production-QA trust contraction — PRODUCTION-VERIFIED

Workstream: #499. Release PR: #505. Governing specification: `P2-V0.23.19`. Architecture: `ARCHITECTURE.md` v3.31.

P2-V0.23.19 completes the staged P2-V0.23.17 migration. Standing GitHub Actions production-QA authorization is now exactly one server-owned tuple: repository `Ryan9876/parallax-qa`, stable GitHub repository ID `1351817336`, workflow `Ryan9876/parallax-qa/.github/workflows/production-replay.yml@refs/heads/main`. The former `Ryan9876/parallax` `qa-production-replay.yml` and `w8-s2-qa-replay.yml` identities are rejected and their standing workflow files are absent from the application repository. Issuer, `parallax://qa-production` audience, `refs/heads/main`, GitHub-hosted runner, admitted event set, bounded run-ID validation and bounded QA-principal mapping remain unchanged.

Release and production evidence:

- exact green PR head: `7a68e91e2ced95c1c9939391718f339c97b0a271`;
- release merge / deployed API source: `ea00a943d4bc5f00f0f5416881d482c0f799be63`;
- production deployment: `dpl_ACcZLXGNc9Rt1kBekWRJaFw9Vov8`, target production, state `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- exact-head Parallax P2 CI `33350296468`: SUCCESS;
- exact-head Bounded Autonomy `33350296492`: SUCCESS;
- exact-head Workstream Spec Validation `33350296493`: SUCCESS;
- post-merge Workstream Spec Validation `33350390486`: SUCCESS;
- post-merge Parallax P2 CI `33350390524`: SUCCESS, including full API regression, client checks, protected promotion evaluation and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact-deployment post-release error/fatal runtime-log scan: clean in the checked window;
- dedicated-repository production replay `33350555555`: SUCCESS under the contracted one-tuple trust set;
- Python job `99362951997`: SUCCESS; Project `d00e23cb-6d84-4805-bf15-4f738d920136`, Engineering Run `1b3c3413-2854-4af9-9625-d6d1838d0357`, final state REVIEW, authenticated source-only ZIP 7 entries / 1,422 bytes;
- OT Time job `99362951812`: SUCCESS; Project `7b4c2377-6f06-4b43-b174-206e059e24f0`, Engineering Run `beadb914-1ab5-45b2-ba72-50b31efe1f16`, final state REVIEW, authenticated source-only ZIP 32 entries / 74,712 bytes;
- both routine replays recorded `source_publication=false` and `app_deployment=false`;
- the temporary QA push trigger used only to initiate the accepted replay was removed immediately afterward; `Ryan9876/parallax-qa` main is restored to manual-only production replay at commit `7ec51807bcd68c8a411f36c41dcb7b0bc941838c`.

This release contracts authentication surface only. Normal user authentication, the bounded QA principal, Project / Work Specification / Engineering Run authority, accepted source lineage, hosted-model routing, worker recovery, Git/deployment authority and the human REVIEW ceiling are unchanged. Rollback restores only the previously deployment-verified exact tuples; wildcard or partial-claim trust remains prohibited.

## P2-V0.23.20 — exact GitHub empty-repository ref compatibility — PRODUCTION-DEPLOYMENT-VERIFIED / CANONICAL GREENFIELD ACCEPTANCE STILL OPEN

Workstream: #442. Release PR: #506. Governing specification: `P2-V0.23.20`. Architecture: `ARCHITECTURE.md` v3.32.

P2-V0.23.20 corrects the authenticated greenfield inspection boundary for GitHub's exact empty-repository default-ref response: HTTP 409 with message `Git Repository is empty.` is accepted as no head only after canonical repository identity/default-branch verification. Existing HTTP 404 no-head behavior remains equivalent; malformed or unrelated 409 responses, ordinary shared Git-ref conflicts, 422 responses and other provider failures remain fail-closed. The shared GitHub ref reader is unchanged and no pre-REVIEW mutation authority was added.

Release evidence: exact merge/deployed API source `bfc2373d690113a592a52ca8a12fc6b5343d481d`; production deployment `dpl_AUapYhiyoD2G16t8uH4AzR5hqKQv` is READY on `parallax-api-tan.vercel.app`; post-merge Workstream Spec Validation `33353572435` and Parallax P2 CI `33353572439` succeeded, including full API regression, protected promotion and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification; `/health` and `/ready` both returned HTTP 200 with database/providers ready.

The fresh user-approved canonical target `Ryan9876/parallax-qa1` (repository ID `1351932371`) was positively verified truly empty before both bounded attempts and remains empty afterward. Corrected dedicated-QA replay `33353749430` / job `99371868349` used exact deployed source `bfc2373d690113a592a52ca8a12fc6b5343d481d`; Project `ba697355-424c-4d86-8b89-3cf23455a6f5`, Work Specification `7f8effdf-be77-4a2d-8967-8780cf41fe73`, Engineering Run `dd81cacd-932c-4414-9dae-c906beee24a9`. The run stopped safely at PLAN with `AUTONOMOUS_REQUEST_FAILED_HTTP_503`, zero out-of-band source edits and runtime provider-repository failure `PROVIDER_INVALID_RESPONSE`. No repository initialization, branch, PR or Preview mutation occurred.

Therefore the compatibility release itself is production-deployment-verified, but #442 / AC-27 full canonical greenfield acceptance remains open. Positive exact GitHub App / Vercel Connect coverage for `Ryan9876/parallax-qa1` must be established through the existing provider/user authorization boundary before another frozen Decision Ledger retry; provider/source failure alone must not be reinterpreted as greenfield.

## P2-V0.23.21 — bounded greenfield inspection diagnostics — PRODUCTION-VERIFIED / EXTERNAL EXACT-REPOSITORY AUTHORIZATION REQUIRED

Workstream: #442. Release PR: #507. Governing specification: `P2-V0.23.21`. Architecture remains `ARCHITECTURE.md` v3.32 because the release changes observation only and does not alter durable authority, lifecycle, provider, persistence, recovery, source-lineage, Git, deployment, or REVIEW semantics.

P2-V0.23.21 closes the diagnostic blind spot at the authenticated greenfield inspection fallback. When that protected inspection fails, runtime emits only fixed event `greenfield_repository_inspection_failed` plus the existing bounded normalized provider result code, or fixed `UNCLASSIFIED_PROVIDER_FAILURE` when no protected code exists. Raw exception/provider payload material is not logged. Structured `REPOSITORY_AUTHORIZATION_REQUIRED` recovery and the original public-source outward failure for every other inspection failure remain unchanged.

Release evidence: exact merge/deployed API source `71849d0979d940065efdefc909f1937272c87834`; production deployment `dpl_CoTeZoRWcupTLhJkD9viUE8YfBB3`, target production, READY on `parallax-api-tan.vercel.app`; post-merge Workstream Spec Validation `33355379613` SUCCESS; post-merge Parallax P2 CI `33355379617` SUCCESS including full API regression, client checks, protected promotion, and fresh main SpecCritic/SpecCompiler compilation + verification; `/health` and `/ready` HTTP 200 with database/providers ready; pre-replay runtime error scan clean.

Fresh-target diagnostic replay `Ryan9876/parallax-qa` run `33355557297`, job `99376902748`, checked out exact deployed source and positively verified `Ryan9876/parallax-qa1` (repository ID `1351932371`) empty immediately before execution. Canonical Project `ba697355-424c-4d86-8b89-3cf23455a6f5`; Conversation `516f4d7a-2ce7-4df4-acf4-b8fc56aa891f`; Work Specification `960709f3-1db6-425a-8d34-d1e050ca0c51` revision 1; Engineering Run `aa53bb66-d0fc-4423-ae89-b7367cd54603`. The run stopped safely at PLAN revision 1 with disposition `AUTONOMOUS_REQUEST_FAILED_HTTP_503`, zero clarifications, and zero out-of-band source edits.

Exact deployment runtime evidence captured `greenfield_repository_inspection_failed result_code=REPOSITORY_AUTHORIZATION_REQUIRED`. This proves the remaining W9-S1 blocker is the existing external provider/user authorization boundary: `Ryan9876/parallax-qa1` is not covered by the `github/parallax-runtime` GitHub App / Vercel Connect exact-repository authorization. The prior outward public-source `PROVIDER_INVALID_RESPONSE` was masking that authenticated result by the preserved public-first fallback; this is not another empty-repository parsing defect.

After replay, `Ryan9876/parallax-qa1` was re-verified still truly empty; no REVIEW-only baseline initialization, branch, PR, or Preview mutation occurred. The dedicated QA workflow was restored immediately to standing manual-only content SHA `cfb41caffd5e16531b28d55f65eb730cb8fcc082` at `Ryan9876/parallax-qa` commit `cb4a772adecd237df42367efa3bc6a673b9792b2`.

#442 remains open. Canonical completion now requires external exact-repository authorization for `Ryan9876/parallax-qa1`, followed by the same frozen Decision Ledger retry. Full AC-27 greenfield acceptance is not claimed until the ordinary protected lifecycle reaches accepted implementation/validation, REVIEW-only initialization, bounded branch/PR, READY Preview, and REVIEW.

## Current production truth

Parallax production now has verified end-to-end source-only engineering paths for both the established Python validation profile and the admitted .NET validation profile. In each accepted path, the bounded QA identity creates or reuses a Project, creates a conversation, produces and approves a Work Specification, activates an Engineering Run, bootstraps exact public GitHub source, advances through protected PLAN, IMPLEMENT, BUILD, TEST and VERIFY, stops at REVIEW, and returns an authenticated ZIP of the accepted source lineage.

W8-S2 is now complete. The former OT Time failure was reduced from public-source bootstrap, to missing .NET sandbox readiness, and finally to independent defects in the OT Time benchmark repository itself. Parallax now selects a dedicated server-owned .NET execution snapshot for `dotnet-v1`; production preflight verifies exact snapshot identity, deny-all networking, fixed toolchain readiness and source-free state. After the OT Time benchmark was independently repaired and validated, the canonical authenticated production replay reached REVIEW at revision 6 with no failure and verified the exact-lineage source-only handoff.

The public-source bootstrap remains independent from Vercel application delivery. Public commit-bearing GitHub source uses Git smart HTTP plus exact commit-addressed codeload archives. Source-only Projects do not require a Vercel Project, Preview target, application deployment, GitHub publication, or production-promotion authority.

P2-V0.23.8 / Architecture v3.22 is now production-deployment-verified. Rejected pre-mutation implementation candidates are distinct from worker/process loss and may recover only through deterministic, already-admitted alternate agents within the existing reassignment bound. Protected proposal validation and all canonical source, lineage, Git, deployment, and REVIEW authority remain unchanged.

P2-V0.23.9 / Architecture v3.23 is now production-deployment-verified and has a successful authenticated normal-path production replay. The production incident showed that all already-admitted alternates could independently return provider-successful proposals that the protected safe-patch validator rejected; later admitted candidates now receive only fixed server-owned validator-repair guidance after a bounded `VALIDATION_EXHAUSTED` classification. Provider/rate-limit failures remain separate, retry bounds are unchanged, and no mutation authority is added. The corrected post-deploy OT Time replay reached REVIEW at revision 6 with no failure and verified the authenticated source-only ZIP handoff. The replay did not artificially induce candidate rejection; branch-specific validator-guided recovery is established by deterministic protected tests.

The production client now projects resumed component health against the latest persisted control boundary rather than treating an older worker failure as current health forever. Historical failure events remain visible and unchanged. After a later persisted `RUN_CONTROL / RESUMED` event, an older dedicated worker failure is presented as `Awaiting evidence` until fresh worker evidence arrives. Worker IDs and source-lineage references on unrelated failed events are observation references only; they no longer cause Worker runtime or Source lineage to inherit that event failure. Dedicated lineage acceptance evidence remains authoritative for lineage health.

Safe deletion is now production-accepted. The previously deployed P2-V0.18.12 logical-deletion correction has an authenticated post-cutover production smoke proving the active-work 409 guard, terminal cancellation path, Project and bound-conversation disappearance from active reads, active slug/repository identity reuse, fixture cleanup, and zero external-provider mutation. Internal protected-evidence retention and non-owner authorization remain established by the exact-head regression suite; production does not expose a deleted-history audit read merely for QA.

W9-S1 empty-greenfield initialization authority is now implemented and production-deployment-verified under P2-V0.23.7 / Architecture v3.21. Parallax can positively inspect an exact credentialed repository as empty, create an explicit zero-file greenfield root lineage, preserve the ordinary protected lifecycle, and at REVIEW use a separate fixed `repository.initialize-empty` capability before ordinary bounded publication. The canonical Decision Ledger end-to-end acceptance is not yet complete because its fixed disposable repository was initialized by earlier Parallax QA fixture activity before this release; v3.21 did not mutate that target.

## P2-V0.23.10 — Hosted model escalation ordering — PRODUCTION-ACCEPTED

Workstream: #453. Governing specification: `P2-V0.23.10`. Architecture: `ARCHITECTURE.md` v3.24.

Production evidence showed autonomous IMPLEMENT could invoke `openai/gpt-5.6-sol -> openai/gpt-5.6-terra -> openai/gpt-5.6-luna` even though the canonical hosted escalation policy is `Luna -> Terra -> Sol`. The cause was deterministic SHA-256 identity sorting inside agent-team orchestration, which unintentionally made an integrity identifier a routing priority.

The implementation adds bounded server-owned selection priority to admitted-agent evidence and canonicalizes roster, selected-team and unit-eligibility order from that policy. Hosted implementation priorities are Luna `0`, Terra `1`, Sol `2`; equal priorities retain identity-digest tie determinism. Candidate-rejection recovery and the existing validator-guided repair path consume the same canonical admitted sequence. Capability admission, proposal validation, candidate validation, source mutation, lineage, Git/deployment and REVIEW authority are unchanged.

The P2-V0.23.10 implementation is now present in the exact production API source recorded below. Its focused orchestration, candidate-recovery and runtime-activation regressions plus full protected release gates passed before the later P2-V0.23.11 release, and the shared exact production deployment is READY. Representative authenticated production autonomous evidence now proves Luna-first hosted implementation selection. Luna was attempted first on the accepted current-source OT Time replay before bounded fallback to Terra and Sol when lower-tier proposal/output validation did not pass; the server-owned route order remains `Luna -> Terra -> Sol`.

## P2-V0.23.13 / P2-V0.23.14 — Failed IMPLEMENT replan and recovered-worker PLAN rebind — PRODUCTION-ACCEPTED

P2-V0.23.13 / Architecture v3.26 adds one narrow human-authorized retry transition for Project-bound agentic runs that are durably `FAILED` with `resume_stage=IMPLEMENT`: explicit resume targets `PLAN`, ordinary protected PLAN execution persists current evidence, and IMPLEMENT may then obtain the existing bounded worker recovery lease. Historical PLAN evidence, Work Specification binding, source lineage, worker ceilings, public resume payloads, and ordinary autonomous/reconnect behavior remain unchanged.

P2-V0.23.14 / Architecture v3.27 binds a recovered worker checkpoint to the exact fresh PLAN accepted after that human-authorized replan. It preserves checkpoint/source-lineage history and does not widen model, mutation, Git, deployment, or REVIEW authority.

Production acceptance evidence:

- deployed API source: `c6c7b80e912f4f68efe43b8fa83ee30b8c18ee20`;
- production deployment: `dpl_2kQpJfG9hk5gppPySMBbgT3Zi4Nz`, target production, state `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- P2-V0.23.14 retry QA run `33336924911`: SUCCESS; explicit FAILED/IMPLEMENT resume returned PLAN, autonomous continuation returned HTTP 200, fresh PLAN passed, and the worker advanced from lease generation 4 to generation 5 before hosted proposal work;
- the immutable historical OT Time fixture then failed later at `dotnet restore` with `DEPENDENCY_PREPARATION_FAILED`, probe exit 0 and prepare exit 1; that fixture predates the independent OT Time .NET repair and was correctly not silently rebased;
- fresh current-source production replay `33336924912`: SUCCESS; OT Time Engineering Run `27deec1b-9234-40f0-809f-2fc957f9f7d6` advanced PLAN -> IMPLEMENT -> BUILD -> TEST -> VERIFY -> REVIEW, revision 6, with no failure;
- that replay returned and validated the authenticated source-only ZIP: 32 entries, 74,761 bytes;
- the same replay independently proved hosted selection starts with Luna; bounded validation fallback later reached Terra and Sol without changing the canonical route order;
- parallel source-only Python full-experience run `4b046e29-718f-42d8-b8eb-5d5183681911` also reached REVIEW revision 6 with PLAN, IMPLEMENT, BUILD, TEST and VERIFY all PASSED;
- main QA-harness reconciliation source `5303eef4053a2ed6100dbbe4e28429124e992e5d` passed Parallax P2 CI, including API/contracts, client/browser/Skia, protected promotion, and DSPy release compilation; its Vercel deployment was canceled because it changed QA/workflow files only, so it is not a newer deployed API runtime.

The former dependency-preparation blocker is therefore classified as stale immutable source-lineage behavior on the historical fixture, not a current `dotnet-v1` runtime defect. No dependency-preparation runtime change is warranted from that evidence.

## P2-V0.23.15 — Structured-output validation classification — PRODUCTION-ACCEPTED

Workstream: #488. Release PR: #491. Governing specification: `P2-V0.23.15`. Architecture: `ARCHITECTURE.md` v3.28.

The production replay that accepted P2-V0.23.14 also exposed a telemetry/control-classification defect at the hosted implementation boundary. Luna completed its provider call successfully, but protected `ImplementationProposal` JSON/schema decoding raised a Pydantic validation failure; the generic router exception boundary then mislabeled that provider-successful model-output failure as `provider_failed`. P2-V0.23.15 adds one bounded server-owned `ModelOutputValidationError` emitted only by protected proposal decoding and records that attempt as `validation_failed` before the generic provider-failure boundary. Transport, configuration, rate-limit and unrelated exceptions remain `provider_failed`; all-validation exhaustion remains `VALIDATION_EXHAUSTED`; all-rate-limit exhaustion remains `RATE_LIMITED`; mixed provider/validation outcomes remain conservatively `PROVIDER_EXHAUSTED`.

The fixed implementation proposal prompt now states the exact JSON keys already enforced by the protected schema, but parsing remains strict and fail-closed. No Markdown stripping, JSON repair, prose extraction, permissive fallback, same-model retry, source-mutation authority, candidate-validation relaxation, worker-ceiling change, Git/deployment authority, or REVIEW authority was added. The typed output-validation exception is raised without retaining the original Pydantic exception as its cause, and durable routing diagnostics still omit raw model output and provider payloads.

Release and deployment evidence:

- exact green PR head: `71f5bbab36ce1efb5595ff0972c06186fd575c16`;
- release merge / deployed application source: `04b1893e3a520202a77614fd1ff4ab00dac0ab1c`;
- production deployment: `dpl_EngoShekvZLYDC3mfdyzDwP8rUpx`, target production, state `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- exact-head Workstream Spec Validation `33340266792`: SUCCESS;
- exact-head Bounded Autonomy `33340266798`: SUCCESS;
- exact-head Parallax P2 CI `33340266789`: SUCCESS, including API/contracts, client/browser/Skia, protected promotion and DSPy release compilation;
- post-merge Workstream Spec Validation `33340420874`: SUCCESS;
- post-merge Parallax P2 CI `33340420982`: SUCCESS;
- production build provider, delivery-permission, projected-source, Blob, lineage-composition, agentic-runtime, projected-bootstrap, execution-snapshot and run-event-schema preflights: PASS;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- production runtime-error scan after deployment: no runtime errors in the checked 30-minute window.

Authenticated production acceptance was repeated twice against the current disposable OT Time source under the exact deployment above. Engineering Run `4221c919-ad70-46fe-886e-b1c6231444db` reached REVIEW revision 6 with PLAN, IMPLEMENT, BUILD, TEST and VERIFY all PASSED and returned a validated 32-entry, 74,757-byte source-only ZIP. A second independent replay, Engineering Run `b9db6eb1-7621-446c-a6c6-7cfdffeed78d`, also reached REVIEW revision 6 with every protected stage PASSED and returned a validated 32-entry, 74,739-byte source-only ZIP.

Both production runs proved the canonical hosted route begins with `openai/gpt-5.6-luna`. In each run Luna completed provider calls and the routing layer recorded the rejected attempt as `validation_failed`, followed by bounded Terra fallback; no `provider_failed / ValidationError` misclassification appeared and the full engineering lifecycle still completed. Production telemetry intentionally does not persist a subtype that distinguishes typed structured-decode rejection from the ordinary protected validator's `False` result, so the exact typed decode branch is established by deterministic protected release tests rather than by manufacturing invalid production model output. The production evidence establishes that provider-successful Luna rejection now remains inside validation classification without regressing normal fallback or lifecycle completion.

## P2-V0.23.16 — WebGL preflight reduced-graphics fallback — PRODUCTION-ACCEPTED

Workstream: #398. Release PR: #493. Governing specification: `P2-V0.23.16`. Architecture remains `ARCHITECTURE.md` v3.28 because this correction changes client startup capability handling, not durable server authority or state-machine architecture.

The production client previously attempted CanvasKit/Skia startup before knowing whether the browser could provide WebGL. Browsers or environments with neither WebGL2 nor WebGL could therefore fail before the already-supported authenticated reduced-graphics experience became available. P2-V0.23.16 adds a bounded browser capability preflight before `LoadSkiaWeb` and before importing the Skia application. If WebGL2 and WebGL context creation are both unavailable, or the capability probe itself throws, the client selects the existing `FallbackApp` immediately. Normal WebGL-capable startup and the existing CanvasKit-initialization catch/fallback remain unchanged.

The probe records no GPU vendor, renderer, extension set, fingerprint, persistence, telemetry, or API evidence. Authentication, Project binding, Work Specification behavior, Engineering Run authority, source lineage, hosted-model routing, worker ceilings, Git/deployment authority and the REVIEW boundary are unchanged.

Release and production evidence:

- exact green PR head: `34b4917a59e1cc3175261a24e2cd0d11a5c0823a`;
- release merge / deployed client source: `7f6b57aa4e44414dfbe7e2045d4ada244336eb93`;
- production deployment: `dpl_4c4KnCtsTheUiKGfvy9fpTtUxTqB`, target production, state `READY`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- production aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`;
- exact-head Workstream Spec Validation `33341723502`: SUCCESS;
- exact-head Bounded Autonomy `33341723488`: SUCCESS;
- exact-head Parallax P2 CI `33341723505`: SUCCESS, including API/contracts, client state/typecheck/export, browser/Skia acceptance, protected promotion and DSPy release compilation;
- the WebGL-unavailable Playwright acceptance disabled WebGL2, WebGL and experimental WebGL before application startup and proved the authenticated reduced-graphics shell rendered with zero mounted canvases, no `/canvaskit.wasm` request and zero browser errors;
- the ordinary WebGL acceptance remained green and continued to mount the Skia canvas and animated client treatment;
- production `/` returned HTTP 200 from the exact deployment above;
- production client runtime-error scan after release found no runtime errors in the checked window.

This closes the known WebGL startup gap without broadening browser capability collection or server authority.

## Post-acceptance QA trust retirement — PRODUCTION-VERIFIED

Issue: #495. Release PR: #496. This cleanup retires the temporary authenticated GitHub Actions workflow used to prove the P2-V0.23.13/P2-V0.23.14 production retry path after that behavioral acceptance was completed.

The earlier retry-specific QA workflow remains retired. P2-V0.23.17 subsequently admitted the exact dedicated `Ryan9876/parallax-qa` repository ID/workflow tuple while temporarily retaining two application-repository QA tuples for migration safety. P2-V0.23.19 has now completed the cutover: those two legacy tuples and their standing workflow files are removed, and the dedicated repository replay is production-verified under the contracted trust set. Repository-ID binding, `refs/heads/main`, GitHub-hosted runner, event-name and `parallax://qa-production` audience checks remain fail-closed.

Release and production evidence:

- exact green PR head: `22a9cf19f3e1de9f2ad9092976d3fe960f88249d`;
- release merge / deployed API source: `51e1c95873a813464b45c6c4ce50b8c2f35e1111`;
- production deployment: `dpl_G2TFSXDgxZXyGKGZMfKH33F44s3H`, target production, state `READY`;
- exact-head Bounded Autonomy `33342425289`: SUCCESS;
- exact-head Parallax P2 CI `33342425268`: SUCCESS, including API/contracts, client/browser/Skia, protected promotion and DSPy release compilation;
- production provider, exact-repository delivery-permission, projected-source, private Blob, lineage-composition, agentic-runtime, projected-bootstrap, execution-snapshot and run-event-schema preflights: PASS;
- canonical production alias: `parallax-api-tan.vercel.app`;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- production runtime-error scan after deployment: no runtime errors in the checked 30-minute window;
- main no longer contains `.github/workflows/qa-p2313-production-retry.yml`, and the deployed source's exact allowlist no longer contains the P2-V0.23.14 retry workflow.

This is a contraction of temporary QA authentication surface only. Normal user authentication, the continuing bounded QA principal, Project and Work Specification identity, Engineering Run state authority, source lineage, hosted-model routing, worker recovery, Git/deployment authority and the REVIEW boundary are unchanged. `ARCHITECTURE.md` remains v3.28 because no durable architecture contract changed.

## Production components

### Client

Current deployment-verified client:

- application source: `7f6b57aa4e44414dfbe7e2045d4ada244336eb93`;
- production deployment: `dpl_4c4KnCtsTheUiKGfvy9fpTtUxTqB`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- state: `READY`;
- production shell: HTTP 200;
- post-release runtime-error scan: clean in the checked production window.

Normal `/` remains Google-first. `/?qa=1` exposes the bounded dedicated QA password/recovery path. Agent-runnable GitHub Actions OIDC maps to that same bounded QA principal without storing or exposing the QA password.

### API

Current deployment-verified production API:

- source: `ea00a943d4bc5f00f0f5416881d482c0f799be63`;
- production deployment: `dpl_ACcZLXGNc9Rt1kBekWRJaFw9Vov8`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- state: `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- `/health`: HTTP 200;
- `/ready`: HTTP 200 with database/providers ready and one provider target;
- post-release runtime-error scan: clean in the checked post-release production window;
- architecture: `ARCHITECTURE.md` v3.31.

The production build preflight restored and qualified both execution substrates before release:

- common Python/Node snapshot: `snap_vagbatADKKndxwFGSDNbt08Ueigm`;
- dedicated .NET snapshot: `snap_qO26lCgjTq7xvQOpWctqy8xFyvZ1`;
- common snapshot: exact identity, deny-all networking, required Python dependencies, `node --version`, and source-free root verified;
- .NET snapshot: exact identity, deny-all networking, `dotnet --info` on .NET SDK 8.0.424, and source-free root verified.

Later main commits used only for authoritative-record and QA-harness reconciliation are not newer deployed API runtimes and must not be recorded as such. The current API runtime source remains the exact application source above.

## P2-V0.23.11 — Human-resume terminal-worker re-arm — PRODUCTION-ACCEPTED THROUGH LATER RETRY PROOF

Workstream: #470. Release PR: #472. Governing specification: `P2-V0.23.11`. Architecture: `ARCHITECTURE.md` v3.25.

Production evidence on Engineering Run `2b3cd15f-c5e2-481a-8266-c92c6534b08b` showed that the already-deployed client correctly performed `resume -> autonomous`, but autonomous continuation stopped before hosted candidate generation because the prior durable worker remained terminal `FAILED`. The correction adds one narrow server-owned recovery transition: only a successful explicit Engineering Run resume that began from run state `FAILED` may move the matching unleased terminal worker from `FAILED` to `RECOVERING`. It preserves worker identity, checkpoint/source-lineage/current-step evidence and lease-generation history, resets only worker-local anti-loop counters/fingerprints and current terminal markers, and reuses the existing protected `RECOVERING -> REASSIGNED` path for the fresh mutation lease generation. Ordinary autonomous calls and reconnects still cannot restart a terminal worker.

Deployment evidence:

- release PR: #472;
- application merge / deployed API source: `d3a75f6c0da1317ad50898d71e3d61b64acdb961`;
- production API deployment: `dpl_4jkfnW81nkocKwMbNNKu42mcjw1p`;
- deployment target/state: production / `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- Workstream Spec Validation workflow `33295368023`: SUCCESS;
- Bounded Autonomy workflow `33295368017`: SUCCESS;
- Parallax P2 CI workflow `33295368018`: SUCCESS, including API/contracts, client/browser/Skia, protected promotion and DSPy release compilation;
- production build provider preflight: PASS;
- exact-repository delivery permission preflight: PASS;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- post-release runtime-error scan: no runtime errors in the checked production window.

Later P2-V0.23.13/P2-V0.23.14 production retry evidence exercises this boundary: the explicit FAILED/IMPLEMENT retry re-arms the recovered worker, a fresh worker generation is minted, and hosted implementation dispatch proceeds. P2-V0.23.11 is therefore behaviorally production-accepted through that later proof.

## Failed-run resume autonomy handoff — DEPLOYMENT-VERIFIED

A production recovery observation on Engineering Run `2b3cd15f-c5e2-481a-8266-c92c6534b08b` exposed a client handoff gap after a protected failure. The server accepted `/resume`, persisted `RUN_CONTROL / RESUMED` as event #15, and returned the run to `IMPLEMENT`, but the client treated that successful resume response as the end of the retry action and did not immediately invoke bounded autonomous continuation for the returned active revision. The result was a truthful active `IMPLEMENT` run that could appear parked with Worker runtime `Awaiting evidence`.

PR #466 corrects both the continuation and persisted-recovery surfaces without changing server authority. After a successful FAILED/PAUSED resume, the client now immediately invokes the existing bounded autonomous endpoint when the returned run is in `PLAN`, `IMPLEMENT`, `BUILD`, `TEST`, or `VERIFY`. `REVIEW` remains a hard human boundary. The mobile Progress surface also treats an authoritatively persisted `FAILED` run as retryable after reload, rather than depending only on an ephemeral in-session failure signal, and it keeps the technical-detail path available beside the retry action.

Release evidence:

- release PR: #466;
- exact green PR head: `580d12674a57b770f477578fad3a1ad8921277c6`;
- application release merge / deployed client source: `35c832fdd80e2a230b1ab19d51fff7980479041e`;
- production client deployment: `dpl_4Q72neK7ofr2WZMn5mCgdL3MrHYB`;
- deployment state: `READY`;
- production aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`;
- Bounded Autonomy workflow `33294115049`: SUCCESS;
- Parallax P2 CI workflow `33294115034`: SUCCESS;
- Fast API/contracts, Fast client/typecheck/state/export/browser/Skia, protected promotion and DSPy release compilation: PASS;
- exact 390×844 failed-resume browser regression proves `resume -> autonomous`, resumed revision 4, and bounded continuation to `REVIEW` revision 5;
- production alias shell: HTTP 200;
- exact deployment build error scan: clean;
- exact deployment production error/fatal runtime scan after release: clean.

This release changes no API contract, persisted state-machine transition, persistence model, source-lineage semantics, provider authority, deployment ceiling, or REVIEW boundary. It closes a client orchestration gap between a persisted protected resume and the already-authorized bounded autonomous continuation that should follow it.

## Long-running client release freshness — DEPLOYMENT-VERIFIED

A production observation exposed a second, distinct client issue after the resumed-component health correction was deployed: an iPhone Safari tab that had been opened before the new client release continued executing its already-loaded JavaScript while receiving later API events. The server and production alias were current, but the long-running tab had no mechanism to learn that a newer client shell existed. This can leave truthful fresh run events rendered through obsolete client projection logic until the operator manually reloads.

PR #463 adds an advisory web release guard without changing API or Engineering Run semantics. The loaded client records the same-origin hashed script/stylesheet signature from its shell, checks a no-cache `/index.html` release shell every 60 seconds and when the page regains focus, returns from the page cache, or becomes visible, and compares the current release signature. If a newer shell is present, Parallax shows an accessible persistent `Parallax was updated` notice with a minimum-44pt `Refresh now` action. It does not force-reload an active operator session. Network failures in the release check are non-disruptive. `/index.html` is explicitly served with `Cache-Control: public, max-age=0, must-revalidate` so the comparison cannot silently rely on an obsolete shell.

The same release closes the browser-level acceptance gap that allowed the original observation to escape automation. A 390×844 Playwright regression now reproduces the exact Activity sequence `#11 WORKER_STATE FAILED / AGENTIC_CANDIDATE_EXHAUSTED` → `#12 IMPLEMENT FAILED / AUTONOMOUS_IMPLEMENT_FAILED` → `#13 RUN_CONTROL RESUMED` → `#14 IMPLEMENT FAILED / AUTONOMOUS_IMPLEMENT_FAILED` on the actual operator Activity surface. The regression requires Component Health to preserve the historical failures in the timeline while projecting Worker runtime as `Awaiting evidence`, preserving accepted Source lineage as observed, and rejecting stale current `Attention` inherited from pre-resume worker evidence. A separate browser regression simulates a newer deployed shell while the old tab remains open and proves stale-client detection, explicit refresh availability, minimum mobile target sizing, and successful loading of the current shell after refresh.

Release evidence:

- release PR: #463;
- exact green PR head: `e77bdf22c3070a57638fdc4f3d15e733a932792e`;
- application release merge / deployed client source: `8ad310ec0efeb54dbe6067d80878e40b91f8560d`;
- production client deployment: `dpl_7CC8atxBusUuBXYnVg3XBzagSJ4E`;
- deployment state: `READY`;
- user-observed production alias `parallax-ashy-one-20.vercel.app` is attached to that deployment;
- Bounded Autonomy workflow `33292775470`: SUCCESS;
- Parallax P2 CI workflow `33292775471`: SUCCESS;
- Fast API/contracts, Fast client/typecheck/state/export/browser/Skia, protected promotion and DSPy release compilation: PASS;
- production release-check shell on `parallax-ashy-one-20.vercel.app`: HTTP 200 with `Cache-Control: public, max-age=0, must-revalidate`;
- exact deployment build error scan: clean.

A browser tab loaded before this release cannot retroactively contain the release guard and requires one final manual refresh. Once this release is loaded, later client deployments are detected by the guard on the bounded interval or page-return signals above. No API, persistence, persisted event, Engineering Run state machine, source-lineage authority, provider authority, deployment ceiling or REVIEW boundary changed.

## Client resumed-component health projection — DEPLOYMENT-VERIFIED

Production observation showed a truthful event history but a stale current-health projection: persisted event #11 recorded a failed Worker state (`AGENTIC_CANDIDATE_EXHAUSTED`), event #12 recorded failed IMPLEMENT (`AUTONOMOUS_IMPLEMENT_FAILED`), and later event #13 recorded `RUN_CONTROL / RESUMED`, while the authoritative Engineering Run was active in IMPLEMENT. The Component Health card nevertheless continued to show Worker runtime and Source lineage as current `Attention` from #11.

The defect was client-only. `componentHealth()` treated any event carrying `worker_execution_id` or `source_lineage_ref` as direct health evidence for those components and had no resume supersession rule. That allowed an unrelated failure to contaminate component health and allowed a historical worker failure to remain current after a persisted resume.

Correction and release evidence:

- release PR: #461;
- merged/deployed client source: `77cf1f4537023849f43c5b9eaaff9363ef77196c`;
- production client deployment: `dpl_7rLxgFh9CH3aY9sdoSCTnD1xHDV3`;
- deployment state: `READY`;
- production alias observed by the user: `parallax-ashy-one-20.vercel.app`;
- Bounded Autonomy workflow `33291202942`: SUCCESS;
- Parallax P2 CI workflow `33291202984`: SUCCESS;
- Fast API/contracts, Fast client/typecheck/state/export/browser/Skia, protected promotion and DSPy release compilation: PASS.

Current-health projection now separates dedicated component evidence from reference-only evidence. A newer persisted resume boundary supersedes an older dedicated worker failure for current-health presentation, yielding `Awaiting evidence` until fresh component evidence exists; it does not erase or rewrite the historical failure event. Source lineage uses dedicated lineage/acceptance evidence when available, while a lineage reference on another subsystem's failed event is observation-only. Worker execution references receive the same observation-only treatment. GitHub and Vercel remain `Unavailable` until their own persisted evidence exists.

This release changes no API, persisted event, Engineering Run state-machine, source-lineage authority, provider authority, deployment ceiling or REVIEW boundary.

## P2-V0.23.9 — Validator-guided alternate-candidate repair — DEPLOYMENT-VERIFIED / NORMAL-PATH PRODUCTION-ACCEPTED

Workstream: #456 (completed).

Governing specification: `P2-V0.23.9`.

Architecture: `ARCHITECTURE.md` v3.23.

Production incident evidence:

- affected Engineering Run: `2b3cd15f-c5e2-481a-8266-c92c6534b08b`;
- all three already-admitted hosted implementation candidates completed provider calls but were rejected by the unchanged protected proposal validator;
- terminal evidence: `AGENTIC_CANDIDATE_EXHAUSTED` / `AUTONOMOUS_IMPLEMENT_FAILED`;
- canonical source mutation: none;
- defect: alternate-candidate recovery was finite and safe but blind to the bounded fact that a prior candidate had failed strict safe-patch validation.

P2-V0.23.9 preserves the validator and every mutation/authority ceiling. Only a server-classified `VALIDATION_EXHAUSTED` result may cause a later already-admitted candidate for the same work unit to receive fixed server-owned safe-patch repair guidance. The guidance restates exact path/digest binding and strict single-file unified-diff form only. Provider/rate-limit failures remain separate. The existing eligible-agent roster and `max_reassignments_per_work_unit` bound remain authoritative, and no new same-model or unbounded retry loop exists.

Release evidence:

- release PR: #457;
- exact green release head: `682faae2eadfeb63698a8fffc0ee772cba89348d`;
- application release merge / deployed source: `f0706d489b26ff715891f75c8d2723fb0f734c3b`;
- production API deployment: `dpl_Dz9dNegGMSdY1GoZdzD2tThQbATm`;
- deployment state: `READY`;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database and providers ready;
- provider/storage, exact-repository delivery-token, projected-source, private Blob, lineage-composition, agentic-runtime, projected-bootstrap, execution-snapshot and run-event preflights: PASS;
- exact deployment error/fatal runtime-log scan: clean;
- workstream contract and protected-plan validation, Bounded Autonomy/full API regression, client/browser/Skia, protected promotion and DSPy release compilation: PASS.

Post-deploy acceptance was intentionally non-destructive and did not manufacture a validator failure. The first trusted replay `33289874294` already proved the released runtime could progress through PLAN, IMPLEMENT, BUILD, TEST and VERIFY to REVIEW revision 6 with no runtime failure; that job failed only after REVIEW because the QA harness called the obsolete `/v1/engineering-runs/{run}/source-archive` route and received HTTP 404. Harness-only PR #459 corrected verification to the existing Project-scoped authenticated `/source-download` endpoint and merged as `a4d7cc83f2e3c60619e19d735c63af843742647e`; no application runtime changed.

Corrected trusted workflow-dispatch acceptance:

- workflow run: `33290221272`;
- W8 OT Time job: `99200534358` — SUCCESS;
- Project: `7b4c2377-6f06-4b43-b174-206e059e24f0`;
- Engineering Run: `cb9a75aa-413b-4f6c-b019-e493fa112655`;
- initial state/revision: PLAN / 1;
- final stop/state/revision: `REVIEW_REQUIRED` / REVIEW / 6;
- `last_failure_code`: null;
- PLAN, IMPLEMENT, BUILD, TEST and VERIFY: PASSED;
- IMPLEMENT tool: `safe-source-implementation-v1`;
- authenticated source-only ZIP handoff: 32 entries / 74,870 bytes;
- companion Python full-experience job `99200534320`: SUCCESS.

The corrected production replay succeeded on its first admitted `openai/gpt-5.6-sol` implementation candidate, so validator-guided alternate-candidate repair was not artificially triggered in production. That branch is established by deterministic protected regression tests covering bounded failure classification, validation-only next-candidate guidance, provider-failure separation, finite recovery, bounded diagnostics and unchanged authority. Production acceptance therefore combines exact-source deployment verification, clean normal-path full-experience replay, and deterministic protected proof of the repair branch rather than weakening or deliberately tripping the production validator.

## P2-V0.23.8 — Bounded rejected-candidate recovery — DEPLOYMENT-VERIFIED

Workstream: #446.

Governing specification: `P2-V0.23.8`.

Production incident evidence:

- affected Engineering Run: `0cb9e8c5-1381-4913-a890-7bd48bc0384f`;
- prior runtime: `dpl_8LBreMU3LGxUR8RWW8LfSCJRGxxx`;
- hosted `openai/gpt-5.6-sol` call completed successfully, then the server-owned proposal validator emitted `parallax_model_route validation_failed`;
- the rejected proposal did not mutate canonical source;
- pre-v3.22 behavior incorrectly projected that candidate rejection as `AGENTIC_TASK_FAILED` and persisted `AUTONOMOUS_IMPLEMENT_FAILED`.

Architecture v3.22 now separates pre-mutation candidate rejection from worker/process loss. A rejected proposal remains non-authoritative and non-mutating. The same work unit may retry only through another already-admitted eligible implementation agent in deterministic server-owned order, with incremented assignment generation and fresh dispatch identity. Recovery is capped by the existing `max_reassignments_per_work_unit` bound. Exhaustion fails closed as bounded `CANDIDATE_GENERATION_EXHAUSTED` evidence with `worker_process_loss=false`; protected proposal validation, safe mutation, lineage, Git, deployment and REVIEW authority are unchanged.

Release evidence:

- release PR: #447;
- exact green release head: `22e96f20378c1e91e1c105a0e62c4865a7034510`;
- application release merge: `319f548b5950ba1c27603ccf0c5921d5a3aaee5f`;
- production deployment: `dpl_H6oQUkxyzX9C32VEHgWiRwLpZr1G`;
- deployment state: `READY`;
- exact deployment source: `319f548b5950ba1c27603ccf0c5921d5a3aaee5f`;
- production provider/storage, exact-repository scoped delivery permission, projected-source, private Blob, lineage-composition, agentic-runtime, projected-bootstrap, run-event schema and execution-snapshot preflights: PASS;
- exact-head full API regression, Bounded Autonomy, client state/type/export, browser/Skia, changed-spec protected DSPy plan, DSPy release compilation and protected-promotion gates: PASS;
- authentic P2-V0.23.8 DSPy qualification used `ollama_chat/qwen2.5-coder:1.5b` and passed `--require-dspy` before merge.

Post-deploy regression used the existing bounded QA OIDC identity against `github:Ryan9876/Movies`: workflow run `33285758959`, rerun job `99191707001` — **SUCCESS**. Engineering Run `f13e9c12-b0ca-47ac-a0ba-b5578f2e5c62` reached `REVIEW` revision `6`, `last_failure_code=null`, stop reason `REVIEW_REQUIRED`; EXECUTOR, PLAN, IMPLEMENT, BUILD, TEST and VERIFY all passed; authenticated source archive verification passed with 7 entries / 1404 bytes; `source_publication=false`; `app_deployment=false`.

That post-deploy run proves normal production execution remains healthy but its first implementation candidate was accepted. It therefore does **not** claim that the candidate-rejection retry branch happened naturally in production. The retry/exhaustion branch is established by deterministic protected regression tests and the exact-head release gates; no production failure injector or weakened validator was introduced merely to manufacture that observation.

## P2-V0.23.6 — Profile-qualified protected execution snapshots — DEPLOYMENT-VERIFIED

Workstream: #438.

Governing specification: `P2-V0.23.6`.

Durable contract:

- deterministic validation-profile selection remains source-derived and separate from execution-snapshot selection;
- `python-v1` and the reserved `node-v1` identity retain the established common snapshot;
- `dotnet-v1` requires the dedicated `PARALLAX_EXECUTION_SNAPSHOT_DOTNET_ID` snapshot and never falls back to the common image;
- snapshot mapping is finite and server-owned; unrecognized profiles and missing/malformed dedicated configuration fail closed;
- candidate and canonical same-lineage validation use the same selected snapshot identity;
- fixed validation commands and the existing bounded PREPARE authority are unchanged;
- no user Engineering Run installs an SDK/toolchain dynamically;
- production preflight verifies every enabled snapshot before the deployment can become qualified;
- the snapshot contains toolchain state only, never Project/application source or credentials.

Release evidence:

- architecture: `ARCHITECTURE.md` v3.20;
- application release merge: `e204d69ed0d6a9a69d68374ad63e8a1dbd630813`;
- production deployment: `dpl_8e87ZdYGACUvf4YvivsSWwomDE5n`;
- deployment state: `READY`;
- dedicated .NET snapshot: `snap_qO26lCgjTq7xvQOpWctqy8xFyvZ1`;
- canonical OT Time production acceptance: workflow `33280783143`, attempt 2 — PASS.

Vercel remains an isolated execution/infrastructure provider for this substrate; it is not an application-delivery dependency for `source-only` Projects.

## W8-S2 .NET source-only full experience — ACCEPTED

Acceptance target: `github:Ryan9876/ot-time`.

Authorized canonical QA workflow: `.github/workflows/w8-s2-qa-replay.yml`.

Final workflow run: `33280783143`, attempt `2`.

Final workflow job: `99177057782` / `replay-public-ot-time-source-only` — **SUCCESS**.

Exact production evidence:

- Project: `7b4c2377-6f06-4b43-b174-206e059e24f0`;
- Engineering Run: `82170d38-24ff-4f91-af2a-e247ebbe17a7`;
- initial state/revision: `PLAN` / `1`;
- final state/revision: `REVIEW` / `6`;
- `last_failure_code`: `null`;
- public source bootstrap: PASS;
- deterministic validation profile: `dotnet-v1`;
- dedicated qualified snapshot: `snap_qO26lCgjTq7xvQOpWctqy8xFyvZ1`;
- PLAN through VERIFY protected advancement: PASS;
- authenticated source ZIP integrity check: PASS;
- ZIP contained the accepted source lineage and generated `PARALLAX_QA.md` (`135` bytes);
- application deployment: not required;
- Vercel Preview target: not required;
- source publication: not required.

The workflow concluded: `Public OT Time source-only run reached REVIEW: revision=6; failure=none` and `Authenticated source-only handoff verified; no Vercel target or Preview was required.`

### Benchmark prerequisite repaired independently

The first post-release replay correctly selected and restored the new .NET snapshot and passed `dotnet --info`, but `dotnet restore` failed. An unrestricted .NET 8.0.424 diagnostic proved the failure reproduced outside Parallax. The OT Time repository had invalid/inconsistent package references, a vulnerable MailKit version treated as an error, overlapping one-commit scaffold implementations, and test-harness analyzer defects.

OT Time PR #2 repaired that benchmark without weakening its behavioral assertions. Exact validated OT Time head `b0174da80adea4f30d724214923de623734a2c4a` passed:

- `dotnet restore OtTime.sln --nologo` — PASS;
- `dotnet build OtTime.sln --no-restore --nologo` — PASS with 0 warnings / 0 errors;
- `dotnet test OtTime.sln --no-restore --nologo` — PASS, 9/9 tests.

OT Time PR #2 merged as `2a369b9d79967ca603172d33c1bb941d1630b2a9`. This target-repository repair is not a Parallax application deployment and did not widen Parallax runtime authority.

## Production Python source-only full experience — ACCEPTED

Acceptance target: `github:Ryan9876/Movies`.

Authorized QA workflow: `.github/workflows/qa-production-replay.yml`.

Final canonical workflow run: `33277189927`.

Final canonical workflow job: `99165862378` / `python-full-experience` — **SUCCESS**.

Exact production evidence:

- Project: `d00e23cb-6d84-4805-bf15-4f738d920136`;
- Engineering Run: `e9a1772f-88b3-450c-b619-8008de8c9576`;
- final state: `REVIEW`;
- final revision: `6`;
- `last_failure_code`: `null`;
- stop reason: `REVIEW_REQUIRED`;
- executor: `python` — PASSED;
- PLAN — PASSED;
- IMPLEMENT — PASSED using `safe-source-implementation-v1`;
- BUILD — PASSED;
- TEST — PASSED;
- VERIFY — PASSED;
- source ZIP: verified;
- required generated acceptance file: `PARALLAX_QA_PYTHON.md` present;
- source publication: `false`;
- application deployment: `false`.

The companion Python regression in QA Production Replay `33287875970`, job `99194169048`, also passed while the safe-deletion production acceptance was executed. This confirms the accepted common-snapshot Python source-only path remained healthy during the deletion verification.

## Safe deletion — DEPLOYMENT-VERIFIED / PRODUCTION-ACCEPTED

Workstream: #290.

Corrective specification: `P2-V0.18.12`.

Corrective release evidence:

- initial logical-deletion merge: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- production migration: `20260827173141` / `safe_conversation_project_deletion` — applied;
- corrective PR: #294;
- corrective merge: `109444dcd7e13bfe842dea71355607941258b073`;
- production API deployment: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- deployment state: `READY`;
- exact corrective deployment source: `109444dcd7e13bfe842dea71355607941258b073`;
- post-cutover `/health` and `/ready`: HTTP 200;
- exact corrective API deployment error/fatal scan: clean;
- unauthenticated protected conversation route: HTTP 401;
- exact-head specification, API, Bounded Autonomy, client, protected lifecycle and deletion regressions: PASS.

Final authenticated production behavior was accepted through the existing trusted `QA Production Replay` OIDC identity:

- workflow run: `33287875970`;
- job: `99194168944` / `safe-deletion-production-smoke` — **SUCCESS**;
- disposable Project: `4e062e22-e706-4dbb-ac14-e1319d2b82ff`;
- disposable conversation: `2c990ee7-61bc-4499-b0f9-8c467a61b472`;
- Work Specification: `5d3e7000-b252-4bdf-8395-ad2a84d347e8`;
- protected Engineering Run: `0851a300-0041-4d46-a7a6-8d03a1609af1`;
- run activation: `PLAN` revision `1`;
- Project delete while protected work was active: HTTP `409`, with the Project remaining active;
- protected run cancellation: `CANCELLED` revision `2`;
- Project delete after terminal cancellation: HTTP `204`;
- deleted Project active read: HTTP `404`;
- deleted bound-conversation active read: HTTP `404`;
- active-list checks: deleted Project and conversation absent;
- exact slug/repository active identity reuse: HTTP `201`, new Project `c37ae153-e653-49d1-9d11-76125a7e38f1`;
- replacement Project cleanup: HTTP `204`, followed by `404` active read;
- synthetic repository identity: `github:Ryan9876/qa-safe-delete-33287875970-1`;
- external provider mutation authorized: `false`;
- external provider resource created: `false`;
- external provider resource deleted: `false`;
- bounded evidence artifact: `safe-deletion-production-evidence-33287875970-1`, artifact `9725006991`, 602 bytes, ZIP SHA-256 `719d17a92d69d8c1050b6fd9d84f9110ead17d8c2eb34845448432fa346e65ae`.

The production smoke establishes the server-authoritative user-visible destructive behavior without deleting a real GitHub repository, Vercel deployment, or other provider resource. Production active-owner routes intentionally hide logically deleted Project-bound records, so this smoke does not manufacture a deleted-history audit endpoint to prove physical retention. Protected Work Specifications, Engineering Runs, attempts, events, source-lineage evidence, immutable artifacts, cross-owner failure behavior, historical-unbound owner requirements and active-row uniqueness remain established by the exact-head regression suite that qualified the deployed P2-V0.18.12 semantics.

A first standalone smoke workflow correctly failed OIDC session exchange with HTTP 401 before creating any fixture because the bounded QA trust policy did not authorize that workflow identity. The acceptance run was moved into the already-authorized `QA Production Replay` workflow rather than widening authentication. The one-shot destructive job was removed after successful evidence capture; `scripts/qa_safe_deletion_smoke.sh` remains as a bounded reusable harness.

## Public source bootstrap — DEPLOYMENT-VERIFIED

Architecture v3.20 incorporates the v3.19 public-source authority boundary unchanged.

For a public GitHub repository with a commit-bearing default branch, production:

1. resolves canonical HEAD/default-branch identity through unauthenticated Git smart HTTP;
2. pins the immutable commit;
3. reads source from the exact commit-addressed GitHub codeload archive;
4. applies bounded archive, path, file-type, size and UTF-8 validation;
5. exposes read-only repository/source capability only;
6. never silently constructs a Vercel-backed credential path merely because the public transport is throttled or unavailable.

Private/non-public source remains fail-closed behind exact repository authority. Empty greenfield repositories remain a separate initialization/mutation-authority problem because there is no existing commit to read.

## Wave 8 — COMPLETE / PRODUCTION-ACCEPTED

W8-S1, W8-S3 and W8-S4 remain deployment-verified. W8-S2 is now also production-accepted.

Wave 8 now has both general source-backed experience evidence and the previously missing .NET protected-validation evidence. The canonical OT Time replay proves the former missing-static-target/source-bootstrap/toolchain sequence no longer reproduces and that the durable run remains within the REVIEW/source-only authority ceiling.

Workstreams #377 and #438 may be closed as completed on the exact evidence above.

## Wave 9 S1 — Real-world greenfield benchmark

Control Tower: #391.

Workstream: #392.

Governing benchmark specification: `P2-V0.23.0`.

Benchmark-admission release:

- qualified worker head: `1d053823d08d8e5050e77c624dafcd09199fe942`;
- application release merge: `ee6af25d09c495f2550f39a7d7f90f527dc7e447`;
- production API deployment: `dpl_9fWd2fZLsfXyexSC8hohvS9X5iDa`;
- state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

Greenfield repository-authority remediation:

- finding: #406;
- governing remediation specification: `P2-V0.23.3`;
- qualified implementation head: `1cad61de06ce4d1da4aaec12f4f4da97d16b63a3`;
- application release merge: `0cfe499ac787a23142067e95e80af80dedab36c5`;
- production deployment: `dpl_4LAkdawZteqrAX34pmGAtLMvVq9V`;
- state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

The frozen Decision Ledger benchmark remains open. Its original empty-repository observation is a valid failed reference observation rather than a passing application benchmark. P2-V0.23.7 now supplies the previously missing governed empty-greenfield authority; however, the former disposable target was consumed by legacy Parallax QA fixture activity before v3.21. A fresh approved truly empty target is therefore required to complete the canonical end-to-end trial without rewriting repository history.

## P2-V0.23.7 — Empty-greenfield repository authority — DEPLOYMENT-VERIFIED / CANONICAL TARGET REPLACEMENT REQUIRED

Workstream follow-up: #442.

Architecture: `ARCHITECTURE.md` v3.21.

Release evidence:

- release PR: #443;
- exact green release head: `a36a81d379e8f9b696f0879afa7126c31761a0e8`;
- application release merge: `2619aada4d3fd732589c6489a99ebe95dcc0d01d`;
- production API deployment: `dpl_8LBreMU3LGxUR8RWW8LfSCJRGxxx`;
- deployment state: `READY`;
- exact deployment source: `2619aada4d3fd732589c6489a99ebe95dcc0d01d`;
- production provider/storage preflight: PASS;
- exact-repository scoped delivery-token preflight: PASS;
- projected-source, private Blob, lineage composition and agentic-runtime preflights: PASS;
- exact-head specification, API regression, Bounded Autonomy, client/browser/Skia, DSPy release compilation and protected-promotion gates: PASS.

Durable behavior now supports a positively authenticated empty GitHub repository without manufacturing source or widening authority. Empty classification requires exact credentialed inspection; ambiguous/provider failures remain fail-closed. A zero-file `greenfield` root is explicit durable lineage, and accepted implementation must become non-empty before validation. Missing repository authorization is surfaced as structured `REPOSITORY_AUTHORIZATION_REQUIRED` with same-run retry. Empty-baseline mutation is REVIEW-only, fixed, idempotent and isolated behind `repository.initialize-empty`; normal GitHub delivery, Preview ceiling and human REVIEW boundary remain unchanged.

### Canonical Decision Ledger acceptance target was consumed before v3.21

The fixed target `Ryan9876/sickbeard` is no longer an empty repository. Its root commit `b7e8399724e38ee60b3380aa02ecb079a43acee3` was created at `2026-08-29T20:46:01Z` with message `Initialize minimal Parallax QA source fixture`, followed by four serial commits titled `Complete minimal Parallax QA source fixture`. Those commits predate the v3.21 production deployment by roughly nineteen minutes and contain QA-only fixture content. They are therefore not evidence that the v3.21 greenfield initializer ran.

After v3.21 became READY, bounded QA replay `33285377567` / job `99187551677` obtained the existing approved `parallax://qa-production` OIDC identity, but `scripts/w9_s1_reference_trial.sh` correctly stopped at its preflight with `Decision Ledger target is no longer greenfield; refusing to start trial.` No new Project/run or v3.21 repository mutation was created by that attempt.

The repository history is preserved rather than destructively rewritten. Canonical AC-27 remains pending a fresh user-approved truly empty repository with exact GitHub App/Vercel Connect coverage and the required Preview target readiness. This is an acceptance-fixture prerequisite, not an unverified runtime implementation claim.

## Wave 9 S2 — Governed skill intake and capability catalog

Control Tower: #391.

Workstream: #395.

Governing specification: `P2-V0.23.1`.

Release:

- qualified worker head: `0965969da3224ebe62e8a33348440b5753e76d6e`;
- application release merge: `fcb6abf4f794e038bcf48daac8d3400f006a18d8`;
- production API deployment: `dpl_57xiHUKBm3qK4HAA47kYzc9mJM13`;
- state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

S2 remains non-executing capability intake. External observations are quarantined metadata until exact approval and existing registry admission succeed; discovered content receives no package-install, generic shell/network, provider, merge, deployment, or REVIEW authority.

## Other open governed work

- #442 — P2-V0.23.7 empty-greenfield authority is implementation- and deployment-verified; canonical Decision Ledger acceptance remains pending a fresh approved empty target because the prior disposable target was consumed by legacy QA fixture activity.

## Authoritative-record update

`CURRENT-STATE.md` was updated again after deployment verification of the resumed-component-health client correction. It records the production symptom, client-only projection root cause, exact merged source and READY deployment, successful release gates, and the rule that historical failures remain intact while current health follows later persisted resume/component evidence.

`ARCHITECTURE.md` remains authoritative at v3.23 because this correction changes no durable lifecycle, authority, persistence, recovery or provider contract; it fixes only how existing persisted evidence is projected in the client.

`DESIGN-SYSTEM.md` was not changed because no durable visual token, component pattern or interaction rule changed.

`PROJECT-CONSTITUTION.md` was not changed because no constitutional product or authority principle changed.

`CURRENT-STATE.md` was updated after P2-V0.23.9 exact-source deployment verification and successful authenticated normal-path production acceptance. It records the original validator-exhaustion incident, the bounded repair semantics, release/deployment evidence, the obsolete-QA-route finding and correction, the corrected REVIEW/source-handoff replay, and closure of #456. #442 remains the only listed open governed work.

`ARCHITECTURE.md` was advanced to v3.23 because P2-V0.23.9 introduces a durable candidate-recovery rule: only bounded server-classified validation rejection may project fixed safe-patch repair guidance to a later already-admitted candidate, while provider failures, retry bounds, mutation authority and lifecycle ceilings remain unchanged.

`DESIGN-SYSTEM.md` was not changed because this release does not alter durable visual or interaction-system rules.

`PROJECT-CONSTITUTION.md` was not changed because the release preserves existing least-privilege, explicit-authority, fail-closed validation and evidence-preservation principles rather than introducing a new constitutional rule.

Latest authoritative reconciliation: P2-V0.23.19 is production-verified on exact API source `ea00a943d4bc5f00f0f5416881d482c0f799be63` / deployment `dpl_ACcZLXGNc9Rt1kBekWRJaFw9Vov8`. Post-merge Workstream Spec Validation `33350390486` and Parallax P2 CI `33350390524` passed, including fresh promotion-boundary DSPy compilation and verification. Dedicated `parallax-qa` replay `33350555555` then passed both routine jobs under the contracted one-tuple trust set: Python run `1b3c3413-2854-4af9-9625-d6d1838d0357` and OT Time run `beadb914-1ab5-45b2-ba72-50b31efe1f16` both reached REVIEW with verified authenticated source-only ZIP handoff. `ARCHITECTURE.md` is authoritative at v3.31. `DESIGN-SYSTEM.md` and `PROJECT-CONSTITUTION.md` require no change because this release changes neither durable visual-system rules nor constitutional authority principles. Issues #501 and #499 are complete; #442 canonical greenfield acceptance remains open.

Latest authoritative reconciliation: P2-V0.23.20 is production-deployment-verified on exact API source `bfc2373d690113a592a52ca8a12fc6b5343d481d` / deployment `dpl_AUapYhiyoD2G16t8uH4AzR5hqKQv`; Architecture is authoritative at v3.32. The fresh approved `Ryan9876/parallax-qa1` target remains truly empty after bounded replay `33353749430`; #442 remains open because positive exact GitHub App / Vercel Connect repository coverage has not yet been established through the protected inspection path. `DESIGN-SYSTEM.md` and `PROJECT-CONSTITUTION.md` require no change because P2-V0.23.20 changes neither durable visual-system rules nor constitutional authority principles.

Latest authoritative reconciliation: P2-V0.23.21 is production-verified on exact API source `71849d0979d940065efdefc909f1937272c87834` / deployment `dpl_CoTeZoRWcupTLhJkD9viUE8YfBB3`. Dedicated replay `33355557297` proved the hidden authenticated greenfield inspection result is `REPOSITORY_AUTHORIZATION_REQUIRED`; `Ryan9876/parallax-qa1` remains truly empty and unmodified, and #442 remains open pending external exact-repository authorization through `github/parallax-runtime`. `ARCHITECTURE.md` remains authoritative at v3.32. `DESIGN-SYSTEM.md` and `PROJECT-CONSTITUTION.md` require no change because this release changes neither durable visual-system rules nor constitutional authority principles.
