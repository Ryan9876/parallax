from pathlib import Path

# DESIGN-SYSTEM: accepted durable visual contract is now integrated.
design = Path('DESIGN-SYSTEM.md')
text = design.read_text(encoding='utf-8')
text = text.replace('Status: Authoritative candidate under `P2-V0.17.0` until integrated', 'Status: Authoritative')
design.write_text(text, encoding='utf-8')

# ARCHITECTURE: source-integrated client surface is no longer future work, but
# production activation remains explicitly migration-gated until release proof.
arch = Path('ARCHITECTURE.md')
text = arch.read_text(encoding='utf-8')
text = text.replace('Version: 2.8', 'Version: 2.9', 1)
text = text.replace('  └─ bounded API / future live-observation client', '  └─ bounded API + governed Live Build / observability client')
text = text.replace('  └─ optional Wave 4 non-authoritative run-event projection', '  └─ migration-gated Wave 4 non-authoritative run-event projection')
arch.write_text(text, encoding='utf-8')

# CURRENT-STATE: record the exact pre-production Wave 4 release-candidate state.
state = Path('CURRENT-STATE.md')
text = state.read_text(encoding='utf-8')
text = text.replace(
    'Release: Wave 3 production app-builder runtime with bootstrap hardening; Wave 4 run-event and live-observation source integration in progress',
    'Release: Wave 3 production app-builder runtime remains deployment-verified; Wave 4 Live Development release candidate is source-integrated and under final production promotion validation',
    1,
)
text = text.replace(
    'Status: **WAVE 3 PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED THROUGH P2-V0.16.5; AUTONOMOUS SOURCE BOOTSTRAP REGRESSION RESOLVED; WAVE 4 RUN-EVENT + LIVE-OBSERVATION SOURCE INTEGRATED BUT MIGRATION UNAPPLIED / TELEMETRY AND READ SURFACE INACTIVE; SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**',
    'Status: **WAVE 3 PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED THROUGH P2-V0.16.5; WAVE 4 P2-V0.17.0–P2-V0.17.4 SOURCE-INTEGRATED ON MAIN; P2-V0.17.5 RELEASE PROOF ACTIVE; PRODUCTION RUN-EVENT MIGRATION UNAPPLIED / ACTIVATION OFF / WAVE 4 NOT YET DEPLOYMENT-VERIFIED; SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**',
    1,
)
old_intro = 'The Wave 3 protected app-builder runtime remains the deployed execution architecture through `P2-V0.16.5`. Wave 4 source work is being developed separately and is not implicitly activated by this production release.'
new_intro = '''The Wave 3 protected app-builder runtime remains the deployment-verified production execution architecture through `P2-V0.16.5`. Wave 4 source through `P2-V0.17.4` is integrated on repository `main@22fa4f34b617bceafe5b6a0ad7cf520af2c7c403`, including the Warm Editorial shell and governed Live Build/Observability client, but those facts do not by themselves establish production activation or deployment. `P2-V0.17.5` is the final integrated release-proof boundary.'''
text = text.replace(old_intro, new_intro, 1)

old_wave4 = '''Wave 4 durable run-event telemetry (`P2-V0.17.1`, issue #145) and resumable live transport/protected reads (`P2-V0.17.2`, issue #146) are **source integrated but not production activated**.'''
new_wave4 = '''Wave 4 experience/design, durable run-event telemetry, resumable transport/protected reads, Warm Editorial shell and Live Build/Observability workspace (`P2-V0.17.0` through `P2-V0.17.4`, issues #144–#148) are **source integrated but not yet production migration/activation/deployment verified**. `P2-V0.17.5` / #149 is the active integrated reference-proof and release boundary.'''
text = text.replace(old_wave4, new_wave4, 1)
text = text.replace('- Wave 4 client Live Build UI: **NOT DEPLOYED**.', '- Wave 4 client Live Build UI source integrated on `main`: **YES**; production deployment verified: **NO**.', 1)

old_active = '''## Active parallel work

Wave 4 work continues on isolated workstreams. At this record update:

- #145 / `P2-V0.17.1` run-event telemetry source is integrated but inactive as described above;
- #146 / `P2-V0.17.2` live transport and protected reads is integrated on `main` at merge `ee5b55ebcf3a6da14dfb2233cb69ed9dedee774f`, but remains inactive and undeployed;
- #147 / `P2-V0.17.3` warm editorial application shell is the next planned implementation slice;
- #148 / `P2-V0.17.4` Live Build/Observability workspace remains dependent on the accepted shell and integrated transport;
- #149 / `P2-V0.17.5` remains the integrated reference proof/release boundary;
- no Wave 4 migration or production activation was performed by the #146 integration.

Parallel workers must reconcile against current `main` before integration and rerun the applicable cumulative protected gates after material composition changes.'''
new_active = '''## Active Wave 4 release work

Wave 4 implementation workstreams #144–#148 are integrated. Current release facts:

- #144 / `P2-V0.17.0`: experience/design contract integrated;
- #145 / `P2-V0.17.1`: durable run-event projection integrated, production activation still off;
- #146 / `P2-V0.17.2`: resumable SSE and protected source/diff/evidence reads integrated;
- #147 / `P2-V0.17.3`: Warm Editorial application shell integrated;
- #148 / `P2-V0.17.4`: governed Live Build/Observability workspace integrated on `main` at `22fa4f34b617bceafe5b6a0ad7cf520af2c7c403` after exact-head protected gates;
- #149 / `P2-V0.17.5`: active final integrated reference proof and release boundary; authentic DSPy plan is committed and the permanent reference proof now exercises durable failed TEST evidence, bounded autonomous correction to a fresh immutable lineage, exact-lineage observation/diff, REVIEW/HUMAN_REQUIRED and explicit operator completion;
- the #149 reference proof identified and fixed an observability privacy gap so secret/private-reasoning-like command excerpts are redacted at the protected read boundary;
- production `engineering_run_events` migration applied: **NO**;
- production `PARALLAX_RUN_EVENTS_ENABLED=1`: **NO**;
- Wave 4 production deployment verified: **NO**.

The final release candidate must still pass the full exact-head release-mode P2 CI, browser/Skia, protected promotion evaluation, DSPy, Bounded Autonomy and migration-readiness gates before any production migration or activation occurs.'''
if old_active not in text:
    raise SystemExit('CURRENT-STATE active work anchor missing')
text = text.replace(old_active, new_active, 1)
state.write_text(text, encoding='utf-8')
