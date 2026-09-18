from __future__ import annotations

from collections.abc import Iterator

from ...analysis import nounRuns
from ...config import Config
from ...fingerprint import DocumentPrint
from ...usage import attested, usageKindOf
from ..finding import SENTENCE, Finding
from ..registry import rule


@rule("nounPile", mechanism="threshold")
def nounPile(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """명사가 조사 없이 nounPileMin 개 이상 이어진 자리. 그 종류의 글에서 관용인 연쇄는 짚지 않는다.

    왜: 가상환경 생성 후 패키지 설치 확인 은 무엇이 무엇의 목적어인지 표시되어 있지 않다. 독자가 조사를
        끼워 넣어야 읽힐 수 있다. 표층 근사라 기본 notice이며 enforceStyle로 선택한 정책에서만 error다.
    어디서: 글쓰기 스킬의 설명을 풀어 쓰기 (명사를 쌓지 말고 동사로 되돌린다). im-not-ai A-13, F-4.
        임계는 config.nounPileMin. 파이썬 데이터프레임 라이브러리 가 넷이라 다섯부터 짚는다 (PRD 부록 A).
    고치기: 동사로 되돌린다. 가상환경을 만든 뒤 패키지가 설치됐는지 확인한다.
    안 잡는 것: 쉼표로 나열한 고유명사 (pandas, Polars, DuckDB). 쉼표가 연속을 끊는다. 임계 아래의 복합어.
        용례가 있는 연쇄: 문장의 긴 연쇄가 전부 그 종류의 빈도표 (data/usageCounts.<종류>.json) 에 usageMin 편
        이상의 문서로 있으면 관용이다. 정관상 배당절차 개선방안 이행 가부 는 사업보고서의 낱말이지 쌓은 것이 아니다.
        종류는 프리셋이 정한다 (config.USAGE_OF, report 만). 실측: 사업보고서 961편 747,583문장에서 접기 전
        1,000문장당 6.2건, 접은 뒤 4.8건이다 (22.6% 감소). 접힌 것은 양식의 항목 이름 (정관상 배당절차 개선방안 이행
        가부, 661편) 과 관용 용어 (무기명식 이권부 무보증 사모 전환사채, 17편) 이고 남은 것은 한 회사의 사업 이름 같은
        고유한 쌓기다 (2026-09-19, scripts/measure/reports.py).
    """
    kind = usageKindOf(config)
    for sentence in doc.sentences:
        if sentence.nounRun < config.nounPileMin:
            continue
        if kind:
            piles = [chain for chain, length in nounRuns(sentence.text) if length >= config.nounPileMin]
            if piles and all(attested(chain, kind, config.usageMin) for chain in piles):
                continue
        yield Finding(
            "nounPile",
            sentence.line,
            sentence.text,
            f"명사 {sentence.nounRun}개가 조사 없이 이어진다. 관계가 표시되지 않아 독자가 조사를 끼워 넣는다. 동사로 되돌린다",
            None,
            "error" if "nounPile" in config.enforceStyle else "notice",
            SENTENCE,
            sentence.index,
        )
