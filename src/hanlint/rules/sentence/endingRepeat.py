from __future__ import annotations

from collections.abc import Iterator

from ...analysis.grammar import fitJosa
from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, SENTENCE, Finding
from ..registry import rule
from ..shared import runsOf

COUNTED_ENDINGS = frozenset({"니다", "다", "것이다", "요", "죠"})


@rule("endingRepeat", mechanism="repeat")
def endingRepeat(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """같은 종결어미로 끝나는 문장 4개가 까닭을 잇는 말도 질문도 독자를 부르는 말도 없이 이어지는 곳.

    왜: `습니다`가 네 번 이어지고 그 사이에 까닭을 잇는 말도 독자를 부르는 말도 없으면 글이 단조로워지고 사실이
        나란히 놓이기만 한다. 서너 문장에 한 번은 앞뒤를 까닭으로 잇는 문장이 있어야 읽힌다.
    어디서: AI 문체 신호 조사(im-not-ai E-2 동일 종결어미 4문장 이상, gist 패턴35), 경희대 글쓰기 교육의
        `것이다` 반복. 짧은 문장만 늘어놓지 않는다는 글쓰기 원칙. 몇 문장부터 잡을지는 설정 endingRun(기본 4)이
        정한다.
    고치기: 하나를 질문으로 바꾸거나, 두 문장을 까닭으로 잇거나, 독자가 할 행동을 동사로 끝낸다.
    안 잡는 것: 까닭을 잇는 말(`그래서`, `때문에`)이나 독자를 부르는 말이 든 문장. 그 문장이 연속을 끊는다.
        어미가 같아도 까닭으로 이어져 있으면 단조롭지 않다. 실측: 이 조건을 넣기 전에는 발행한 글 다섯 편에서
        56건이 나왔고 그중 대부분이 합니다체 자체를 센 것이었다. 명령형과 의문형의 연속. 종결어미를 정하지 못한
        문장. 글쓰기 규칙을 어긴 것이 아니라 리듬을 살펴볼 곳이라 확인 권고로 낸다.
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
                f"`{ending}`{fitJosa(ending, '로')} 끝나는 문장 {length}개에 까닭을 잇는 말도 질문도 독자를 부르는 말도 없다. "
                "질문, 까닭을 잇는 말, 행동 동사로 리듬을 바꾼다",
                None,
                NOTICE,
                SENTENCE,
                first.index,
            )
