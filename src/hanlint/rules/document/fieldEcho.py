from __future__ import annotations

from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.sectionPrint import SectionPrint
from ...fingerprint.topics import topicsOf
from ..finding import DOCUMENT, NOTICE, Finding
from ..registry import rule


def check(doc: DocumentPrint, section: SectionPrint, fields: list[str], where: str) -> Iterator[Finding]:
    for name in fields:
        value = doc.frontmatter.get(name)
        if not value:
            continue
        promised = topicsOf(value)
        if not promised:
            continue
        if promised & section.topics:
            continue
        yield Finding(
            "fieldEcho",
            section.startLine,
            value,
            f"frontmatter 의 `{name}` 가 약속한 말이 {where}에 하나도 없다. 약속한 것을 {where}에서 그 말로 답한다",
            None,
            NOTICE,
            DOCUMENT,
            section.index,
        )


@rule("fieldEcho")
def fieldEcho(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """frontmatter 가 약속한 것을 도입이나 마지막 절이 하나도 부르지 않는 글.

    왜: frontmatter 에 독자의 질문과 독자가 얻을 것을 적어 두고 본문이 다른 말을 하면, 검색해 들어온 독자는
        미리보기에서 본 약속과 다른 글을 읽는다. 도입은 그 질문에 답하기 시작해야 하고 마지막 절은 얻을
        것을 손에 남겨야 한다.
    어디서: cinch 의 전역 blog-writing 스킬, 도입은 결핍부터와 결말. 실측 사례는 eddmpython 블로그의
        frontmatter 로, readerQuestion 과 readerTakeaway 를 적어 두고 어떤 검사기도 본문과 맞춰 보지 않았다.
        볼 필드는 config.introFields 와 config.endingFields 가 정한다. 둘 다 비어 있으면 이 규칙은 돌지 않는다.
    고치기: 도입 첫 문단에서 그 질문의 말을 그대로 쓰고, 마지막 절에서 얻을 것을 그 이름으로 다시 부른다.
        본문이 맞고 frontmatter 가 낡았으면 frontmatter 를 고친다.
    안 잡는 것: 설정에 필드를 적지 않은 글. frontmatter 에 그 필드가 없거나 빈 글. 화제어가 없는 값. 화제어
        중첩은 근사라 notice 로만 낸다.
    """
    if not config.introFields and not config.endingFields:
        return
    yield from check(doc, doc.intro, config.introFields, "도입")
    if len(doc.sections) > 1:
        yield from check(doc, doc.sections[-1], config.endingFields, "마지막 절")
