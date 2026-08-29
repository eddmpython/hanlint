from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule
from ..shared import doublePassiveCandidates


@rule("doublePassive", mechanism="dictionary")
def doublePassive(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """되어지다, 보여지다, 잊혀지다 처럼 피동에 어지다 를 또 붙인 이중 피동.

    왜: 피동이 두 번 겹치면 누가 하는지 한 번 더 흐려진다. 독자는 주어를 찾아 되돌아간다.
    어디서: 국립국어원 어문 규범. im-not-ai A-8 (오경순 2010, 김은일 2015, 서보현 2018). 피동 어간 사전은
        data/passiveStems.txt.
    고치기: 하나만 남긴다. 되어진다 는 된다, 보여진다 는 보인다, 잊혀진 은 잊힌.
    안 잡는 것: 만들어진다 같은 단순 피동. 어간이 피동사가 아니면 지적하지 않는다.
    """
    for sentence in doc.sentences:
        if sentence.passives:
            yield Finding(
                "doublePassive",
                sentence.line,
                sentence.text,
                f"`{sentence.passives[0]}` 는 피동에 어지다 를 또 붙인 이중 피동이다. 하나만 남긴다",
                None,
                "error",
                SENTENCE,
                sentence.index,
                candidates=doublePassiveCandidates(sentence.text, sentence.passives),
            )
