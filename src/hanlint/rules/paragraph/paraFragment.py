from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint, ParagraphPrint
from ..finding import PARAGRAPH, Finding
from ..registry import rule


@rule("paraFragment", mechanism="repeat")
def paraFragment(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """한두 문장짜리 산문 문단이 fragmentRun 개 이상 연달아 오는 자리.

    왜: 설명글에 줄바꿈을 마구 넣으면 이유로 이어야 할 문장 사이가 전부 끊긴다. 독자는 조각 사이의
        관계를 다시 세워야 한다.
    어디서: 운영자 규칙 (설명글은 줄바꿈을 막 쳐넣지 않는다). 글쓰기 스킬의 설명을 풀어 쓰기. 임계는
        config.fragmentRun.
    고치기: 화제가 같으면 한 문단으로 묶는다. 줄바꿈은 화제가 바뀌는 자리에만 둔다.
    안 잡는 것: 사이에 코드 블록이나 표가 끼면 줄을 다시 센다. 코드 앞뒤에 한 문장씩 놓는 것은 조각남이
        아니라 설명이다. 목록은 세지 않는다.
    """
    for section in doc.sections:
        run: list[ParagraphPrint] = []
        for paragraph in section.paragraphs:
            short = paragraph.sentenceCount <= 2
            if short and (not run or paragraph.followsProseDirectly):
                run.append(paragraph)
            elif short:
                run = [paragraph]
            else:
                run = []
            if len(run) == config.fragmentRun:
                first = run[0]
                yield Finding(
                    "paraFragment",
                    first.startLine,
                    first.sentences[0].text if first.sentences else "",
                    f"{len(run)}개 문단이 연달아 한두 문장씩이다. 화제가 같으면 한 문단으로 묶는다. "
                    "줄바꿈은 화제가 바뀌는 자리에만",
                    None,
                    "error",
                    PARAGRAPH,
                    first.index,
                )
