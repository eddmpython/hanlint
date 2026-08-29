from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("japaneseLoan", mechanism="dictionary")
def japaneseLoan(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """구좌, 익일, 잔고, 고참, 망년회 같은 일본어투 낱말.

    왜: 순화어가 이미 자리 잡아 일본어투가 낡고 딱딱하게 읽힌다.
    어디서: 국립국어원 일본어 투 용어 순화 자료집 2005, 꼭 가려 써야 할 일본어 투 용어 50개 2019.
        사전은 data/japaneseLoan.toml.
    고치기: 순화어로 바꾼다. 구좌 는 계좌, 익일 은 다음날.
    안 잡는 것: 앞뒤에 한글이 붙은 자리. 익일 은 잡지만 익일이라는 은 다른 낱말일 수 있어 두지 않고
        경계를 본다. 굳어진 한자어 (견적 등) 는 사전에 넣지 않았다.
    """
    yield from dictionaryFindings(doc, "japaneseLoan", "japaneseLoan")
