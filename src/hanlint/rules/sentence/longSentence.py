from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, SENTENCE, Finding
from ..registry import rule


@rule("longSentence")
def longSentence(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """어절 수가 longSentenceMax 를 넘는 문장.

    왜: 문장이 길면 독자가 주어와 서술어를 잇느라 되돌아간다. 짧은 문장과 긴 문장을 섞으라는 규칙의 상한이다.
    어디서: 실측. 블로그 다섯 편의 최장 문장이 23, 33, 23, 26, 45 어절이었고 30 을 넘는 둘은 읽어 보니 한 문장에
        목록 넷을 넣은 것이었다. 임계는 config.longSentenceMax.
    고치기: 마침표로 끊는다. 나열이면 목록으로 꺼낸다.
    안 잡는 것: 임계 아래 문장. 코드와 표. 글쓰기 규칙의 위반이 아니라 신호라 notice 로 낸다.
    """
    for sentence in doc.sentences:
        if sentence.length > config.longSentenceMax:
            yield Finding(
                "longSentence",
                sentence.line,
                sentence.text,
                f"어절 {sentence.length}개다. 상한은 {config.longSentenceMax}. 마침표로 끊거나 나열이면 목록으로 꺼낸다",
                None,
                NOTICE,
                SENTENCE,
                sentence.index,
            )
