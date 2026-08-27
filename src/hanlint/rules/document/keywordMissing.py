from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ..finding import DOCUMENT, Finding
from ..registry import rule


@rule("keywordMissing")
def keywordMissing(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """대표 검색어가 제목에도 첫 문단에도 없는 글.

    왜: 검색해서 들어온 독자는 자기가 검색창에 친 이름을 첫 화면에서 찾는다. 그 이름이 안 보이면 본문을
        읽기 전에 뒤로 간다.
    어디서: 글쓰기 스킬의 검색 독자 역할 (독자가 검색창에 친 이름과 이 글이 쓰는 이름이 다르면 첫 문단에서
        처리한다). 필드 이름은 config.keywordField.
    고치기: 제목이나 첫 문단에 그 이름을 그대로 쓴다. 이름이 다르면 첫 문단에서 그 차이를 한 문장으로.
    안 잡는 것: keywordField 를 설정하지 않은 글. 그 필드가 비어 있는 글.
    """
    if not config.keywordField:
        return
    keyword = doc.frontmatter.get(config.keywordField, "").strip()
    if not keyword:
        return
    title = doc.frontmatter.get("title", "")
    first = doc.paragraphs[0] if doc.paragraphs else None
    head = title + "\n" + (first.text if first else "")
    if keyword in head:
        return
    yield Finding(
        "keywordMissing",
        first.startLine if first else 1,
        title or (first.text if first else ""),
        f"대표 검색어 `{keyword}` 가 제목에도 첫 문단에도 없다. 검색해 들어온 독자가 자기가 친 이름을 못 본다",
        None,
        "error",
        DOCUMENT,
        -1,
    )
