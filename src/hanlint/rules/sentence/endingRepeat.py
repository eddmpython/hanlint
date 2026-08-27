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
    """같은 종결어미가 endingRun 개 이어지는데 그 사이에 인과도 질문도 독자를 부르는 말도 없는 자리.

    왜: 습니다 가 네 번 이어지고 그 사이에 이유를 잇는 말도 독자에게 거는 말도 없으면 리듬이 멈추고 사실이
        나란히 놓이기만 한다. 서너 문장에 한 번은 앞뒤 인과를 잇는 문장이 있어야 읽힌다.
    어디서: AI 문체 신호 조사 (im-not-ai E-2 동일 종결어미 4문장 이상, gist 패턴35), 경희대 글쓰기 교육의
        것이다 반복. cinch 의 전역 blog-writing 스킬, 설명을 풀어 쓰기의 짧은 문장만 늘어놓지 않는다. 임계는
        config.endingRun.
    고치기: 하나를 질문으로 바꾸거나, 두 문장을 인과로 잇거나, 독자가 할 행동을 동사로 끝낸다.
    안 잡는 것: 인과 표지 (그래서, 때문에) 나 독자 호출이 든 문장. 그 문장이 연속을 끊는다. 어미가 같아도
        이유로 이어져 있으면 리듬이 산 것이다. 실측: 이 조건을 넣기 전 발행본 다섯 편에서 56건이 나왔고
        그중 대부분이 합니다체 자체를 센 것이었다. 명령형과 의문형의 연속. 종결어미를 못 정한 문장 (없음).
        글쓰기 규칙의 위반이 아니라 리듬 신호라 notice 로 낸다.
    """
    for section in doc.sections:
        sentences = [s for p in section.paragraphs for s in p.sentences]
        endings = [s.ending if s.ending in COUNTED_ENDINGS else f"__{s.index}" for s in sentences]
        for start, length, ending in runsOf(endings, config.endingRun):
            # 구간 어딘가에 이유를 잇는 말이나 독자를 부르는 말이 있으면 리듬이 산 것이다. 구간을 쪼개면
            # 조각마다 지적이 되어 오히려 늘어난다. 구간 전체를 하나로 보고 살린다.
            if any(s.causal or s.readerCall for s in sentences[start : start + length]):
                continue
            first = sentences[start]
            yield Finding(
                "endingRepeat",
                first.line,
                first.text,
                f"`{ending}` 로 끝나는 문장 {length}개에 인과도 질문도 독자를 부르는 말도 없다. "
                "질문, 인과, 행동 동사로 리듬을 바꾼다",
                None,
                NOTICE,
                SENTENCE,
                first.index,
            )
