"""사전 규칙의 공통 구현. cliche, translationese, redundantPair, japaneseLoan 이 사전 이름만 바꿔 쓴다.

사전 매치는 지문이 이미 해 뒀다. 여기서는 그것을 Finding 으로 옮기고, fix 가 있으면 문장 전체에서
그 자리를 바꾼 문장을 낸다.
"""

from __future__ import annotations

from collections.abc import Iterator

from ...fingerprint import DocumentPrint
from ..finding import ERROR, SENTENCE, Finding


def dictionaryFindings(doc: DocumentPrint, dictionary: str, ruleName: str, severity: str = ERROR) -> Iterator[Finding]:
    for sentence in doc.sentences:
        for match in sentence.matches:
            if match.dictionary != dictionary:
                continue
            fix = None
            if match.fix is not None:
                fix = sentence.text[: match.start] + match.fix + sentence.text[match.end :]
            yield Finding(
                ruleName,
                sentence.line,
                sentence.text,
                f"`{match.text}` {match.why} ({match.source})",
                fix,
                severity,
                SENTENCE,
                sentence.index,
            )
