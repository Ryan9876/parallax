# Decision Ledger v1 — W9-S1 controlled real-world benchmark runbook

Status: governed benchmark protocol
Spec: `P2-V0.23.0`
Template: `decision-ledger@1.0.0`
Fixture: `decision-ledger-v1.json`
Fixture digest: `15b098df3956ffe71833778e18a301a8e77fae9f37705223256703619f684900`
Expected autonomous publication ceiling: `REVIEW`

## Purpose

This runbook defines the first controlled real-world Parallax app-builder observation. It evaluates the ordinary product path; it does not create a benchmark-only runtime, provider, source, authentication, lifecycle, deployment, or expected-answer path.

The benchmark target is an independent greenfield repository containing no reference implementation. The frozen fixture is evaluation evidence only. Parallax receives the ordinary product objective and requirement tokens; runtime code must not inspect the fixture identity or digest.

## Frozen objective payload

Use the `objective` plus every ordered `requirements[].requirement_id`, `title`, and `outcome` from `decision-ledger-v1.json` without semantic rewriting. The canonical Work Specification must preserve `DL-01` through `DL-12` exactly once across its approved acceptance text before the run can be admitted to ParallaxBench.

Do not provide Parallax with a hidden source tree, implementation answer, framework mandate, provider credential, production secret, or manually prepared application source. Implementation technology remains Parallax's choice.

## Controlled run protocol

1. Use an independent target GitHub repository with no application implementation or reference solution.
2. Create or select a normal authenticated Parallax Project bound to that repository.
3. Submit the frozen objective and all `DL-01` through `DL-12` requirement tokens/outcomes through the normal product conversation.
4. Record necessary pre-approval clarification separately. Clarification is observable evidence, not automatically a failure.
5. Review the generated Build plan. Do not manually rewrite target repository source.
6. Approve only through the ordinary Parallax approval boundary when the plan is suitable for the benchmark.
7. Allow the ordinary Engineering Run to progress through PLAN, IMPLEMENT, BUILD, TEST, VERIFY, Preview, and REVIEW behavior.
8. If correction is required, request it through ordinary Parallax interaction and record it as post-approval corrective intervention. Do not edit target source out of band.
9. At REVIEW or an earlier terminal/HUMAN_REQUIRED boundary, capture only trustworthy exact identity/evidence described below.
10. Record product defects before any corrective Parallax implementation. A semantic product fix requires a separate approved spec/workstream.

The protocol never authorizes production promotion. Preview is the autonomous publication ceiling and REVIEW remains human-required.

## Human-intervention evidence policy

Classify observable human actions as follows:

- `REQUIRED_APPROVAL`: normal Build-plan approval; expected boundary, not undesirable intervention.
- `REQUIRED_REVIEW`: normal final REVIEW decision; expected boundary, not undesirable intervention.
- `PRE_APPROVAL_CLARIFICATION`: user clarification before plan approval; record count and evidence reference separately.
- `POST_APPROVAL_CORRECTION`: user-requested corrective change after approval; count as human-intervention evidence when mechanically attributable.
- `EXPLICIT_RETRY_RECOVERY`: user-initiated retry or recovery action; record as retry/recovery evidence when observable.
- `OUT_OF_BAND_SOURCE_EDIT`: protocol violation. It invalidates a claim of a clean low-intervention trial and is never relabeled as success.

Do not infer hidden operator actions. If evidence is unavailable, record `UNKNOWN` or `UNAVAILABLE` under the existing ParallaxBench evidence semantics.

## Reference-observation evidence record

Capture the following bounded values when trustworthy:

- template ID, version, and fixture digest;
- canonical Project ID;
- canonical approved Work Specification ID, revision, digest, and complete acceptance-ID set;
- bound `BenchmarkCase.digest`;
- Engineering Run ID and final observed run state;
- accepted source lineage/reference digest and exact commit identity when exposed by ordinary evidence;
- Preview deployment identity and observed readiness state, without embedding credentials;
- protected validation/evidence digest and protected-floor result;
- objective-completion evidence tied to the exact accepted candidate;
- observable pre-approval clarification count;
- observable post-approval corrective-intervention count;
- observable retry/recovery count;
- elapsed time only from trustworthy timestamps tied to the exact run boundary;
- cost/usage only from existing provider/economic provenance, otherwise `UNKNOWN`/`UNAVAILABLE`;
- visual/UX evidence only after deterministic validation passes;
- final benchmark disposition or diagnostic boundary.

The record must not contain source bytes, patches, prompts, hidden reasoning, raw provider payloads, credentials, secrets, unrestricted logs, arbitrary command authority, or arbitrary URL authority.

## Admission check

Before interpreting the trial as the Decision Ledger benchmark, construct `CanonicalWorkSpecificationEvidence` from ordinary canonical Project/spec evidence and call `bind_real_world_template(...)` with the loaded fixture.

Admission fails closed when:

- Project/spec identity is malformed;
- the Work Specification is not approved;
- revision is not positive or digest is malformed;
- canonical acceptance IDs are missing or duplicated;
- repository shape differs from the frozen template;
- any `DL-01` through `DL-12` token is missing; or
- any frozen requirement token appears more than once across canonical acceptance text.

No model or evaluator may substitute semantic similarity for failed token coverage.

## Failure remains evidence

A first trial that fails, stops at HUMAN_REQUIRED, or exposes incomplete evidence is still useful when its exact observable boundary is recorded honestly. Do not weaken authentication, protected checks, source lineage, Project/spec identity, Preview/REVIEW ceilings, or provider authority to manufacture a passing application.

A trial that cannot be admitted because the generated Work Specification loses or duplicates frozen requirement tokens is specifically specification-fidelity evidence, not an invitation for the binder to repair the spec.
