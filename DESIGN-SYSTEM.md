# Parallax 2.0 Design System

Version: 1.5
Status: Authoritative

## Design direction

Parallax is a premium optical reasoning and engineering workspace. Conversation remains the primary product surface; the interface should feel quiet at rest and visibly alive only when intelligence is working.

The v0.6.3 baseline establishes the **Deep Violet Optical** system. It replaces the prior light mineral palette with the previously selected dark Parallax direction: deep navy/black substrate, restrained indigo and violet depth, cyan optical energy, translucent dark glass, and high-contrast pale narrative text.

This is not a generic neon-AI theme. Distinction comes from precision, spatial depth, material restraint, and a small number of signature optical behaviors. Saturated color is concentrated in identity, active focus, and response energy rather than spread across every surface.

Content wins every visual competition. Ambient effects must be perceived second, never first. If the living surface, glass treatment, identity color, or response energy attracts attention before the conversation does, its intensity is too high.

Reason 2.0 preserves one durable interaction principle: a material objective change is a calm protected hand-off, not a failure alarm. Visual intensity communicates state without punishing the user for changing direction.

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
- Danger: `#FF9AAB`
- Warning: `#E7C98F`
- Verified/success: `#72E3C4`
- Dark glass: `rgba(13,16,29,0.70)`
- Strong glass: `rgba(17,21,37,0.90)`
- Optical border: `rgba(167,151,255,0.18)`

The cyan → indigo → violet family is hierarchical rather than decorative:

- cyan = active optical energy, send/focus detail, live renderer;
- indigo = precision structure, status metadata, secondary active framing;
- violet = identity, selected state, and primary product atmosphere.

Purple must not become the sole carrier of semantic status.

## Optical workplane

The living surface is an optical workplane, not a decorative fluid background or HUD.

- Use a deep navy substrate with broad, low-frequency violet/indigo drift.
- Sparse topographic isolines provide a unique spatial signature.
- A nearly invisible drafting grid provides scale and orientation.
- One slow optical focus region may become slightly more apparent while intelligence is active.
- A restrained violet calibration trace keeps the field from collapsing into generic blue SaaS styling.
- Motion stays below readable content and never creates high-frequency shimmer.
- Reduced motion freezes the field without changing semantic state.
- At idle, isolines, grid, focus ring, and calibration trace remain near the threshold of perception.
- Increased response-state energy may raise the optical focus slightly, but must not materially raise full-screen contrast.
- The conversation stage maintains a dark center bias so copy is always the dominant visual layer.

The surface is atmosphere and spatial reference, not content.

## Optical typesetter

The active assistant response is inscribed by a precise optical head:

- head moves left-to-right through the active line;
- text is revealed at the head position;
- fresh glyphs carry a short lavender/cyan energy edge;
- glyphs cool quickly to normal pale text;
- the beam disappears when complete;
- final text remains selectable and accessible.

The optical typesetter represents substantive generated response content. It does not run for a `SPEC_AMENDMENT` hand-off that intentionally stops substantive continuation.

Reduced motion disables the beam and reveals substantive response text normally.

## Specification-amendment state

`SPEC_AMENDMENT` is a first-class product state with its own visual semantics:

- preserve the conversation and user request in place;
- show the concise amendment-required message in the normal conversation flow;
- use restrained indigo/neutral treatment rather than red error treatment;
- keep the living surface close to idle energy;
- laser remains off because no substantive answer is being inscribed;
- do not shake, flash, pulse aggressively, or imply system malfunction;
- retain the normal composer and navigation so the state feels recoverable;
- reduced-motion and reduced-graphics presentations communicate the same semantics in static form.

The visual message is: **the objective boundary changed and Parallax stopped deliberately**.

## Recoverable error state

`ERROR` is reserved for actual inability to complete the requested response, such as protected provider/validation exhaustion or unavailable required context. It remains visually quieter than destructive-failure UI because durable conversation is preserved.

User-facing error text should prefer the server-provided sanitized recovery message. Technical provider exceptions, secret-bearing diagnostics, candidate output, and hidden reasoning are never rendered as product copy.

## Parallax mark

The representative identity is the **Parallax Optical Mark**:

- one stable outer optical boundary around a centered intelligence lens;
- cyan outer optical energy, indigo inner structure, and violet aperture gesture;
- one directional aperture gesture rather than orbital loops or spinner geometry;
- a small cyan focus point may shift only a few pixels over a slow cycle;
- no continuous rotation, orbiting particles, scanner crosshairs, or decorative HUD behavior;
- the mark must remain legible at sidebar scale before it is allowed to become more expressive at larger sizes;
- reduced motion uses the centered static mark.

The mark should feel like an instrument symbol that belongs to Parallax, not a generic AI glyph.

## Typography

Use system-native sans-serif typography in the foundation build. Prioritize legibility and rendering reliability over custom-font identity until the product shell is stable.

Primary narrative text is pale violet-white rather than pure white to reduce glare against the dark substrate. Secondary copy and metadata step down through lavender-gray values while retaining accessible contrast.

All final assistant text remains normal selectable/accessibility-aware text. Motion must not become the only way state or content is communicated.

## Layout and material separation

Conversation remains primary. Wide layouts may show a recent-conversation rail; mobile collapses that rail. The assistant response surface may use dark glass separation but should not become a card-heavy dashboard.

Use visible chrome sparingly. Hierarchy should come from typography, spacing, optical alignment, and material separation before introducing additional cards or controls.

Response surfaces should read as part of a continuous precision workspace rather than independent chat bubbles. User content may retain a contained strong-glass surface; assistant content uses flatter dark glass with violet/indigo optical edge treatment and a stronger reading rhythm.

The active conversation's durable `spec_id` may be shown as quiet metadata. Never hard-code a stale release label into the visible shell; historical conversations must remain capable of displaying their own stored specification identity.

Private production begins with a restrained access surface using the same deep substrate, dark glass, Parallax mark, typography, and violet action color. It asks only for the operator credential, uses normal accessible form semantics, and does not expose technical authentication detail. The full conversation shell appears only after access is accepted.

## Reduced-graphics parity

The non-Skia fallback is not a separate visual product. It uses the same Deep Violet Optical palette, identity hierarchy, dark glass, readable copy, mode controls, conversation layout, and composer semantics without depending on animated graphics.

A user who selects or requires reduced graphics should lose decorative rendering cost, not product identity, content, state information, or capability.

## Motion state mapping

| Response state | Surface energy | Logo | Laser | Meaning |
| --- | ---: | --- | --- | --- |
| IDLE | 0.18 | calm | off | ready |
| THINKING | 0.42 | calm | off | resolving objective/context |
| RESPONDING | 0.72 | calm | active | substantive answer arriving |
| VERIFYING | 0.48 | calm | off | protected verification/finalization |
| COMPLETE | 0.18 | calm | off | response settled |
| SPEC_AMENDMENT | 0.22 | calm | off | deliberate protected hand-off |
| ERROR | 0.12 | static/calm | off | recoverable inability to complete |

All motion respects system reduced-motion preferences. Reduced-graphics mode preserves the same semantic states without depending on Skia or CanvasKit.

## Accessibility

- Core narrative text targets WCAG AA contrast against its rendered dark surface.
- State is communicated with text/shape in addition to color.
- 44 pt minimum mobile interaction targets remain required.
- Keyboard and screen-reader semantics are preserved.
- Reduced motion and reduced graphics remain first-class modes.
- Glows and translucent layers may be reduced where contrast requires it.
- Ambient violet/cyan effects may never lower the contrast of narrative text.
