# Parallax 2.0 Current State

Version: 0.1.0-bootstrap
Date: 2026-08-20
Status: GENERATED / PARTIALLY LOCALLY VALIDATED — NOT DEPLOYED

## Material decision

Parallax 2.0 is being built as a separate product track in `Ryan9876/parallax` using a spec-first development process and a DSPy-compatible optimization architecture.

The approved v0.1.0 specification is `specs/P2-V0.1.0.md`.

## Generated foundation

- Expo/React Native/Skia client scaffold.
- Living Skia material surface.
- Calm animated Parallax Lens Mark.
- Optical laser typesetter tied to response state.
- Pure response reducer and deterministic motion-state mapping.
- FastAPI service scaffold.
- Durable conversation/message persistence via SQLAlchemy.
- Multi-turn conversation append contract.
- Luna → Terra → Sol fallback router.
- DSPy reasoning/spec-compiler boundaries.
- Protected metrics outside optimizer-controlled modules.
- Spec validation, compilation, and optimization tooling.
- GitHub CI definitions.

## Validation evidence

Local environment validation available without package-registry access:

- Python source compile: PASS (`python -m compileall` against API and build scripts).
- Backend tests using installed FastAPI/SQLAlchemy: PASS — 6 tests.
- Pure TypeScript response-state compile/test: PASS.
- TypeScript/TSX syntax parse across the client source: PASS.
- Full Expo dependency install, package-level typecheck, web export, and Skia runtime validation: NOT YET POSSIBLE in the current offline build container.
- Real DSPy compiler/optimizer execution: NOT EXECUTED. Current container cannot reach package registries and has no provider credentials. The bootstrap plan is explicitly marked as human-reviewed, not optimizer-generated.

## Deployment

No deployment has been performed or claimed.

## Next validation gate

In a network-enabled environment:

1. install client dependencies;
2. run Skia CanvasKit setup;
3. run client typecheck/tests and web export;
4. install API dependencies including DSPy;
5. execute the DSPy spec compiler against the approved spec with provider credentials;
6. run API tests;
7. compare any DSPy-produced implementation-plan changes against the bootstrap plan before accepting them;
8. create a preview deployment and collect desktop/mobile motion evidence.
