from pathlib import Path

app = Path('apps/client/src/App.tsx')
text = app.read_text(encoding='utf-8')
anchor = "  navRowActive: { backgroundColor: palette.rust600 },\n"
addition = "  navRowDormant: { opacity: 0.68 },\n  navTextDormant: { color: '#AEB79A' },\n"
if addition not in text:
    if anchor not in text:
        raise SystemExit('App nav style anchor missing')
    text = text.replace(anchor, anchor + addition)
app.write_text(text, encoding='utf-8')

workspace = Path('apps/client/src/components/observability/LiveBuildWorkspace.tsx')
text = workspace.read_text(encoding='utf-8')
text = text.replace("observer.view.events[observer.view.events.length - 1].sequence", "observer.view.events.at(-1)?.sequence ?? '—'")
text = text.replace('palette.charcoal700', 'palette.charcoal800')
workspace.write_text(text, encoding='utf-8')

stream = Path('apps/client/src/components/observability/RunEventStream.tsx')
text = stream.read_text(encoding='utf-8')
text = text.replace("events[events.length - 1].sequence", "events.at(-1)?.sequence ?? '—'")
stream.write_text(text, encoding='utf-8')

projection = Path('apps/client/src/lib/observabilityProjection.ts')
text = projection.read_text(encoding='utf-8')
old = "    const event = events[index];\n    if (event.source_lineage_ref) return { candidate: event.source_lineage_ref, parent: event.parent_source_lineage_ref };\n"
new = "    const event = events[index];\n    if (!event) continue;\n    if (event.source_lineage_ref) return { candidate: event.source_lineage_ref, parent: event.parent_source_lineage_ref };\n"
if old not in text:
    raise SystemExit('projection strict-index anchor missing')
text = text.replace(old, new)
projection.write_text(text, encoding='utf-8')
