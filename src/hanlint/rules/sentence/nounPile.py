from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule


@rule("nounPile")
def nounPile(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """명사가 조사 없이 nounPileMin 개 이상 이어진 자리.

    왜: 가상환경 생성 후 패키지 설치 확인 은 무엇이 무엇의 목적어인지 표시되어 있지 않다. 독자가 조사를
        끼워 넣어야 읽힌다.
    어디서: 글쓰기 스킬의 설명을 풀어 쓰기 (명사를 쌓지 말고 동사로 되돌린다). im-not-ai A-13, F-4.
        임계는 config.nounPileMin. 파이썬 데이터프레임 라이브러리 가 넷이라 다섯부터 짚는다 (PRD 부록 A).
    고치기: 동사로 되돌린다. 가상환경을 만든 뒤 패키지가 설치됐는지 확인한다.
    안 잡는 것: 쉼표로 나열한 고유명사 (pandas, Polars, DuckDB). 쉼표가 연속을 끊는다. 임계 아래의 복합어.
    """
    for sentence in doc.sentences:
        if sentence.nounRun >= config.nounPileMin:
            yield Finding(
                "nounPile",
                sentence.line,
                sentence.text,
                f"명사 {sentence.nounRun}개가 조사 없이 이어진다. 관계가 표시되지 않아 독자가 조사를 끼워 넣는다. "
                "동사로 되돌린다",
                None,
                "error",
                SENTENCE,
                sentence.index,
            )
