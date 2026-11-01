from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, SENTENCE, Finding
from ..registry import rule
from ..shared import longSentenceCandidates


@rule("longSentence", mechanism="threshold")
def longSentence(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """30어절을 넘는 문장.

    왜: 문장이 길면 독자가 주어와 서술어를 잇느라 되돌아간다. 짧은 문장과 긴 문장을 섞으라는 규칙의 상한이다.
    어디서: 실측. 블로그 다섯 편의 가장 긴 문장이 23, 33, 23, 26, 45어절이었고 30어절을 넘는 둘은 읽어 보니 한
        문장에 목록 넷을 넣은 것이었다. 상한은 설정 longSentenceMax(기본 30)로 바꾼다.
    고치기: 마침표로 끊는다. 나열이면 목록으로 꺼낸다.
    안 잡는 것: 상한 이하의 문장. 코드와 표. 글쓰기 규칙을 어긴 것이 아니라 살펴볼 곳이라 확인 권고로 낸다.
    """
    for sentence in doc.sentences:
        if sentence.length > config.longSentenceMax:
            yield Finding(
                "longSentence",
                sentence.line,
                sentence.text,
                f"어절이 {sentence.length}개로 상한 {config.longSentenceMax}개를 넘는다. "
                "마침표로 끊거나 나열이면 목록으로 꺼낸다",
                None,
                NOTICE,
                SENTENCE,
                sentence.index,
                candidates=longSentenceCandidates(sentence.text),
            )
