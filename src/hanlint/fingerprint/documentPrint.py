"""글 지문. 절 지문 열과 글 전체에서만 보이는 것."""

from __future__ import annotations

from dataclasses import dataclass

from ..document import Block
from .paragraphPrint import ParagraphPrint
from .sectionPrint import SectionPrint
from .sentencePrint import SentencePrint


@dataclass(frozen=True)
class DocumentPrint:
    path: str | None
    frontmatter: dict[str, str]
    blocks: tuple[Block, ...]
    """원문 블록. 코드 블록까지 보는 규칙 (dash) 이 쓴다."""
    sentences: tuple[SentencePrint, ...]
    paragraphs: tuple[ParagraphPrint, ...]
    sections: tuple[SectionPrint, ...]
    headings: tuple[tuple[int, str, int], ...]
    """(레벨, 제목, 줄)."""
    wordCount: int
    questionCount: int
    readerCallCount: int
    countPromises: tuple[tuple[int, str, int, str], ...]
    """(수, 단위, 줄, 원문)."""
    promises: tuple[tuple[int, str], ...]
    """(줄, 표지 원문)."""
    recalls: tuple[tuple[int, str], ...]

    @property
    def intro(self) -> SectionPrint:
        return self.sections[0]

    @property
    def bodySections(self) -> tuple[SectionPrint, ...]:
        return tuple(s for s in self.sections if not s.isIntro)

    def headingsOfLevel(self, level: int) -> list[tuple[int, str, int]]:
        return [h for h in self.headings if h[0] == level]
