# Parallax 2.0 Design System

Version: 2.1
Status: Authoritative

## Design direction

Parallax is a premium optical reasoning and engineering workspace. Conversation remains the primary product surface; the interface should feel calm, dimensional, and authored rather than like a conventional dashboard or generic AI chat application.

The visual system remains **Editorial Optical**: Deep Violet Optical provides precision and technical depth, while restrained editorial composition supplies hierarchy, asymmetry, negative space, tactile material, and selective warmth.

Content wins every visual competition. Ambient color, identity motion, optical engraving, governed surfaces, and workspace chrome must support reading rather than compete with it.

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
- Conversation/governed material: neutral-grey/navy translucency in the approximate range `rgba(110–140, 108–144, 135–153, 0.10–0.16)`
- Optical border when required: `rgba(167,151,255,0.18)`

Color hierarchy is intentional:

- cyan = active optical energy and live focus;
- indigo = precision structure and technical status;
- violet = identity, selection, and product atmosphere;
- cream = selected editorial reading warmth;
- peach = restrained human/operator emphasis, not structural framing;
- sage = approved/ready treatment when paired with explicit state text.

Color alone never carries semantic meaning.

## Editorial hierarchy

Parallax uses two coordinated scales:

1. **Narrative scale** — assistant/user conversation is the highest-contrast, most readable layer.
2. **Governed-state scale** — Work Specification and Code surfaces expose durable state with compact status, strong titles, and restrained controls.

Avoid stacking decorative frames. Prefer spacing, translucent material, subtle depth, compact status pills, and optical alignment over four-sided outlines.

## Ambient Chroma Flow

The living surface is an editorial optical workplane, not a HUD, scanner, particle field, or literal lava-lamp simulation.

The production field uses **Ambient Chroma Flow**: broad heavily feathered regions of violet, indigo, cobalt, blue, restrained magenta/lavender, and rare warm counterpoints drift through one another like diffused light behind liquid glass.

Use:

- deep navy/near-black substrate;
- broad overlapping chroma fields rather than bounded blobs;
- dominant indigo, violet, midnight blue, and cobalt;
- restrained magenta/lavender atmosphere;
- sparse amber/peach counterpoints;
- cyan only as an optical accent;
- low-frequency warped haze that blends neighboring regions;
- a materially darker central reading field beneath conversation content;
- activity energy that raises chroma presence modestly without materially increasing speed;
- subtle grain.

**Motion must be perceptible during an ordinary 5–15 second observation.** Major compositions may evolve over roughly one to two minutes, but nested multipliers must not make the production field appear static during normal use.

Avoid:

- grids or scanner/calibration lines;
- hard-edged lava blobs;
- bouncing or synchronized looping motion;
- particles, sparkles, high-frequency shimmer, or bright neon liquid;
- motion that competes with reading.

Reduced motion freezes the time-dependent field. Reduced graphics preserves product hierarchy without requiring Skia.

## Parallax knot identity

The representative Parallax identity is the **3D interlocking knot** approved in v0.13.

Identity rules:

- use one interwoven three-loop silhouette for both primary brand and assistant avatar/emoji identity;
- retain dimensional glossy shading rather than flattening the knot into a line icon;
- dominant surface colors are deep blue, indigo, violet, magenta highlights, and restrained cyan energy;
- the area outside the knot is transparent: no circular badge, enclosing orb, ring, or background plate;
- primary UI implementations use a slow continuous 360-degree rotation with a period long enough that it never reads as a loading spinner;
- web may add a restrained cyan/violet traveling highlight clipped to the knot alpha so light appears to move over the material;
- the traveling highlight supplements rather than replaces the baked 3D shading;
- small assistant-avatar use must remain recognizably the same mark, not a separate emoji design;
- reduced motion uses the same knot in a stable static orientation.

The mark may carry a soft local shadow or bloom appropriate to its size, but it should not be placed inside decorative circles solely to create contrast.

## Workspace chrome

Desktop navigation and top chrome are quiet optical materials rather than flat utility bars.

### Left navigation rail

- use deep translucent material with subtle violet depth;
- brand/knot identity is the strongest element at the top of the rail;
- connection/workspace state may appear as compact secondary metadata;
- active conversation uses rounded translucent depth rather than a solid rectangular highlight or bright outline;
- inactive conversations stay low-contrast but readable;
- new-conversation action is compact and clearly discoverable;
- do not turn the rail into a dashboard of badges or controls.

### Top workspace banner

- remain compact and subordinate to conversation;
- use translucent deep optical material with a restrained violet atmosphere;
- title/status and Reason/Code remain explicit;
- selected mode may use solid violet material, while the mode container avoids conventional heavy borders;
- mobile identity/mode geometry must remain non-overlapping.

## Optical typesetter

The active assistant response is rendered as **stream-synchronized theme-colored optical engraving**.

Rules:

- substantive text is displayed as soon as SSE delivers it;
- there is no independent client-side character clock that retypes, delays, or races ahead of streamed content;
- the optical head follows the end of the newest rendered wrapped line;
- the head is compact and localized: a short indigo/violet trail, lavender precision core, and cyan hot point;
- do not use a long scanner beam across the response;
- only a short newest-glyph tail carries visible violet/lavender etched energy;
- fresh-glyph energy cools quickly into normal pale selectable narrative text;
- the head may ease between measured positions but must not invent content timing;
- final response text remains selectable and accessibility-aware.

The typesetter does not run for `SPEC_AMENDMENT`, because that hand-off intentionally stops substantive continuation.

Reduced motion removes animated head motion and shows streamed substantive text normally.

## Conversation follow behavior

The conversation thread follows the live response while respecting operator intent.

- sending a new message re-enables live-edge following;
- when an assistant response begins, its start is automatically brought into the visible thread region;
- while the operator remains near the live edge, streamed content stays visible as it grows;
- the composer reserves actual layout space as an in-flow dock, and the conversation thread is the flexible shrinkable scroll region above it;
- conversation content must never rely on estimated composer-height padding as the primary clearance mechanism;
- if the operator intentionally scrolls materially upward during a response, Parallax stops forcing the thread to the bottom;
- the next new operator message re-enables live-edge following;
- this behavior is interaction logic, not animation spectacle.

## Work Specification surface

Work Specification is an implementation contract, not a ticket card or editorial poster.

Presentation rules:

- `SPEC · DRAFT/APPROVED` remains explicit compact metadata;
- revision identity remains visible;
- title/objective form the primary reading hierarchy;
- use rounded translucent neutral/violet optical material consistent with conversation surfaces;
- do not use a heavy peach left rule or conventional four-sided outline as the primary structure;
- draft may use restrained violet status treatment;
- approved may use muted sage, always paired with explicit `APPROVED` text;
- acceptance criteria remain readable as contract clauses, not dashboard metrics;
- approval remains an obvious accessible operator action;
- expansion/collapse preserves conversation-first page rhythm;
- phone controls remain at least 44 pt and preserve v0.11.1 non-overlap rules.

## Code execution surface

Code execution presents durable truth rather than simulated progress.

- current run stage is the display anchor;
- exact bound Work Specification revision and acceptance identity remain visible;
- execution evidence is quiet secondary text;
- controls remain available only where the protected state machine allows them;
- presentation may use governed translucent optical material distinct from ordinary narrative content;
- visual treatment must never imply a stage transition before server state changes;
- historical unbound runs remain visibly/textually distinguishable.

## Conversation material

Conversation is the visual center of Parallax and must not resemble a stack of generic dashboard cards.

### User message

- right aligned;
- soft neutral-grey/indigo translucent material;
- approximately 18–22 px radius;
- no visible continuous border or bright glow;
- metadata is smaller/quieter than message text;
- width is constrained so the turn reads as a conversational object rather than a page panel.

### Assistant message

- left aligned and wider than the user message, but not full-width by default;
- neutral-grey/navy translucent material with approximately 20–24 px radius;
- no conventional top/bottom/left narrative rules;
- faint local violet depth is allowed instead of a hard outline;
- assistant knot identity row remains outside message material;
- settled narrative remains high-contrast, selectable, and calm.

### Composer

- same soft rounded translucent material language;
- approximately 20–24 px radius;
- no heavy field outline;
- send action remains the strongest local control;
- mobile targets remain at least 44 pt;
- the composer is an in-flow dock below the shrinkable conversation thread, not an absolute overlay over narrative content;
- newest response and amendment content must remain fully reachable above the composer at the thread's live edge;
- reduced-graphics mode preserves the same structural composer-clearance behavior.

### Mobile web viewport and keyboard

Mobile web must remain compositionally stable while the software keyboard is visible, including on iOS WebKit where the keyboard may overlay rather than resize the layout viewport.

- editable text on phone-sized web layouts uses at least 16 CSS px so focusing an input does not trigger Safari focus zoom or horizontal cropping;
- do not disable user zoom globally to solve focus zoom; accessibility zoom remains available;
- when a focused editable field coincides with a materially reduced `visualViewport`, the Parallax root fits the visible viewport rather than remaining behind the keyboard;
- compensate a non-zero visual-viewport offset so WebKit panning does not displace the workspace away from the visible region;
- the keyboard-aware adjustment is temporary and resets when the visual viewport recovers or editable focus ends;
- the in-flow composer remains fully above the keyboard, while conversation and governed surfaces yield vertical space naturally;
- do not hard-code device heights or keyboard sizes; respond to measured viewport geometry;
- desktop and mobile browsers that already resize the layout viewport correctly should not receive unnecessary compensation.

## Specification-amendment state

`SPEC_AMENDMENT` is a first-class protected hand-off state, not a generic error.

- preserve conversation and user request in place;
- show the concise amendment-required message in normal flow;
- use restrained indigo/neutral treatment rather than danger styling;
- keep workplane energy near idle;
- optical engraving remains off because no substantive continuation is rendered;
- do not shake, flash, or aggressively pulse;
- keep composer/navigation available so the state feels recoverable.

The visual message is: **the objective boundary changed and Parallax stopped deliberately**.

## Recoverable error state

`ERROR` is reserved for actual inability to complete the requested response. Durable conversation remains preserved. Provider exceptions, secret-bearing diagnostics, candidate output, and hidden reasoning are never rendered as product copy.

## Typography

Use system-native sans-serif typography for production reliability. Narrative text uses pale violet-white to reduce glare. Technical metadata remains small and restrained but readable. Motion is never the only carrier of content or state.

## Reduced-graphics parity

The non-Skia fallback is not a separate visual product. It preserves:

- Deep Violet + editorial accent palette;
- 3D knot identity as a normal image surface;
- display hierarchy and workspace chrome;
- soft conversation/governed material grouping;
- Work Specification semantics;
- bound Code run identity/controls;
- conversation/composer behavior, including in-flow composer clearance;
- all accessibility/state text.

It deliberately omits Skia Ambient Chroma Flow and animated engraving head. Reduced graphics removes decorative rendering cost, not product identity, state, or capability.

## Motion state mapping

| Response state | Surface energy | Knot | Typesetter | Meaning |
| --- | ---: | --- | --- | --- |
| IDLE | 0.18 | slow ambient spin | off | ready |
| THINKING | 0.42 | slow ambient spin | off | resolving objective/context |
| RESPONDING | 0.72 | slow ambient spin | synchronized engraving | substantive answer arriving |
| VERIFYING | 0.48 | slow ambient spin | off | protected verification/finalization |
| COMPLETE | 0.18 | slow ambient spin | off | response settled |
| SPEC_AMENDMENT | 0.22 | slow ambient spin | off | deliberate protected hand-off |
| ERROR | 0.12 | calm/static acceptable | off | recoverable inability to complete |

Reduced motion freezes knot rotation and time-dependent workplane motion.

## Accessibility

- Core narrative text targets WCAG AA contrast against rendered material.
- State is communicated with explicit text/shape in addition to color.
- Minimum 44 pt mobile interaction targets remain required.
- Mobile editable text remains at least 16 CSS px while preserving user-controlled page zoom.
- Keyboard and screen-reader semantics are preserved.
- Reduced motion and reduced graphics remain first-class modes.
- Grain/ambient optical effects may never materially reduce narrative contrast.
- Ambient motion may never obscure narrative text or primary controls.
- Final assistant text remains selectable regardless of whether animated engraving was used during generation.
- Automatic conversation following must respect deliberate operator scroll-away.
