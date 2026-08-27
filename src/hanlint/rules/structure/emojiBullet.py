from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...document.model import LIST
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule

# 이모지 범위. 코드포인트로 만든다 (도구가 이스케이프를 건드리지 않게).
EMOJI = "[" + chr(0x1F300) + "-" + chr(0x1FAFF) + chr(0x2600) + "-" + chr(0x27BF) + chr(0x2B50) + chr(0x2B06) + "]"
BULLET_WITH_EMOJI = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+" + EMOJI)


@rule("emojiBullet")
def emojiBullet(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """이모지로 시작하는 목록 항목.

    왜: 불릿마다 이모지를 달면 장식이 정보를 가리고 AI 가 쓴 홍보 글처럼 읽힌다.
    어디서: Wikipedia Signs of AI writing 4.7 (Emoji as formatting), Bloomberg 2026-01 (LinkedIn AI 게시물).
    고치기: 이모지를 지우고 항목의 첫 낱말이 내용을 말하게 한다.
    안 잡는 것: 본문 문장 안의 이모지. 목록 항목의 첫 자리만 본다.
    """
    for block in doc.blocks:
        if block.kind != LIST:
            continue
        for offset, lineText in enumerate(block.text.split("\n")):
            if BULLET_WITH_EMOJI.match(lineText):
                yield Finding(
                    "emojiBullet",
                    block.startLine + offset,
                    lineText.strip(),
                    "목록 항목이 이모지로 시작한다. 이모지를 지우고 첫 낱말이 내용을 말하게 한다",
                    None,
                    "error",
                    DOCUMENT,
                    block.index,
                )
                break
