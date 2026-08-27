"""마크다운 텍스트를 문서 모델로 바꾼다.

빈 줄로 블록을 나누고 첫 줄로 종류를 정한다. 코드 펜스 안은 통째로 code 다. 제목은 빈 줄 없이 문단에
붙어 있어도 제 블록이다. H2 가 절을 열고 첫 H2 앞은 도입 절이다.
"""

from __future__ import annotations

import re

from .model import CODE, EMBED, HEADING, HTML, IMAGE, LIST, PROSE, TABLE, Block, Document, Section

FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING_LINE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
IMAGE_LINE = re.compile(r"^!\[")
LIST_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
TABLE_LINE = re.compile(r"^\s*\|")
URL_LINE = re.compile(r"^\s*https?://\S+\s*$")
HTML_LINE = re.compile(r"^\s*<")
META_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
# 인라인 제어. `<!-- hanlint-disable cliche -->` 부터 `<!-- hanlint-enable cliche -->` 까지, 또는 다음 블록 하나.
CONTROL = re.compile(r"^\s*<!--\s*hanlint-(disable-next-line|disable-next|disable|enable)\b([^>]*?)-->\s*$")
ALL_RULES = "*"


def parseFrontmatter(text: str) -> tuple[dict[str, str], int]:
    """frontmatter 를 읽고 본문이 시작하는 줄 번호 (1 부터) 를 함께 준다."""
    match = FRONTMATTER.match(text)
    if not match:
        return {}, 1
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and META_KEY.match(key.strip()):
            meta[key.strip()] = value.strip()
    return meta, match.group(0).count("\n") + 1


def classify(firstLine: str) -> str:
    if HEADING_LINE.match(firstLine):
        return HEADING
    if IMAGE_LINE.match(firstLine):
        return IMAGE
    if TABLE_LINE.match(firstLine):
        return TABLE
    if LIST_LINE.match(firstLine):
        return LIST
    if URL_LINE.match(firstLine):
        return EMBED
    if HTML_LINE.match(firstLine):
        return HTML
    return PROSE


def splitBlocks(text: str, firstLine: int) -> list[Block]:
    blocks: list[Block] = []
    buffer: list[str] = []
    bufferStart = 0
    lineNo = firstLine - 1
    fence: str | None = None
    fenceStart = 0
    fenceLines: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if not buffer:
            return
        kind = classify(buffer[0])
        joined = "\n".join(buffer)
        level = 0
        if kind == HEADING:
            match = HEADING_LINE.match(buffer[0])
            level = len(match.group(1))
            joined = match.group(2)
        blocks.append(Block(kind, bufferStart, bufferStart + len(buffer) - 1, joined, level, len(blocks)))
        buffer = []

    for raw in text.splitlines():
        lineNo += 1
        line = raw.rstrip("\r")
        if fence:
            fenceLines.append(line)
            if FENCE.match(line) and line.strip().startswith(fence):
                blocks.append(Block(CODE, fenceStart, lineNo, "\n".join(fenceLines), 0, len(blocks)))
                fence = None
                fenceLines = []
            continue
        opening = FENCE.match(line)
        if opening:
            flush()
            fence = opening.group(1)
            fenceStart = lineNo
            fenceLines = [line]
            continue
        if not line.strip():
            flush()
            continue
        if CONTROL.match(line):
            # 제어 주석은 빈 줄 없이 문단에 붙어 있어도 제 블록이다. 안 그러면 문단째 html 이 되어 검사에서 빠진다.
            flush()
            blocks.append(Block(HTML, lineNo, lineNo, line, 0, len(blocks)))
            continue
        if HEADING_LINE.match(line) and buffer:
            flush()
        if not buffer:
            bufferStart = lineNo
        buffer.append(line)
        if HEADING_LINE.match(line):
            flush()
    flush()
    if fence:
        # 닫히지 않은 펜스는 코드로 둔다. 닫힘 여부는 이 층의 관심사가 아니다.
        blocks.append(Block(CODE, fenceStart, lineNo, "\n".join(fenceLines), 0, len(blocks)))
    return blocks


def groupSections(blocks: list[Block]) -> list[Section]:
    sections = [Section(None)]
    for block in blocks:
        if block.kind == HEADING and block.level == 2:
            sections.append(Section(block))
            continue
        sections[-1].blocks.append(block)
    return sections


def controlNames(raw: str) -> list[str]:
    names = [name for name in re.split(r"[\s,]+", raw.strip()) if name]
    return names or [ALL_RULES]


def disabledRanges(blocks: list[Block]) -> list[tuple[str, int, int]]:
    """제어 주석이 끈 (규칙, 시작 줄, 끝 줄). disable 은 enable 이나 글 끝까지, disable-next 는 다음 블록 하나."""
    ranges: list[tuple[str, int, int]] = []
    opened: dict[str, int] = {}
    lastLine = blocks[-1].endLine if blocks else 1
    for index, block in enumerate(blocks):
        match = CONTROL.match(block.text) if block.kind == HTML else None
        if not match:
            continue
        action, names = match.group(1), controlNames(match.group(2))
        if action in ("disable-next", "disable-next-line"):
            if index + 1 < len(blocks):
                target = blocks[index + 1]
                ranges.extend((name, target.startLine, target.endLine) for name in names)
        elif action == "disable":
            for name in names:
                opened.setdefault(name, block.startLine)
        else:
            closing = list(opened) if names == [ALL_RULES] else names
            for name in closing:
                if name in opened:
                    ranges.append((name, opened.pop(name), block.endLine))
    ranges.extend((name, start, lastLine) for name, start in opened.items())
    return ranges


def parseMarkdown(text: str, path: str | None = None) -> Document:
    meta, firstLine = parseFrontmatter(text)
    body = text if firstLine == 1 else "\n".join(text.splitlines()[firstLine - 1 :])
    blocks = splitBlocks(body, firstLine)
    return Document(path=path, frontmatter=meta, blocks=blocks, sections=groupSections(blocks), disabled=disabledRanges(blocks))
