from __future__ import annotations

from collections.abc import Iterator

from ...analysis.grammar import fitJosa
from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule
from ..shared import shareOf


@rule("headingUniform", mechanism="repeat")
def headingUniform(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """H2가 셋 이상인 목차에서 75% 이상이 같은 글자로 끝나는 것.

    왜: 목차 전체가 `기`로 끝나면 순서가 있는 과정이 아니라 같은 항목의 나열로 읽힌다.
    어디서: 실제 블로그 글 하나에서 H2 여덟 개 가운데 일곱 개가 `기`로 끝나 목차가 같은 항목의 나열처럼 읽혔다.
        예시 제목의 어미를 그대로 따라 쓰지 않는다는 절 제목 쓰기 방식에서 왔다. 기준값은 설정
        headingUniformRatio(기본 0.75)다.
    고치기: 형태를 섞는다. `오류 원인 찾기`, `왜 파일이 열리지 않을까`, `pandas가 멈추는 곳`처럼 쓴다. 제목을 바꾸기
        전에 그 제목을 가리키는 곳이 있는지 본다. 실제 블로그 하나는 media.json이 절 제목으로 이미지를 묶고 있어
        제목만 고치자 이미지 연결이 깨졌다.
    안 잡는 것: H2가 둘 이하인 글과 H3 이하는 잡지 않는다. 한글 음절로 끝나지 않는 제목도 세지 않는다. 어미는
        한글이기 때문이다. 버전과 날짜(`[0.0.2] - 2026-08-27` 같은 CHANGELOG 절), 한자 독음 괄호로 닫은 수필 제목
        (`約婚[약혼]까지의 來歷[내력]`은 `]`로 끝난다), 라틴 약어로 닫은 제목(`소스 IP`)이 여기 든다. 셋 다 기준
        말뭉치에서 오탐이었다.
    경고로 내는 까닭: 제대로 잡은 목차와 잘못 잡은 목차가 겉으로 똑같다. `구현하기 / 사용하기 / 같이 보기`
        (제대로 잡은 것)와 `생성하기 / 적용하기 / 검증하기 / 정리하기`(쿠버네티스 태스크 문서의 관례)를 글자 모양으로는
        가르지 못한다. 그 목차가 순서 있는 과정인지 관례인지는 사람이 본다. 표본 20건 가운데 제대로 잡은 것은
        하나였다.
    """
    headings = doc.headingsOfLevel(2)
    # 어미는 한글이다. 숫자, 부호, 라틴 문자로 끝나는 제목은 판정에서 뺀다.
    eligible = [(line, text, at) for line, text, at in headings if text.strip() and "가" <= text.rstrip()[-1] <= "힣"]
    if len(eligible) < 3:
        return
    char, count, total = shareOf([text.rstrip()[-1] for _, text, _ in eligible])
    if count / total >= config.headingUniformRatio:
        yield Finding(
            "headingUniform",
            eligible[0][2],
            " / ".join(text for _, text, _ in eligible),
            f"H2 {len(eligible)}개 가운데 {count}개가 `{char}`{fitJosa(char, '로')} 끝난다. 목차가 한 어미로 끝나면 "
            "과정이 아니라 나열로 읽힌다. 그 문서의 관례라면 그대로 둔다",
            None,
            "notice",
            DOCUMENT,
            -1,
        )
