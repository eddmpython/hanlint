from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule
from ..shared import doublePassiveCandidates


def _approvedEdit(
    text: str,
    candidateText: str,
    quoted: tuple[tuple[int, int], ...],
) -> tuple[str, str] | None:
    """검토를 통과한 이중 피동 후보에서 인용 밖의 단일 치환만 꺼낸다."""
    prefix = 0
    while prefix < len(text) and prefix < len(candidateText) and text[prefix] == candidateText[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < len(text) - prefix
        and suffix < len(candidateText) - prefix
        and text[len(text) - suffix - 1] == candidateText[len(candidateText) - suffix - 1]
    ):
        suffix += 1
    sourceEnd = len(text) - suffix
    candidateEnd = len(candidateText) - suffix
    fragment = text[prefix:sourceEnd]
    replacement = candidateText[prefix:candidateEnd]
    if not fragment or text.count(fragment) != 1:
        return None
    if any(prefix < end and sourceEnd > start for start, end in quoted):
        return None
    return fragment, replacement


@rule("doublePassive", mechanism="dictionary")
def doublePassive(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """되어지다, 보여지다, 잊혀지다 처럼 피동에 어지다 를 또 붙인 이중 피동.

    왜: 피동이 두 번 겹치면 누가 하는지 한 번 더 흐려진다. 독자는 주어를 찾아 되돌아간다.
    어디서: 국립국어원 어문 규범. im-not-ai A-8 (오경순 2010, 김은일 2015, 서보현 2018). 피동 어간 사전은
        data/passiveStems.txt.
    고치기: 하나만 남긴다. 되어진다 는 된다, 보여진다 는 보인다, 잊혀진 은 잊힌. 활용 후보가 하나이고
        바뀌는 조각이 인용 밖에 한 번만 있을 때는 검토를 마친 확정 치환으로 고친다.
    안 잡는 것: 만들어진다 같은 단순 피동. 어간이 피동사가 아니면 지적하지 않는다.
    """
    for sentence in doc.sentences:
        if sentence.passives:
            candidates = doublePassiveCandidates(sentence.text, sentence.passives)
            approved = _approvedEdit(sentence.text, candidates[0].text, sentence.quoted) if len(candidates) == 1 else None
            yield Finding(
                "doublePassive",
                sentence.line,
                sentence.text,
                f"`{sentence.passives[0]}` 는 피동에 어지다 를 또 붙인 이중 피동이다. 하나만 남긴다",
                candidates[0].text if approved else None,
                "error",
                SENTENCE,
                sentence.index,
                fragment=approved[0] if approved else None,
                replacement=approved[1] if approved else None,
                candidates=() if approved else candidates,
            )
