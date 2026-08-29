# Parallax 2.0 Design System

Version: 3.3
Status: Authoritative

## Design direction

Parallax is a premium reasoning and engineering workspace that should feel calm, capable, legible and authored. Conversation remains the primary creation surface. Governed engineering state becomes visibly inspectable when it matters, but the product must not feel like a generic IDE, log console or dense operations dashboard.

Wave 4 established the **Warm Editorial Observatory** visual identity. Wave 8 adds a human-centered interaction and content standard: primary surfaces use natural, outcome-oriented language and mobile behaves as a guided control surface rather than a compressed engineering workspace.

The dominant visual language is:

- dark forest / olive navigation;
- warm ivory / cream workplane;
- burnt rust primary action and active-navigation treatment;
- flat deep teal for live focus and interaction;
- restrained olive for support, ready and verified treatment;
- near-charcoal primary text;
- warm low-contrast cards, dividers and shadows;
- editorial display hierarchy paired with highly legible application typography;
- subtle organic topographic / landscape depth that never competes with content.

Content and authoritative state win every visual competition. No visual effect or simplified wording may imply engineering progress before the server records it.

## Brand identity

The primary Wave 4 Parallax mark is the **orbital planet identity** from the approved mockup family:

- warm rust/orange central body;
- intersecting teal and olive orbital rings;
- transparent or locally integrated background rather than a decorative enclosing badge;
- recognizable at both full brand and small assistant/avatar sizes;
- paired with the `Parallax` wordmark in the editorial display voice where space permits;
- tagline treatment may use `Build with perspective.` in quiet olive/cream secondary text.

The prior violet interlocking knot is retired from primary Wave 4 product chrome. It may remain in historical screenshots/assets during transition but must not coexist as a competing primary identity in production surfaces.

The orbital mark should read as identity, not a loading spinner. Default product use is static or nearly static. If later motion is introduced, it must be subtle, non-essential, reduced-motion aware and never imply run progress.

## Semantic palette

Implementation centralizes semantic tokens. Initial production targets are:

### Forest / navigation

- `forest950`: `#1C2A18`
- `forest900`: `#24341F`
- `forest800`: `#31442A`
- `forest700`: `#405536`

### Olive / support

- `olive700`: `#66753A`
- `olive600`: `#768443`
- `olive500`: `#87954D`
- `olive200`: `#D8DCC0`

### Warm workplane

- `ivory50`: `#FBF7EE`
- `cream100`: `#F5EEDF`
- `cream150`: `#F0E7D7`
- `cream200`: `#E9DFCC`
- `stone300`: `#D8CEBC`

### Rust / primary action

- `rust700`: `#A83B17`
- `rust600`: `#C44A1B`
- `rust500`: `#D75B24`
- `rust100`: `#F4D7C8`

### Teal / live interaction

- `teal700`: `#006E70`
- `teal600`: `#008487`
- `teal500`: `#15999A`
- `teal100`: `#D4EBE7`

### Text

- `charcoal950`: `#172024`
- `charcoal800`: `#30383A`
- `charcoal600`: `#626664`
- `charcoal450`: `#7C7E79`

### State

- success / verified: olive-green treatment plus explicit text;
- warning: warm amber distinct from rust brand action;
- danger: warm red distinct from rust brand action;
- information / active execution: teal plus explicit text;
- inactive / pending: warm stone/charcoal treatment.

Color alone never carries state meaning.

Exact values may be tuned by protected browser/screenshot validation while preserving these semantic hue roles. Do not reintroduce violet/cyan as the dominant product identity through local component styling.

## Typography

Wave 4 uses a coordinated editorial and application hierarchy. Wave 8 makes legibility a protected interaction requirement rather than allowing small type to preserve dense layouts.

### Display

Greeting, hero and major editorial headings use a reliable serif stack where available, for example system `ui-serif`, Georgia, Charter or equivalent platform serif fallbacks. No external font service is required.

Display typography should feel composed rather than decorative:

- strong dark-charcoal contrast on the warm workplane;
- moderate negative tracking only at large sizes;
- compact line height;
- no novelty scripts or ornamental display faces.

### Application text

Navigation, controls, conversation body, metadata, tables, statuses and forms use system-native sans-serif typography for reliability and accessibility.

At phone width:

- ordinary primary body copy targets at least 16 CSS px;
- primary navigation and actionable control labels target at least 14 CSS px;
- orientation labels and secondary metadata target at least 12 CSS px;
- dense technical-detail text may use 12 CSS px when necessary but must remain readable and selectable;
- layouts reflow before reducing important text below these targets.

### Technical text

Code, diffs, command output, hashes, source-lineage IDs and similar technical evidence use a platform monospace stack. Technical text remains selectable and must not be rasterized into decorative canvases.

## Content design and product language

Plain language is the default product voice.

- Primary copy explains outcomes, meaning and next actions before implementation mechanics.
- Prefer familiar verbs such as `Create`, `Review`, `Continue`, `Check`, `Try again`, `View progress`, and `Choose project` over internal operation names.
- Primary surfaces must not require users to understand software-engineering object names, lifecycle codes, provider terminology, raw error codes, IDs, revisions, bindings or evidence models unless those concepts are necessary to the decision at hand.
- Canonical technical terms remain available through clearly labeled secondary surfaces such as `Technical details`, detailed build views, Observability and audit/evidence views.
- Important messages should answer, in order where practical: **what happened, what it means, what the user can do next**.
- Simplification must not euphemize destructive actions, hide uncertainty, conceal a failure, obscure a required human decision, or imply work completed before authoritative state says so.
- Screen-reader labels follow the same plain-language rule as visible copy.
- Error copy shown by default is human-readable; raw server/provider messages belong in technical detail unless the raw wording itself is already the clearest safe explanation.

Canonical system terminology is still valid in engineering/audit contexts. The rule is progressive disclosure, not deletion of technical evidence.

## Material and depth

Primary warm cards use:

- ivory/cream surfaces;
- approximately 14–20 px desktop corner radii;
- low-contrast warm stone borders where a boundary is needed;
- soft, short warm shadows rather than dark floating-card shadows;
- restrained internal separators;
- generous but not wasteful padding.

Cards should feel like paper/light material on a warm workplane, not translucent glass floating over a dark background.

Do not wrap every small piece of content in an independent card. Use surface grouping only when it clarifies information architecture.

## Organic background treatment

The mockup's organic character may be expressed through subtle contour lines, soft radial/elliptical warm gradients or restrained landscape silhouettes.

Rules:

- decorative background contrast stays materially below content contrast;
- no particles, scanner grids, neon glow, high-frequency shimmer or lava-lamp motion;
- the left rail may carry a very subdued forest/hill silhouette near its lower edge on desktop;
- the main workplane may use broad soft warm forms or faint contour lines;
- reduced graphics removes decorative layers without changing layout or capability.

## Application shell

### Desktop composition

At standard desktop widths the approved mockup establishes a three-region hierarchy:

1. **Navigation rail** — dark forest, approximately 16–20% of the viewport and visually stable.
2. **Primary workplane** — dominant warm ivory/cream region for conversation, run state and Live Build.
3. **Utility rail** — narrower warm region for System Health, Active Run, Recent Alerts/activity and other secondary context.

The exact responsive widths may tune during browser validation, but the major order and dominance cannot change merely for implementation convenience.

### Navigation rail

- dark forest substrate with subtle tonal depth;
- orbital Parallax identity is the strongest element at the top;
- navigation labels remain readable warm white/cream;
- active navigation is a filled rust rounded rectangle, not a thin outline;
- inactive rows remain calm and high-enough contrast without individual cards;
- Observability is a first-class destination when the feature is available;
- Project/user/plan information may occupy restrained cards near the bottom where desktop height permits;
- mobile does not preserve a permanently wide desktop rail.

### Workspace header

- major greeting/title is editorial serif and near-charcoal;
- supporting line is olive/charcoal secondary text;
- primary creation action uses rust;
- alert/help controls use quiet warm surfaces;
- header remains subordinate to the current task and does not become a toolbar wall.

## Home and conversation surface

Conversation remains the product's primary creation experience.

The approved warm home composition may include:

- greeting and short prompt/subtitle;
- large warm hero/conversation card;
- concise Plan / Design / Build / Ship orientation where useful;
- suggested starting prompts when no meaningful conversation is active;
- the normal composer as the actionable focus;
- current-session/tool/activity context in the utility rail when meaningful;
- compact product summary cards only when they help orientation.

A returning user with an active conversation should not be forced through a decorative dashboard before continuing work.

### User message

- right aligned;
- warm neutral or teal-tinted restrained surface;
- rounded approximately 18–22 px;
- no loud border/glow;
- metadata quieter than content;
- constrained width.

### Assistant message

- left aligned and generally wider than user messages;
- warm cream/ivory governed material or minimally surfaced narrative depending on context;
- no decorative four-sided border as the primary narrative structure;
- settled narrative is high contrast, selectable and calm;
- orbital assistant identity may appear outside the message material.

### Composer

- warm rounded in-flow dock;
- approximately 18–22 px radius;
- send action is the strongest local teal or rust control according to context;
- attachments/context controls remain secondary;
- mobile targets remain at least approximately 44 pt;
- conversation content must remain fully reachable above the composer.

## Streaming response treatment

Wave 4 retires the prior violet laser/scanner aesthetic.

Substantive response text appears as SSE delivers it. An optional compact **live trace** may mark the newest streamed content using restrained teal/olive/rust energy, but:

- it may not retype or delay already-streamed text;
- it may not race ahead of server content;
- it may not become a long beam across the response;
- settled text quickly becomes normal selectable charcoal narrative text;
- reduced motion renders streamed text normally with no animated trace;
- `SPEC_AMENDMENT` uses normal protected hand-off presentation rather than live-writing effects.

## Conversation follow behavior

- sending a message re-enables live-edge following;
- new assistant output brings its start into view;
- the thread follows while the operator remains near the live edge;
- intentional upward scrolling suspends forced following;
- a visible jump-to-latest affordance may restore following when useful;
- the composer remains an in-flow dock below the flexible thread;
- page navigation alone must not simulate a global processing state.

## Build plan / Work Specification surface

The canonical server object remains the Work Specification, but ordinary product copy presents it as the user's **build plan**.

- objective and intended outcome are primary;
- acceptance criteria are presented as `What success looks like` or equivalent plain language;
- constraints become `Important limits`, open questions become `Questions to resolve`, and risks become `Things to watch` where those translations preserve meaning;
- draft state is described as waiting for review/approval rather than exposing `DRAFT` as the primary label;
- approved state uses olive/sage treatment plus clear `Approved` language;
- revision, exact canonical status, confidence and the `Work Specification` object name remain available in Technical details;
- approval is an obvious accessible operator action;
- expansion/collapse preserves conversation rhythm;
- mobile controls remain non-overlapping and touch-safe.

## Progress / Engineering Run surface

The canonical Engineering Run continues to provide durable server truth. Ordinary mobile product copy presents that truth as **Progress** and groups low-level stages into a stable five-step user journey:

`Define → Plan → Create → Check → Review`

The deterministic presentation mapping is:

- `SPECIFY` / Work Specification preparation → `Define`;
- `PLAN` → `Plan`;
- `IMPLEMENT` and `BUILD` → `Create`;
- `TEST` and `VERIFY` → `Check`;
- `REVIEW` → `Review`;
- `COMPLETE` marks the journey complete;
- failure, pause or cancellation retains the authoritative server state and is attached to the mapped current/resume step without inventing progress.

Primary progress surfaces should show the current step, overall position, what is happening now and the next meaningful action. Exact stage name, raw status, retry/correction/recovery attempts, IDs and evidence remain available through Technical details or the detailed engineering view.

- completed/current/pending states come from server facts;
- retry, correction, recovery and human-required states are explicit;
- visual treatment never implies a transition before server state changes;
- historical unbound runs remain clearly distinguished;
- ordinary operator controls appear only when the protected state machine permits them.

## Delivery choice and source handoff

Delivery is presented as an outcome choice inside the existing **Progress / Engineering Run** surface, not as a separate provider-administration workspace. The UI remains subordinate to authoritative Project and Engineering Run state.

- During `SPECIFY` and `PLAN`, a Project-bound approved run may show the server-owned delivery choice.
- `Download source` is the plain-language presentation of `source-only`; supporting copy may name IIS, local, or another deployment environment as examples without implying Parallax deployed there.
- `Vercel Preview` is the explicit hosted-preview choice; selecting it does not imply a Preview exists until provider evidence says so.
- Once implementation begins, delivery selection becomes read-only for that active build. The client must not offer a mode change the server would reject.
- At `REVIEW`, a successful `source-only` handoff may expose `Download verified source` on web/desktop only after the server has recorded the exact accepted-lineage handoff.
- Mobile may explain that the verified package can be downloaded from web/desktop rather than pretending a native download or deployment occurred.
- Delivery controls use the existing warm card, teal interaction, olive support, readable text, explicit selected state, and approximately 44 pt actionable-target rules. Color alone never identifies the selected delivery mode.
- Provider names stay secondary to the user outcome. Technical details preserve canonical `source-only` / `vercel-preview`, lineage, handoff, Preview and audit identities when inspection requires them.
- Download success means only that the exact verified source package was handed to the user. It must never be styled or worded as IIS/local/other deployment success without separate deployment evidence.

## Observability workspace

Observability is a governed technical view of actual Parallax execution, not a replacement runtime. Because the user deliberately entered a technical inspection surface, canonical engineering terminology is appropriate here when it improves precision.

### Run pipeline

Display:

`SPEC · PLAN · IMPLEMENT · BUILD · TEST · VERIFY · REVIEW`

`SPEC` may visually represent server `SPECIFY`. Completed stages use explicit checks/status, current stage uses teal live treatment and pending stages use warm neutral treatment. Failure/recovery/human-required state is represented with text and iconography, never color alone.

### KPI strip

A compact row may show useful bounded operational context such as success rate, median latency, retries, provider failures, compute/tokens and active runs. KPIs are secondary to the active run and must come from real data or clearly identified unavailable/empty state.

### Run Event Stream

The central event list is the primary observability narrative.

Rows show, where available:

- timestamp / relative time;
- event/state icon;
- concise bounded summary;
- duration;
- responsible protected subsystem/tool;
- safe action link such as Open Preview/Open PR where authorized;
- attempt/replay/recovery indication where meaningful.

The event stream never exposes hidden reasoning or raw provider payloads.

### Component Health

Health rows may include Reasoner, Spec Builder, worker runtime, source lineage, GitHub provider, Vercel Preview, validation/evaluation and similar real components. Status words such as `Healthy`, `Warning`, `Degraded`, `Unavailable` accompany color.

### Evidence & Audit

Show bounded authoritative identities such as:

- Project ID;
- Run ID;
- Work Specification revision/digest;
- accepted/candidate source lineage;
- repository identity;
- safe GitHub PR identity/link;
- Vercel Preview identity/link/status;
- protected evaluation result;
- last human approval/review event.

Secrets, auth material and raw provider payloads never appear.

## Live Build workspace

Live Build is the detailed run-inspection surface reached from Observability or the active run.

### Desktop layout

The dominant workspace may use:

- bounded file tree / source selector at left;
- large code/diff content area in the center;
- compact live activity rail at right;
- tab bar for `Code`, `Diff`, `Terminal`, `Tests`, `Events`, `Evidence`;
- run pipeline/header above the work area.

The layout may resemble an engineering workspace but remains product-curated and read-only except for already-governed Parallax controls.

### Code

- exact accepted/candidate lineage only;
- selected path clearly visible;
- syntax-readable monospace text;
- line numbers may be shown;
- source remains selectable;
- no unrestricted filesystem browser or direct editor write authority.

### Diff

- exact immutable from/to lineage identities are visible;
- additions/removals use accessible semantic treatment, not color alone;
- diff remains bounded to protected source content.

### Terminal

- shows only bounded redacted output from registered protected commands/tests;
- command identity is server registered;
- no arbitrary prompt, shell input or environment inspection field is present;
- exit state, duration, timeout/redaction indicators are explicit.

### Tests

- show real suite/test status and bounded failure summaries where retained;
- queued/running/passed/failed/replayed states are explicit;
- correction/retry is visibly associated with a new attempt/candidate where applicable.

### Events and Evidence

Reuse the canonical run-event/evidence models rather than inventing a client-only timeline.

## Observer controls versus execution controls

Observation controls:

- `Follow Live` — auto-follow newest event/content;
- `Pause View` — stops visual auto-follow only;
- `Jump to Latest` — resumes live-edge observation;
- tab/file selection — changes inspection context only.

Protected execution controls remain visually and semantically separate:

- Pause Run;
- Resume/continue Run;
- Cancel Run;
- approval/review actions.

A user browsing old code or scrolling events must never accidentally alter worker execution.

## System and utility rail

### System Health

May summarize overall state, active alerts, queue/worker health and latest relevant incident using real server evidence. Missing telemetry is shown as unavailable, never `Healthy` by default.

### Active Run

May show Project, model/runtime identity, context count, repository/branch/ref, current stage, source lineage and bounded estimated/elapsed timing where evidence supports it.

### Recent Alerts / Activity

Use bounded event-derived warnings/info/success items with timestamp and subsystem. Do not persist or render secret-bearing diagnostics.

## Destructive cleanup actions

Conversation and Project cleanup is a deliberate workspace-management action, not an ordinary navigation affordance.

- `Delete` must require an explicit second confirmation before the request is sent.
- The destructive action uses danger/rust treatment distinct from normal primary creation controls and always includes readable destructive wording; color alone is insufficient.
- The confirmation copy must state the user-visible scope: the item disappears from active Parallax workspace/history.
- For Projects, confirmation must also make the retained boundary clear: protected engineering evidence remains and linked GitHub repositories or Vercel deployments are not deleted by the workspace action.
- A non-terminal Engineering Run may block deletion. The UI must preserve the item and show the protected server reason instead of optimistically hiding it.
- Current active context should not expose a casual one-tap delete affordance. Cleanup belongs in recent-history/Project-management context or an equivalently deliberate management surface.
- Desktop and compact/mobile layouts must provide semantically equivalent confirmation and error behavior even when the exact control placement differs.
- Successful deletion updates the active list without presenting audit/evidence purge as having occurred.

## Mobile and narrow layouts

Do not shrink the desktop dashboard. Mobile is a guided control surface for understanding progress, making decisions, giving direction and inspecting results.

At phone width:

- persistent orientation should make the current Project/conversation context understandable;
- primary navigation uses a small stable set of destinations, currently `Chat`, `Progress`, and `Project` for the guided mobile shell;
- the Progress surface exposes the five-step `Define → Plan → Create → Check → Review` journey rather than seven low-level engineering stages;
- show one dominant task or decision at a time and move secondary engineering evidence behind progressive disclosure;
- explicitly communicate **where the user is, what Parallax is doing now, and what the user should do next**;
- avoid forcing users to jump among several screens merely to reconstruct process state;
- code/diff/terminal and other dense engineering views remain available as dedicated detail surfaces rather than competing with primary workflow guidance;
- utility-rail cards stack or move into dedicated secondary surfaces;
- all normal creation/conversation capability remains available;
- important text reflows rather than shrinking below the phone typography targets.

## Mobile web viewport and keyboard

Existing protected keyboard rules remain unchanged in intent:

- editable text uses at least 16 CSS px at phone sizes to avoid Safari focus zoom;
- user zoom is not disabled globally;
- when `visualViewport` becomes materially smaller while an editable control is focused, the Parallax root fits the visible viewport;
- non-zero visual-viewport offsets are compensated so WebKit panning does not move the active workspace behind the keyboard;
- adjustment resets when the keyboard/focus condition ends;
- the in-flow composer remains above the keyboard;
- no hard-coded device or keyboard heights.

## Accessibility

- normal product text remains selectable and semantically exposed;
- touch targets are approximately 44×44 pt or larger where practical;
- state always includes readable text/icon meaning in addition to color;
- focus treatment is visible against both forest and warm surfaces;
- contrast is validated for text, controls and statuses;
- no primary action depends on hover;
- motion is never the only carrier of progress/state;
- reduced motion and reduced graphics preserve equivalent capability;
- code/diff/terminal views remain keyboard navigable on web;
- plain-language accessibility labels describe the user action rather than exposing internal implementation terminology unnecessarily.

## Reduced motion and reduced graphics

Reduced motion removes non-essential transitions, live-trace motion and decorative orbital/background movement while preserving state updates.

Reduced graphics removes topographic/landscape/gradient decoration while preserving the same layout hierarchy, controls, text, run stages, evidence and Live Build functionality.

## Protected state presentations

### SPEC_AMENDMENT

A deliberate boundary, not a generic error. Preserve conversation and requested change. Primary copy should explain in plain language that the new request is different from the approved plan and offer only the protected choices the server permits. Canonical `SPEC_AMENDMENT` terminology may remain in Technical details/audit surfaces.

### Recoverable failure

Use warm warning treatment and explicit human-readable reason/next action from protected classification. Do not imply retry is available when server policy does not allow it. Raw failure codes belong in Technical details unless they are themselves meaningful user language.

### HUMAN_REQUIRED / REVIEW

Use clear operator-attention treatment, distinct from ordinary failure and ordinary live execution. Primary copy may say `Ready for your review` or equivalent, while technical surfaces preserve the exact state. The UI cannot convert these boundaries into automatic progress.

### ERROR / unavailable telemetry

Preserve durable content. Secret-bearing diagnostics and hidden reasoning are never product copy. Missing event/health data renders `Unavailable`/`Degraded` rather than fabricated success. Primary error copy explains the user impact first; safe raw diagnostics remain secondary.

## Visual acceptance and anti-drift rules

Wave 4 implementation converted the approved home and Observability mockups into repeatable browser/screenshot assertions. Wave 8 adds mobile usability and content assertions.

Protected visual relationships include:

- forest left rail with rust active navigation;
- warm ivory/cream main workplane;
- editorial greeting hierarchy;
- dominant central work area;
- narrower right utility rail;
- consistent warm card radius/material;
- run pipeline prominence in technical observability surfaces;
- compact KPI row;
- Live Build/event content as the largest operational technical surface;
- teal live state, rust action state and restrained olive support state;
- responsive mobile reflow rather than desktop miniaturization;
- phone primary navigation/control text at readable sizes and touch targets approximately 44 pt or larger;
- a stable five-step plain-language mobile progress journey derived only from authoritative server state;
- technical terminology hidden from ordinary primary mobile workflow surfaces until the user asks for detail.

Centralized theme tokens are the required source for product colors. One-off local colors should be exceptional and justified.

Deterministic functional, accessibility, security and authoritative-state failures outrank visual similarity. If fidelity conflicts with a protected requirement, adjust the design implementation rather than weaken the protected requirement.

## Development-state rule

Mockups, fixtures and deterministic adapters are design/test evidence, not production runtime truth. UI screenshots may prove appearance but do not prove a run, provider action or deployment occurred.

Generated, validated, Preview, deployed and deployment-verified states remain distinct throughout product copy and project records.
