from __future__ import annotations

from collections.abc import Iterator

from ...analysis.grammar import fitJosa
from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.sentencePrint import SentencePrint
from ...fingerprint.topics import overlap
from ..finding import SENTENCE, Finding
from ..registry import rule
from ..shared import danglingDeixisCandidates, hasLocalAntecedent

QUESTION = "의문"
"""markers.moodOf 가 물음에 붙이는 값. 문장이 `?` 로 끝나는 경우도 여기 든다."""

EXCLAIM = ("!", "！")


def isPrompt(previous: SentencePrint | None) -> bool:
    """앞 문장이 물음이나 감탄인가. 그러면 그 문장 자체가 지시어의 선행어다.

    왜: `왜일까요?` 다음의 `이것은` 은 되돌아갈 데가 없는 것이 아니라 방금 그 물음을 가리킨다.
        낱말이 안 겹치는 것이 당연하고, 그것이 결함이 아니다.
    어디서: 실측. 2026-08-28 말뭉치 20건을 읽어 오탐 셋을 찾았고 그 가운데 둘이 이 꼴이었는데
        판정만 tests/_attempts/corpus/judgments.toml 에 남고 구현이 없었다. 2026-08-31 에 다시 재니
        발화 987건 가운데 48건 (4.9%) 이 이 꼴이다. 수필 10.2%, 소설 8.0%, 안내와 문서는 0%다.
    """
    if previous is None:
        return False
    return previous.mood == QUESTION or previous.text.rstrip().endswith(EXCLAIM)


@rule("danglingDeixis", mechanism="reader")
def danglingDeixis(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """지시어가 든 문장인데 바로 앞 문장과 화제어가 하나도 겹치지 않는 경우.

    왜: `이것`이 가리킬 것이 앞 문장에 없다. 독자는 되돌아가도 찾지 못한다. 지시어 가운데 가장 나쁜 경우다.
    어디서: 독자가 바로 앞에서 읽은 화제어와 이 문장의 화제어를 비교해 겹치는 것이 하나도 없으면 짚는다. 실제
        블로그 글을 사람 평가자가 네 차례 검토했는데 네 번 모두 지시어를 지적했다.
    고치기: 가리키는 대상의 이름을 쓴다. 앞 문장에 그 이름이 없다면 앞 문장에 먼저 세운다.
    안 잡는 것: 앞 문장과 화제어가 겹치는 지시어는 deixis가 짚는다. 글의 첫 문장은 앞이 없으므로 여기서
        잡는다. 앞 문장이 물음이나 감탄이면 그 문장을 가리키는 것이라 단어가 안 겹쳐도 잡지 않는다.
    """
    for sentence in doc.sentences:
        if not sentence.deixis:
            continue
        if hasLocalAntecedent(sentence):
            continue
        reader = doc.reader.beforeSentence[sentence.index]
        if overlap(reader.recent, sentence.topics) > 0.0:
            continue
        if isPrompt(reader.previous):
            continue
        yield Finding(
            "danglingDeixis",
            sentence.line,
            sentence.text,
            f"`{sentence.deixis[0]}`{fitJosa(sentence.deixis[0], '이')} 가리킬 것이 앞 문장에 없다. "
            "가리키는 파일, 값, 코드의 이름을 쓴다",
            None,
            "error",
            SENTENCE,
            sentence.index,
            candidates=danglingDeixisCandidates(sentence, reader.previous),
        )
