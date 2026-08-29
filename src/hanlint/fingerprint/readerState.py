"""독자 상태. 글을 위에서 아래로 읽는 독자가 어느 자리에서 무엇을 손에 들고 무엇을 이미 보았는가.

reader 기제의 규칙은 어느 자리가 요구하는 것 (지시어가 가리킬 것, 견줌의 기준값, 코드가 읽는 파일, 미룬 것의
회수) 을 그 자리의 상태에 대 본다. 상태는 블록과 문장 순서로 쌓이고 한 번 쌓은 것은 바뀌지 않는다. 규칙은
상태를 묻기만 하고 글을 다시 읽지 않는다.

contrast 가 두 자리를 맞대는 것이라면 reader 는 자리 하나를 그 앞 전부에 맞댄다. 순서를 뒤집으면 답이
달라지는 것이 둘을 가르는 선이다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..document import Block
from ..document.model import CODE, PROSE
from .codeBlocks import CodeBlock
from .codeMarkers import createdIn
from .markers import numeralsIn
from .sentencePrint import SentencePrint


@dataclass(frozen=True)
class ReaderState:
    """한 자리 (문장 하나 또는 블록 하나) 를 읽기 직전의 독자."""

    previous: SentencePrint | None
    """바로 앞에 읽은 산문 문장. 지시어는 여기까지만 가리킬 수 있다."""
    numerals: frozenset[str]
    """지금까지 산문과 블록에 나온 수 (천 단위 쉼표를 뗀 꼴). 견줌의 기준값은 여기 있어야 한다."""
    files: frozenset[str]
    """앞선 코드 블록이 만든 파일 이름과 폴더. 코드가 읽는 파일은 여기 있거나 산문이 이름을 불렀어야 한다."""
    sentencesRead: int
    """지금까지 읽은 산문 문장 수. 앞선 산문이 이름을 불렀는지는 이 수까지만 본다."""
    promises: tuple[tuple[int, str], ...]
    """지금까지 뒤로 미룬 표지 (줄, 원문)."""
    recalls: tuple[tuple[int, str], ...]
    """지금까지 앞을 회수한 표지 (줄, 원문)."""

    @property
    def recent(self) -> frozenset[str]:
        """손에 든 화제어. 바로 앞 문장의 것이고 앞 문장이 없으면 빈 집합이다."""
        return self.previous.topics if self.previous is not None else frozenset()


START = ReaderState(None, frozenset(), frozenset(), 0, (), ())
"""아직 아무것도 읽지 않은 독자."""


@dataclass(frozen=True)
class ReaderTrail:
    """자리마다의 독자 상태. 문장은 `SentencePrint.index` 로, 블록은 `Block.index` 로 찾는다."""

    sentences: tuple[SentencePrint, ...]
    beforeSentence: tuple[ReaderState, ...]
    beforeBlock: tuple[ReaderState, ...]
    final: ReaderState
    """글을 다 읽은 독자."""

    def mentionedBefore(self, blockIndex: int, name: str) -> bool:
        """블록보다 앞선 산문이 그 이름을 불렀는가. 불렀으면 독자가 준비한 것으로 본다."""
        read = self.beforeBlock[blockIndex].sentencesRead
        return any(name in sentence.text for sentence in self.sentences[:read])


def afterSentence(state: ReaderState, sentence: SentencePrint) -> ReaderState:
    found = numeralsIn(sentence.text)
    return ReaderState(
        previous=sentence,
        numerals=state.numerals | found if found else state.numerals,
        files=state.files,
        sentencesRead=state.sentencesRead + 1,
        promises=state.promises + tuple((sentence.line, text) for text in sentence.promises),
        recalls=state.recalls + tuple((sentence.line, text) for text in sentence.recalls),
    )


def afterBlock(state: ReaderState, block: Block, code: CodeBlock | None) -> ReaderState:
    """산문 아닌 블록을 지난 독자. 수는 어느 블록에서든 보고 파일은 코드 블록이 만든다."""
    found = numeralsIn(block.text)
    files = state.files
    if code is not None:
        made, dirs = createdIn(line for _, line in code.lines)
        files = files | made | dirs
    return ReaderState(
        previous=state.previous,
        numerals=state.numerals | found if found else state.numerals,
        files=files,
        sentencesRead=state.sentencesRead,
        promises=state.promises,
        recalls=state.recalls,
    )


def buildReaderTrail(blocks: Sequence[Block], codeBlocks: Sequence[CodeBlock], sentences: Sequence[SentencePrint]) -> ReaderTrail:
    """블록 순서로 한 번 지나며 자리마다의 상태를 적는다. 산문 블록은 문장 하나씩, 나머지는 블록째 읽는다."""
    codeByIndex = {code.index: code for code in codeBlocks}
    beforeSentence: list[ReaderState] = []
    beforeBlock: list[ReaderState] = []
    state = START
    position = 0
    for block in blocks:
        beforeBlock.append(state)
        if block.kind == PROSE:
            while position < len(sentences) and sentences[position].blockIndex == block.index:
                beforeSentence.append(state)
                state = afterSentence(state, sentences[position])
                position += 1
        else:
            state = afterBlock(state, block, codeByIndex.get(block.index) if block.kind == CODE else None)
    if position != len(sentences):
        raise ValueError(f"문장 {len(sentences) - position}개가 어느 블록에도 안 든다. 문장과 블록의 순서가 어긋났다")
    return ReaderTrail(tuple(sentences), tuple(beforeSentence), tuple(beforeBlock), state)
