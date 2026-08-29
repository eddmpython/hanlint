from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("headingQuestion", mechanism="repeat")
def headingQuestion(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """H2 셋 이상 가운데 headingQuestionRatio 넘게 물음표로 끝나는 목차.

    왜: 절 제목을 전부 질문으로 도배하면 순서가 있는 과정이 아니라 FAQ 로 보인다. 독자는 목차를 훑어
        출발점에서 결과까지 가는 길을 찾는데, 질문만 늘어서면 어느 것을 먼저 읽어야 하는지 알 수 없다.
    어디서: cinch 의 전역 blog-writing 스킬, 사실과 목소리. 절 제목을 전부 질문으로 도배하면 순서가 있는
        과정이 아니라 FAQ 로 보인다. headingUniform 의 반대쪽이다. 임계는 config.headingQuestionRatio.
    고치기: 질문 제목을 절반 아래로 줄이고 나머지는 행동이나 결과로 바꾼다. 오류 원인 찾기, pandas 가
        멈추는 자리처럼 형태를 섞는다.
    안 잡는 것: H2 가 둘 이하인 글. 정말 FAQ 문서라면 이 규칙을 끈다. 본문 문장의 물음표 수는 세지 않는다
        (그것은 noQuestion 이 반대쪽에서 본다).
    """
    headings = doc.headingsOfLevel(2)
    if len(headings) < 3:
        return
    asking = [text for _, text, _ in headings if text.rstrip().endswith("?")]
    if len(asking) / len(headings) <= config.headingQuestionRatio:
        return
    yield Finding(
        "headingQuestion",
        headings[0][2],
        " / ".join(asking),
        f"H2 {len(headings)}개 중 {len(asking)}개가 물음표로 끝난다. 목차가 과정이 아니라 FAQ 로 읽힌다. 형태를 섞는다",
        None,
        "error",
        DOCUMENT,
        -1,
    )
