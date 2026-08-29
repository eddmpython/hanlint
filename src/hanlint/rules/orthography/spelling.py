from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import Finding
from ..registry import rule
from ..shared import dictionaryFindings


@rule("spelling", mechanism="dictionary")
def spelling(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """됬, 돼고, 않 해, 왠일, 몇일, 금새, 오랫만, 어떻해, 할께, 바램 처럼 자주 틀리는 표기.

    왜: 틀린 표기는 독자가 먼저 알아채고 그 순간 글보다 글쓴이를 본다. 사람 작가가 가장 자주 지적받는
        자리이고 전부 결정적으로 잡힌다.
    어디서: 국립국어원 한글 맞춤법 (제27항 붙임 2 며칠, 제35항 붙임 2 되어→돼, 제53항 -ㄹ게, 제56항 -든지),
        온라인가나다 답변, 표준국어대사전 표제어. 항목마다 근거가 붙어 있다 (data/spelling.toml).
    고치기: 항목마다 고친 표기를 fix 로 낸다. hanlint fix 가 적용한다.
    안 잡는 것: 뜻에 따라 둘 다 맞는 자리 (데/대, 이따가/있다가, 못하다/못 하다, 한번/한 번, 안되다/안 되다).
        백틱과 따옴표 안의 인용. 사전에 없는 표기.
    """
    yield from dictionaryFindings(doc, "spelling", "spelling")
