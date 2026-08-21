# Parallax 2.0 Design System

Version: 1.7
Status: Authoritative

## Design direction

Parallax is a premium optical reasoning and engineering workspace. Conversation remains the primary product surface; the interface should feel quiet at rest and visibly alive only when intelligence is working.

The visual system is **Editorial Optical**: Deep Violet Optical remains the precision foundation, while a restrained editorial layer adds stronger hierarchy, asymmetry, negative space, tactile material, and selective human warmth. The intended balance is approximately **80% Deep Violet precision / 20% editorial personality**.

The editorial layer is inspired by principles such as confident section hierarchy, softly framed groups, controlled color accents, and hand-made graphic character. It must never copy an external brand, restaurant/menu layout, illustration language, or typography system.

This is not a generic neon-AI theme and it is not a pastel redesign. Distinction comes from spatial depth, material restraint, authored hierarchy, and a small number of signature optical behaviors.

Content wins every visual competition. Ambient effects must be perceived second, never first. If the living surface, trace treatment, identity color, response energy, or laser inscription attracts attention before the conversation does, its intensity is too high.

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
- Violet laser: `#B88CFF`
- Violet laser core: `#F2E9FF`
- Editorial cream: `#F0E4CF`
- Editorial dusty peach: `#DFA78F`
- Editorial muted sage: `#9FB9A5`
- Danger: `#FF9AAB`
- Warning: `#E7C98F`
- Verified/success: `#72E3C4`
- Dark glass: `rgba(13,16,29,0.70)`
- Strong glass: `rgba(17,21,37,0.90)`
- Conversation glass: `rgba(84,86,103,0.20)`
- Strong conversation glass: `rgba(92,94,112,0.27)`
- Conversation edge: `rgba(228,225,242,0.07)`
- Optical border: `rgba(167,151,255,0.18)`

Color hierarchy is intentional:

- cyan = restrained secondary optical focus and live technical energy;
- indigo = precision structure and technical status;
- violet = identity, selection, product atmosphere, and the primary response-inscription energy;
- cream = display reading warmth and selected editorial headings;
- peach = human/operator annotation and soft editorial emphasis;
- sage = approved/ready editorial treatment when paired with explicit state text.

Editorial colors are secondary accents. They must not replace semantic success, warning, danger, or state labels, and color alone never carries meaning.

## Editorial hierarchy

Parallax uses two coordinated reading scales:

1. **Narrative scale** — assistant/user conversation remains the highest-contrast, most readable layer.
2. **Editorial state scale** — Work Specification and Code execution surfaces may use larger display labels, compact kickers, and more negative space to make governed state legible without becoming dashboard cards.

Use visible chrome sparingly. Prefer spacing, soft material, offset rules, typography, and optical alignment over enclosing every region in a full card.

A governed surface may use:

- an open left or bottom rule instead of four borders;
- an intentionally asymmetric edge treatment;
- soft irregular-radius controls within an otherwise open field;
- one editorial trace that visually marks the active section;
- quiet technical metadata beneath or beside the display anchor.

Do not stack multiple decorative frames around the same content.

## Ambient optical workplane

The living surface is a calm **ambient optical lava field**. It borrows the slow, organic behavior of a lava lamp without becoming novelty decoration or a bright liquid wallpaper.

Use:

- a deep navy/midnight substrate;
- three to five very large indigo, violet, midnight-blue, and restrained lavender organic fields;
- soft metaball-like fusion and broad liquid seams rather than discrete particles;
- non-synchronous low-frequency drift/deformation with visually long cycles, typically on the order of 20–45 seconds or longer;
- extremely subtle procedural grain;
- a dark center reading bias behind conversation copy;
- only a modest energy lift while Parallax is actively responding.

Avoid:

- particles or starfields;
- obvious drafting grids;
- scanner/calibration lines;
- uniform topographic repetition;
- continuous orbital motion;
- fast morphing blobs;
- high-frequency shimmer;
- bright saturated forms beneath narrative text;
- obvious short loops.

At idle, the field should read as depth and atmosphere. The motion should be noticeable only after looking for it. During response activity, the background may gain slightly more presence but remains subordinate to copy and the local laser inscription.

Reduced motion freezes the time-dependent field into a stable composition without changing semantic state or product depth.

## Editorial trace

The **Editorial Trace** is a reusable Skia primitive for governed product-state surfaces such as Work Specification and Code execution.

It consists of one imperfect open contour and a small focus mark. It is intentionally incomplete: it suggests an authored annotation rather than a full card border.

Rules:

- decorative only; `pointerEvents="none"` and excluded from accessibility semantics;
- no orbiting, spinning, scanning, or perpetual attention-seeking motion;
- active state may slightly increase optical presence;
- reduced motion keeps a static trace;
- reduced-graphics mode renders no Skia trace at all while retaining the same layout hierarchy through normal React Native views/text.

## Purple laser typesetter

The active assistant response is inscribed as a fine **violet/purple optical etch** into the conversation surface.

Required character:

- the optical head follows the active wrapped line and the actual growing SSE text target;
- a short soft violet trail leads into a concentrated purple-white core;
- freshly inscribed glyphs carry a brighter lavender/violet energized edge and restrained glow;
- the energized tail is short and cools quickly to normal pale narrative text;
- cyan, if present, is a secondary optical highlight rather than the dominant beam color;
- the effect must read as glass-like laser inscription, not a typewriter cursor, scanner, or post-response replay;
- final text remains normal selectable and accessibility-aware text.

The typesetter represents substantive generated response content. It does not run for a `SPEC_AMENDMENT` hand-off that intentionally stops substantive continuation.

Reduced motion disables the moving head/beam and reveals substantive response text normally.

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

Conversation remains visually dominant. Ordinary messages are not dashboard panels and should not be enclosed by persistent conventional hard-line boxes.

### Conversation material

User and assistant messages share one quiet material family:

- softly rounded graphite/neutral-gray translucent glass;
- approximately 18–22 px radii, tuned by viewport;
- no persistent full rectangular outline or heavy left rail;
- separation comes primarily from translucency, spacing, alignment, subtle shadow/depth, and at most a nearly imperceptible edge light;
- user messages remain right aligned and somewhat narrower;
- assistant responses remain left aligned and may be broader, but should not become full-width panels;
- role is also communicated by alignment and metadata, never color alone.

Assistant identity remains outside/above the response surface as a compact signature. The laser inscription occurs inside the assistant glass surface while responding.

On mobile, bubble width and padding should preserve breathing room without the stacked full-width-card appearance. The surrounding ambient field should remain visible enough to make the conversation feel spatial rather than boxed.

### Composer

The composer anchors the interaction in the same soft graphite glass family:

- rounded translucent neutral-gray material;
- no strong permanent outline; a very low-opacity edge is acceptable where contrast requires it;
- violet send control retains product identity;
- input text remains the visual priority;
- the composer should feel grounded, not like a glossy floating pill.

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
- soft conversation material and role/alignment semantics;
- Work Specification revision/approval semantics;
- bound Code run identity and controls;
- conversation/composer behavior;
- all accessibility and state text.

It deliberately omits Skia ambient lava motion, grain, optical traces, and animated laser head. A user requiring reduced graphics loses decorative rendering cost, not product identity, content, state information, or capability.

## Motion state mapping

| Response state | Surface energy | Logo | Typesetter | Meaning |
| --- | ---: | --- | --- | --- |
| IDLE | 0.18 | calm | off | ready |
| THINKING | 0.42 | calm | off | resolving objective/context |
| RESPONDING | 0.72 | calm | active violet laser etch | substantive answer arriving |
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
- Final assistant text remains selectable.
- Ambient motion and laser inscription are decorative enhancements, never the sole carrier of content or state.
- Grain/lava effects may never lower narrative contrast materially.
- Editorial traces are decorative and excluded from accessibility navigation.
- Ambient violet/indigo/lavender and editorial accent effects may never obscure narrative text or primary controls.
