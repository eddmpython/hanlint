"""문서 모델을 한 번 훑어 글 분석 결과를 만든다. 텍스트를 읽는 곳은 여기 하나다."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, pstdev

from ..analysis import Sentence, doublePassiveSpans, euiCount, longestNounRun, splitSentences
from ..analysis.grammar import NONE as NO_REGISTER
from ..analysis.grammar import documentRegister, lastWord, registerOfWord
from ..config import Config
from ..document import Block, Document, Section, codeSpans, dropFences, plainText
from ..document.model import HEADING, PROSE
from . import markers
from .codeBlocks import codeBlocksOf
from .dictionaries import Entry, entriesFor, matchesIn
from .documentPrint import DocumentPrint
from .paragraphPrint import ParagraphPrint
from .readerState import buildReaderTrail
from .sectionPrint import SectionPrint
from .sentencePrint import SentencePrint
from .topics import overlap, topicsOf


def quotedIn(sentence: Sentence, blockSpans: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    """문장 안의 인용 구간. 블록 좌표의 구간을 문장 좌표로 옮긴다.

    **따옴표 쌍도 블록에서 재서 넘겨받는다.** 문장 안에서 재던 때는 문장 분리가 따옴표 안에서 잘리면
    (`TERMINAL`은 물음표 뒤 공백에서 자른다) 조각에 여는 따옴표만 남아 쌍이 안 잡히고, docstring이
    "안 잡는다"고 선언한 인용 예외가 통째로 풀렸다. 실측: `"네가 탄 곡조는 누구의 것인데? 대단히 듣기
    좋던데..."`가 두 문장으로 잘려 양쪽 다 인용 구간이 0이었다(2026-08-31). ellipsis 표본 20건 가운데
    10건이 이 결함이었고 deixis와 이중 피동과 사전 규칙도 같은 예외를 쓴다.
    """
    spans: list[tuple[int, int]] = []
    for start, end in blockSpans:
        lo, hi = max(start, sentence.start), min(end, sentence.end)
        if lo < hi:
            spans.append((lo - sentence.start, hi - sentence.start))
    return tuple(sorted(set(spans)))


@dataclass
class Build:
    """분석 결과를 쌓는 동안 들고 다니는 것. 사전은 안 바뀌고 두 목록은 쌓인다.

    위치(문장 index와 문단 index)는 넘겨받지 않고 쌓인 길이에서 얻는다. 넘겨받으면 부르는 쪽이 셈을
    맞춰야 하고 그 셈이 틀려도 아무도 모른다. 여기서 세면 틀릴 일이 없다.
    """

    entries: tuple[Entry, ...]
    protectedTerms: tuple[str, ...] = ()
    """설정의 protectedTerms. 이 용어와 겹치는 사전 매치, 지시어, 이중 피동은 문장 분석 결과에 넣지 않는다."""
    sentences: list[SentencePrint] = field(default_factory=list)
    paragraphs: list[ParagraphPrint] = field(default_factory=list)


def makeSentencePrint(
    build: Build,
    text: str,
    line: int,
    block: Block,
    sectionIndex: int,
    quoted: tuple[tuple[int, int], ...],
) -> SentencePrint:
    ending = markers.endingOf(text)
    protected = markers.termSpans(text, build.protectedTerms)

    def kept(start: int, end: int) -> bool:
        # 인용 안의 것과 보호한 용어에 걸친 것은 뺀다. 실측: protectedTerms에 `물때`를 넣어도 spacing이
        # `물때는`을 `물 때는`으로 고치라고 했다(2026-11-01). 보호한 용어는 지적의 대상이 아니다.
        return not markers.insideAny(start, end, quoted) and not markers.overlapsAny(start, end, protected)

    deixis = tuple(found for start, end, found in markers.matchedSpans(text, "deixis.txt") if kept(start, end))
    matches = tuple(m for m in matchesIn(text, build.entries) if kept(m.start, m.end))
    return SentencePrint(
        index=len(build.sentences),
        line=line,
        text=text,
        blockIndex=block.index,
        paragraphIndex=len(build.paragraphs),
        sectionIndex=sectionIndex,
        length=len(text.split()),
        ending=ending,
        mood=(mood := markers.moodOf(text, ending)),
        register=(registerOfWord(lastWord(text)) or NO_REGISTER) if mood == "평서" else NO_REGISTER,
        commas=markers.countCommas(text),
        connectorStart=markers.connectorStartOf(text),
        causal=markers.countMatches(text, "causalMarkers.txt"),
        deixis=deixis,
        euiCount=euiCount(text),
        nounRun=longestNounRun(text),
        passives=tuple(surface for start, end, surface in doublePassiveSpans(text) if kept(start, end)),
        hedges=markers.countMatches(text, "hedges.txt"),
        numbers=markers.countNumbers(text),
        topics=topicsOf(text),
        promises=markers.matchedTexts(text, "promiseMarkers.txt"),
        recalls=markers.matchedTexts(text, "recallMarkers.txt"),
        countPromises=markers.countPromisesIn(text),
        readerCall=bool(markers.matchedTexts(text, "readerCalls.txt")),
        matches=matches,
        quoted=quoted,
    )


def makeParagraphPrint(
    build: Build,
    sentences: list[SentencePrint],
    block: Block,
    sectionIndex: int,
    previous: ParagraphPrint | None,
    followsProseDirectly: bool,
) -> ParagraphPrint:
    lengths = [s.length for s in sentences]
    topics = frozenset().union(*(s.topics for s in sentences)) if sentences else frozenset()
    return ParagraphPrint(
        index=len(build.paragraphs),
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


def buildSection(build: Build, section: Section, sectionIndex: int) -> SectionPrint:
    sectionParagraphs: list[ParagraphPrint] = []
    previousBlock: Block | None = None
    for block in section.blocks:
        if block.kind != PROSE:
            previousBlock = block
            continue
        text = plainText(block.text)
        # 인라인 코드와 따옴표 쌍을 둘 다 블록 좌표에서 잰다. 문장 분리가 인용 안에서 잘려도 쌍이 남는다.
        blockSpans = tuple(sorted(set(codeSpans(block.text, text) + markers.quoteSpans(text))))
        blockSentences: list[SentencePrint] = []
        for sentence in splitSentences(text):
            line = block.startLine + text.count("\n", 0, sentence.start)
            quoted = quotedIn(sentence, blockSpans)
            made = makeSentencePrint(build, sentence.text, line, block, sectionIndex, quoted)
            # 만든 곳에서 바로 쌓는다. 다음 문장의 index가 이 길이에서 나오므로 미루면 셈이 어긋난다.
            build.sentences.append(made)
            blockSentences.append(made)
        previous = sectionParagraphs[-1] if sectionParagraphs else None
        paragraph = makeParagraphPrint(
            build,
            blockSentences,
            block,
            sectionIndex,
            previous,
            previousBlock is not None and previousBlock.kind == PROSE,
        )
        build.paragraphs.append(paragraph)
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


def buildFingerprint(doc: Document, config: Config | None = None) -> DocumentPrint:
    config = config or Config()
    # 코드도 산문도 아닌 펜스는 분석에 들어오기 전에 뺀다. 모든 진입점이 여기를 지나므로 한 곳이면 된다.
    doc = dropFences(doc, config.ignoreFences)
    build = Build(entriesFor(config), tuple(config.protectedTerms))
    sections = [buildSection(build, section, index) for index, section in enumerate(doc.sections)]
    sentences, paragraphs = build.sentences, build.paragraphs
    headings = tuple((b.level, b.text, b.startLine) for b in doc.blocks if b.kind == HEADING)
    headingQuestions = sum(1 for b in doc.blocks if b.kind == HEADING and "?" in b.text)
    register, registerShare = documentRegister([lastWord(s.text) for s in sentences if s.mood == "평서"], config.registerMinShare)
    codeBlocks = codeBlocksOf(doc.blocks)
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
        codeBlocks=codeBlocks,
        reader=buildReaderTrail(doc.blocks, codeBlocks, sentences),
        register=register,
        registerShare=registerShare,
        disabled=tuple(doc.disabled),
        ignored=tuple(doc.ignored),
    )
