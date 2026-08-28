# Parallax 2.0 Project Constitution

Version: 1.5
Status: Authoritative

## Product purpose

Parallax 2.0 is an outcome-focused AI reasoning and software-engineering environment. It should turn ambiguous objectives into durable specifications, evidence-backed decisions, verified implementations, and measurable improvement over time.

## Governing principles

1. **Specification precedes substantive implementation.** Every material build or behavior change starts from an explicit objective, constraints, acceptance criteria, risks, and non-goals.
2. **Evaluation is structurally above optimization.** DSPy and other optimizers may improve prompts, examples, routing, planning, repair strategies, and AI programs, but they may not silently redefine the protected success criteria used to judge those improvements.
3. **Parallax 2.0 must be built with the same methodology it provides.** Its own development uses spec-first artifacts, DSPy-compatible program boundaries, explicit metrics, held-out evaluation, and traceable implementation evidence.
4. **Conversation is the primary product surface.** Engineering machinery and evidence remain inspectable without turning the interface into a dense IDE or dashboard.
5. **Persistent context is mandatory.** Conversations, specifications, decisions, execution state, and recoverable work survive refreshes and resumptions.
6. **Human control is explicit.** Consequential, destructive, security-sensitive, expensive, or hard-to-reverse decisions require human approval. Low-risk reversible work may proceed autonomously. A bounded standing authorization recorded in this Constitution may satisfy the approval requirement for the exact class of actions it covers until that authorization expires or is revoked.
7. **Release status is evidence-based.** Generated, validated, deployed, and deployment-verified are distinct states. A package is never recorded as deployed without deployment evidence.
8. **Accessibility and reduced-motion behavior are first-class.** Visual effects must degrade gracefully without hiding content or blocking work.
9. **Security boundaries are product requirements, not later hardening.** Secrets, authorization, tool trust, and data isolation are designed deliberately.
10. **Simplicity wins when outcomes are equivalent.** Complexity must justify itself through measurable quality, reliability, maintainability, capability, or user-experience improvement.
11. **Parallel development is isolated; integration is serialized.** Concurrent ChatGPT workers use GitHub-authoritative workstream reservations, isolated branches, explicit dependency/path ownership, and validated PRs. Individual chat history does not establish current code ownership or release state. Final integration occurs one candidate at a time against the latest relevant `main`, with applicable gates rerun before merge and production promotion.
12. **The Parallax development-policy baseline is inherited by every Parallax-developed project.** Project-specific policy may add stricter requirements or capability-specific validation, but it may not silently weaken the platform baseline for specification binding, canonical identity, source lineage, tool authority, durable checkpoints, bounded autonomy, stall/recovery controls, protected evaluation, evidence integrity, rollback, or human-control boundaries.
13. **Development efficiency is optimized for validated outcome time, not raw worker activity.** Parallax's own development and every Project it develops must prefer critical-path reduction, impact-aware validation, safe reuse, early conflict detection, right-sized workstreams and measured bottleneck reduction. Efficiency mechanisms may reduce redundant work but may never weaken exact-head evidence, source lineage, privacy, authorization, protected promotion, rollback or human-control requirements.
14. **Single-user Parallax production promotion is standing pre-authorized while the owner remains the only real production user.** Once a Parallax release or hotfix has passed the applicable exact-head release gates and has a viable rollback path, the development operator may merge and promote that validated candidate to Parallax production without requesting a separate per-release approval. This standing authority expires automatically when additional real users begin relying on Parallax production, or immediately if the owner revokes it. It does not waive validation, evidence, rollback, least-privilege, or security boundaries and does not authorize unrelated destructive database operations, data loss, broader credential/provider scope, materially new external commitments, or weakening protected acceptance or evaluation controls.
15. **Plain language is the default product language.** Primary user-facing copy must use natural, outcome-oriented wording that a capable non-software-engineer can understand wherever technical precision is not required. Internal stage names, object names, IDs, status codes, provider details, logs, and engineering evidence remain available through clearly secondary technical-detail surfaces when useful. Plain language may simplify presentation but may not conceal consequences, uncertainty, required human approval, security boundaries, failures, or authoritative system state.

## Inherited development policy

Every Project developed through Parallax is governed by three policy layers:

1. **Platform baseline** — non-weakenable Parallax development guarantees and safety/reliability controls.
2. **Project profile** — durable project-specific architecture, design-system, security, deployment, compatibility, performance, accessibility, testing and operational requirements. A project profile may only preserve or strengthen the platform baseline.
3. **Work Specification** — the objective-specific constraints and acceptance criteria for one bounded change. A Work Specification may narrow scope or add stricter requirements but cannot grant authority forbidden by the platform baseline or Project profile.

The effective policy is the strictest applicable requirement across those layers. Missing project-specific configuration falls back to the platform baseline rather than disabling a control.

The inherited platform baseline is intended to include, once its corresponding Wave 3 runtime capability is implemented and accepted: bounded autonomous correction, same-lineage BUILD/TEST/VERIFY, deterministic and capability-aware validation, last-known-good preservation, continuous bounded worker utilization, fast-versus-promotion validation lanes, machine-checkable interfaces, safe caching, automated Integration / Control Tower composition, durable resumable checkpoints, stall detection/classification, bounded recovery/reassignment, no-progress/oscillation protection, single-writer lease semantics, protected promotion evidence, and explicit human-control boundaries.

Wave 3 must also apply the same development-efficiency baseline to Parallax self-development and all Parallax-developed Projects:

- critical-path scheduling and bounded work stealing from the dependency graph;
- change-impact-driven fast validation while retaining complete protected promotion gates;
- immutable, secret-free warm execution environments with digest-bound invalidation;
- validated reusable project patterns/components/configuration rather than unnecessary regeneration;
- privacy-safe failure fingerprinting and repair memory whose suggestions must be revalidated in the current Project;
- adaptive model routing that minimizes latency/cost without lowering protected evaluation or authority standards;
- specification preflight for contradictions, missing dependencies, impossible acceptance criteria, authority conflicts and unsupported validation before implementation starts;
- speculative integration on disposable candidates to expose interface/conflict failures before workers finish, without advancing accepted lineage or merge state;
- automatic workstream sizing/rebalancing so work is neither too large to recover nor fragmented into unnecessary integration overhead;
- development-performance telemetry that measures planning, generation, environment setup, build, validation, provider waits, retries, integration and human waits using bounded non-secret evidence.

Reusable patterns, failure memory, telemetry, caches and warm environments must not become cross-Project data-exfiltration paths. Project-private source, secrets and sensitive evidence are not reusable global memory unless an explicit protected policy permits that exact artifact class.

These Wave 3 controls are constitutional requirements for the future development runtime; recording them here does not assert that the current production runtime already implements them.

## Standing single-user release authority

The project owner has granted standing authorization for Parallax's own validated releases and hotfixes to be promoted to production without a separate approval request while Parallax has no additional real production users. This is a release-promotion authorization, not a blanket authorization for every consequential mutation.

A candidate may use this standing authority only when:

- the candidate is the exact head that passed all applicable required release gates;
- production promotion does not weaken protected evaluation, canonical identity, source-lineage, tool/provider authority, security, or evidence boundaries;
- rollback or forward-recovery evidence is available for the affected deployable surface;
- any required migration is additive/forward-compatible or separately authorized if destructive or difficult to reverse;
- deployment evidence is collected before the release is recorded as deployed or deployment-verified.

The operator must stop relying on this standing authority when a second real user or any broader user population begins relying on Parallax production. At that point per-release production authority must be re-established explicitly before further production promotion.

## Required authoritative records

The repository maintains these files as the durable project record:

- `PROJECT-CONSTITUTION.md`
- `ARCHITECTURE.md`
- `DESIGN-SYSTEM.md`
- `CURRENT-STATE.md`

`CURRENT-STATE.md` is updated after every meaningful validated release, confirmed deployment, data refresh, or material decision. The other records change only when their durable subject matter changes.

## Concurrent development authority

`PARALLEL-DEVELOPMENT.md` defines the operating protocol for concurrent ChatGPT workstreams. Open GitHub `[WS]` issues, branches, PRs, validation evidence, and deployment evidence are the live coordination record. When chat recollection conflicts with those records, GitHub and the authoritative project files control.
