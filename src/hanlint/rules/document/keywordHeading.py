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

    왜: 검색해 들어온 독자는 본문을 읽기 전에 목차를 훑는다. 제목에서 본 말이 목차에 한 번도 없으면 이 글이
        자기 질문을 다루는지 확신하지 못한 채 뒤로 간다. 제목은 한 번 약속하고, 목차는 그 약속을 어디에서
        지키는지 보여 준다.
    어디서: 실제 블로그 글 하나를 평가자 다섯이 역할을 나눠 네 차례 읽었고, 둘째 차례에 검색 독자 역할이 짚었다.
        `절 제목만 위에서 아래로 훑으면 목차 전체에 파이썬 이라는 말이 한 번도 안 나온다. 나는 브라우저
        안에서 만드는 도구가 아니라 파이썬 코드를 찾아 들어온 사람이다.` 검색어를 읽을 필드는 설정
        keywordField가 정한다.
    고치기: 그 말이 실제로 하는 일을 맡은 절의 제목에 넣는다. 위 글이라면 `파이썬으로 QR코드 파일 만들기`다.
        억지로 모든 제목에 넣지 않는다. 한 번이면 된다.
    안 잡는 것: keywordField를 설정하지 않은 글, 검색어가 제목에도 첫 문단에도 없는 글(그것은 keywordMissing이
        먼저 짚는다), H2가 셋 미만인 글, 한 글자 단어는 잡지 않는다. 뜻이 같은 다른 말로 목차를 쓴 경우는 가려내지
        못하므로 경고로만 낸다. 다른 글 하나에서는 `시작`이 목차에 없었지만 `프로젝트 폴더 열기`가 그 일을 했다.
    제목만 보지 않는 까닭: 제목에만 있는지 보면 제목에는 없고 첫 문단에만 있는 검색어가 두 규칙 사이에서
        빠진다. keywordMissing은 제목과 첫 문단을 함께 보므로 통과시키고, 이 규칙은 제목에 없다고 건너뛴다.
        그래서 이 규칙도 keywordMissing과 같은 곳(제목과 첫 문단)을 본다.
    """
    if not config.keywordField:
        return
    keyword = doc.frontmatter.get(config.keywordField, "").strip()
    title = doc.frontmatter.get("title", "")
    headings = doc.headingsOfLevel(2)
    if not keyword or len(headings) < MIN_HEADINGS:
        return
    # keywordMissing 과 같은 자리를 본다. 제목만 보면 첫 문단에만 있는 검색어가 두 규칙 사이로 빠진다.
    first = doc.paragraphs[0] if doc.paragraphs else None
    promised = title + "\n" + (first.text if first else "")
    joined = " / ".join(text for _, text, _ in headings)
    missing = [word for word in keyword.split() if len(word) >= MIN_WORD and word in promised and word not in joined]
    if not missing:
        return
    yield Finding(
        "keywordHeading",
        headings[0][2],
        joined,
        f"글이 내건 말이 절 제목 어디에도 없다: `{missing[0]}`. 목차를 훑는 독자는 이 글이 그것을 다루는지 알 수 없다",
        None,
        NOTICE,
        DOCUMENT,
        -1,
    )
