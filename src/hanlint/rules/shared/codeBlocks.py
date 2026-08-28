"""코드 블록을 언어와 본문으로 나눈다. code 부류 규칙이 함께 쓴다.

펜스 첫 줄의 언어 표기 (```python) 를 읽고 본문 줄에 원문 줄 번호를 붙인다. text 펜스는 출력이다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ...document import fenceLanguage
from ...document.model import CODE
from ...fingerprint import DocumentPrint

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


def codeBlocksOf(doc: DocumentPrint) -> list[CodeBlock]:
    blocks: list[CodeBlock] = []
    for block in doc.blocks:
        if block.kind != CODE:
            continue
        raw = block.text.split("\n")
        language = fenceLanguage(block.text)
        body = raw[1:]
        if body and CLOSING_FENCE.match(body[-1]):
            body = body[:-1]
        lines = tuple((block.startLine + 1 + offset, line) for offset, line in enumerate(body))
        blocks.append(CodeBlock(block.index, block.startLine, language, lines))
    return blocks
