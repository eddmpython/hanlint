"""산문에서 마크다운 표식을 걷어 문장 분석에 넣을 수 있게 만든다.

인라인 코드는 백틱만 떼고 내용은 남긴다. 지우면 `sales.csv 를 읽습니다` 가 `를 읽습니다` 로 조각나 인용이
깨지고, 다른 낱말을 넣으면 그 낱말이 검사에 걸린다. 식별자는 영문과 숫자라 한국어 규칙에 걸리지 않고
화제어로는 쓸모가 있다. 링크는 보이는 글자만 남긴다. 강조 표식은 뗀다. 줄바꿈은 남겨 줄 번호 계산에 쓴다.

인라인 코드가 있던 자리는 `codeSpans` 로 다시 찾는다. 백틱 안은 사용이 아니라 인용이라 사전 규칙과 지시어
규칙이 건너뛴다 (실측: 002 가 상투어를 백틱으로 인용하자 네 건이 잡혔다).
"""

from __future__ import annotations

import re

INLINE_CODE = re.compile(r"`([^`\n]*)`")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
EMPHASIS = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")
SINGLE_EMPHASIS = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])")
SPACES = re.compile(r"[ \t]+")


def plainText(text: str) -> str:
    text = INLINE_CODE.sub(r"\1", text)
    text = LINK.sub(r"\1", text)
    text = EMPHASIS.sub(r"\2", text)
    text = SINGLE_EMPHASIS.sub(r"\1", text)
    return SPACES.sub(" ", text).strip()


def codeSpans(raw: str, plain: str) -> tuple[tuple[int, int], ...]:
    """원문의 인라인 코드 내용이 plain 안에서 차지하는 (시작, 끝). 앞에서부터 차례로 찾고 못 찾으면 건너뛴다."""
    spans: list[tuple[int, int]] = []
    cursor = 0
    for match in INLINE_CODE.finditer(raw):
        needle = SPACES.sub(" ", match.group(1))
        if not needle:
            continue
        at = plain.find(needle, cursor)
        if at < 0:
            continue
        spans.append((at, at + len(needle)))
        cursor = at + len(needle)
    return tuple(spans)
