from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.markers import insideAny, matchedSpans
from ..finding import SENTENCE, Finding
from ..registry import rule


@rule("draftHistory", mechanism="dictionary")
def draftHistory(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """글쓴이의 수정 이력과 자기 검증 기록. 처음에는 ~라고 썼습니다, ~것을 확인했습니다.

    왜: 독자는 초고를 본 적이 없다. 무엇을 어떻게 고쳤는지는 독자가 지금 하려는 일과 아무 관계가 없고,
        글쓴이가 직접 확인했다는 보고도 독자가 자기 화면에서 할 일을 대신해 주지 못한다. 알아낸 사실만
        결과 문장으로 남기고 알아낸 과정은 뺀다.
    어디서: cinch 의 전역 blog-writing 스킬, 무엇을 빼는가의 반드시 빼는 것 첫 항목. 실측 사례는 블로그 004 의
        `ibis-framework[duckdb] 만 설치한 환경에서 아래 코드가 그대로 도는 것을 확인했습니다` 로, 평가자가
        3라운드에서 글쓴이의 자기 검증 기록으로 읽힌다고 집었다. 표지 목록은 data/draftHistory.txt.
    고치기: 알아낸 사실만 남긴다. `확인했습니다` 를 지우고 그 사실을 바로 쓴다. 독자가 할 일이면 `확인해
        보세요` 로 시킨다. 과정을 남기고 싶으면 회고 글로 따로 뺀다.
    안 잡는 것: 수치의 출처를 밝히는 문장 (`일곱 번씩 재서 가운데 값을 적었습니다`). 사실 확인은 글쓰기
        규칙이 요구하는 것이라 재는 방법은 남긴다. 인용 안의 같은 표현.
    """
    for sentence in doc.sentences:
        for start, end, text in matchedSpans(sentence.text, "draftHistory.txt"):
            if insideAny(start, end, sentence.quoted):
                continue
            yield Finding(
                "draftHistory",
                sentence.line,
                sentence.text,
                f"`{text}` 는 글쓴이의 과정이다. 독자는 초고를 본 적이 없다. 알아낸 사실만 결과 문장으로 남긴다",
                None,
                "error",
                SENTENCE,
                sentence.index,
            )
