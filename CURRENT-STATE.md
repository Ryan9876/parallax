# Parallax 2.0 Current State

Version: 0.1.0-foundation
Date: 2026-08-20
Status: VALIDATED FOUNDATION — NOT DEPLOYED
Active spec: `P2-V0.1.0`
Branch: `p2/bootstrap-v0.1.0`
Validated implementation head: `d686bc639fd99fe1b1218801d14632558b78295e`
Validation workflow: GitHub Actions `Parallax P2 CI` run `32355760742`

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
- `ParallaxLogo` provides calm non-spinner motion with reduced-motion behavior.
- Responsive visual acceptance passed at the required mobile, tablet, and desktop sizes.
- Intentional CanvasKit/WASM failure was tested: the application remains usable in reduced-graphics mode with normal conversation text and no Skia dependency for message truth.

### Spec-first + DSPy development evidence

The repository was specified before implementation through `specs/P2-V0.1.0.md`, and CI now requires a real DSPy development execution after the deterministic spec/API gate passes.

Validation run `32355760742` executed both `SpecCritic` and `SpecCompiler` through DSPy using the credential-free local development model `ollama_chat/qwen2.5:0.5b` because no provider secret was configured. The resulting artifact records:

- `executed: true`;
- `spec_compiler_executed: true`;
- `spec_critic_executed: true`;
- `provider_backed: false`;
- protected metrics required;
- exact protected acceptance contract injected outside optimizer control.

The local 0.5B model is **not** treated as the plan-quality authority. Its generated implementation proposal is intentionally CI evidence only and is not promoted into the branch. Protected deterministic code preserves every approved acceptance criterion and supplies missing validation coverage before evaluation.

A provider-backed Sol + MIPROv2 optimization run has **not yet been executed**. That remains a separate quality-optimization gate and must not be represented as complete until provider-backed evidence exists.

## Validation evidence

GitHub Actions run `32355760742` completed successfully at implementation head `d686bc639fd99fe1b1218801d14632558b78295e`.

PASS:

- approved spec gate;
- Python dependency installation;
- Python source compilation;
- FastAPI/SQLAlchemy/DSPy backend automated tests;
- mandatory DSPy SpecCritic + SpecCompiler execution;
- protected acceptance-contract evaluation;
- frontend dependency installation;
- TypeScript typecheck;
- response-state tests;
- Expo web export;
- Playwright/Chromium browser validation;
- Skia/CanvasKit initialization;
- live optical inscription during an open SSE response;
- responsive mobile/tablet/desktop visual checks;
- CanvasKit failure-degradation check;
- CI evidence artifact upload.

### Known validation note

`npm audit` still reports vulnerabilities in the current Expo/Metro build-tool dependency graph. The exported browser artifact does not ship the identified Metro/image-parser tooling. An unsafe major Expo downgrade via `npm audit fix --force` was intentionally not applied. This remains a tracked dependency-maintenance risk rather than a release-state claim that the toolchain is vulnerability-free.

## Release state

- Generated: **YES**
- Validated foundation: **YES**
- Deployed: **NO**
- Deployment-verified: **NO**
- Provider-backed DSPy/MIPROv2 optimization: **NO**

No P2 deployment has been performed or claimed.

## Next gate

1. Execute the provider-backed DSPy SpecCritic/SpecCompiler and MIPROv2 optimizer with an approved development model/provider configuration.
2. Compare the challenger artifact against the protected metrics and the validated foundation rather than accepting it automatically.
3. Create a preview deployment only after the provider/runtime environment and persistence target are selected.
4. Collect target-environment health, persistence, responsive UI, Skia motion, and failure-degradation evidence before claiming deployment-verified status.
