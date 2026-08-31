# Parallax CI/CD Validation Policy

Status: Engineering policy

## Objective

Keep development feedback fast without weakening protected promotion or production evidence.

## Validation tiers

### Development / pull request

Every pull request keeps fast deterministic feedback:

- API compilation and full API regression suite;
- baseline specification contract checks;
- client typecheck, state tests, and export;
- protected recorded promotion evaluation for non-draft pull requests;
- deterministic validation of the latest committed DSPy plan for non-draft pull requests;
- focused bounded-autonomy execution tests.

Independent jobs run in parallel. A failure in the API suite must not suppress protected evaluation or DSPy plan validation, so one run reports independent problems together.

### Client-change acceptance

Browser/Skia acceptance and the production dependency audit run only when client source or the client visual workflow changes. They also remain manually dispatchable and run for matching pushes to `main`.

This prevents unrelated API, specification, documentation, and governance changes from paying the browser-runtime installation and visual-suite cost.

### Promotion boundary

Pushes to `main` and explicit workflow dispatch retain fresh DSPy SpecCritic/SpecCompiler execution and protected plan validation. The pipeline selects the latest governed `P2-V*.md` specification instead of compiling a historical fixed release.

Production QA/replay workflows remain separate and unchanged.

## Non-goals

This policy does not relax:

- specification validity;
- full API regression coverage;
- protected benchmark regression rejection;
- bounded-autonomy protected tests;
- committed DSPy plan requirements;
- production QA/replay requirements;
- deployment or REVIEW authority.

The optimization changes when expensive evidence is generated and removes duplicate execution; it does not broaden runtime or deployment authority.
