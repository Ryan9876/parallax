# Parallax 2.0 Engineering Rules

1. Read `PROJECT-CONSTITUTION.md`, `ARCHITECTURE.md`, `DESIGN-SYSTEM.md`, and `CURRENT-STATE.md` before material changes.
2. Every material change must reference an approved spec under `specs/`.
3. Never change implementation first and backfill the spec later.
4. Run `python scripts/validate_spec.py <spec>` before substantive implementation.
5. For AI-program changes, run the mandatory DSPy SpecCritic + SpecCompiler development gate before treating implementation as authorized.
6. DSPy optimizers may consume development-suite examples/metrics but never promotion-suite expected contracts, protected thresholds, protected evaluator implementations, or promotion rules.
7. A benchmark improvement does not authorize promotion by itself; protected case/category floors and baseline/challenger regression gates remain authoritative.
8. Never store, score, or expose hidden chain-of-thought or scratchpad content in traces, benchmarks, or evaluation evidence.
9. Preserve normal accessible text; Skia is visual augmentation.
10. Keep conversation primary; do not drift into dashboard/IDE UI without an approved spec change.
11. Distinguish generated, validated, deployed, and deployment-verified states.
12. Update authoritative records only when their durable subject changes; always update `CURRENT-STATE.md` after a meaningful validated release/deployment/material decision.
13. For concurrent ChatGPT development, read `PARALLEL-DEVELOPMENT.md` and inspect open GitHub `[WS]` issues plus relevant open PRs before substantive work. GitHub coordination state outranks individual chat history.
14. A parallel worker chat owns exactly one bounded ACTIVE workstream at a time. Register its objective, branch/base, owned paths, shared paths, dependencies, acceptance gate, collision policy, and completion condition before implementation.
15. New parallel work uses an isolated `ws/<workstream>-<slug>` branch from current `main` unless an explicit dependency requires another base. Never treat another chat's unmerged branch as shared state without declaring that dependency.
16. Stay within declared ownership. If implementation materially expands into another ACTIVE workstream's paths or contract, stop and coordinate through the workstream issues before changing those files.
17. Worker chats prepare validated PRs but do not merge or deploy by default. The Integration / Control Tower chat serializes final integration and production promotion.
18. A PR that passed against an older base is not automatically merge-ready. After a relevant dependency or conflicting PR lands, incorporate latest `main` and rerun the applicable gates before merge.
19. Production promotion remains serialized. A successful build or READY deployment is not equivalent to deployment verification.
20. When a workstream finishes, record its PR, final changed paths, validation evidence, risks, integration notes, and authoritative-record implications on its `[WS]` issue; the Integration chat closes the issue after merge/abandonment and required deployment verification.
