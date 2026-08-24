from pathlib import Path

path = Path('apps/client/scripts/live-build-smoke.mjs')
text = path.read_text(encoding='utf-8')
replacements = {
    "  await desktop.getByText('GITHUB', { exact: true }).waitFor();\n": "  await desktop.getByText('GitHub', { exact: true }).waitFor();\n",
    "  await desktop.getByText('VERCEL', { exact: true }).waitFor();\n": "  await desktop.getByText('Vercel', { exact: true }).waitFor();\n",
    "  await desktop.getByText('165', { exact: false }).first().waitFor();\n": "  await desktop.getByText('PR #165', { exact: true }).waitFor();\n  await desktop.getByText(/preview-wave4-165/).waitFor();\n",
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f'expected provider evidence locator not found: {old.strip()}')
    text = text.replace(old, new)
path.write_text(text, encoding='utf-8')
