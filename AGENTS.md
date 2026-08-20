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
