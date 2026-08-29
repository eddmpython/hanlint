from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...document import plainText
from ...document.model import LIST
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, SECTION, Finding
from ..registry import rule

BULLET = re.compile(r"^\s*(?:[-*+]|[0-9]+[.)])\s+")


def itemsOf(text: str) -> list[tuple[int, str]]:
    """(블록 안 줄 번호 오프셋, 항목 전체). 이어지는 줄은 앞 항목에 붙인다."""
    items: list[tuple[int, str]] = []
    for offset, line in enumerate(text.split("\n")):
        if BULLET.match(line):
            items.append((offset, BULLET.sub("", line).strip()))
        elif items and line.strip():
            index, body = items[-1]
            items[-1] = (index, f"{body} {line.strip()}")
    return items


@rule("moreLater", mechanism="threshold")
def moreLater(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """마지막 절의 목록 항목이 moreLaterMaxChars 를 넘어 본문만큼 설명하는 것.

    왜: 글 끝의 목록은 본문에서 뺀 것의 갈 곳이다. 무엇을 할 수 있는지 한 줄과 링크나 코드 한 줄이면 된다.
        항목이 본문 문단만큼 길어지면 미룬 것이 아니라 옮겨 적은 것이고, 결말로 닫힌 글이 다시 열린다.
    어디서: cinch 의 전역 blog-writing 스킬, 무엇을 빼는가. 목록 항목이 본문만큼 설명하면 미룬 것이 아니라
        옮겨 적은 것이다. 임계는 config.moreLaterMaxChars 이고 실측으로 정했다 (다섯 편의 마지막 절 항목
        24개가 17~196자, 149자부터가 문장 셋 이상).
    고치기: 항목을 한 줄로 줄이고 자세한 것은 링크나 코드 한 줄로 넘긴다. 정말 본문에 있어야 하면 본문 절로 올린다.
    안 잡는 것: 마지막 절이 아닌 곳의 목록 (본문 목록은 설명의 일부다). 목록이 없는 마지막 절. 한 글에 한 번만
        낸다. 길이는 근사라 notice 로만 낸다.
    """
    if len(doc.sections) < 2:
        return
    last = doc.sections[-1]
    if last.isIntro:
        return
    over: list[tuple[int, str]] = []
    for block in doc.blocks:
        if block.kind != LIST or block.startLine < last.startLine:
            continue
        for offset, item in itemsOf(block.text):
            visible = plainText(item)
            if len(visible) > config.moreLaterMaxChars:
                over.append((block.startLine + offset, visible))
    if not over:
        return
    line, longest = max(over, key=lambda pair: len(pair[1]))
    yield Finding(
        "moreLater",
        line,
        longest,
        f"마지막 절의 목록 항목 {len(over)}개가 {config.moreLaterMaxChars}자를 넘는다 (가장 긴 것 {len(longest)}자). "
        "미룬 것이 아니라 옮겨 적은 것이다. 한 줄과 링크로 줄인다",
        None,
        NOTICE,
        SECTION,
        last.index,
    )
