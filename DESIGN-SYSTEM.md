# Parallax 2.0 Design System

Version: 3.0
Status: Authoritative

## Design direction

Parallax is a premium reasoning and engineering workspace that should feel calm, capable, legible and authored. Conversation remains the primary creation surface. Governed engineering state becomes visibly inspectable when it matters, but the product must not feel like a generic IDE, log console or dense operations dashboard.

Wave 4 replaces the prior Deep Violet Optical identity with **Warm Editorial Observatory**, based on the approved Parallax home and Observability mockups. The visual language is dark forest/olive navigation, warm ivory/cream workplanes, burnt rust primary action, flat deep teal live interaction, restrained olive verified/support treatment, near-charcoal text, warm low-contrast material and editorial display hierarchy. Content and authoritative state win every visual competition.

## Brand and palette

The primary mark is the rust central body with intersecting teal/olive orbital rings. The prior violet knot is retired from primary product chrome. The mark is identity, not a loading spinner.

Core semantic tokens:

- forest: `#1C2A18`, `#24341F`, `#31442A`, `#405536`;
- olive: `#66753A`, `#768443`, `#87954D`, `#D8DCC0`;
- warm workplane: `#FBF7EE`, `#F5EEDF`, `#F0E7D7`, `#E9DFCC`, `#D8CEBC`;
- rust: `#A83B17`, `#C44A1B`, `#D75B24`, `#F4D7C8`;
- teal: `#006E70`, `#008487`, `#15999A`, `#D4EBE7`;
- charcoal text: `#172024`, `#30383A`, `#626664`, `#7C7E79`.

State meaning never relies on color alone. Success/verified uses olive plus text, active execution uses teal plus text, warnings/danger use distinct warm state semantics, and pending uses warm stone/charcoal.

## Typography and material

Major headings use reliable system serif stacks; application text uses system sans-serif; code/diffs/command evidence/lineage IDs use selectable platform monospace. Primary cards use ivory/cream material, approximately 14–20 px desktop radii, low-contrast warm borders, short warm shadows and restrained separators. Avoid glassmorphism and unnecessary card nesting.

## Application shell and conversation

Desktop uses a dark-forest navigation rail, dominant warm workplane and narrower warm utility rail. Active navigation is a filled rust rounded rectangle. Observability is a first-class destination when available. Mobile collapses/reflows rather than shrinking the desktop shell.

Conversation stays primary. User messages are restrained right-aligned warm/teal surfaces; assistant narrative is wider, calm, selectable and high contrast. The composer is an in-flow warm dock with practical mobile targets. Streaming text appears as server SSE delivers it; decorative motion never retypes, delays or outruns content.

## Work Specification and Engineering Run

Work Specification remains an operator-controlled implementation contract with explicit draft/approved state, revision and stable acceptance clauses. Approval remains an explicit accessible action.

Engineering execution presents durable server truth rather than simulated progress. Completed/current/pending stage state, retries, corrections, recovery and HUMAN_REQUIRED derive from persisted facts. UI controls appear only when the protected state machine permits them.

## Observability and Live Build

Observability is a governed view of actual execution, not a replacement runtime. The pipeline displays `SPEC · PLAN · IMPLEMENT · BUILD · TEST · VERIFY · REVIEW`; completed/current/pending, failure/recovery and human-required states are explicit and evidence-backed.

The Run Event Stream is the main narrative. Health, alerts, GitHub PR, Vercel Preview and audit identities appear only when supported by persisted facts; missing telemetry is shown as unavailable rather than fabricated. Secrets, auth material, raw provider payloads and hidden reasoning never appear.

Live Build is the detailed read-only run-inspection workspace. It uses the approved Warm Editorial composition with run pipeline/header and tabs for `Code`, `Diff`, `Terminal`, `Tests`, `Events`, `Evidence`.

- **Code:** exact observed accepted/candidate lineage only; selectable source; no unrestricted filesystem browser or direct editor authority.
- **Diff:** exact immutable from/to lineage identities and bounded source diff.
- **Terminal:** bounded redacted output from registered protected commands; no shell input, arbitrary execution or environment inspection.
- **Tests:** actual persisted attempts and bounded retained failure evidence; correction/retry associates with new attempts/candidates.
- **Events/Evidence:** canonical server-owned event/evidence models rather than client-only timelines.

Observation controls (`Follow Live`, `Pause View`, `Jump to Latest`, tab/file selection) never mutate execution. Protected `Pause Run`, resume/continue, cancel and operator review remain distinct.

## Mobile, accessibility and reduced graphics

Phone layouts use focused sections/tabs, practical full-width technical views and stacked context rather than a miniaturized desktop. Editable phone text remains at least 16 CSS px; zoom stays enabled; visual-viewport keyboard handling keeps the composer reachable; practical targets are approximately 44×44 pt.

Product text/source/diff/evidence stays selectable and semantically exposed. State always includes text/icon meaning beyond color. Focus is visible on forest and warm surfaces. Reduced motion removes nonessential animation; reduced graphics removes decoration while preserving capability and hierarchy.

## Protected states

`SPEC_AMENDMENT` is a deliberate handoff, not a generic error. Recoverable failure shows protected reason/next action. `HUMAN_REQUIRED / REVIEW` is distinct from failure and live execution; the client cannot convert it into autonomous completion.

## Non-negotiable design constraints

- conversation remains primary;
- Warm Editorial forest/ivory/rust/teal/olive semantics stay centralized;
- dominant legacy violet/cyan identity does not return through local styling;
- source/diff/terminal/evidence remain selectable, bounded and truthful;
- no secret material, raw provider payload or hidden reasoning is visualized;
- no progress is presented ahead of authoritative server state;
- observer controls never masquerade as execution controls;
- desktop and mobile retain equivalent product capability.
