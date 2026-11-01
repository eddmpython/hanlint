from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("translationese", mechanism="dictionary")
def translationese(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """`~에 있어서`, `~에 의해`, `~을 통해`, `~로부터`, `~에도 불구하고` 같은 번역투.

    왜: 영어와 일본어 구문을 그대로 옮긴 표현이라 한국어로 읽을 때 매끄럽지 않다. 독자가 머릿속에서
        다시 번역한다.
    어디서: 국립국어원 새국어생활 1990과 2012, urimal.org 김민지 2020, egowriting 번역투 고치기,
        kubernetes.io 한국어 현지화 가이드. 사전은 data/translationese.toml에 있다.
    고치기: 항목마다 고친 예가 있다. `에 있어서`는 `에서`로, `음에도 불구하고`는 `지만`으로 쓴다. 기계가
        바꿀 수 있는 것은 `hanlint fix`가 고친다. `로부터`는 받는 사람이면 `에게`, 출발점이면 `에서`라 기계가
        고르지 않는다.
    안 잡는 것: 사전에 없는 번역투. 무생물 주어 타동사 구문처럼 구문 분석이 필요한 것은 잡지 않는다. 그 종류의
        글이 거의 다 쓰는 항목은 그 종류의 말이라 짚지 않는다. report 프리셋에서는 사업보고서 문서의 90%
        이상(설정 usageShare)에 나온 항목(`에 대한`, `을 통해`, `로부터`, `에 관한`, `로 인해`, `을 위해`, `에 대해`,
        `에 의해`)이다. 실측: 사업보고서 200편 171,276문장에서 번역투 지적은 1,000문장당 289.8건이었고 그중
        254건이 이 여덟 항목이었다.
    """
    yield from dictionaryFindings(doc, "translationese", "translationese", config=config)
