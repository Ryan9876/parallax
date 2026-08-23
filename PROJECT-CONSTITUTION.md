# Parallax 2.0 Project Constitution

Version: 1.2
Status: Authoritative

## Product purpose

Parallax 2.0 is an outcome-focused AI reasoning and software-engineering environment. It should turn ambiguous objectives into durable specifications, evidence-backed decisions, verified implementations, and measurable improvement over time.

## Governing principles

1. **Specification precedes substantive implementation.** Every material build or behavior change starts from an explicit objective, constraints, acceptance criteria, risks, and non-goals.
2. **Evaluation is structurally above optimization.** DSPy and other optimizers may improve prompts, examples, routing, planning, repair strategies, and AI programs, but they may not silently redefine the protected success criteria used to judge those improvements.
3. **Parallax 2.0 must be built with the same methodology it provides.** Its own development uses spec-first artifacts, DSPy-compatible program boundaries, explicit metrics, held-out evaluation, and traceable implementation evidence.
4. **Conversation is the primary product surface.** Engineering machinery and evidence remain inspectable without turning the interface into a dense IDE or dashboard.
5. **Persistent context is mandatory.** Conversations, specifications, decisions, execution state, and recoverable work survive refreshes and resumptions.
6. **Human control is explicit.** Consequential, destructive, security-sensitive, expensive, or hard-to-reverse decisions require human approval. Low-risk reversible work may proceed autonomously.
7. **Release status is evidence-based.** Generated, validated, deployed, and deployment-verified are distinct states. A package is never recorded as deployed without deployment evidence.
8. **Accessibility and reduced-motion behavior are first-class.** Visual effects must degrade gracefully without hiding content or blocking work.
9. **Security boundaries are product requirements, not later hardening.** Secrets, authorization, tool trust, and data isolation are designed deliberately.
10. **Simplicity wins when outcomes are equivalent.** Complexity must justify itself through measurable quality, reliability, maintainability, capability, or user-experience improvement.
11. **Parallel development is isolated; integration is serialized.** Concurrent ChatGPT workers use GitHub-authoritative workstream reservations, isolated branches, explicit dependency/path ownership, and validated PRs. Individual chat history does not establish current code ownership or release state. Final integration occurs one candidate at a time against the latest relevant `main`, with applicable gates rerun before merge and production promotion.
12. **The Parallax development-policy baseline is inherited by every Parallax-developed project.** Project-specific policy may add stricter requirements or capability-specific validation, but it may not silently weaken the platform baseline for specification binding, canonical identity, source lineage, tool authority, durable checkpoints, bounded autonomy, stall/recovery controls, protected evaluation, evidence integrity, rollback, or human-control boundaries.

## Inherited development policy

Every Project developed through Parallax is governed by three policy layers:

1. **Platform baseline** — non-weakenable Parallax development guarantees and safety/reliability controls.
2. **Project profile** — durable project-specific architecture, design-system, security, deployment, compatibility, performance, accessibility, testing and operational requirements. A project profile may only preserve or strengthen the platform baseline.
3. **Work Specification** — the objective-specific constraints and acceptance criteria for one bounded change. A Work Specification may narrow scope or add stricter requirements but cannot grant authority forbidden by the platform baseline or Project profile.

The effective policy is the strictest applicable requirement across those layers. Missing project-specific configuration falls back to the platform baseline rather than disabling a control.

The inherited platform baseline is intended to include, once its corresponding Wave 3 runtime capability is implemented and accepted: bounded autonomous correction, same-lineage BUILD/TEST/VERIFY, deterministic and capability-aware validation, last-known-good preservation, continuous bounded worker utilization, fast-versus-promotion validation lanes, machine-checkable interfaces, safe caching, automated Integration / Control Tower composition, durable resumable checkpoints, stall detection/classification, bounded recovery/reassignment, no-progress/oscillation protection, single-writer lease semantics, protected promotion evidence, and explicit human-control boundaries.

These Wave 3 controls are constitutional requirements for the future development runtime; recording them here does not assert that the current production runtime already implements them.

## Required authoritative records

The repository maintains these files as the durable project record:

- `PROJECT-CONSTITUTION.md`
- `ARCHITECTURE.md`
- `DESIGN-SYSTEM.md`
- `CURRENT-STATE.md`

`CURRENT-STATE.md` is updated after every meaningful validated release, confirmed deployment, data refresh, or material decision. The other records change only when their durable subject matter changes.

## Concurrent development authority

`PARALLEL-DEVELOPMENT.md` defines the operating protocol for concurrent ChatGPT workstreams. Open GitHub `[WS]` issues, branches, PRs, validation evidence, and deployment evidence are the live coordination record. When chat recollection conflicts with those records, GitHub and the authoritative project files control.
