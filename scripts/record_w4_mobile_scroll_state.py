from pathlib import Path

path = Path('CURRENT-STATE.md')
text = path.read_text(encoding='utf-8')

old_release = (
    'Release: Wave 4 Live Development stabilization is deployment-verified. The production API/runtime recovery is complete, '
    'the Warm Editorial client stabilization remains deployed, and a fresh real Project-bound autonomous production proof advanced '
    'through protected IMPLEMENT/BUILD/TEST/VERIFY to the explicit REVIEW/HUMAN_REQUIRED boundary with persisted exact-lineage GitHub/Vercel Preview delivery evidence.'
)
new_release = old_release + ' A deployment-verified mobile governed-context scroll hotfix now keeps approved Work Specification and active Engineering Run surfaces reachable on narrow viewports while preserving the fixed composer.'
text = text.replace(old_release, new_release, 1)

old_status = 'Status: **WAVE 4 PRODUCTION DEPLOYED / LIVE OBSERVABILITY ACTIVE / STABILIZATION VERIFIED / END-TO-END AUTONOMOUS PRODUCTION READINESS RESTORED / HUMAN REVIEW BOUNDARY PRESERVED / PREVIOUS API RELEASE RETAINED AS ROLLBACK CANDIDATE / SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**'
new_status = 'Status: **WAVE 4 PRODUCTION DEPLOYED / MOBILE GOVERNED-CONTEXT SCROLL HOTFIX DEPLOYED / LIVE OBSERVABILITY ACTIVE / STABILIZATION VERIFIED / END-TO-END AUTONOMOUS PRODUCTION READINESS RESTORED / HUMAN REVIEW BOUNDARY PRESERVED / PREVIOUS API AND CLIENT RELEASES RETAINED AS ROLLBACK CANDIDATES / SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**'
text = text.replace(old_status, new_status, 1)

old_client = (
    'The production client remains Vercel deployment `dpl_AHKAix8J11knSfSCRzCupM6ND7vn` from `main@f61ba4f65ea108994dbda8f507bf079fac534145`, '
    'the Wave 4 stabilization promotion containing the validated #170-#174 visual/runtime convergence package. It is `READY` and owns the production aliases '
    '`parallax-lew7.vercel.app`, `parallax-ashy-one-20.vercel.app`, and `parallax-git-main-lew7.vercel.app`. Later recovery commits were API-only and were correctly ignored by the client project rather than replacing the deployed visual stabilization.'
)
new_client = (
    'The deployment-verified production client is Vercel deployment `dpl_6xVHMhcdyrbb8SwSahGSuw5DLLiY` from `main@7e10b6d492361b2a8d046672b5bcd331d44172b3` (PR #225, mobile governed-context scroll recovery). '
    'It is `READY`, has no alias error, and currently owns `parallax-lew7.vercel.app`, `parallax-ashy-one-20.vercel.app`, and `parallax-git-main-lew7.vercel.app`. '
    'This hotfix is layered on the previously validated Wave 4 #170-#174 visual/runtime convergence package and changes only the compact conversation scroll composition plus its permanent browser regression gate.'
)
text = text.replace(old_client, new_client, 1)

old_rollback = (
    'The immediately preceding known-good API production deployment `dpl_LYTeixMa2rfWDatzeSRL6wBAuaXj` from `main@d9069d264d7ca47e831634c663890abf7ee02da8` remains identified by Vercel as a rollback candidate. '
    'Routine rollback remains non-destructive and follows the existing flag-first/application-deployment policy.'
)
new_rollback = old_rollback + (
    '\n\nThe immediately preceding known-good client production deployment `dpl_AHKAix8J11knSfSCRzCupM6ND7vn` from `main@f61ba4f65ea108994dbda8f507bf079fac534145` remains the client rollback point for this hotfix.'
)
text = text.replace(old_rollback, new_rollback, 1)

marker = '## Wave 4 stabilization and recovery outcome\n'
hotfix = '''## Wave 4 mobile governed-context scroll hotfix\n\nUser acceptance testing on an iPhone exposed a narrow-layout defect after Wave 4 closeout: an approved Work Specification and active Engineering Run were rendered in a fixed `governedContext` above the only conversation `ScrollView`. When those governed surfaces exceeded the phone viewport, the conversation scroll area collapsed and the user could not reach the lower execution controls or conversation content.\n\nIssue #224 / PR #225 corrected the compact composition without changing runtime semantics: on mobile, the existing Work Specification + Engineering Run governed context is now the first content inside the existing conversation scroll surface, while the composer remains outside that surface and fixed in place. Non-compact desktop/tablet composition, Projects, Observability, authentication, provider authority, execution authority and API behavior are unchanged.\n\nPermanent regression coverage `mobile-governed-scroll-smoke.mjs` now renders a 390x844 Project-bound Code conversation with an APPROVED Work Specification and active `IMPLEMENT` Engineering Run. It verifies that the execution surface has a meaningful vertical scroll ancestor, lower execution controls are reachable after scrolling, the composer remains position-stable, and no browser errors occur. This case is part of the standard `test:visual` browser/Skia suite.\n\nExact candidate `51e7cfcf47b927da66624118fed11b9b8911af38` passed Parallax P2 CI #880, Bounded Autonomy #530, the browser/Skia suite including the new regression, protected promotion evaluation, release DSPy, and both Vercel Preview checks before expected-head squash merge. Production client deployment `dpl_6xVHMhcdyrbb8SwSahGSuw5DLLiY` then reached `READY` on exact merge SHA `7e10b6d492361b2a8d046672b5bcd331d44172b3`; the exact user-observed alias `parallax-ashy-one-20.vercel.app` resolves to that deployment, an authenticated deployment fetch returned HTTP 200, and the deployment-scoped `error`/`fatal` log query returned no entries.\n\n'''
if marker not in text:
    raise SystemExit('state marker not found')
text = text.replace(marker, hotfix + marker, 1)

activation_marker = '- Warm Editorial stabilization client deployed: **YES**;'
activation_new = activation_marker + '\n- mobile governed-context scroll hotfix deployed and active-run regression gate present: **YES / DEPLOYMENT-VERIFIED**;'
text = text.replace(activation_marker, activation_new, 1)

old_design = '`DESIGN-SYSTEM.md` remains authoritative for the Warm Editorial Observatory design direction. No design-system change was required during the final runtime-recovery proof closeout; the deployed client already corresponds to the validated Wave 4 stabilization promotion.'
new_design = '`DESIGN-SYSTEM.md` remains authoritative for the Warm Editorial Observatory design direction. No design-system change was required for the mobile scroll hotfix: it restores the already-required intentional mobile usability/composition behavior rather than introducing a new visual language or durable design rule.'
text = text.replace(old_design, new_design, 1)

required = [
    'dpl_6xVHMhcdyrbb8SwSahGSuw5DLLiY',
    '7e10b6d492361b2a8d046672b5bcd331d44172b3',
    'mobile-governed-scroll-smoke.mjs',
    'dpl_AHKAix8J11knSfSCRzCupM6ND7vn',
]
if not all(item in text for item in required):
    raise SystemExit('required hotfix evidence missing from reconciled state')

path.write_text(text, encoding='utf-8')
