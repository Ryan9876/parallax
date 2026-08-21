# Parallax 2.0 Design System

Version: 1.6
Status: Authoritative

## Design direction

Parallax is a premium optical reasoning and engineering workspace. Conversation remains the primary product surface; the interface should feel quiet at rest and visibly alive only when intelligence is working.

The visual system is **Editorial Optical**: Deep Violet Optical remains the precision foundation, while a restrained editorial layer adds stronger hierarchy, asymmetry, negative space, tactile material, and selective human warmth. The intended balance is approximately **80% Deep Violet precision / 20% editorial personality**.

The editorial layer is inspired by principles such as confident section hierarchy, softly framed groups, controlled color accents, and hand-made graphic character. It must never copy an external brand, restaurant/menu layout, illustration language, or typography system.

This is not a generic neon-AI theme and it is not a pastel redesign. Distinction comes from spatial depth, material restraint, authored hierarchy, and a small number of signature optical behaviors.

Content wins every visual competition. Ambient effects must be perceived second, never first. If the living surface, trace treatment, identity color, or response energy attracts attention before the conversation does, its intensity is too high.

## Material palette

Core production tokens:

- Deep substrate: `#080B12`
- Dark optical surface: `#0B1019`
- Strong surface: `#111525`
- Raised surface: `#161A2B`
- Primary text: `#F4F2FF`
- Secondary text: `#B8B6CC`
- Muted metadata: `#85849B`
- Cyan optical accent: `#7DE7FF`
- Indigo transition accent: `#8B9CFF`
- Violet identity/action accent: `#D18BFF`
- Deep violet control accent: `#8F63D8`
- Editorial cream: `#F0E4CF`
- Editorial dusty peach: `#DFA78F`
- Editorial muted sage: `#9FB9A5`
- Danger: `#FF9AAB`
- Warning: `#E7C98F`
- Verified/success: `#72E3C4`
- Dark glass: `rgba(13,16,29,0.70)`
- Strong glass: `rgba(17,21,37,0.90)`
- Optical border: `rgba(167,151,255,0.18)`

Color hierarchy is intentional:

- cyan = active optical energy and live focus;
- indigo = precision structure and technical status;
- violet = identity, selection, and product atmosphere;
- cream = display reading warmth and selected editorial headings;
- peach = human/operator annotation and soft editorial emphasis;
- sage = approved/ready editorial treatment when paired with explicit state text.

Editorial colors are secondary accents. They must not replace semantic success, warning, danger, or state labels, and color alone never carries meaning.

## Editorial hierarchy

Parallax uses two coordinated reading scales:

1. **Narrative scale** — assistant/user conversation remains the highest-contrast, most readable layer.
2. **Editorial state scale** — Work Specification and Code execution surfaces may use larger display labels, compact kickers, and more negative space to make governed state legible without becoming dashboard cards.

Use visible chrome sparingly. Prefer spacing, offset rules, open framing, typography, and optical alignment over enclosing every region in a full card.

A governed surface may use:

- an open left or bottom rule instead of four borders;
- an intentionally asymmetric edge treatment;
- soft irregular-radius controls within an otherwise open field;
- one editorial trace that visually marks the active section;
- quiet technical metadata beneath or beside the display anchor.

Do not stack multiple decorative frames around the same content.

## Optical workplane

The living surface is an editorial optical workplane, not a HUD, scanner, or decorative liquid wallpaper.

Use:

- a deep navy substrate;
- broad low-frequency violet and indigo ink fields with asymmetric centers;
- sparse hand-drawn contour ribbons with controlled irregularity;
- extremely subtle procedural print/paper grain;
- one low-energy cyan optical focus region tied to response energy;
- a dark center bias behind conversation copy.

Avoid:

- obvious drafting grids;
- scanner/calibration lines;
- uniform topographic repetition;
- continuous orbital motion;
- high-frequency shimmer or neon noise.

At idle, the workplane should read as material atmosphere. During response activity, only the focus region and local optical energy rise modestly.

Reduced motion freezes the time-dependent field without changing semantic state.

## Editorial trace

The **Editorial Trace** is a reusable Skia primitive for governed product-state surfaces such as Work Specification and Code execution.

It consists of one imperfect open contour and a small focus mark. It is intentionally incomplete: it suggests an authored annotation rather than a full card border.

Rules:

- decorative only; `pointerEvents="none"` and excluded from accessibility semantics;
- no orbiting, spinning, scanning, or perpetual attention-seeking motion;
- active state may slightly increase optical presence;
- reduced motion keeps a static trace;
- reduced-graphics mode renders no Skia trace at all while retaining the same layout hierarchy through normal React Native views/text.

## Optical typesetter

The active assistant response is inscribed as illuminated ink:

- the optical head follows the active wrapped line;
- response text arrives continuously with the live SSE stream;
- fresh glyphs carry a short lavender energy edge;
- a small cyan hot point marks the active inscription position;
- the beam is intentionally softer and less scanner-like than the original Deep Violet implementation;
- glyphs cool quickly to normal pale text;
- final text remains selectable and accessibility-aware.

The typesetter represents substantive generated response content. It does not run for a `SPEC_AMENDMENT` hand-off that intentionally stops substantive continuation.

Reduced motion disables the animated head and reveals substantive response text normally.

## Work Specification surface

Work Specification is an implementation contract, not a ticket card.

Presentation rules:

- `SPEC · DRAFT/APPROVED` remains explicit, compact metadata;
- revision identity remains visible;
- title and objective form the primary reading hierarchy;
- use an open editorial frame with peach/sage treatment rather than a full uniform rectangle;
- acceptance criteria remain readable as contract clauses, not dashboard metrics;
- approval remains an obvious accessible operator action;
- approved state may use muted sage, always paired with explicit `APPROVED` text;
- expansion/collapse preserves the conversation-first page rhythm.

## Code execution surface

Code execution presents durable truth rather than simulated progress.

Presentation rules:

- current run stage is the display anchor;
- exact bound Work Specification revision and acceptance-count identity appear immediately below;
- execution evidence is quiet secondary text;
- controls remain available only where the protected state machine allows them;
- an open sage editorial frame differentiates governed execution from ordinary conversation;
- the trace may indicate active governed state but must never imply a stage transition before server state changes;
- historical unbound runs remain visually and textually distinguishable.

## Conversation and composer

Conversation remains visually dominant. Assistant response surfaces should read as one continuous precision workspace rather than a stack of independent dashboard cards.

User content may remain lightly contained, but unnecessary border weight should be avoided. Metadata stays quieter than narrative text.

The composer anchors the interaction and may use a strong dark material surface, but it should not become a glossy floating pill or compete with the active response.

## Specification-amendment state

`SPEC_AMENDMENT` is a first-class protected hand-off state, not a generic error.

- preserve conversation and user request in place;
- show the concise amendment-required message in normal flow;
- use restrained indigo/neutral treatment rather than danger styling;
- keep workplane energy near idle;
- optical inscription remains off because no substantive continuation is being rendered;
- do not shake, flash, or aggressively pulse;
- keep composer/navigation available so the state feels recoverable;
- reduced-motion and reduced-graphics presentations communicate the same meaning statically.

The visual message is: **the objective boundary changed and Parallax stopped deliberately**.

## Recoverable error state

`ERROR` is reserved for actual inability to complete the requested response. It remains visually quieter than destructive-failure UI because durable conversation is preserved.

User-facing error text should prefer sanitized server recovery messages. Provider exceptions, secret-bearing diagnostics, candidate output, and hidden reasoning are never rendered as product copy.

## Parallax mark

The Parallax Optical Mark remains the representative identity:

- stable outer optical boundary around a centered intelligence lens;
- cyan outer optical energy, indigo inner structure, violet aperture gesture;
- one directional aperture gesture rather than orbital loops/spinner geometry;
- a small cyan focus point may shift only a few pixels over a slow cycle;
- no continuous rotation, orbiting particles, or scanner crosshairs;
- the mark must remain legible at sidebar scale;
- reduced motion uses the centered static mark.

Editorial personality belongs mainly to surrounding composition and material, not by making the logo ornate.

## Typography

Use system-native sans-serif typography for production reliability. Do not ship custom font binaries merely to imitate a reference site.

Narrative text uses pale violet-white to reduce glare. Editorial display headings may use cream to create warmth and hierarchy. Technical metadata remains small and restrained but must remain readable.

All final assistant text is normal selectable/accessibility-aware text. Motion is never the only carrier of state or content.

## Reduced-graphics parity

The non-Skia fallback is not a separate visual product.

It preserves:

- Deep Violet + editorial accent palette;
- display hierarchy;
- open framing through normal borders/spacing;
- Work Specification revision/approval semantics;
- bound Code run identity and controls;
- conversation/composer behavior;
- all accessibility and state text.

It deliberately omits Skia ink, grain, optical traces, and animated inscription head. A user requiring reduced graphics loses decorative rendering cost, not product identity, content, state information, or capability.

## Motion state mapping

| Response state | Surface energy | Logo | Typesetter | Meaning |
| --- | ---: | --- | --- | --- |
| IDLE | 0.18 | calm | off | ready |
| THINKING | 0.42 | calm | off | resolving objective/context |
| RESPONDING | 0.72 | calm | active illuminated ink | substantive answer arriving |
| VERIFYING | 0.48 | calm | off | protected verification/finalization |
| COMPLETE | 0.18 | calm | off | response settled |
| SPEC_AMENDMENT | 0.22 | calm | off | deliberate protected hand-off |
| ERROR | 0.12 | static/calm | off | recoverable inability to complete |

Governed section traces follow their own product state but remain subordinate to narrative content.

## Accessibility

- Core narrative text targets WCAG AA contrast against its rendered surface.
- State is communicated with explicit text/shape in addition to color.
- Minimum 44 pt mobile interaction targets remain required.
- Keyboard and screen-reader semantics are preserved.
- Reduced motion and reduced graphics remain first-class modes.
- Grain/ink effects may never lower narrative contrast materially.
- Editorial traces are decorative and excluded from accessibility navigation.
- Ambient violet/cyan/peach/sage effects may never obscure narrative text or primary controls.
