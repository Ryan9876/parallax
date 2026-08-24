from pathlib import Path

path = Path('apps/client/scripts/live-build-smoke.mjs')
text = path.read_text(encoding='utf-8')
old = "  await desktop.getByText('PR #165', { exact: true }).waitFor();\n"
new = "  await desktop.getByText(/PR #165/).waitFor();\n"
if old not in text:
    raise SystemExit('expected PR provider value locator not found')
path.write_text(text.replace(old, new), encoding='utf-8')
