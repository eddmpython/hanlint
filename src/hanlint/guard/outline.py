"""Reader Contract가 잠근 제목 순서와 글 지문의 구조 요약."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Outline
from ..fingerprint import DocumentPrint


@dataclass(frozen=True)
class OutlineMismatch:
    """한 제목 위치에서 기대와 실제가 갈린 자리."""

    position: int
    expected: str | None
    actual: str | None

    @property
    def signature(self) -> str:
        return f"{self.position}:{self.expected or ''}:{self.actual or ''}"

    def asDict(self) -> dict:
        return {"position": self.position, "expected": self.expected, "actual": self.actual}


@dataclass(frozen=True)
class OutlineDiff:
    """한 제목 수준의 기대 순서와 실제 순서를 맞댄 결과."""

    level: int
    expected: tuple[str, ...]
    actual: tuple[str, ...]
    mismatches: tuple[OutlineMismatch, ...]

    @property
    def matches(self) -> bool:
        return not self.mismatches

    @property
    def violationCount(self) -> int:
        return len(self.mismatches)

    def asDict(self) -> dict:
        return {
            "matches": self.matches,
            "level": self.level,
            "expected": list(self.expected),
            "actual": list(self.actual),
            "mismatches": [mismatch.asDict() for mismatch in self.mismatches],
        }


@dataclass(frozen=True)
class SectionSummary:
    """잘리지 않은 절 제목과 눈으로 확인할 최소 모양."""

    heading: str
    line: int
    paragraphCount: int
    codeBlockCount: int

    def asDict(self) -> dict:
        return {
            "heading": self.heading,
            "line": self.line,
            "paragraphCount": self.paragraphCount,
            "codeBlockCount": self.codeBlockCount,
        }


@dataclass(frozen=True)
class DocumentSummary:
    """check 영수증에서 바로 읽는 글의 크기와 절 목록."""

    sentenceCount: int
    paragraphCount: int
    sectionCount: int
    wordCount: int
    questionCount: int
    readerCallCount: int
    sections: tuple[SectionSummary, ...]

    def asDict(self) -> dict:
        return {
            "sentenceCount": self.sentenceCount,
            "paragraphCount": self.paragraphCount,
            "sectionCount": self.sectionCount,
            "wordCount": self.wordCount,
            "questionCount": self.questionCount,
            "readerCallCount": self.readerCallCount,
            "sections": [section.asDict() for section in self.sections],
        }


def compareOutline(outline: Outline, doc: DocumentPrint) -> OutlineDiff:
    """잠근 수준의 제목을 순서와 개수까지 정확히 대조한다."""
    actual = tuple(title for level, title, _ in doc.headings if level == outline.level)
    mismatches = []
    for index in range(max(len(outline.headings), len(actual))):
        expectedTitle = outline.headings[index] if index < len(outline.headings) else None
        actualTitle = actual[index] if index < len(actual) else None
        if expectedTitle != actualTitle:
            mismatches.append(OutlineMismatch(index + 1, expectedTitle, actualTitle))
    return OutlineDiff(outline.level, outline.headings, actual, tuple(mismatches))


def summarizeDocument(doc: DocumentPrint) -> DocumentSummary:
    """지문을 다시 읽지 않고 전체 제목과 절 모양을 압축한다."""
    sections = tuple(
        SectionSummary(section.title, section.startLine, len(section.paragraphs), section.count("code"))
        for section in doc.bodySections
    )
    return DocumentSummary(
        sentenceCount=len(doc.sentences),
        paragraphCount=len(doc.paragraphs),
        sectionCount=len(doc.bodySections),
        wordCount=doc.wordCount,
        questionCount=doc.questionCount,
        readerCallCount=doc.readerCallCount,
        sections=sections,
    )


__all__ = [
    "DocumentSummary",
    "OutlineDiff",
    "OutlineMismatch",
    "SectionSummary",
    "compareOutline",
    "summarizeDocument",
]
