# Parallax 2.0 Engineering Rules

1. Read `PROJECT-CONSTITUTION.md`, `ARCHITECTURE.md`, `DESIGN-SYSTEM.md`, and `CURRENT-STATE.md` before material changes.
2. Every material change must reference an approved spec under `specs/`.
3. Never change implementation first and backfill the spec later.
4. Run `python scripts/validate_spec.py <spec>` before substantive implementation.
5. DSPy optimizers may improve AI programs but never edit protected evaluation functions or release gates.
6. Preserve normal accessible text; Skia is visual augmentation.
7. Keep conversation primary; do not drift into dashboard/IDE UI without an approved spec change.
8. Distinguish generated, validated, deployed, and deployment-verified states.
9. Update authoritative records only when their durable subject changes; always update `CURRENT-STATE.md` after a meaningful validated release/deployment/material decision.
