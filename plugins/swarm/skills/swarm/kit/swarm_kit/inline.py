"""Inline Markdown (**bold**, *italic*, `code`, [text](url)) shared by decks and documents."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

_TOKEN = re.compile(
    r"(\*\*(?P<b>.+?)\*\*)"
    r"|(__(?P<b2>.+?)__)"
    r"|(?<![\w*])\*(?P<i>[^*\s][^*]*?)\*(?![\w*])"
    r"|(?<![\w_])_(?P<i2>[^_\s][^_]*?)_(?![\w_])"
    r"|(`(?P<c>[^`]+)`)"
    r"|(\[(?P<lt>[^\]]+)\]\((?P<lu>[^)\s]+)\))"
)


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    code: bool = False
    link: str | None = None


def parse(text: str, bold: bool = False, italic: bool = False) -> list[Run]:
    runs: list[Run] = []
    pos = 0
    for m in _TOKEN.finditer(text):
        if m.start() > pos:
            runs.append(Run(text[pos:m.start()], bold, italic))
        if m.group("b") is not None or m.group("b2") is not None:
            runs += parse(m.group("b") or m.group("b2"), True, italic)
        elif m.group("i") is not None or m.group("i2") is not None:
            runs += parse(m.group("i") or m.group("i2"), bold, True)
        elif m.group("c") is not None:
            runs.append(Run(m.group("c"), bold, italic, code=True))
        else:
            for inner in parse(m.group("lt"), bold, italic):
                inner.link = m.group("lu")
                runs.append(inner)
        pos = m.end()
    if pos < len(text):
        runs.append(Run(text[pos:], bold, italic))
    return [r for r in runs if r.text]


def plain(text: str) -> str:
    return "".join(r.text for r in parse(text))


def to_html(text: str) -> str:
    out = []
    for r in parse(text):
        piece = html.escape(r.text)
        if r.code:
            piece = f"<code>{piece}</code>"
        if r.italic:
            piece = f"<em>{piece}</em>"
        if r.bold:
            piece = f"<strong>{piece}</strong>"
        if r.link:
            piece = f'<a href="{html.escape(r.link, quote=True)}">{piece}</a>'
        out.append(piece)
    return "".join(out)
