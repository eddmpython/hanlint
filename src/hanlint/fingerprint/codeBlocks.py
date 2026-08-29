"""코드 블록을 언어와 본문으로 나눈다. 지문이 한 번 만들고 (`DocumentPrint.codeBlocks`) code 부류 규칙과 독자 상태가 읽는다.

펜스 첫 줄의 언어 표기 (```python) 를 읽고 본문 줄에 원문 줄 번호를 붙인다. text 펜스는 출력이다.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from ..document import Block, fenceLanguage
from ..document.model import CODE

CLOSING_FENCE = re.compile(r"^\s*(?:```|~~~)\s*$")


@dataclass(frozen=True)
class CodeBlock:
    index: int
    startLine: int
    language: str
    lines: tuple[tuple[int, str], ...]
    """(원문 줄 번호, 코드 줄)."""

    @property
    def text(self) -> str:
        return "\n".join(line for _, line in self.lines)

    @property
    def isOutput(self) -> bool:
        return self.language in ("text", "", "output", "console")


def codeBlocksOf(blocks: Sequence[Block]) -> tuple[CodeBlock, ...]:
    found: list[CodeBlock] = []
    for block in blocks:
        if block.kind != CODE:
            continue
        raw = block.text.split("\n")
        language = fenceLanguage(block.text)
        body = raw[1:]
        if body and CLOSING_FENCE.match(body[-1]):
            body = body[:-1]
        lines = tuple((block.startLine + 1 + offset, line) for offset, line in enumerate(body))
        found.append(CodeBlock(block.index, block.startLine, language, lines))
    return tuple(found)
