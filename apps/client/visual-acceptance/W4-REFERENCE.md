# Wave 4 visual acceptance reference

Status: release-gate reference evidence for workstream #174
Authority: `DESIGN-SYSTEM.md` v3.0 + approved `specs/P2-V0.17.4.md` + approved `specs/P2-V0.17.5.md`

## Acceptance target

The approved Warm Editorial Observatory direction is the visual target. This file does not create a second design authority or freeze individual pixels. The deterministic browser gate checks material composition and interaction invariants that express the approved reference:

- forest/ivory/rust/teal/olive/charcoal Warm Editorial shell;
- desktop navigation rail plus primary Live Build workplane and contextual health rail when width permits;
- intentional tablet composition without the desktop contextual rail compressing the workplane;
- intentional phone composition with mobile Live Build entry/return and horizontally usable tabs;
- serif display hierarchy for `Run observability` over compact evidence labels and body facts;
- bounded card density with no clipped primary controls, no document-level horizontal overflow, and practical 44 CSS px tab/control targets;
- persisted evidence remains visually distinguishable for active, success, unavailable telemetry, provider failure, reconnect/retry and `HUMAN_REQUIRED` states;
- reduced-motion and reduced-graphics operation preserves information, focus order and controls.

## Viewports

The gate records deterministic screenshots at these reference viewports:

| Reference | CSS viewport | Intent |
| --- | --- | --- |
| Desktop reference | 1440 × 900 | Full Warm Editorial shell + Live Build contextual rail |
| Desktop compact | 1280 × 800 | Desktop shell under tighter vertical density |
| Tablet portrait | 834 × 1112 | Primary workspace without desktop contextual compression |
| Phone | 390 × 844 | Mobile Live Build composition and return path |

Screenshots are evidence, not the sole oracle. Release failure is driven by semantic/layout assertions (rail proportions, overflow/clipping, hierarchy, target size, navigation state, focus and responsive transitions) so harmless raster differences do not create brittle failures.

## Test-only fixture policy

`apps/client/test-fixtures/w4-release-states.json` contains deterministic test-only persisted-run facts. The production client remains wired to authenticated protected APIs. Fixture values must never be copied into production code or used to infer success in the absence of persisted facts.

## Protected functional proof

Visual fixture acceptance is not production-readiness evidence by itself. `scripts/w4_release_proof.py` must be run against an authorized production-like target and a Project-bound run. It invokes the real `/v1/engineering-runs/{run_id}/autonomous` path, requires advancement beyond PLAN, then reads persisted run events through the protected observability route. HTTP 503, `CREDENTIAL_UNAVAILABLE`, missing persisted events, non-monotonic sequence, or absence of observable post-PLAN facts fails the proof.

The protected proof intentionally does not provide a PAT/static-token fallback and does not widen provider, merge, deployment or production-promotion authority. Workstream #170 owns credential recovery; #174 owns the release gate that must detect failure of that path.