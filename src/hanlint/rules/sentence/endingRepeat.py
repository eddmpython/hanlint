from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, SENTENCE, Finding
from ..registry import rule
from ..shared import runsOf

COUNTED_ENDINGS = frozenset({"니다", "다", "것이다", "요", "죠"})


@rule("endingRepeat")
def endingRepeat(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """같은 종결어미로 끝나는 문장이 한 절 안에 endingRun 개 이상 이어지는 자리.

    왜: 습니다 가 네 번 이어지면 리듬이 죽고 AI 가 쓴 글처럼 읽힌다. 짧은 문장과 긴 문장, 평서와 질문을
        섞으라는 규칙의 기계 판이다.
    어디서: AI 문체 신호 조사 (im-not-ai E-2 동일 종결어미 4문장 이상, gist 패턴35), 경희대 글쓰기 교육의
        것이다 반복. 임계는 config.endingRun.
    고치기: 하나를 질문으로 바꾸거나, 두 문장을 인과로 잇거나, 독자가 할 행동을 동사로 끝낸다.
    안 잡는 것: 명령형과 의문형의 연속. 종결어미를 못 정한 문장 (없음) 은 연속을 끊는다. 글쓰기 규칙의
        위반이 아니라 리듬 신호라 notice 로 낸다. 참고 문서는 다 로 끝나는 것이 정상이다.
    """
    for section in doc.sections:
        sentences = [s for p in section.paragraphs for s in p.sentences]
        endings = [s.ending if s.ending in COUNTED_ENDINGS else f"__{s.index}" for s in sentences]
        for start, length, ending in runsOf(endings, config.endingRun):
            first = sentences[start]
            yield Finding(
                "endingRepeat",
                first.line,
                first.text,
                f"`{ending}` 로 끝나는 문장이 {length}개 이어진다. 질문, 인과, 행동 동사로 리듬을 바꾼다",
                None,
                NOTICE,
                SENTENCE,
                first.index,
            )
