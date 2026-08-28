from __future__ import annotations

from collections.abc import Iterator

from ...analysis.grammar import fitJosa
from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.topics import overlap
from ..finding import SENTENCE, Finding
from ..registry import rule
from ..shared import danglingDeixisCandidates, hasLocalAntecedent


@rule("danglingDeixis")
def danglingDeixis(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """지시어가 있는데 바로 앞 문장과 화제어가 하나도 겹치지 않는 자리.

    왜: 이것 이 가리킬 것이 앞 문장에 없다. 독자는 되돌아가도 못 찾는다. 지시어 가운데 가장 나쁜 꼴이다.
    어디서: 지문 계층이 처음 가능하게 한 규칙이다. 앞 문장 화제어 집합과의 자카드 중첩이 0 이면 짚는다.
        블로그 004 실측에서 사람 평가자가 네 라운드 내내 지시어를 집었다.
    고치기: 가리키는 대상의 이름을 쓴다. 앞 문장에 그 이름이 없다면 앞 문장에 먼저 세운다.
    안 잡는 것: 앞 문장과 화제어가 겹치는 지시어는 deixis 가 짚는다. 글의 첫 문장은 앞이 없으므로 여기서
        잡는다.
    """
    for sentence in doc.sentences:
        if not sentence.deixis:
            continue
        if hasLocalAntecedent(sentence):
            continue
        previous = doc.sentences[sentence.index - 1] if sentence.index > 0 else None
        if previous is not None and overlap(previous.topics, sentence.topics) > 0.0:
            continue
        yield Finding(
            "danglingDeixis",
            sentence.line,
            sentence.text,
            f"`{sentence.deixis[0]}` {fitJosa(sentence.deixis[0], '이')} 가리킬 것이 앞 문장에 없다. "
            "가리키는 파일, 값, 코드의 이름을 쓴다",
            None,
            "error",
            SENTENCE,
            sentence.index,
            candidates=danglingDeixisCandidates(sentence, previous),
        )
