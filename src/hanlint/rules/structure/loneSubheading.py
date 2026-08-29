from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.topics import topicsOf
from ..finding import NOTICE, SECTION, Finding
from ..registry import rule


def onlyChild(headings: tuple[tuple[int, str, int], ...]) -> Iterator[tuple[str, str, int]]:
    """(부모 H2 제목, 외동 H3 제목, 그 줄). H2 하나 아래 H3 이 정확히 하나일 때만."""
    for position, (level, text, _) in enumerate(headings):
        if level != 2:
            continue
        children = []
        for childLevel, childText, childLine in headings[position + 1 :]:
            if childLevel <= 2:
                break
            if childLevel == 3:
                children.append((childText, childLine))
        if len(children) == 1:
            yield text, children[0][0], children[0][1]


@rule("loneSubheading", mechanism="contrast")
def loneSubheading(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """H2 아래 소제목이 하나뿐이고 그 제목이 절 제목의 말을 되풀이하는 자리.

    왜: 소제목은 절 안을 나누려고 둔다. 하나뿐이면 나눈 것이 없고, 그 하나가 절 제목과 같은 말이면
        독자는 같은 제목을 두 번 읽는다. 목차만 길어지고 얻는 것이 없다.
    어디서: cinch 의 전역 blog-writing 스킬, 블로그 글의 뼈대 마지막 문장. 한 절 아래에 소제목이 하나뿐이고
        같은 뜻을 되풀이하면 소제목을 지운다.
    고치기: 소제목을 지우고 본문을 절 제목 아래로 올린다. 정말 둘로 나뉘면 소제목을 하나 더 만든다.
    안 잡는 것: 소제목이 둘 이상인 절. H4 이하. 절 제목에 없는 말이 소제목에 하나라도 있으면 새 이야기를 여는
        것이므로 하나여도 제 몫을 한다. 실측: 002 의 `AI에게 원문과 이 페이지 주소 보내기` 아래 `AI에게 보낼
        요청 예시` 는 `AI` 하나만 겹치고 `요청` 과 `예시` 를 새로 꺼내므로 오탐이었다. 화제어는 근사라
        notice 로만 낸다.
    """
    for parent, child, line in onlyChild(doc.headings):
        childTopics = topicsOf(child)
        if not childTopics or not childTopics <= topicsOf(parent):
            continue
        yield Finding(
            "loneSubheading",
            line,
            child,
            f"`{parent}` 아래 소제목이 이것 하나뿐이고 절 제목에 없는 말이 하나도 없다. 소제목을 지우고 본문을 올린다",
            None,
            NOTICE,
            SECTION,
            -1,
        )
