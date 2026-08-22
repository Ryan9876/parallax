# Parallax 2.0 Design System

Version: 1.8
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
- Conversation material: neutral-grey/navy translucency in the approximate range `rgba(118–140, 122–144, 138–153, 0.10–0.15)`
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

The living surface is an editorial optical workplane, not a HUD, scanner, particle field, or literal lava-lamp simulation.

The production field uses **Ambient Chroma Flow**: large, heavily feathered regions of violet, indigo, blue, and restrained magenta move through one another like diffused light behind liquid glass. The treatment is reference-informed motion language translated into Parallax's own palette, contrast, and reading behavior.

Use:

- a deep navy/near-black substrate;
- broad overlapping chroma fields rather than discrete bounded blobs;
- dominant indigo, violet, midnight blue, and cobalt presence;
- restrained magenta and lavender as secondary atmosphere;
- sparse warm amber/peach blooms as occasional counterpoints, never dominant color fields;
- cyan only as a restrained optical accent;
- low-frequency warped haze that blends neighboring color regions rather than drawing edges around them;
- continuous drift with perceived composition changes measured in tens of seconds;
- subtle material grain;
- a materially darker central reading field beneath conversation content;
- activity energy that raises chroma presence only modestly and does not materially increase speed.

Avoid:

- obvious drafting grids;
- scanner/calibration lines;
- uniform topographic repetition;
- discrete hard-edged or obviously separated lava blobs;
- bouncing or obviously looping motion;
- particles, sparkles, high-frequency shimmer, or bright neon liquid;
- a warm field large enough to displace the violet/indigo identity;
- movement that competes with reading.

At idle, the workplane should feel alive after a moment of observation while still being visibly dimensional. During response activity, local optical energy may rise modestly without changing the page into an animation showcase.

Reduced motion freezes the time-dependent field without changing semantic state or visual identity. Reduced graphics preserves the layout and material hierarchy without requiring Skia.

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

The active assistant response is inscribed as **theme-colored optical etching**:

- the optical head follows the active wrapped line;
- response text arrives continuously with the live SSE stream;
- fresh glyphs carry a visible violet/indigo etched edge and short-lived lavender internal energy;
- a small cyan hot point marks the active inscription position;
- the optical head reads as precision inscription rather than scanner/HUD machinery;
- the hot tail remains perceptible at normal reading speed but cools quickly;
- settled glyphs return to normal pale narrative text rather than persistent neon;
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

## Conversation material

Conversation is the visual center of Parallax and must not resemble a stack of generic dashboard cards.

### User message

- right aligned;
- soft neutral-grey/indigo translucent material;
- approximately 18–22 px corner radius in the production scale;
- no visible continuous border;
- no bright glow;
- metadata remains smaller and quieter than message text;
- width is constrained so the user turn reads as a conversational object rather than a page panel.

### Assistant message

- left aligned and wider than the user message, but not full-width by default;
- neutral-grey/navy translucent material with approximately 20–24 px corner radius;
- no conventional top, bottom, or left rules around ordinary narrative content;
- faint local violet depth/shadow is allowed instead of a hard outline;
- assistant identity row remains outside the message material;
- settled narrative text remains high-contrast, selectable, and calm.

Message grouping is carried by alignment, spacing, material translucency, and metadata—not by four-sided borders.

### Composer

The composer anchors interaction with the same soft rounded material language:

- translucent dark neutral material;
- approximately 20–24 px radius;
- no heavy field outline;
- send action remains the strongest local control;
- mobile interaction targets remain at least 44 pt;
- composer must not visually overpower the active assistant response.

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
- soft conversation-material grouping through ordinary React Native translucency and spacing;
- Work Specification revision/approval semantics;
- bound Code run identity and controls;
- conversation/composer behavior;
- all accessibility and state text.

It deliberately omits Skia ambient chroma-flow rendering, optical traces, and animated inscription head. A user requiring reduced graphics loses decorative rendering cost, not product identity, content, state information, or capability.

## Motion state mapping

| Response state | Surface energy | Logo | Typesetter | Meaning |
| --- | ---: | --- | --- | --- |
| IDLE | 0.18 | calm | off | ready |
| THINKING | 0.42 | calm | off | resolving objective/context |
| RESPONDING | 0.72 | calm | active optical etching | substantive answer arriving |
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
- Grain and ambient optical effects may never lower narrative contrast materially.
- Editorial traces are decorative and excluded from accessibility navigation.
- Ambient chroma-flow motion may never obscure narrative text or primary controls.
- Final assistant text remains selectable regardless of whether animated inscription was used during generation.
