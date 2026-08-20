# Parallax Engineering Benchmark

Repository-safe synthetic cases for P2 evaluation development.

- `development-v0.1.json` may be exposed to DSPy development/optimization.
- `promotion-v0.1.json` is protected promotion evidence and must not be supplied to optimizer-controlled code.
- `fixtures/` contains recorded offline outputs used to prove deterministic scoring and regression rejection in CI.

The initial benchmark is deliberately small. Passing it does not establish general engineering quality and does not authorize deployment.
