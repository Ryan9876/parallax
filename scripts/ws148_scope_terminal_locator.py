from pathlib import Path

path = Path('apps/client/scripts/live-build-smoke.mjs')
text = path.read_text(encoding='utf-8')
old = "  await desktop.getByText('python-compile', { exact: false }).waitFor();\n"
new = "  await desktop.getByText('python-compile', { exact: true }).waitFor();\n"
if old not in text:
    raise SystemExit('expected Terminal tool locator not found')
path.write_text(text.replace(old, new), encoding='utf-8')
