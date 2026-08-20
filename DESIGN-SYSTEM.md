# Parallax 2.0 Design System

Version: 1.0
Status: Authoritative

## Design direction

P2 evolves the calmer P1 visual language instead of replacing it with dashboard or editorial experimentation. The product should feel like a premium optical instrument: quiet at rest, visibly alive only when intelligence is working.

## Material palette

- Mineral canvas: `#F4F3EE`
- Ink: `#20282B`
- Restrained optical blue: `#147D9F`
- Laser core: `#D8F9FF`
- Laser energy: `#54D8FF`
- Smoke glass: `rgba(214,220,219,0.28)`
- Soft peach undertone: `#DEC5B6`
- Muted yellow-green undertone: `#C2CAAF`
- Secondary metadata: soft peach/brown family rather than cool gray where appropriate.

## Living surface

The first P2 motion baseline uses a slow mineral/pearl interference field:

- large low-frequency waves;
- restrained teal, peach, and yellow-green mixing;
- sparse caustic highlights;
- low amplitude at idle;
- moderately increased energy during THINKING and RESPONDING;
- no high-frequency noise behind readable text.

The surface is atmosphere, not content.

## Optical typesetter

The active assistant response is inscribed by a precise optical head:

- head moves left-to-right through the active line;
- text is revealed at the head position;
- fresh glyphs carry a short cool-blue energy edge;
- glyphs cool quickly to normal ink;
- the beam disappears when complete;
- final text remains selectable and accessible.

Reduced motion disables the beam and reveals text normally.

## Parallax mark

The representative logo is the **Parallax Lens Mark**:

- two thin, offset optical planes/lenses around one stable center point;
- planes drift by only a few pixels over a 7–9 second cycle;
- they approach near-alignment, then separate again;
- a restrained center glint appears near alignment;
- no continuous rotation and no spinner behavior;
- reduced motion uses the centered static mark.

The mark communicates the product name literally: a change in viewpoint creates a perceptible shift while the reference center remains stable.

## Typography

Use system-native sans-serif typography in the foundation build. Prioritize legibility and rendering reliability over custom-font identity until the product shell is stable.

## Layout

Conversation remains primary. Wide layouts may show a recent-conversation rail; mobile collapses that rail. The assistant response surface may use glass separation but should not become a card-heavy dashboard.

## Motion state mapping

| Response state | Surface energy | Logo | Laser |
| --- | ---: | --- | --- |
| IDLE | 0.18 | calm | off |
| THINKING | 0.42 | calm | off |
| RESPONDING | 0.72 | calm | active |
| VERIFYING | 0.48 | calm | off |
| COMPLETE | 0.18 | calm | off |
| ERROR | 0.12 | static/calm | off |

All motion respects system reduced-motion preferences.
