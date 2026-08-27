from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule

SENTENCE_ENDINGS = ("니다", "세요", "십시오", "합시다", ".")


@rule("headingSentence")
def headingSentence(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """본문 문장을 그대로 복사한 절 제목.

    왜: 절 제목은 간단명료하게 쓴다. 합니다, 하세요 로 끝나는 제목은 목차에서 대상이 안 보이고 본문과
        같은 문장이 두 번 읽힌다.
    어디서: 운영자 규칙 (섹션 타이틀은 간단명료하게). 글쓰기 스킬의 절 제목 규칙.
    고치기: 대상이나 질문을 짧게 쓴다. 파일을 엽니다 는 파일 열기, 왜 파일이 열리지 않을까.
    안 잡는 것: 물음표로 끝나는 질문 제목. 명사로 끝나는 제목.
    """
    for _, text, line in doc.headings:
        if text.rstrip().endswith(SENTENCE_ENDINGS):
            yield Finding(
                "headingSentence",
                line,
                text,
                "절 제목이 본문 문장을 복사했다. 대상이나 질문을 짧게 쓴다",
                None,
                "error",
                DOCUMENT,
                -1,
            )
