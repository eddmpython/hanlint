from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("japaneseLoan", mechanism="dictionary")
def japaneseLoan(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """`구좌`, `익일`, `잔고`, `고참`, `망년회` 같은 일본어투 단어.

    왜: 순화어가 이미 자리 잡아 일본어투가 낡고 딱딱하게 읽힌다.
    어디서: 국립국어원 일본어 투 용어 순화 자료집 2005, 꼭 가려 써야 할 일본어 투 용어 50개 2019.
        사전은 data/japaneseLoan.toml에 있다.
    고치기: 순화어로 바꾼다. `구좌`는 `계좌`로, `익일`은 `다음 날`로 쓴다.
    안 잡는 것: 앞에 한글이 붙은 경우. `최고참`의 `고참`처럼 다른 단어의 일부일 수 있어 단어가 시작하는 곳을
        본다. 굳어진 한자어(`견적` 등)는 사전에 넣지 않았다.
        그 종류의 글이 거의 다 쓰는 항목은 짚지 않는다. report 프리셋에서는 사업보고서 문서의 90% 이상(설정
        usageShare)에 나온 항목이다.
    """
    yield from dictionaryFindings(doc, "japaneseLoan", "japaneseLoan", config=config)
