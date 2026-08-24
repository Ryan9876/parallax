from pathlib import Path

path = Path('services/api/parallax_api/code/live_observability.py')
text = path.read_text(encoding='utf-8')

anchor = '_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,199}$")\n'
addition = '''_SECRET_EXCERPT_PATTERNS = (\n    re.compile(\n        r"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|authorization|cookie|credential)"\n        r"\\s*[:=]\\s*[\\\"\\\']?[^\\s,\\\"\\\']{8,}"\n    ),\n    re.compile(r"(?i)\\bbearer\\s+[A-Za-z0-9._~+/=-]{8,}"),\n    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),\n)\n_PRIVATE_REASONING_EXCERPT_TERMS = (\n    "chain_of_thought",\n    "chain-of-thought",\n    "scratchpad",\n    "hidden_reasoning",\n    "hidden-reasoning",\n    "internal_reasoning",\n    "internal-reasoning",\n)\n'''
if addition not in text:
    if anchor not in text:
        raise SystemExit('secret-pattern anchor missing')
    text = text.replace(anchor, anchor + addition)

old = '''def _safe_excerpt(value: object) -> tuple[str | None, bool]:\n    if not isinstance(value, str):\n        return None, False\n    candidate = value[:MAX_EVIDENCE_EXCERPT]\n    truncated = len(candidate) != len(value)\n    if security_findings({"excerpt": candidate}):\n        return "[REDACTED]", True\n    return candidate, truncated\n'''
new = '''def _safe_excerpt(value: object) -> tuple[str | None, bool]:\n    if not isinstance(value, str):\n        return None, False\n    candidate = value[:MAX_EVIDENCE_EXCERPT]\n    truncated = len(candidate) != len(value)\n    lowered = candidate.casefold()\n    if (\n        any(pattern.search(candidate) for pattern in _SECRET_EXCERPT_PATTERNS)\n        or any(term in lowered for term in _PRIVATE_REASONING_EXCERPT_TERMS)\n        or security_findings({"excerpt": candidate})\n    ):\n        return "[REDACTED]", True\n    return candidate, truncated\n'''
if old not in text:
    raise SystemExit('safe excerpt function anchor missing')
text = text.replace(old, new)
path.write_text(text, encoding='utf-8')
