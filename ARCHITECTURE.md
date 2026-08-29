# Parallax 2.0 Architecture

Version: 3.16
Status: Authoritative

## Version relationship

Architecture v3.16 is a bounded authority-model update to v3.15, not a platform rewrite. The complete v3.15 architecture at repository commit `0cfe499ac787a23142067e95e80af80dedab36c5` is incorporated by reference. Every v3.15 durable contract not explicitly changed below remains authoritative, including canonical Project / Work Specification / Engineering Run authority, immutable accepted source lineage, single-writer canonical mutation, durable worker recovery, deny-all Sandbox validation, Project-scoped tool/provider authority, protected evaluation, logical workspace deletion/retention, Preview/REVIEW ceilings, governed release evidence, accepted Wave 7 productization, W8-S2 deferred Vercel Project readiness, W9-S1 benchmark admission, and W9-S2 governed skill intake.

This revision records the deployment-verified `P2-V0.23.3` greenfield GitHub repository-authority boundary introduced by PR #412 and production API deployment `dpl_4LAkdawZteqrAX34pmGAtLMvVq9V`.

## Greenfield GitHub repository authority

Parallax now treats **provider installation coverage** and **runtime repository-token scope** as separate authority layers.

A canonical Project may bind a GitHub repository that is not yet covered by the approved `github/parallax-runtime` Vercel Connect / GitHub App installation. Repository identity by itself is not authorization. Before source bootstrap may read or mutate that repository, the provider installation must have explicit coverage for the exact canonical repository.

Installation coverage may be narrow to one repository or may cover multiple repositories when the GitHub account or organization owner explicitly chooses that broader installation scope. Parallax must never silently broaden provider installation coverage.

### Exact runtime token scope remains mandatory

Broader installation coverage does not create broader runtime authority. Every Engineering Runtime credential exchange remains short-lived and requests exact repository authorization through Vercel Connect `authorizationDetails` for the canonical Project repository.

A derived GitHub credential is accepted only after provider read-back proves it can see **exactly one repository** and that repository matches the canonical Project binding. A token that can see multiple repositories, the wrong repository, or an ambiguous scope fails closed with the existing scope-mismatch semantics.

This preserves least privilege even when a user intentionally authorizes the GitHub App installation for several or all repositories needed for future greenfield Projects.

### Repository authorization readiness

When Vercel Connect returns HTTP 422 for an otherwise valid exact-repository `github_app_installation` authorization request, Parallax classifies the condition as `REPOSITORY_AUTHORIZATION_REQUIRED` rather than collapsing it into a generic credential-unavailable failure.

That classification means the runtime identity and connector are present but the canonical repository is outside the currently approved installation coverage. It is an explicit provider-consent boundary, not a retryable source mutation failure.

Timeouts, network failures, provider 5xx responses, missing runtime OIDC, malformed token responses, expiry failures, and unrelated credential failures retain their existing fail-closed classifications. They must not be mislabeled as repository-consent requirements.

### Mutation and lifecycle ceiling

Repository authorization is checked before source mutation. When coverage is absent:

- no repository source is accepted or rewritten;
- no Git commit, branch, pull request or merge is created;
- no Vercel Project readiness action is used as a substitute for GitHub authorization;
- the canonical Project, approved Work Specification and Engineering Run remain durable and retryable;
- no lifecycle state is fabricated to make the run appear to have progressed.

Provider consent grants only the repository coverage the owner approves. It grants no source-acceptance bypass, production promotion, domain or environment-variable administration, deployment authority, Engineering Run transition authority, or REVIEW completion authority.

### Relationship to W8-S2

W8-S2's accepted deferred Vercel Project-readiness architecture remains unchanged. The original defect was that PLAN incorrectly depended on static Vercel Preview-target registration. `P2-V0.23.3` addresses a different prerequisite exposed by authenticated replay: the GitHub App installation must cover the Project repository before repository bootstrap can obtain its exact runtime token.

The W8-S2 canonical acceptance remains open until the QA-owned run `a3a32343-507a-4384-a9bd-2fddaa0ce7fc` receives explicit repository coverage for `Ryan9876/sickbeard` and durably advances beyond PLAN revision 1 without a `source_bootstrap_failed` caused by static Vercel-target registration or missing GitHub repository authority.

## Production verification

Production API source `0cfe499ac787a23142067e95e80af80dedab36c5` reached READY as deployment `dpl_4LAkdawZteqrAX34pmGAtLMvVq9V`. Provider, exact delivery-permission, projected-source, lineage-composition, agentic-runtime, projected-bootstrap, execution-snapshot and run-event-schema preflights passed.

Authenticated QA workflow run `33232396195` then re-exercised the canonical run through the ordinary QA session boundary. The run was read at `PLAN`, revision `1`, with no prior failure. The protected autonomous continuation reached the exact Vercel Connect repository exchange and returned HTTP 422. Production runtime evidence recorded:

`source_bootstrap_failed stage=provider-repository error_class=ProviderActionFailed result_code=REPOSITORY_AUTHORIZATION_REQUIRED`

This verifies the new fail-closed classification and confirms no completion claim is permitted until provider consent is granted and the same canonical replay advances durably.