from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("cliche")
def cliche(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """핵심은, 결국 중요한 것은, 단순히 A 를 넘어, 살펴보겠습니다 같은 상투어.

    왜: 문장이 하는 일 없이 매끈하기만 한 표현이다. 독자는 그 자리에서 정보를 받지 못하고 광고를 읽는
        기분이 든다. 살펴보겠습니다 뒤에 실제 행동이 없으면 문장째 지운다.
    어디서: 글쓰기 스킬의 AI 표현 제거 단계. AI 문체 신호 조사 (Wikipedia Signs of AI writing, gist 패턴4).
        사전은 data/cliches.toml 이고 설정의 dictionary.cliches 로 더한다.
    고치기: 그 표현이 맡은 일이 있으면 그 일을 직접 쓴다. 핵심은 X 다 는 X 다 로, 살펴보겠습니다 는
        살펴본 결과로.
    안 잡는 것: 사전에 없는 표현. 사전이 없어도 목적어가 흐린 문장은 나쁘지만 그것은 사람 평가자 몫이다.
    """
    yield from dictionaryFindings(doc, "cliches", "cliche")
