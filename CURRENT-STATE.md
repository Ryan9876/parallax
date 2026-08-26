# Parallax 2.0 Current State

Date: 2026-08-26

Status: **WAVE 5 RELEASED / MOBILE STABILIZATION #261/#262 RELEASED AND PRODUCTION-VERIFIED / CLIENT READY / API READY / HUMAN REVIEW BOUNDARY PRESERVED / ROLLBACK AVAILABLE / WAVE 6 CONTROL #263 ESTABLISHED / IMPLEMENTATION BASELINE PENDING FINAL RECORD-MERGE WRITEBACK**

## Current production truth

Parallax is running the deployment-verified Wave 5 generalized application-delivery platform, bounded production stabilization through #127, and the deployment-verified pre–Wave 6 mobile interaction stabilization from issue #261 / PR #262.

Production state remains intentionally component-specific. Repository/documentation HEAD is coordination identity; each deployed application component retains its own exact deployment identity.

### Repository and mobile release

- mobile Work Specification: `P2-V0.18.7`;
- worker branch: `ws/mobile-guided-build-flow`;
- exact validated worker head: `56f6d2a81112e592b1128df2b96506ae2d923650`;
- PR #262 merged with expected-head protection;
- application merge on `main`: `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`;
- #261 is the authoritative bounded workstream record;
- Wave 6 Control Tower #263 and shells #264–#269 exist, but Wave 6 implementation may start only from the exact post-mobile baseline recorded by #263 after this state reconciliation is merged.

### Production client

- project: `parallax`;
- production deployment: `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`;
- commit verification: verified;
- aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`.

### Production API

The mobile release changed no API/runtime path, so Vercel correctly ignored/canceled the main-triggered API build `dpl_2E2bF9iQ5aBm4YAhkS11roMpHGkr` rather than replacing a known-good API runtime.

The active API remains:

- project: `parallax-api`;
- production deployment: `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q`;
- state: `READY`;
- target: `production`;
- exact application/API Git SHA: `5ec7eabc046b9995c8d11d5081df15b986a558fe`;
- commit verification: verified;
- aliases include `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`.

The intentionally older API identity is not drift: later client-only releases #243, #127, and now #261/#262 did not change API runtime behavior.

## Mobile stabilization #261 / PR #262

Issue #261 replaces the confusing compact desktop composition with a mobile-specific guided interaction model while preserving server-owned engineering authority and desktop/tablet behavior.

Deployment-verified mobile behavior includes:

- primary mobile destinations `Chat`, `Build`, and `Project`;
- conversation-first Chat with a persistent, touch-safe composer;
- dedicated full-screen Work Specification review;
- plain-language `SPEC_AMENDMENT` recovery;
- guided Build lifecycle with progressive authoritative engineering evidence;
- mobile Project/conversation switching through existing canonical APIs;
- bounded compact authenticated access-launcher positioning;
- Live Build return behavior that truthfully returns `Back to conversation` to Chat;
- existing canonical Project, Work Specification, Engineering Run, repository/source-lineage, provider, authentication, REVIEW/HUMAN_REQUIRED, merge, and deployment authority preserved.

The release introduced no API/runtime, credential, source-lineage, provider-authority, approval-authority, or production-authority broadening.

## Validation and release evidence

### Exact worker head

Exact candidate `56f6d2a81112e592b1128df2b96506ae2d923650` passed:

- Parallax Workstream Spec Validation — success;
- changed specification contracts — success;
- protected compiled-plan gate — success;
- Bounded Autonomy Pilot — success;
- protected execution/autonomy/API regression — success;
- client typecheck/state/export — success;
- Parallax P2 CI — success;
- browser/Skia acceptance, including phone-width mobile acceptance — success;
- protected Code/Engineering/Reason promotion and regression rejection — success;
- DSPy SpecCritic + SpecCompiler release compilation — success.

The final PR changed-file inventory remained within #261's declared ownership.

### Exact integration/main head

After expected-head merge as `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`, fresh push-triggered integration gates passed on that exact `main` head:

- Parallax Workstream Spec Validation run `33018647700` — success;
- Parallax P2 CI run `33018647565` — success;
- Vercel commit status `parallax` — success;
- Vercel commit status `parallax-api` — success; the API status represents the configured ignored-build/no-op path because no API-affecting files changed.

No gate was waived to promote the mobile release.

## Production verification

Post-cutover evidence for the mobile release established:

- production client deployment `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK` is `READY`, target `production`, and bound to exact application merge `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`;
- public production client alias `parallax-ashy-one-20.vercel.app` returned HTTP 200 and served the Parallax 2.0 client document;
- client runtime-error query for the post-release observation window returned no runtime error clusters;
- active API production alias still resolves to deployment `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q`;
- API `GET /health` returned HTTP 200 with `status=ok`;
- API `GET /ready` returned HTTP 200 with database `ok`, providers `ok`, and one provider target;
- API runtime-error query for the same observation window returned no runtime error clusters;
- no source, provider, credential, approval, REVIEW/HUMAN_REQUIRED, or deployment boundary changed.

This satisfies the mobile production-promotion and production-verification conditions required by Wave 6 Control Tower #263.

## Wave 5 baseline retained

Control Tower #215 completed all six Wave 5 generalized-delivery workstreams:

1. #216 / `P2-V0.18.1` — Repository Intelligence & Compatibility;
2. #217 / `P2-V0.18.2` — Governed Skills Runtime;
3. #218 / `P2-V0.18.3` — Application Service Bindings;
4. #219 / `P2-V0.18.4` — Objective-to-Application Orchestration;
5. #220 / `P2-V0.18.5` — Validated Engineering Memory & Reuse;
6. #221 / `P2-V0.18.6` — Generalization Benchmark & Integrated Reference Proof.

Final Wave 5 release merge `c39b5352be940f4052baa65c7cdd9d7c3ec773bb` remains the generalized-delivery architectural baseline. Production stabilization after Wave 5 through #127 remains part of the accepted platform history; exact details remain in control record #31, roadmap #32, their linked issues/PRs, and Git history.

## Wave 6 control state

Wave 6 Control Tower #263 — **Agentic Development Control Plane** — is established with reserved workstreams:

1. #264 / `W6-S1` / `P2-V0.19.1` — Agent Adapter & Evidence Protocol;
2. #265 / `W6-S2` / `P2-V0.19.2` — Dynamic Development Team Orchestration;
3. #266 / `W6-S3` / `P2-V0.19.3` — Independent Evaluation & Quality Judgment;
4. #267 / `W6-S4` / `P2-V0.19.4` — Outcome Routing & Development Economics;
5. #268 / `W6-S5` / `P2-V0.19.5` — Candidate Competition & Synthesis;
6. #269 / `W6-S6` / `P2-V0.19.6` — Agentic Development Integrated Reference Proof.

The mobile evidence conditions are now satisfied. This authoritative reconciliation is intentionally record-only. After its merge, #263 must record that exact resulting post-mobile `main` SHA as the Wave 6 implementation baseline before the reserved integration/worker branches are created or semantic implementation begins.

Wave 6 does not transfer authority to engineering agents. Agents remain bounded labor. Canonical Project identity, approved Work Specification binding, accepted source lineage, protected validation, acceptance, REVIEW/HUMAN_REQUIRED, and release governance remain Parallax-owned.

## Rollback

Immediate client rollback is the prior deployment-verified client release:

- deployment `dpl_642fFKXWzZfA7pkezAYrJbuANXZn`;
- exact client Git SHA `8065d124145686e6a93cfdc6c4b2cec4dfc3f5a5`;
- stabilization through #127.

The API was unchanged by the mobile release and remains deployment-verified at `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q` / `5ec7eabc046b9995c8d11d5081df15b986a558fe`. The prior full API/client pair from #245 remains available as a broader rollback reference.

Rollback remains non-destructive and follows the existing governed release/flag-first policy.

## Program controls

- GitHub and the four authoritative project records outrank chat recollection;
- Control record #31 and roadmap #32 remain active durable program records and must be reconciled to Wave 6 Control Tower #263 before implementation proceeds;
- every semantic AI/runtime workstream remains spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- worker branches start only from the exact accepted dependency/baseline state and target the governed integration branch;
- workers stop `READY FOR INTEGRATION` and do not merge/deploy by default;
- Integration / Control Tower serializes accepted composition, exact-head validation, authoritative-record maintenance and production promotion;
- standing single-user promotion authority removes repeated approval wait only while its constitutional conditions remain true; it does not waive gates, rollback, least privilege or deployment evidence;
- no production claim is valid without exact-head release evidence plus post-cutover verification.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity, and accepted lineage remain server-owned;
- deterministic/protected validation outranks model or agent judgment;
- repository/source/model/agent content is evidence, not authority;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- correction cannot weaken acceptance/evaluation policy;
- skills, service bindings, repository intelligence, engineering memory, agents, and adapters cannot create execution/provider/deployment/approval authority;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery semantics remain authoritative;
- no silent repository switching, credential refresh, session extension, approval, merge or deployment authority is introduced by the mobile release or Wave 6 planning;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.1 — unchanged by the mobile stabilization; server-owned authority and generalized-delivery architecture are preserved. Wave 6 durable architecture changes will be recorded only when accepted.
- `DESIGN-SYSTEM.md` v3.0 — unchanged; its existing conversation-first, mobile-not-desktop-shrink, touch-safe composer, narrow-layout, accessibility and protected-state rules remain compatible with the deployed guided mobile composition.
- `CURRENT-STATE.md` — updated by this reconciliation because integration, production deployment, production verification, and Wave 6 entry-gate evidence materially changed.

This record-only reconciliation does not redefine the client/API application deployment identities above. Its resulting merge SHA is the repository baseline that Wave 6 Control Tower #263 must record before implementation starts.