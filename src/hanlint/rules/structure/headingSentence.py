from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule

SENTENCE_ENDINGS = ("니다", "한다", "해요", "세요", "십시오", "합시다", ".")


@rule("headingSentence", mechanism="threshold")
def headingSentence(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """본문 문장을 그대로 복사한 절 제목.

    왜: 절 제목은 간단명료하게 쓴다. `합니다`, `하세요`로 끝나는 제목은 목차에서 대상이 안 보이고 본문과 같은
        문장이 두 번 읽힌다.
    어디서: 절 제목은 간단명료하게 쓴다는, 글을 검토한 사람이 정한 규칙이다.
    고치기: 대상이나 질문을 짧게 쓴다. `파일을 엽니다`는 `파일 열기`나 `왜 파일이 열리지 않을까`로 쓴다.
    안 잡는 것: 물음표로 끝나는 질문 제목과 명사로 끝나는 제목은 잡지 않는다. 설정 headingSentenceMaxLevel(기본 6)보다
        깊은 제목도 잡지 않는다. 절 제목 아래에 문장형 부제를 두는 형식(강의 교안의 H3 부제는 정한 형식에 따라 행동과
        결과를 말하는 문장이다)은 그 값을 2로 두어 H2까지만 본다. 실제 강의 글 여섯 편에서 이 부제 62개가 모두
        걸렸다.
    """
    for level, text, line in doc.headings:
        if level > config.headingSentenceMaxLevel:
            continue
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
