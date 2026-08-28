from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule

# 리터럴로 쓰면 이 파일이 자기 게이트에 걸린다. 코드포인트로 만든다.
DASHES = re.compile("[" + chr(0x2013) + chr(0x2014) + "]")


@rule("dash")
def dash(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """em 대시 (U+2014) 와 en 대시 (U+2013). 코드 블록까지 글 전체를 본다.

    왜: AI 가 매끄럽게 고친다면서 새로 넣는 대표적인 부호다. 한국어 문장 부호가 아니라 독자가 멈춘다.
        GPT-4.1 이 인간 대비 3.28배 쓴다는 조사가 있다.
    어디서: 글쓰기 스킬의 사실과 목소리. Wikipedia Signs of AI writing 4.6. Freeburg 조사.
    고치기: 부연은 마침표로 끊거나 괄호로, 범위는 물결표로 쓴다. 2020~2024.
    안 잡는 것: 하이픈 (-) 과 물결표. 코드 안의 대시도 잡고, 설정 (ignoreFences) 이 지문에서 뺀 펜스 안도 잡는다.
        렌더러가 지우는 펜스라도 파일에 있는 글자다. 코드가 대시를 정말 필요로 하면 그 파일에서 이 규칙을 끈다.
    """
    for block in (*doc.blocks, *doc.ignored):
        for offset, lineText in enumerate(block.text.split("\n")):
            if DASHES.search(lineText):
                yield Finding(
                    "dash",
                    block.startLine + offset,
                    lineText.strip(),
                    "긴 줄표다. 부연은 마침표로 끊거나 괄호로, 범위는 물결표 ~ 로 쓴다",
                    None,
                    "error",
                    DOCUMENT,
                    block.index,
                )
