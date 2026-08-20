# Parallax 2.0 Current State

Version: 0.4.0-code-candidate
Date: 2026-08-20
Status: LOCALLY VALIDATED CODE 2.0 CANDIDATE ON VALIDATED REASON 2.0 FOUNDATION — EXACT-HEAD CI PENDING — NOT DEPLOYED
Active candidate spec: `P2-V0.4.0`
Target branch: `p2/code-v0.4.0`
Validated implementation head: `d96442c39fc2534fd733a50d39527ffd158653ee`
Validation workflow: GitHub Actions `Parallax P2 CI` run `32371806776`

The validated implementation head and workflow above remain the last completed exact-head GitHub evidence and cover Reason 2.0. The Code 2.0 candidate described below is reconstructed, validated locally, committed, and pushed; exact-head CI validation remains pending.

Published Code candidate commit: `ef8812f251268d67af0c4295629ec7db99344373`. GitHub Actions `Parallax P2 CI` run `32391149258` started for that commit; its result is pending and is not yet validation evidence.

## Material decisions

- Parallax 2.0 remains a separate product track in `Ryan9876/parallax`.
- P2 itself is built using approved specifications, mandatory DSPy development execution, and protected evaluation before a material AI-program release is called validated.
- Evaluation remains structurally above optimization: development evidence may guide optimizers; protected promotion contracts, thresholds, evaluators, and release rules may not be silently changed by optimizer-controlled code.
- Runtime model routing remains Luna → Terra → Sol.
- Expo + React Native + React Native Skia remains the universal client baseline; FastAPI + SQLAlchemy + DSPy remains the intelligence-service baseline.
- Durable server-side conversations remain the source of truth; browser storage remains draft convenience only.
- Each durable conversation carries its own stored specification identity. New conversations receive `PARALLAX_ACTIVE_SPEC_ID`; existing conversations retain their historical spec ID.
- The approved P2 living mineral/sunlit-water material, optical laser typesetter, and calm Parallax Lens Mark remain the visual baseline.
- `SPEC_AMENDMENT` is now a first-class calm protected hand-off state, not a generic error state.
- P2 preview deployment remains isolated from the existing Parallax 1.x Vercel production project.
- Dedicated P2 Vercel web/API projects and a dedicated P2 Supabase PostgreSQL project have not been created or deployment-verified.
- Code 2.0 uses durable append-only engineering runs, protected evidence gates, bounded workspace identity, and a deny-by-default recorded execution contract.
- FastAPI is pinned to the validated `0.128.x` minor line after the broader range admitted test-client dependency drift that stalled the full suite.

## Locally validated v0.4.0 Code 2.0 candidate

- Durable Code run lifecycle, immutable conversation/spec binding, revisions, idempotency, failure history, pause/resume, amendment, and cancellation are implemented.
- PLAN, IMPLEMENT, BUILD, TEST, VERIFY, and REVIEW have protected evidence contracts; implementation prose and failed/timed-out execution cannot be treated as success.
- Workspace artifacts use contained relative paths, bounded file sizes, SHA-256 identity, and symlink/path-traversal rejection.
- The deterministic executor rejects unregistered tools, shell metacharacters, out-of-root working directories, undeclared environment access, and non-BUILD/TEST/VERIFY execution.
- Code API routes expose create/get/latest/advance/pause/resume/cancel without placing orchestration in the client.
- The client shows concise accessible run status, evidence-bearing stages, failures, and protected pause/resume/cancel actions without becoming an IDE or terminal.
- Separate ten-case Code development and promotion suites validate successfully. The recorded baseline and equivalent challenger each score `1.0000`; promotion passes with zero aggregate regression. Stage-skipping, false-status, spec-drift, and unsafe-execution fixtures are rejected.
- Local evidence: Python compilation passed; backend suite `52/52` passed; client TypeScript and response-state tests passed; Expo web export passed; CI YAML parses.
- Mandatory DSPy SpecCritic + SpecCompiler execution, Playwright visual acceptance, and complete inherited/new gates remain exact-head CI requirements.
- Generated: **YES**. Locally validated: **YES**. Exact-head CI validated: **NO**. Committed/pushed: **YES**. Deployed: **NO**. Deployment-verified: **NO**.

## Validated v0.3.0 Reason 2.0

### Deterministic bounded multi-turn context

- Server-side Reason context composition is deterministic and provider-independent.
- Context includes the durable conversation/spec identity, lifecycle status, mode, current user turn, bounded recent prior messages, and explicit user/assistant role markers.
- Later explicit user corrections are authoritative over conflicting older assistant statements or inferred assumptions.
- Hard limits bound total context, prior-message count, individual prior-message size, and current-turn size.
- Oldest eligible prior messages are removed first; the active spec and current user turn are never silently discarded.
- Each context carries an observable SHA-256 digest, included-turn count, and truncation flag.

### Server-side scope authority

- Normal product behavior no longer treats the client `material_scope_change` Boolean as scope authority.
- The DSPy scope program proposes `CONTINUE`, `CLARIFY`, or `SPEC_AMENDMENT` under a typed contract.
- Protected policy validates the proposal and owns transition semantics.
- Low-confidence material-change proposals become `CLARIFY` rather than silently amending or continuing.
- The transitional test/developer override is disabled by default and requires `PARALLAX_ALLOW_SCOPE_OVERRIDE=true`; override use is observable in the trace.
- If scope routing exhausts all candidates, Parallax does not fabricate a protected decision; the safe trace records `protected_scope_decision: null` and a recoverable `ERROR` state.

### Typed Reason program and protected verification

- The DSPy Reason program receives the current objective, deterministic context, mode, active spec ID, and protected scope decision.
- Typed Reason output includes the user-facing answer, bounded confidence, bounded material uncertainties, bounded material assumptions, and program version.
- Observable uncertainty/assumption metadata is explicitly not hidden chain-of-thought.
- Protected validation rejects malformed confidence/metadata, unsafe secret-bearing output, exposed hidden-reasoning payloads, unfocused clarification responses, and other contract violations before completion.
- Protected-invalid Reason results escalate through Luna → Terra → Sol.
- If every Reason candidate fails provider execution or protected validation, the durable user turn remains preserved and the API returns a sanitized recoverable error.

### Amendment containment

- A protected material-objective change transitions the conversation to `SPEC_AMENDMENT`.
- The prior conversation and current user turn are preserved.
- A concise assistant hand-off message is persisted.
- The SSE endpoint emits an explicit `SPEC_AMENDMENT` state plus an `amendment` event.
- No substantive response chunks are emitted under the old approved objective.
- The client renders the state calmly, keeps the conversation intact, and disables the optical typesetter.

### Observable traces

Reason traces now contain only observable execution evidence needed to explain behavior:

- response/conversation/spec identity;
- scope and Reason program versions when available;
- protected scope decision, nullable only when unresolved;
- scope override/policy-adjustment indicator;
- context digest/turn count/truncation;
- model attempts and statuses;
- protected verification outcome;
- final state.

Invalid candidate answer text, provider credentials, environment values, DSPy rationale, chain-of-thought, and scratchpads are excluded from the public trace.

### Client state and visual behavior

- The response reducer now supports `SPEC_AMENDMENT` in addition to the inherited response lifecycle.
- `SPEC_AMENDMENT` surface energy is `0.22`; laser is off.
- Recoverable `ERROR` state uses sanitized server recovery copy rather than technical provider exception text.
- Visible spec metadata is derived from the active durable conversation rather than a stale hard-coded release label.
- Reduced-motion and reduced-graphics behavior remain functional.

## Validated Reason benchmark and promotion evidence

P2-V0.3.0 adds separate repository-safe Reason `development` and `promotion` suites. Each covers ten protected behaviors:

1. ordinary follow-up continuity;
2. later-user-correction precedence;
3. material objective change requiring `SPEC_AMENDMENT`;
4. focused clarification for materially blocking ambiguity;
5. uncertainty/status honesty when evidence is incomplete;
6. generated-versus-validated-versus-deployed honesty;
7. secret/credential non-disclosure;
8. hidden-chain-of-thought request handling;
9. concise direct engineering communication;
10. protected failure/degradation behavior.

Recorded offline evidence includes a known-good baseline, an equivalent challenger, and deliberate continuity, status-honesty, and material-scope regressions. The equivalent challenger passes; each deliberate regression is rejected for protected machine-readable reasons.

## Exact-head validation evidence

GitHub Actions run `32371806776` completed successfully for implementation head `d96442c39fc2534fd733a50d39527ffd158653ee`.

PASS:

- v0.1.0, v0.2.0, and v0.3.0 specification gates;
- Python dependency installation and source compilation;
- full API/backend automated test suite;
- deterministic context and correction-precedence tests;
- server-side scope authority and low-confidence policy tests;
- protected scope and Reason validation/escalation tests;
- recoverable scope-exhaustion and Reason-exhaustion trace tests;
- SSE continuation and `SPEC_AMENDMENT` API behavior;
- durable conversation active-spec identity and historical-spec preservation;
- general engineering development/promotion benchmark validation;
- Reason development/promotion benchmark validation;
- equivalent Reason challenger promotion pass;
- continuity, status-honesty, and material-scope regression rejection;
- mandatory DSPy SpecCritic + SpecCompiler execution against `P2-V0.3.0`;
- protected compiled-plan acceptance verification;
- frontend dependency installation and TypeScript typecheck;
- response-state tests including `SPEC_AMENDMENT`;
- Expo web export;
- Playwright/Chromium visual acceptance;
- Skia/CanvasKit initialization;
- live optical inscription during an open SSE response;
- responsive mobile/tablet/desktop checks;
- CanvasKit failure-degradation check;
- CI evidence retention.

### Exact-head artifacts

Protected evaluation evidence:

- artifact: `evaluation-evidence`;
- artifact ID: `9407468517`;
- SHA-256: `4c2ebbe990f3ab0f7c52e3d98801c61ed83373819b2d530fc3adfd486d622488`.

Client/browser build evidence:

- artifact: `client-build-evidence`;
- artifact ID: `9407488223`;
- SHA-256: `7da3d87d0b95d85bdc64e58900f69331d4413f602bd1da0375963cf7a43c2736`.

Mandatory DSPy development evidence:

- artifact: `dspy-development-evidence`;
- artifact ID: `9407516992`;
- SHA-256: `bed0ecedb57a82b76c3d66525ff66ac75e67bebc242b2254e1b319f8160f42d4`.

The credential-free local DSPy model proves the required DSPy development methodology executes. It is not the final runtime quality authority. A provider-backed MIPROv2 Reason optimization/promotion run has **not** been executed and is not claimed.

## Inherited validated foundation and v0.2 evaluation spine

- Durable conversation creation/list/get/message persistence remains implemented.
- The browser restores durable conversations and recent history from the FastAPI service.
- The response endpoint streams SSE state/chunk/complete events for substantive answers.
- The client inscribes response text while chunks are arriving rather than replaying an animation after completion.
- `LivingSurface`, `LaserTypesetter`, and `ParallaxLogo` retain Skia/CanvasKit web support and reduced-graphics fallback.
- The v0.2 protected evaluation subsystem remains outside optimizer-controlled runtime programs.
- General development/promotion suite separation, deterministic scoring, evidence construction, secret/hidden-reasoning checks, and baseline/challenger promotion policy remain intact.
- Preview-readiness code/config remains validated but not deployed.

## Known validation notes

`npm audit` continues to report issues in the Expo/Metro build-tool dependency graph. The exported browser artifact does not ship the identified build-time tooling. An unsafe framework downgrade is not justified solely to silence build-tool findings; this remains tracked dependency-maintenance risk.

The foundation still uses SQLAlchemy `Base.metadata.create_all()` for schema bootstrap. Explicit versioned migrations remain required before a durable production release.

The current Reason benchmark is intentionally repository-safe and synthetic. Passing it proves the v0.3.0 contracts and evaluation mechanism; it does not establish general-purpose reasoning supremacy or replace future real-world benchmark expansion.

Provider-backed Reason optimization has not yet been executed. v0.3.0 validation proves the architecture and protected contracts, not that the current unoptimized runtime prompt/program is the final quality ceiling.

## Release state

- Generated v0.3.0: **YES**
- Validated Reason 2.0 architecture/contracts: **YES**
- Validated protected Reason evaluation: **YES**
- Validated inherited evaluation spine/foundation: **YES**
- Validated preview-readiness code/config: **YES**
- Provider-backed DSPy/MIPROv2 Reason optimization: **NO**
- Dedicated P2 Supabase project created: **NO**
- Dedicated P2 Vercel web/API projects created: **NO**
- Deployed: **NO**
- Deployment-verified: **NO**

No P2 release deployment is claimed. The existing P1 Vercel production project has not been modified for P2.

## Next gates

1. Build **Code 2.0** under a new approved specification, stacked on validated Reason 2.0, with the same mandatory DSPy pre-implementation gate.
2. Make engineering-run/workspace state durable and explicitly model the `SPECIFY → PLAN → IMPLEMENT → BUILD → TEST → VERIFY → REVIEW` lifecycle rather than embedding execution behavior in chat handlers.
3. Add protected Code development/promotion benchmarks for specification fidelity, patch correctness, test/build evidence, failure diagnosis, protected-boundary preservation, status honesty, and safe tool/command behavior before Code 2.0 is called validated.
4. Add closed-loop repair only after Code 2.0 has an observable baseline and protected evaluation; do not let repair logic mutate its own acceptance criteria.
5. Execute provider-backed DSPy optimization when approved provider configuration is available and compare challengers against protected promotion evidence before promotion.
6. With explicit organization/cost approval, create dedicated P2 preview infrastructure and collect deployment-verification evidence.
7. Replace schema bootstrap with explicit versioned migrations before a durable production release.
