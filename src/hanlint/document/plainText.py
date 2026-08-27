"""산문에서 마크다운 표식을 걷어 문장 분석에 넣을 수 있게 만든다.

인라인 코드는 백틱만 떼고 내용은 남긴다. 지우면 `sales.csv 를 읽습니다` 가 `를 읽습니다` 로 조각나 인용이
깨지고, 다른 낱말을 넣으면 그 낱말이 검사에 걸린다. 식별자는 영문과 숫자라 한국어 규칙에 걸리지 않고
화제어로는 쓸모가 있다. 링크는 보이는 글자만 남긴다. 강조 표식은 뗀다. 줄바꿈은 남겨 줄 번호 계산에 쓴다.
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
