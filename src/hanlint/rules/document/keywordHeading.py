from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule

MIN_HEADINGS = 3
"""목차라고 부를 수 있는 최소 H2 수. 둘 이하는 훑을 목차가 아니다."""
MIN_WORD = 2
"""한 글자 낱말은 어느 제목에나 우연히 들어 있어 가르지 못한다."""


@rule("keywordHeading", mechanism="contrast")
def keywordHeading(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """제목이 약속한 대표 검색어의 말이 절 제목 어디에도 없는 글.

    왜: 검색해 들어온 독자는 본문을 읽기 전에 목차를 훑는다. 제목에서 본 말이 목차에 한 번도 없으면 이
        글이 자기 질문을 다루는지 확신하지 못한 채 뒤로 간다. 제목은 한 번 약속하고 목차는 그 약속이
        어디에서 지켜지는지 보이는 자리다.
    어디서: 실측. eddmpython 003 을 평가자 다섯 역할이 네 라운드 읽었고 2라운드의 검색 독자가 집었다.
        `절 제목만 위에서 아래로 훑으면 목차 전체에 파이썬 이라는 말이 한 번도 안 나온다. 나는 브라우저
        안에서 만드는 도구가 아니라 파이썬 코드를 찾아 들어온 사람이다.` 필드 이름은 config.keywordField.
    고치기: 그 말이 실제로 하는 일을 맡은 절의 제목에 넣는다. 003 이면 `파이썬으로 QR코드 파일 만들기`.
        억지로 모든 제목에 넣지 않는다. 한 번이면 된다.
    안 잡는 것: keywordField 를 설정하지 않은 글. 검색어가 제목에 없는 글 (그것은 keywordMissing 이 먼저
        짚는다). H2 가 셋 미만인 글. 한 글자 낱말. 뜻이 같은 다른 말로 목차를 쓴 자리는 갈라내지 못하므로
        notice 로만 낸다 (실측: 001 의 `시작` 은 목차에 없지만 `프로젝트 폴더 열기` 가 그 일을 한다).
    """
    if not config.keywordField:
        return
    keyword = doc.frontmatter.get(config.keywordField, "").strip()
    title = doc.frontmatter.get("title", "")
    headings = doc.headingsOfLevel(2)
    if not keyword or len(headings) < MIN_HEADINGS:
        return
    joined = " / ".join(text for _, text, _ in headings)
    missing = [word for word in keyword.split() if len(word) >= MIN_WORD and word in title and word not in joined]
    if not missing:
        return
    yield Finding(
        "keywordHeading",
        headings[0][2],
        joined,
        f"제목이 약속한 `{missing[0]}` 가 절 제목 어디에도 없다. 목차를 훑는 독자가 이 글이 그것을 다루는지 못 본다",
        None,
        NOTICE,
        DOCUMENT,
        -1,
    )
