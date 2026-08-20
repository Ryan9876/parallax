# Parallax 2.0 Current State

Version: 0.2.0-evaluation
Date: 2026-08-20
Status: VALIDATED EVALUATION SPINE + FOUNDATION/PREVIEW READINESS — NOT DEPLOYED
Active spec: `P2-V0.2.0`
Branch: `p2/evaluation-v0.2.0`
Validated implementation head: `3b1e93af9989f6af6a58dc4a4df153c02601ccf7`
Validation workflow: GitHub Actions `Parallax P2 CI` run `32365718862`

## Material decisions

- Parallax 2.0 remains a separate product track in `Ryan9876/parallax`.
- P2 is developed using approved specifications and mandatory DSPy development execution before substantive AI-program work.
- Protected evaluation is now a first-class architecture boundary rather than ad-hoc DSPy scoring code.
- Development benchmark evidence may be consumed by optimizers; promotion-suite contracts, thresholds, evaluators, and promotion rules may not.
- A higher aggregate score cannot compensate for a critical protected failure or an excessive protected category regression.
- Promotion passing does not authorize an automatic merge, deployment, threshold change, or authoritative-record update.
- Runtime model routing remains Luna → Terra → Sol.
- Expo + React Native + React Native Skia remains the universal client baseline; FastAPI + SQLAlchemy + DSPy remains the intelligence-service baseline.
- Server-side durable conversations remain the source of truth; browser storage remains draft convenience only.
- The first approved P2 MP4 material study, optical laser typesetter, and calm Parallax Lens Mark remain the visual baseline.
- P2 preview deployment remains isolated from the existing Parallax 1.x Vercel production project.
- The selected preview topology remains dedicated P2 web/API Vercel projects plus a dedicated Supabase PostgreSQL project; those external resources have not yet been created for P2.

## Validated v0.2.0 evaluation spine

### Benchmark model

- Typed benchmark schemas cover suite identity/version/purpose, case identity/category/objective/context, required and forbidden contracts, exact protected assertions, weights, floors, and candidate fixture data.
- Loaders reject malformed suites, duplicate case IDs, unsupported purposes, invalid weights, and cases without an executable protected contract.
- The initial repository-safe Parallax Engineering Benchmark contains separate `development` and `promotion` suites.
- Both suites cover the required eight behavioral categories: specification fidelity, conversation continuity, implementation-plan completeness, protected-boundary preservation, failure/degradation handling, evidence/status honesty, secret handling, and concise engineering communication.

### Protected scoring and promotion

- Deterministic scoring computes declared required coverage, forbidden violations, exact protected assertions, per-case results, category summaries, aggregate score, and explicit failure reasons.
- Promotion code accepts only compatible promotion-suite artifacts.
- A challenger is rejected for protected case/category-floor failures, new critical protected failures, incompatible evaluator evidence, aggregate/category regression beyond protected tolerances, or use of development evidence as promotion authority.
- The optimizer boundary is structural: protected promotion logic lives outside optimizer-controlled DSPy program modules.

### Evidence and security

- Evaluation artifacts record run/spec/suite/evaluator/program/model identity, input identity/digest, per-case outcomes, category scores, aggregate score, protected pass/fail, and a no-chain-of-thought marker.
- Candidate output is treated as untrusted text.
- Tests reject configured secret-bearing benchmark/evidence content and hidden-reasoning fields such as chain-of-thought and scratchpad payloads.
- CLI tooling validates suites, evaluates recorded candidates, writes evidence, compares baseline/challenger artifacts, and returns non-zero exits on protected failure.

### Offline evaluation CI evidence

Run `32365718862` executed the credential-free evaluation gate at reconciled implementation head `3b1e93af9989f6af6a58dc4a4df153c02601ccf7`.

PASS:

- development and promotion benchmark validation;
- recorded development fixture evaluation;
- promotion baseline evaluation;
- equivalent challenger promotion pass;
- intentional protected-regression challenger rejection;
- evaluation artifact retention.

Exact-head evaluation evidence artifact:

- name: `evaluation-evidence`;
- artifact ID: `9405222370`;
- SHA-256: `fd1db41fe6787755f984e4d25c7d6422befd68820e210e37b452d73d1fc4ae4e`.

## Inherited validated foundation

### Conversation and intelligence

- Durable conversation creation, list/get, message append, and persistence are implemented.
- Ordinary follow-ups remain in the active conversation; material scope change is represented explicitly rather than silently resetting context.
- The browser client restores durable conversations and recent history from the FastAPI service.
- The response endpoint streams SSE state/chunk/complete events.
- The client inscribes the response while chunks are arriving; it does not wait for a complete answer and replay the laser afterward.
- The response state machine is the single source of truth for product state and visual motion state.
- Luna → Terra → Sol routing and failure escalation remain isolated behind the intelligence boundary.

### Visual system

- `LivingSurface` initializes through React Native Skia/CanvasKit on web.
- Surface energy is linked to response state.
- `LaserTypesetter` follows active wrapped text, reveals normal selectable text behind the optical head, and cools new glyphs back to normal typography.
- Browser acceptance holds the mock SSE stream open across staggered chunks and proves visible inscription occurs before completion.
- `ParallaxLogo` provides calm non-spinner motion with reduced-motion behavior.
- Responsive visual acceptance covers mobile, tablet, and desktop.
- Intentional CanvasKit/WASM failure leaves a functional reduced-graphics conversation experience.

### Preview deployment readiness

- `apps/client/vercel.json` defines the Expo web preview artifact.
- `services/api/pyproject.toml` defines the FastAPI Vercel entrypoint and includes psycopg 3 PostgreSQL support.
- PostgreSQL URLs normalize to psycopg 3; preview/production engines use `NullPool`; prepared statements are disabled for transaction-pooler compatibility.
- `/health` proves process availability and `/ready` probes database reachability.
- Dynamic preview CORS uses a narrowly scoped configuration boundary.
- No dedicated P2 Vercel web project, P2 API project, or P2 Supabase project has yet been created or deployment-verified.

## Spec-first + DSPy development evidence

`P2-V0.2.0` was committed before evaluation implementation. The mandatory DSPy SpecCritic + SpecCompiler path executed against the approved v0.2.0 specification before the evaluation subsystem was treated as implementation-authorized.

The reconciled exact-head run `32365718862` again executed the credential-free DSPy development path successfully. Exact-head DSPy evidence:

- artifact name: `dspy-development-evidence`;
- artifact ID: `9405265033`;
- SHA-256: `9271f5bcb2ba179d42bafa2910620a303ca66521ddcb5e10315031bf8ca68016`.

The local development model proves the DSPy build methodology executes; it is not the quality authority. A provider-backed Sol + MIPROv2 optimization/promotion run has **not** been executed and is not claimed.

## Exact-head regression validation

GitHub Actions run `32365718862` completed successfully for reconciled head `3b1e93af9989f6af6a58dc4a4df153c02601ccf7` after v0.2.0 was brought forward onto the latest validated preview-readiness foundation.

PASS:

- v0.1.0 and v0.2.0 approved spec gates;
- Python dependency installation/source compilation;
- full API/backend automated test suite, including evaluation tests and inherited persistence/preview-readiness coverage;
- mandatory DSPy SpecCritic + SpecCompiler execution and protected acceptance validation;
- credential-free protected evaluation smoke gate;
- frontend dependency installation;
- TypeScript typecheck;
- response-state tests;
- Expo web export;
- Playwright/Chromium browser validation;
- Skia/CanvasKit initialization;
- live optical inscription during an open SSE response;
- responsive mobile/tablet/desktop checks;
- CanvasKit failure-degradation check;
- CI artifact retention.

Client build evidence artifact:

- artifact ID: `9405241821`;
- SHA-256: `0b87f5cd77972d81774dd2c611cb71af97b78b1b5c1df0b52607d4afd7c76e92`.

## Known validation notes

`npm audit` continues to report issues in the Expo/Metro build-tool dependency graph. The exported browser artifact does not ship the identified build-time tooling. An unsafe major Expo downgrade was intentionally not applied; this remains tracked dependency-maintenance risk.

The foundation still uses SQLAlchemy `Base.metadata.create_all()` for schema bootstrap. Explicit versioned migrations are required before a durable production release.

The initial benchmark is intentionally small, synthetic, and repository-safe. Passing it proves the v0.2.0 evaluation mechanism, not comprehensive engineering intelligence quality.

## Release state

- Generated v0.2.0: **YES**
- Validated evaluation spine: **YES**
- Validated foundation: **YES**
- Validated preview-readiness code/config: **YES**
- Provider-backed DSPy/MIPROv2 optimization: **NO**
- Dedicated P2 Supabase project created: **NO**
- Dedicated P2 Vercel web/API projects created: **NO**
- Deployed: **NO**
- Deployment-verified: **NO**

No P2 release deployment is claimed. The existing P1 Vercel production project has not been modified for P2.

## Next gates

1. Build **Reason 2.0** under a new approved specification and evaluate it against the protected evaluation spine rather than tuning by intuition.
2. Expand development/promotion benchmark coverage as real P2 behaviors are introduced, without allowing optimizer-controlled code to rewrite protected promotion criteria.
3. Execute provider-backed SpecCritic/SpecCompiler + MIPROv2 optimization when an approved provider configuration is available; compare the challenger against protected promotion evidence before any promotion.
4. With explicit organization/cost approval, create the dedicated P2 Supabase and isolated P2 Vercel preview projects.
5. Replace schema bootstrap with versioned migrations before a durable production release.
