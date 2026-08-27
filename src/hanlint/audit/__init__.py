"""분석 층. 지문 열의 통계를 점수 없이 사실로 낸다. 규칙과 형제라 서로 import 하지 않는다."""

from __future__ import annotations

from ..config import Config
from ..fingerprint import DocumentPrint
from .density import densityOf
from .flow import overlapsOf, valleysOf
from .lexicon import connectorMixOf, lexiconOf
from .rhythm import commaRatioOf, endingMixOf, paragraphHistogramOf, rhythmOf
from .sectionShape import sectionShapesOf
from .shape import AuditResult, Density, Lexicon, Rhythm, SectionShape, Valley

__all__ = ["AuditResult", "Density", "Lexicon", "Rhythm", "SectionShape", "Valley", "auditDocument"]


def auditDocument(doc: DocumentPrint, config: Config | None = None) -> AuditResult:
    config = config or Config()
    sentences = doc.sentences
    paragraphs = doc.paragraphs
    return AuditResult(
        path=doc.path,
        sentenceCount=len(sentences),
        paragraphCount=len(paragraphs),
        sectionCount=len(doc.bodySections),
        wordCount=doc.wordCount,
        lexicon=lexiconOf(sentences),
        connectorMix=connectorMixOf(sentences),
        rhythm=rhythmOf(sentences),
        commaRatio=commaRatioOf(sentences),
        endingMix=endingMixOf(sentences),
        paragraphHistogram=paragraphHistogramOf(paragraphs),
        shortParagraphRatio=(sum(1 for p in paragraphs if p.sentenceCount <= 2) / len(paragraphs)) if paragraphs else 0.0,
        density=densityOf(sentences, doc.wordCount),
        overlaps=overlapsOf(doc),
        valleys=valleysOf(doc, config),
        sections=sectionShapesOf(doc),
        headingLevels=tuple(level for level, _, _ in doc.headings),
        questionCount=doc.questionCount,
        readerCallCount=doc.readerCallCount,
    )
