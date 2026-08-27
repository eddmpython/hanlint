"""화제 흐름. 문단 사이의 화제 중첩과 골짜기."""

from __future__ import annotations

from ..config import Config
from ..fingerprint import DocumentPrint
from .shape import Valley


def overlapsOf(doc: DocumentPrint) -> tuple[tuple[int, float], ...]:
    return tuple((p.index, p.overlapWithPrevious) for p in doc.paragraphs if p.overlapWithPrevious is not None)


def valleysOf(doc: DocumentPrint, config: Config) -> tuple[Valley, ...]:
    valleys = []
    for section in doc.sections:
        paragraphs = section.paragraphs
        for previous, paragraph in zip(paragraphs, paragraphs[1:], strict=False):
            if paragraph.overlapWithPrevious != 0.0:
                continue
            if min(previous.sentenceCount, paragraph.sentenceCount) < config.topicBreakMinSentences:
                continue
            valleys.append(Valley(paragraph.index, paragraph.startLine, previous.startLine, 0.0))
    return tuple(valleys)
