from __future__ import annotations

from collections.abc import Iterator

from ...analysis import euiAdjacent
from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import SENTENCE, Finding
from ..registry import rule


@rule("euiChain", mechanism="threshold")
def euiChain(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """한 문장에 조사 `의`가 세 번 이상 나오거나 `의`로 끝나는 어절 둘이 붙어 있는 곳(`회사의 팀의 결정`).

    왜: 명사를 `의`로 쌓으면 무엇이 무엇의 목적어인지 표시되지 않아 독자가 조사를 머릿속에서 끼워 넣는다.
    어디서: `의`가 이어지면 문장으로 편다는 글쓰기 원칙. 쿠버네티스 한국어 현지화 가이드(일본어 の 직역).
    고치기: 동사로 편다. `회사의 팀의 결정`은 `회사에서 팀이 정한 것`으로 쓴다.
    안 잡는 것: 단어 안의 `의`(`의미`, `의사`)와 `의`로 끝나는 단어(`정의`, `회의`. 목록은 data/euiNouns.txt).
        떨어져 있는 `의` 둘(`글쓰기 규칙의 기준은 사용자 저장소의 스킬이다`)은 자연스러운 한국어라 잡지 않는다.
        실측: `의` 두 번을 기준으로 삼았더니 문서에서 오탐이 4건 났다.
    """
    for sentence in doc.sentences:
        if sentence.euiCount >= 3 or (sentence.euiCount >= 2 and euiAdjacent(sentence.text)):
            yield Finding(
                "euiChain",
                sentence.line,
                sentence.text,
                f"한 문장에 `의`가 {sentence.euiCount}번이다. 명사를 쌓은 문장이라 관계가 표시되지 않는다. 동사로 편다",
                None,
                "error",
                SENTENCE,
                sentence.index,
            )
