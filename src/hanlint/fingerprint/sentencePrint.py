"""문장 지문. 한 문장에서 셀 수 있는 것을 전부 한 번에 센다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DictionaryMatch:
    dictionary: str
    """cliches, translationese, redundantPair, japaneseLoan 가운데 하나."""
    text: str
    """맞은 자리의 원문."""
    start: int
    end: int
    why: str
    source: str
    fix: str | None
    """맞은 자리를 그대로 바꿀 수 있을 때만 있다. 그룹 치환을 마친 값이다."""


@dataclass(frozen=True)
class SentencePrint:
    index: int
    """글 안 문장 순서."""
    line: int
    text: str
    blockIndex: int
    paragraphIndex: int
    sectionIndex: int
    length: int
    """어절 수."""
    ending: str
    """종결어미 부류. data/endings.txt 의 첫 열이거나 `없음`."""
    mood: str
    """평서, 의문, 명령."""
    commas: int
    connectorStart: str | None
    """문두 접속부사."""
    causal: int
    """인과와 조건 표지 수."""
    deixis: tuple[str, ...]
    euiCount: int
    nounRun: int
    passives: tuple[str, ...]
    hedges: int
    numbers: int
    topics: frozenset[str]
    promises: tuple[str, ...]
    """뒤를 약속하는 표지."""
    recalls: tuple[str, ...]
    """앞을 회수하는 표지."""
    countPromises: tuple[tuple[int, str, str], ...]
    """(수, 단위, 원문). `여섯 가지` 처럼 글이 약속한 수."""
    readerCall: bool
    matches: tuple[DictionaryMatch, ...]
    quoted: tuple[tuple[int, int], ...]
    """인용 구간 (시작, 끝). 인라인 코드와 따옴표 쌍의 안. 사전 매치와 지시어는 이 안의 것을 이미 뺐다."""
