# Parallax 2.0

Parallax 2.0 is a new product track for a persistent, spec-first AI reasoning and software-engineering environment.

This repository intentionally starts with the approved specification in `specs/P2-V0.1.0.md`. The implementation is organized so the same spec-first and DSPy methodology used by Parallax is also used to build Parallax itself.

## Stack

- Client: Expo SDK 57, React Native 0.86, React 19.2, React Native Skia 2.11, Reanimated 4.5.
- Intelligence service: Python 3.11+, FastAPI, SQLAlchemy 2, DSPy 3.3.
- Development persistence: SQLite. Production-compatible database URL: PostgreSQL.

## Visual identity

The v0.1 foundation keeps the calm conversation-first character of P1 while introducing:

- a living Skia response surface;
- an optical laser-typesetter response effect;
- a calmly animated Parallax lens mark;
- explicit visual linkage to the response state machine.

## Development flow

1. Write or amend an approved spec under `specs/`.
2. Run `python scripts/validate_spec.py <spec>`.
3. In a provider-enabled environment, run `python scripts/compile_spec.py <spec>` to produce a DSPy-authored implementation plan.
4. Implement only against the approved spec and compiled plan.
5. Run backend and frontend checks.
6. Update `CURRENT-STATE.md` with evidence and exact release state.

The bootstrap plan in `specs/compiled/P2-V0.1.0.plan.json` is explicitly marked as human-reviewed because this build environment cannot reach Python/npm registries or model-provider APIs. It is not represented as a completed DSPy optimizer run.

## Local client

```bash
cd apps/client
npm install
npm run postinstall
npm run web
```

React Native Skia web support uses CanvasKit WASM. The setup script copies `canvaskit.wasm` to `public/`, matching the Skia web deployment requirement.

## Local API

```bash
cd services/api
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn parallax_api.main:app --reload --port 8010
```

## DSPy optimization

Set provider credentials in the environment and run:

```bash
python scripts/compile_spec.py specs/P2-V0.1.0.md
python scripts/optimize_spec.py specs/P2-V0.1.0.md
```

Protected metrics in `services/api/parallax_api/intelligence/protected_metrics.py` are deliberately outside optimizer-controlled modules.

## Release status

See `CURRENT-STATE.md`.
