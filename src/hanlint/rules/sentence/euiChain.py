from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule

ADJACENT = re.compile(r"[가-힣]+의\s+[가-힣]+의(?=[\s,.)\]]|$)")


@rule("euiChain", mechanism="threshold")
def euiChain(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """한 문장에 관형격 조사 의 가 셋 이상이거나, 의 로 끝나는 어절 둘이 붙어 있다 (회사의 팀의 결정).

    왜: 명사를 의 로 쌓으면 무엇이 무엇의 목적어인지 표시되지 않아 독자가 조사를 머릿속에서 끼워 넣는다.
    어디서: 글쓰기 스킬의 설명을 풀어 쓰기 (의 가 이어지면 문장으로 편다). 쿠버네티스 한국어 현지화 가이드
        (일본어 の 직역).
    고치기: 동사로 편다. 회사의 팀의 결정 은 회사에서 팀이 정한 것.
    안 잡는 것: 낱말 안의 의 (의미, 의사) 와 의 로 끝나는 낱말 (정의, 회의. 목록은 data/euiNouns.txt). 떨어져 있는
        의 둘 (글쓰기 규칙의 정본은 사용자 저장소의 스킬이다) 은 자연스러운 한국어라 잡지 않는다. 실측: 문서에서
        둘 기준이 오탐 4건을 냈다. surface 분석기는 의 뒤에 공백이 올 때만 세고 kiwi 는 JKG 태그를 센다.
    """
    for sentence in doc.sentences:
        if sentence.euiCount >= 3 or (sentence.euiCount >= 2 and ADJACENT.search(sentence.text)):
            yield Finding(
                "euiChain",
                sentence.line,
                sentence.text,
                f"한 문장에 `의` 가 {sentence.euiCount}번이다. 명사를 쌓은 자리라 관계가 표시되지 않는다. 동사로 편다",
                None,
                "error",
                SENTENCE,
                sentence.index,
            )
