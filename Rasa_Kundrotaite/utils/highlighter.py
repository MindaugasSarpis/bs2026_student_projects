import html

_COLORS = ["hl-0", "hl-1", "hl-2", "hl-3", "hl-4"]


def highlight_text(text: str, spans: list[str]) -> str:
    """Highlight obligation spans inside chunk text for HTML rendering"""
    if not spans:
        return f"<p>{html.escape(text)}</p>"

    matches: list[tuple[int, int, int]] = []
    for color_idx, span in enumerate(spans):
        if not span:
            continue
        pos = text.find(span)
        if pos == -1:
            lower_text = text.lower()
            lower_span = span.lower()
            pos = lower_text.find(lower_span)
        if pos != -1:
            matches.append((pos, pos + len(span), color_idx % len(_COLORS)))

    if not matches:
        return f"<p>{html.escape(text)}</p>"

    matches.sort(key=lambda x: x[0])
    non_overlapping: list[tuple[int, int, int]] = []
    last_end = 0
    for start, end, cidx in matches:
        if start >= last_end:
            non_overlapping.append((start, end, cidx))
            last_end = end

    parts: list[str] = []
    cursor = 0
    for start, end, cidx in non_overlapping:
        if cursor < start:
            parts.append(html.escape(text[cursor:start]))
        snippet = html.escape(text[start:end])
        parts.append(f'<mark class="{_COLORS[cidx]}">{snippet}</mark>')
        cursor = end
    if cursor < len(text):
        parts.append(html.escape(text[cursor:]))

    inner = "".join(parts)
    inner = inner.replace("\n\n", "</p><p>").replace("\n", "<br>")
    return f"<p>{inner}</p>"
