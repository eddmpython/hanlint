from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import PARAGRAPH, Finding
from ..registry import rule
from ..shared import runsOf


@rule("paraFragment", mechanism="repeat")
def paraFragment(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """한두 문장짜리 산문 문단이 3개 이상 연달아 오는 곳.

    왜: 설명글에 줄바꿈을 마구 넣으면 이유로 이어야 할 문장 사이가 모두 끊긴다. 독자는 조각 사이의 관계를 다시
        세워야 한다.
    어디서: 설명글에는 줄바꿈을 함부로 넣지 않는다는, 글을 검토한 사람이 정한 규칙이다. 설명을 풀어 쓴다는 블로그
        쓰기 방식도 같은 것을 요구한다. 기준값은 설정 fragmentRun(기본 3)이다.
    고치기: 화제가 같으면 한 문단으로 묶는다. 줄바꿈은 화제가 바뀌는 곳에만 둔다.
    안 잡는 것: 사이에 코드 블록이나 표가 끼면 처음부터 다시 센다. 코드 앞뒤에 한 문장씩 놓는 것은 글을 조각낸 것이
        아니라 설명이다. 목록은 세지 않는다.
    """
    for section in doc.sections:
        paragraphs = section.paragraphs
        # 열쇠는 짧은 문단의 구간 번호다. 코드나 표 뒤의 짧은 문단과 긴 문단 뒤의 짧은 문단은 새 구간을 연다.
        keys: list[str] = []
        runId = 0
        previousShort = False
        for paragraph in paragraphs:
            short = paragraph.sentenceCount <= 2
            if short:
                if not previousShort or not paragraph.followsProseDirectly:
                    runId += 1
                keys.append(f"short{runId}")
            else:
                keys.append(f"__{paragraph.index}")
            previousShort = short
        for start, _, _ in runsOf(keys, config.fragmentRun):
            first = paragraphs[start]
            yield Finding(
                "paraFragment",
                first.startLine,
                first.sentences[0].text if first.sentences else "",
                f"{config.fragmentRun}개 문단이 연달아 한두 문장씩이다. 화제가 같으면 한 문단으로 묶는다. "
                "줄바꿈은 화제가 바뀌는 곳에만 둔다",
                None,
                "error",
                PARAGRAPH,
                first.index,
            )
