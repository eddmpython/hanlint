from __future__ import annotations

import re
from collections.abc import Iterator

from ...config import Config
from ...fingerprint import DocumentPrint
from ...fingerprint.markers import insideAny
from ..finding import SENTENCE, Finding
from ..registry import rule

# 영숫자에 붙은 점 셋 (`v0.0.1...HEAD`, compare URL) 은 범위 표기라 말줄임표가 아니다.
# 인라인 코드와 따옴표 안은 지문이 인용 구간으로 이미 표시해 두었으므로 여기서 다시 재지 않는다.
ELLIPSIS = re.compile(r"(?<![A-Za-z0-9])(…|\.{3,})(?![A-Za-z0-9])")
CLI_OPTION = re.compile(r"(?:^|\s)--?[A-Za-z0-9]")


def _insideCommandExample(text: str, start: int, end: int) -> bool:
    """괄호 안 명령 예시의 생략 인자. 예: (kubectl get -o yaml …)."""
    opened = text.rfind("(", 0, start + 1)
    closed = text.find(")", end)
    return opened >= 0 and closed >= 0 and ")" not in text[opened:start] and "(" not in text[end:closed] and bool(
        CLI_OPTION.search(text[opened + 1 : closed])
    )


@rule("ellipsis", mechanism="dictionary")
def ellipsis(doc: DocumentPrint, config: Config) -> Iterator[Finding]:
    """말줄임표.

    왜: 말끝을 흐리면 독자가 결론을 받아 가지 못한다. 설명글의 독자는 답을 찾으러 왔다.
    어디서: 글쓰기 스킬의 사실과 목소리.
    고치기: 문장을 끝까지 쓴다. 모르면 모른다고 쓴다.
    안 잡는 것: 코드 블록 안의 점 셋. 인라인 코드와 따옴표 안의 점 셋. 인용 구간은 사용이 아니라 표기이고
    거기서 점 셋은 생략할 인자를 뜻한다 (실측: 이슈 2번의 ``make_qr("...")``. 그전에는 여는 괄호와
    대괄호만 예외로 두어 그 사이에 큰따옴표가 끼면 예외가 풀렸다). 괄호 안 명령 예시에서 옵션 뒤의 생략
    인자를 뜻하는 기호 (`kubectl get -o yaml …`). 영숫자에 붙은 점 셋 (`v0.0.1...HEAD` 같은 범위 표기.
    CHANGELOG 의 compare URL 이 실측 사례다). 산문만 본다.
    """
    for sentence in doc.sentences:
        found = [
            match
            for match in ELLIPSIS.finditer(sentence.text)
            if not insideAny(match.start(), match.end(), sentence.quoted)
            and not _insideCommandExample(sentence.text, match.start(), match.end())
        ]
        if found:
            yield Finding(
                "ellipsis",
                sentence.line,
                sentence.text,
                "말줄임표로 말끝을 흐리면 독자가 결론을 받아 가지 못한다. 문장을 끝까지 쓴다",
                None,
                "error",
                SENTENCE,
                sentence.index,
            )
