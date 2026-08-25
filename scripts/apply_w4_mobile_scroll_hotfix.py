from pathlib import Path

path = Path('apps/client/src/App.tsx')
text = path.read_text(encoding='utf-8')

context_start = '                <View style={styles.governedContext}>'
scroll_start = '                <ScrollView\n                  ref={threadRef}'
scroll_open = '                  scrollEventThrottle={32}\n                >\n'

start = text.index(context_start)
scroll = text.index(scroll_start, start)
context_block = text[start:scroll].rstrip()

wrapped_desktop = (
    '                {!compact ? (\n'
    + context_block
    + '\n                ) : null}\n\n'
)
text = text[:start] + wrapped_desktop + text[scroll:]

insert_at = text.index(scroll_open, start) + len(scroll_open)
compact_block = (
    '                  {compact ? (\n'
    + context_block
    + '\n                  ) : null}\n'
)
text = text[:insert_at] + compact_block + text[insert_at:]

if text.count('<View style={styles.governedContext}>') != 2:
    raise SystemExit('expected exactly two governedContext render sites after correction')
if '{!compact ? (' not in text or '{compact ? (' not in text:
    raise SystemExit('compact/desktop governed-context split was not applied')

path.write_text(text, encoding='utf-8')
