# Parallax 2.0 Design System

Version: 1.3
Status: Authoritative

## Design direction

P2 evolves the calmer P1 visual language instead of replacing it with dashboard or editorial experimentation. The product should feel like a premium optical instrument: quiet at rest, visibly alive only when intelligence is working.

Reason 2.0 adds one durable interaction principle: a material objective change is treated as a calm protected hand-off, not as a failure alarm. Visual intensity must communicate system state without punishing the user for changing direction.

The v0.6 visual refinement rejects generic AI-neon and generic SaaS-glass aesthetics. Parallax should read as **high-end industrial design software + calm intelligence + optical instrumentation**. Distinction comes from precision, material restraint, spatial depth, and one or two signature behaviors rather than decorative effects.

## Material palette

- Mineral canvas: `#F4F3EE`
- Warm optical paper: `#F7F4EC`
- Ink: `#20282B`
- Restrained optical blue: `#147D9F`
- Laser core: `#D8F9FF`
- Laser energy: `#54D8FF`
- Smoke glass: `rgba(214,220,219,0.28)`
- Soft peach undertone: `#DEC5B6`
- Muted yellow-green undertone: `#C2CAAF`
- Secondary metadata: soft peach/brown family rather than cool gray where appropriate.

## Optical workplane

The living surface is an optical workplane, not a decorative fluid background.

- Use a warm mineral substrate with broad, low-frequency drift.
- Sparse topographic isolines provide a unique spatial signature.
- A nearly invisible drafting grid may provide scale and orientation.
- One slow optical focus region may become slightly more apparent while intelligence is active.
- A warm calibration trace prevents the interface from collapsing into generic blue SaaS styling.
- Motion stays below readable content and never creates high-frequency shimmer.
- Reduced motion freezes the field without changing the semantic state.

The surface is atmosphere and spatial reference, not content.

## Optical typesetter

The active assistant response is inscribed by a precise optical head:

- head moves left-to-right through the active line;
- text is revealed at the head position;
- fresh glyphs carry a short cool-blue energy edge;
- glyphs cool quickly to normal ink;
- the beam disappears when complete;
- final text remains selectable and accessible.

The optical typesetter represents substantive generated response content. It does not run for a `SPEC_AMENDMENT` hand-off that intentionally stops substantive continuation.

Reduced motion disables the beam and reveals substantive response text normally.

## Specification-amendment state

`SPEC_AMENDMENT` is a first-class product state with its own visual semantics:

- preserve the conversation and user request in place;
- show the concise amendment-required message in the normal conversation flow;
- use restrained neutral/optical treatment rather than red error treatment;
- keep the living surface close to idle energy;
- laser remains off because no substantive answer is being inscribed;
- do not shake, flash, pulse aggressively, or imply system malfunction;
- retain the normal composer and navigation so the state feels recoverable;
- reduced-motion and reduced-graphics presentations communicate the same semantics in static form.

The visual message is: **the objective boundary changed and Parallax stopped deliberately**.

## Recoverable error state

`ERROR` is reserved for actual inability to complete the requested response, such as protected provider/validation exhaustion or unavailable required context. It should remain visually quieter than destructive-failure UI because the durable conversation is preserved.

User-facing error text should prefer the server-provided sanitized recovery message. Technical provider exceptions, secret-bearing diagnostics, candidate output, and hidden reasoning are never rendered as product copy.

## Parallax mark

The representative logo is the **Parallax Aperture Mark**:

- one geometric aperture around a stable reference center;
- restrained horizontal and vertical calibration axes;
- a single measurement point drifts only a few pixels over a slow cycle;
- no continuous rotation, orbital loops, or spinner behavior;
- reduced motion uses the centered static mark.

The mark should feel like an instrument calibration symbol rather than an AI-logo trope.

## Typography

Use system-native sans-serif typography in the foundation build. Prioritize legibility and rendering reliability over custom-font identity until the product shell is stable.

All final assistant text remains normal selectable/accessibility-aware text. Motion must not become the only way state or content is communicated.

## Layout

Conversation remains primary. Wide layouts may show a recent-conversation rail; mobile collapses that rail. The assistant response surface may use glass separation but should not become a card-heavy dashboard.

Use visible chrome sparingly. Hierarchy should come from typography, spacing, optical alignment, and material separation before introducing additional cards or controls.

The active conversation's durable `spec_id` may be shown as quiet metadata. Never hard-code a stale release label into the visible shell; historical conversations must remain capable of displaying their own stored specification identity.

Private production begins with a restrained access surface using the same mineral canvas, Parallax mark, typography, and optical-blue action color. It asks only for the operator credential, uses normal accessible form semantics, and does not expose technical authentication detail. The full conversation shell appears only after access is accepted.

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
