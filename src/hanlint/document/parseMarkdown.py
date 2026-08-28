"""마크다운 텍스트를 문서 모델로 바꾼다.

빈 줄로 블록을 나누고 첫 줄로 종류를 정한다. 코드 펜스 안은 통째로 code 다. 제목은 빈 줄 없이 문단에
붙어 있어도 제 블록이다. H2 가 절을 열고 첫 H2 앞은 도입 절이다.
"""

from __future__ import annotations

import re

from .model import CODE, EMBED, HEADING, HTML, IMAGE, LIST, PROSE, QUOTE, TABLE, Block, Document, Section

FRONTMATTER = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
FENCE_OPEN = re.compile(r"^\s*(?:(?P<ticks>`{3,})(?P<tickInfo>[^`]*)|(?P<tildes>~{3,})(?P<tildeInfo>[^~]*))$")
FENCE_CLOSE = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})\s*$")
HEADING_LINE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
INDENTED_CODE_LINE = re.compile(r"^(?: {4}|\t)")
QUOTE_LINE = re.compile(r"^\s*>")
IMAGE_LINE = re.compile(r"^!\[")
LIST_LINE = re.compile(r"^(?P<indent>\s*)(?:[-*+]|\d+[.)])\s+")
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
    if INDENTED_CODE_LINE.match(firstLine):
        return CODE
    if HEADING_LINE.match(firstLine):
        return HEADING
    if QUOTE_LINE.match(firstLine):
        return QUOTE
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


def indentWidth(line: str) -> int:
    """첫 글자 앞 들여쓰기 너비. 탭은 마크다운의 네 칸 탭 정지점으로 센다."""
    width = 0
    for char in line:
        if char == " ":
            width += 1
        elif char == "\t":
            width += 4 - width % 4
        else:
            break
    return width


def afterIndent(line: str, width: int) -> str:
    """들여쓰기 width 칸을 없앤 나머지. 목록 속 문단의 실제 첫 글자를 분류할 때 쓴다."""
    index = 0
    consumed = 0
    while index < len(line) and consumed < width and line[index] in " \t":
        consumed += 1 if line[index] == " " else 4 - consumed % 4
        index += 1
    return line[index:]


def splitBlocks(text: str, firstLine: int) -> list[Block]:
    blocks: list[Block] = []
    buffer: list[str] = []
    bufferStart = 0
    lineNo = firstLine - 1
    fence: str | None = None
    fenceStart = 0
    fenceLines: list[str] = []
    listContinuation: int | None = None
    bufferListContinuation: int | None = None

    def flush() -> None:
        nonlocal buffer, bufferListContinuation
        if not buffer:
            return
        firstLine = buffer[0]
        if bufferListContinuation is not None and indentWidth(firstLine) >= bufferListContinuation:
            firstLine = afterIndent(firstLine, bufferListContinuation)
        kind = classify(firstLine)
        joined = "\n".join(buffer)
        level = 0
        if kind == HEADING:
            match = HEADING_LINE.match(buffer[0])
            level = len(match.group(1))
            joined = match.group(2)
        blocks.append(Block(kind, bufferStart, bufferStart + len(buffer) - 1, joined, level, len(blocks)))
        buffer = []
        bufferListContinuation = None

    for raw in text.splitlines():
        lineNo += 1
        line = raw.rstrip("\r")
        if fence:
            fenceLines.append(line)
            closing = FENCE_CLOSE.match(line)
            closingFence = closing.group("fence") if closing else ""
            if closingFence.startswith(fence) and closingFence[0] == fence[0]:
                blocks.append(Block(CODE, fenceStart, lineNo, "\n".join(fenceLines), 0, len(blocks)))
                fence = None
                fenceLines = []
            continue
        opening = FENCE_OPEN.match(line)
        if opening:
            flush()
            fence = opening.group("ticks") or opening.group("tildes")
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
        listMatch = LIST_LINE.match(line)
        if listMatch:
            contentColumn = listMatch.end()
            listContinuation = ((contentColumn + 3) // 4) * 4
        elif listContinuation is not None and indentWidth(line) < listContinuation:
            listContinuation = None
        if not buffer:
            bufferStart = lineNo
            bufferListContinuation = listContinuation
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
