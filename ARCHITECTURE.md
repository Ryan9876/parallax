# Parallax 2.0 Architecture

Version: 1.0
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo client plus a Python intelligence service.

```text
Expo / React Native client
  ├─ normal accessible conversation text
  ├─ response state machine
  ├─ React Native Skia material + beam effects
  └─ API client
          │
          ▼
FastAPI intelligence service
  ├─ conversation service
  ├─ persistence repositories
  ├─ DSPy reasoning program
  ├─ Luna → Terra → Sol router
  ├─ protected evaluators
  └─ observable execution traces
          │
          ▼
SQLite (development) / PostgreSQL (target)
```

## Core boundaries

### Client

The client owns interaction state and visual presentation. It does not own provider credentials or durable conversation truth.

Assistant content is rendered as standard React Native `Text`. Skia is used for living material, optical beam, glint, and decorative motion. This preserves accessibility and allows a no-Skia degradation path.

The response reducer is the single source of truth for `IDLE`, `THINKING`, `RESPONDING`, `VERIFYING`, `COMPLETE`, and `ERROR`. Motion energy and laser activity are derived from that reducer, not from independent animation flags.

### API

Routes call services. Services call repositories and intelligence adapters. Provider SDK details do not leak into route contracts.

`ReasoningProgram` is an interface boundary. The initial implementation is DSPy-backed, but the API is insulated from compiled-program version changes.

### Persistence

SQLAlchemy 2 models provide a development SQLite path and a PostgreSQL-compatible target path through `DATABASE_URL`.

Conversation identity is an opaque UUID. Messages are durable and ordered by creation time.

### Model routing

Runtime routing order is fixed for the foundation release:

1. `openai/gpt-5.6-luna`
2. `openai/gpt-5.6-terra`
3. `openai/gpt-5.6-sol`

Escalation happens on provider failure or validation failure. Attempt metadata is retained in the response trace.

### DSPy optimization

DSPy is used in two distinct planes:

1. **Product runtime** — structured reasoning modules can be compiled/optimized without changing API contracts.
2. **Parallax development** — specification compilation and critique are DSPy programs with explicit protected metrics.

Optimizer-controlled code cannot alter the protected acceptance/evaluation functions used to promote an optimized program.

## Web Skia

React Native Skia uses CanvasKit/WASM on web. `apps/client/scripts/setup-skia-web.mjs` copies the matching `canvaskit.wasm` into the client public directory. Skia initialization is deferred on web before the application root is registered.

## Failure degradation

- Skia unavailable: show a static material fallback; chat remains functional.
- Provider unavailable: router escalates through Luna, Terra, then Sol.
- All providers fail: preserve user message and return a recoverable error state.
- Database failure: return sanitized service error; never pretend a conversation was persisted.

## Security

No model/provider secret is shipped to the client. Provider configuration is server-side environment only. CORS origins are configured explicitly. ORM-backed SQL is parameterized. Execution traces exclude hidden chain-of-thought.
