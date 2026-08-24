from pathlib import Path

path = Path('apps/client/scripts/live-build-smoke.mjs')
text = path.read_text(encoding='utf-8')
old = "  await desktop.getByText('Operator review required before completion.').waitFor({ timeout: 8000 });\n"
new = "  await desktop.getByTestId('run-event-11').getByText('Operator review required before completion.').waitFor({ timeout: 8000 });\n"
if old not in text:
    raise SystemExit('expected Live Build REVIEW locator not found')
path.write_text(text.replace(old, new), encoding='utf-8')
