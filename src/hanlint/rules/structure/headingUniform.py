from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("headingUniform")
def headingUniform(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """H2 셋 이상 가운데 headingUniformRatio 넘게 같은 글자로 끝나는 목차.

    왜: 목차 전체가 기 로 끝나면 순서가 있는 과정이 아니라 같은 항목의 나열로 읽힌다.
    어디서: 실측. 블로그 004 의 H2 여덟 개 중 일곱 개가 기 로 끝났고 목차가 한 박자로만 읽혔다. 글쓰기
        스킬의 절 제목 규칙 (예시의 어미를 규칙으로 삼지 않는다). 임계는 config.headingUniformRatio.
    고치기: 형태를 섞는다. 오류 원인 찾기, 왜 파일이 열리지 않을까, pandas 가 멈추는 자리.
    안 잡는 것: H2 가 둘 이하인 글. H3 이하. 숫자로 끝나는 제목 (`[0.0.2] - 2026-08-27` 같은 CHANGELOG
        절이 실측 사례다. 버전과 날짜는 어미가 아니다).
    """
    headings = doc.headingsOfLevel(2)
    # 버전이나 날짜처럼 숫자로 끝나는 제목은 어미가 아니라 판정에서 뺀다.
    eligible = [(line, text, at) for line, text, at in headings if text.strip() and not "0" <= text.rstrip()[-1] <= "9"]
    if len(eligible) < 3:
        return
    lastChars = Counter(text.rstrip()[-1] for _, text, _ in eligible)
    char, count = lastChars.most_common(1)[0]
    if count / len(eligible) >= config.headingUniformRatio:
        yield Finding(
            "headingUniform",
            eligible[0][2],
            " / ".join(text for _, text, _ in eligible),
            f"H2 {len(eligible)}개 중 {count}개가 `{char}` 로 끝난다. 목차가 한 어미로 끝나면 과정이 아니라 나열로 읽힌다. "
            "형태를 섞는다",
            None,
            "error",
            DOCUMENT,
            -1,
        )
