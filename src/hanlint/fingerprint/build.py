"""문서 모델을 한 번 훑어 글 지문을 만든다. 텍스트를 읽는 유일한 자리다."""

from __future__ import annotations

from statistics import mean, pstdev

from ..analysis import Analyzer
from ..config import Config
from ..document import Block, Document, Section, plainText
from ..document.model import HEADING, PROSE
from . import markers
from .dictionaries import Entry, entriesFor, matchesIn
from .documentPrint import DocumentPrint
from .paragraphPrint import ParagraphPrint
from .sectionPrint import SectionPrint
from .sentencePrint import SentencePrint
from .topics import overlap, topicsOf


def makeSentencePrint(
    text: str,
    index: int,
    line: int,
    block: Block,
    paragraphIndex: int,
    sectionIndex: int,
    analyzer: Analyzer,
    entries: tuple[Entry, ...],
) -> SentencePrint:
    ending = markers.endingOf(text)
    return SentencePrint(
        index=index,
        line=line,
        text=text,
        blockIndex=block.index,
        paragraphIndex=paragraphIndex,
        sectionIndex=sectionIndex,
        length=len(text.split()),
        ending=ending,
        mood=markers.moodOf(text, ending),
        commas=markers.countCommas(text),
        connectorStart=markers.connectorStartOf(text),
        causal=markers.countMatches(text, "causalMarkers.txt"),
        deixis=markers.matchedTexts(text, "deixis.txt"),
        euiCount=analyzer.euiCount(text),
        nounRun=analyzer.longestNounRun(text),
        passives=tuple(analyzer.doublePassives(text)),
        hedges=markers.countMatches(text, "hedges.txt"),
        numbers=markers.countNumbers(text),
        topics=topicsOf(text),
        promises=markers.matchedTexts(text, "promiseMarkers.txt"),
        recalls=markers.matchedTexts(text, "recallMarkers.txt"),
        countPromises=markers.countPromisesIn(text),
        readerCall=bool(markers.matchedTexts(text, "readerCalls.txt")),
        matches=matchesIn(text, entries),
    )


def makeParagraphPrint(
    sentences: list[SentencePrint],
    index: int,
    block: Block,
    sectionIndex: int,
    previous: ParagraphPrint | None,
    followsProseDirectly: bool,
) -> ParagraphPrint:
    lengths = [s.length for s in sentences]
    topics = frozenset().union(*(s.topics for s in sentences)) if sentences else frozenset()
    return ParagraphPrint(
        index=index,
        blockIndex=block.index,
        sectionIndex=sectionIndex,
        startLine=block.startLine,
        endLine=block.endLine,
        sentences=tuple(sentences),
        meanLength=mean(lengths) if lengths else 0.0,
        lengthStd=pstdev(lengths) if len(lengths) > 1 else 0.0,
        causalTotal=sum(s.causal for s in sentences),
        deixisTotal=sum(len(s.deixis) for s in sentences),
        topics=topics,
        overlapWithPrevious=overlap(previous.topics, topics) if previous else None,
        followsProseDirectly=followsProseDirectly,
    )


def buildSection(
    section: Section,
    sectionIndex: int,
    analyzer: Analyzer,
    entries: tuple[Entry, ...],
    sentences: list[SentencePrint],
    paragraphs: list[ParagraphPrint],
) -> SectionPrint:
    sectionParagraphs: list[ParagraphPrint] = []
    previousBlock: Block | None = None
    for block in section.blocks:
        if block.kind != PROSE:
            previousBlock = block
            continue
        text = plainText(block.text)
        blockSentences: list[SentencePrint] = []
        for sentence in analyzer.sentences(text):
            line = block.startLine + text.count("\n", 0, sentence.start)
            index = len(sentences) + len(blockSentences)
            blockSentences.append(
                makeSentencePrint(sentence.text, index, line, block, len(paragraphs), sectionIndex, analyzer, entries)
            )
        sentences.extend(blockSentences)
        previous = sectionParagraphs[-1] if sectionParagraphs else None
        paragraph = makeParagraphPrint(
            blockSentences,
            len(paragraphs),
            block,
            sectionIndex,
            previous,
            previousBlock is not None and previousBlock.kind == PROSE,
        )
        paragraphs.append(paragraph)
        sectionParagraphs.append(paragraph)
        previousBlock = block
    topics = frozenset().union(*(p.topics for p in sectionParagraphs)) if sectionParagraphs else frozenset()
    return SectionPrint(
        index=sectionIndex,
        title=section.title,
        level=section.heading.level if section.heading else 0,
        startLine=section.startLine,
        paragraphs=tuple(sectionParagraphs),
        blockKinds=tuple(b.kind for b in section.blocks),
        topics=topics,
    )


def buildFingerprint(doc: Document, analyzer: Analyzer, config: Config | None = None) -> DocumentPrint:
    config = config or Config()
    entries = entriesFor(config)
    sentences: list[SentencePrint] = []
    paragraphs: list[ParagraphPrint] = []
    sections = [
        buildSection(section, index, analyzer, entries, sentences, paragraphs) for index, section in enumerate(doc.sections)
    ]
    headings = tuple((b.level, b.text, b.startLine) for b in doc.blocks if b.kind == HEADING)
    headingQuestions = sum(1 for b in doc.blocks if b.kind == HEADING and "?" in b.text)
    return DocumentPrint(
        path=doc.path,
        frontmatter=dict(doc.frontmatter),
        blocks=tuple(doc.blocks),
        sentences=tuple(sentences),
        paragraphs=tuple(paragraphs),
        sections=tuple(sections),
        headings=headings,
        wordCount=sum(s.length for s in sentences),
        questionCount=sum(1 for s in sentences if s.mood == "의문") + headingQuestions,
        readerCallCount=sum(1 for s in sentences if s.readerCall or s.mood == "명령"),
        countPromises=tuple((n, unit, s.line, text) for s in sentences for n, unit, text in s.countPromises),
        promises=tuple((s.line, text) for s in sentences for text in s.promises),
        recalls=tuple((s.line, text) for s in sentences for text in s.recalls),
        disabled=tuple(doc.disabled),
    )
