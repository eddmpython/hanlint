from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import NOTICE, SECTION, Finding
from ..registry import rule
from ..shared import codeBlocksOf


@rule("blockUnread", mechanism="threshold")
def blockUnread(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """코드 블록 바로 뒤에 붙인 출력을 읽어 주는 설명글이 없는 자리.

    왜: 출력을 붙였으면 그 출력을 읽어 준다. 숫자와 기호를 그대로 두면 독자는 어느 부분이 무엇인지 모른 채
        다음으로 넘어가고, 방금 실행한 것이 맞게 된 것인지도 확인하지 못한다.
    어디서: cinch 의 전역 blog-writing 스킬, 설명을 풀어 쓰기. 출력을 붙였으면 그 출력을 읽어 준다. 어느
        부분이 무엇인지 짚는다. 실측 사례는 블로그 004 의 출력 블록으로, 평가자가 서른 줄 가운데 다른 것이
        한 줄뿐인데 아무도 그것을 짚어 주지 않는다고 집었다.
    고치기: 출력 바로 아래에 그 출력을 읽는 문장을 한 줄 붙인다. 어느 숫자가 무엇인지, 무엇을 확인하면
        되는지 말한다.
    안 잡는 것: 언어를 밝힌 코드 블록 (실행할 것이지 읽을 것이 아니다). 앞이 코드 블록이 아닌 text 펜스는
        출력이 아니라 그림이다. 실측: eddmpython 의 운영 문서가 폴더 나무를 text 펜스로 그렸고 그것을
        출력으로 보아 오탐이 났다. 출력 바로 뒤에 산문 문단이 오는 자리. 근사라 notice 로만 낸다.
    """
    languages = {block.index: block.language for block in codeBlocksOf(doc)}
    outputs = {index for index, language in languages.items() if language in ("", "text", "output", "console")}
    if not outputs:
        return
    blocks = sorted(doc.blocks, key=lambda block: block.index)
    for position, block in enumerate(blocks):
        if block.index not in outputs or position == 0:
            continue
        previous = blocks[position - 1]
        if languages.get(previous.index) in (None, "", "text", "output", "console"):
            continue
        following = blocks[position + 1] if position + 1 < len(blocks) else None
        if following is not None and following.isProse:
            continue
        yield Finding(
            "blockUnread",
            block.startLine,
            block.text.split("\n")[1] if "\n" in block.text else block.text,
            "출력을 붙여 놓고 읽어 주지 않았다. 어느 부분이 무엇인지 짚는 문장을 바로 아래에 붙인다",
            None,
            NOTICE,
            SECTION,
            block.index,
        )
