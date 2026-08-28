"""문서 모델. 세 층이다.

- `Block` 빈 줄로 나뉜 덩어리 하나. 종류가 있다 (prose, heading, code, quote, image, list, table, embed, html)
- `Section` H2 하나가 여는 절. 첫 H2 앞은 제목 없는 도입 절이다
- `Document` 전체. frontmatter 와 절 목록을 든다

줄 번호는 1 부터 세고 원문 기준이다. 지적이 인용하는 줄이 편집기에서 바로 열려야 한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PROSE = "prose"
HEADING = "heading"
CODE = "code"
QUOTE = "quote"
IMAGE = "image"
LIST = "list"
TABLE = "table"
EMBED = "embed"
HTML = "html"


@dataclass(frozen=True)
class Block:
    kind: str
    startLine: int
    endLine: int
    text: str
    level: int = 0
    """heading 일 때 `#` 의 개수."""
    index: int = 0
    """문서 안 순서."""

    @property
    def isProse(self) -> bool:
        return self.kind == PROSE


@dataclass
class Section:
    heading: Block | None
    blocks: list[Block] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.heading.text if self.heading else ""

    @property
    def startLine(self) -> int:
        if self.heading:
            return self.heading.startLine
        return self.blocks[0].startLine if self.blocks else 1

    def prose(self) -> list[Block]:
        return [block for block in self.blocks if block.isProse]

    def kinds(self) -> set[str]:
        return {block.kind for block in self.blocks}


@dataclass
class Document:
    path: str | None
    frontmatter: dict[str, str]
    blocks: list[Block]
    sections: list[Section]
    disabled: list[tuple[str, int, int]] = field(default_factory=list)
    """인라인 제어가 끈 (규칙 이름 또는 *, 시작 줄, 끝 줄). `<!-- hanlint-disable cliche -->` 가 만든다."""

    @property
    def intro(self) -> Section:
        """첫 H2 앞의 절. H2 가 하나도 없으면 글 전체가 도입이다."""
        return self.sections[0]

    @property
    def bodySections(self) -> list[Section]:
        return [section for section in self.sections if section.heading is not None]

    def prose(self) -> list[Block]:
        return [block for block in self.blocks if block.isProse]

    def headings(self, level: int | None = None) -> list[Block]:
        return [b for b in self.blocks if b.kind == HEADING and (level is None or b.level == level)]
