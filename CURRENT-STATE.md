# Parallax 2.0 Current State

Version: 0.1.0-foundation
Date: 2026-08-20
Status: VALIDATED FOUNDATION + PREVIEW READINESS — NOT DEPLOYED
Active spec: `P2-V0.1.0`
Branch: `p2/bootstrap-v0.1.0`
Validated implementation head: `3418373631741a2240a4fc1e17ab97816d30787f`
Validation workflow: GitHub Actions `Parallax P2 CI` run `32359617879`

## Material decisions

- Parallax 2.0 is a separate product track in `Ryan9876/parallax`.
- P2 is developed using spec-first contracts and mandatory DSPy development execution, not merely built to expose those capabilities later.
- Expo + React Native + React Native Skia is the universal client baseline.
- FastAPI + SQLAlchemy + DSPy is the intelligence-service baseline.
- Runtime model routing remains Luna → Terra → Sol.
- Server-side durable conversations are the source of truth; browser storage is limited to draft convenience.
- The first approved P2 MP4 material study remains the visual baseline.
- The optical laser typesetter is the signature response behavior.
- The Parallax Lens Mark uses two calm optical planes moving into and out of near-alignment around a stable center.
- P2 preview deployment is isolated from the existing Parallax 1.x Vercel production project; the existing Vercel project named `parallax` is not a P2 target.
- P2 preview uses two dedicated Vercel projects from the same repository: web rooted at `apps/client` and API rooted at `services/api`.
- A dedicated Supabase PostgreSQL project is the selected P2 preview persistence target. No Supabase resource has yet been created for P2.
- Until application-level authentication exists, a P2 deployment attached to durable data or commercial provider credentials must remain a protected preview.

## Validated foundation

### Conversation and intelligence

- Durable conversation creation, list/get, message append, and persistence are implemented.
- Ordinary follow-ups remain in the active conversation; a material scope change is represented explicitly rather than silently resetting context.
- The browser client restores durable conversations and recent history from the FastAPI service.
- The response endpoint streams SSE state/chunk/complete events.
- The client inscribes the response while chunks are arriving; it does not wait for a complete answer and replay the laser afterward.
- The response state machine is the single source of truth for product state and visual motion state.
- Luna → Terra → Sol routing and failure escalation are isolated behind the intelligence boundary and covered by tests.

### Visual system

- `LivingSurface` initializes through React Native Skia/CanvasKit on web.
- Surface energy is linked to response state.
- `LaserTypesetter` follows the active wrapped text line, reveals normal selectable text behind the optical head, and cools freshly revealed glyphs back to normal typography.
- The browser acceptance harness explicitly holds the mock SSE response open across staggered chunks and verifies that visible inscription begins after an intermediate chunk, before the stream completes.
- `ParallaxLogo` provides calm non-spinner motion with reduced-motion behavior.
- Responsive visual acceptance passed at the required mobile, tablet, and desktop sizes.
- Intentional CanvasKit/WASM failure was tested: the application remains usable in reduced-graphics mode with normal conversation text and no Skia dependency for message truth.

### Preview deployment readiness

The deployment contract is now implemented and validated without claiming that external infrastructure exists:

- `apps/client/vercel.json` defines the Expo web export as the P2 web preview artifact.
- `apps/client/.env.example` documents the public API base configuration boundary.
- `services/api/pyproject.toml` defines the FastAPI Vercel entrypoint and includes psycopg 3 PostgreSQL support.
- managed `postgres://` / `postgresql://` URLs normalize to SQLAlchemy psycopg 3 URLs;
- preview/production PostgreSQL engines use `NullPool`, leaving connection reuse to the managed transaction pooler;
- psycopg prepared statements are disabled for Supabase/Supavisor transaction-pooler compatibility;
- preview CORS can use a narrowly scoped `PARALLAX_CORS_ORIGIN_REGEX` for dynamic P2 web preview hostnames;
- `/health` remains the service probe and `/ready` executes a database `select 1` before database readiness is claimed;
- backend tests cover URL normalization, provider-side pooling configuration, health, and readiness.

No P2 Vercel web project, P2 Vercel API project, or P2 Supabase project has been created or deployed yet.

### Spec-first + DSPy development evidence

The repository was specified before implementation through `specs/P2-V0.1.0.md`, and CI requires a real DSPy development execution after the deterministic spec/API gate passes.

Validation run `32359617879` executed both `SpecCritic` and `SpecCompiler` through the credential-free local development path. The local-LM installation step ran successfully, which confirms this was not the provider-backed path.

The local model is **not** treated as the plan-quality authority. Its generated implementation proposal is CI development-method evidence only and is not promoted into the branch. Protected deterministic code preserves every approved acceptance criterion and supplies missing validation coverage before evaluation.

A provider-backed Sol + MIPROv2 optimization run has **not yet been executed**. GitHub Actions currently has no usable `OPENAI_API_KEY` for that gate. This must not be represented as complete until provider-backed evidence exists.

## Validation evidence

GitHub Actions run `32359617879` completed successfully for validated implementation head `3418373631741a2240a4fc1e17ab97816d30787f`.

PASS:

- approved spec gate;
- Python dependency installation including psycopg 3;
- Python source compilation;
- 14 FastAPI/SQLAlchemy/DSPy backend automated tests;
- PostgreSQL URL normalization test;
- preview provider-side pooling / `NullPool` test;
- database readiness-route test;
- mandatory DSPy SpecCritic + SpecCompiler execution through the local development path;
- protected acceptance-contract evaluation;
- frontend dependency installation;
- TypeScript typecheck;
- response-state tests;
- Expo web export using the preview build contract;
- Playwright/Chromium browser validation;
- Skia/CanvasKit initialization;
- live optical inscription during an open SSE response;
- explicit intermediate-chunk observation before SSE completion;
- responsive mobile/tablet/desktop visual checks;
- CanvasKit failure-degradation check;
- CI evidence artifact upload.

### Known validation notes

`npm audit` still reports vulnerabilities in the current Expo/Metro build-tool dependency graph. The exported browser artifact does not ship the identified Metro/image-parser tooling. An unsafe major Expo downgrade via `npm audit fix --force` was intentionally not applied. This remains a tracked dependency-maintenance risk rather than a release-state claim that the toolchain is vulnerability-free.

The foundation still uses SQLAlchemy `Base.metadata.create_all()` for schema bootstrap. That is acceptable for the isolated preview but must be replaced by explicit versioned migrations before a durable production release.

## Release state

- Generated: **YES**
- Validated foundation: **YES**
- Validated preview-readiness code/config: **YES**
- Dedicated P2 Supabase project created: **NO**
- Dedicated P2 Vercel projects created: **NO**
- Deployed: **NO**
- Deployment-verified: **NO**
- Provider-backed DSPy/MIPROv2 optimization: **NO**

No P2 deployment has been performed or claimed. The existing P1 Vercel production project has not been modified for P2.

## Next gates

1. Configure an approved `OPENAI_API_KEY` GitHub Actions secret and execute the provider-backed DSPy SpecCritic/SpecCompiler + MIPROv2 optimization workflow.
2. Compare the provider-backed challenger against protected metrics and the validated foundation; do not promote it automatically.
3. With explicit organization/cost approval, create a dedicated P2 Supabase PostgreSQL project and use its transaction-pooler connection string for `DATABASE_URL`.
4. Create dedicated protected P2 Vercel web/API preview projects, keeping the P1 `parallax` project untouched.
5. Configure scoped runtime environment variables, deploy the protected preview, and verify `/health`, `/ready`, persistence across requests, SSE streaming, live optical inscription, responsive UI, Skia initialization, and reduced-graphics degradation before claiming deployment-verified status.
