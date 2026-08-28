"""사전 규칙의 공통 구현. cliche, translationese, redundantPair, japaneseLoan 이 사전 이름만 바꿔 쓴다.

사전 매치는 지문이 이미 해 뒀다. 여기서는 그것을 Finding 으로 옮기고, fix 가 있으면 문장 전체에서
그 자리를 바꾼 문장을 낸다.

**줄 번호는 걸린 낱말이 있는 줄이다.** 사전 규칙만 문장 안의 정확한 자리를 안다. 실측: 원문에서
두 줄에 걸친 문장의 뒷줄에 `되어지` 가 있는데 지적은 문장이 시작한 앞줄을 가리켰고, `--format github`
주석과 편집기 점프가 멀쩡한 줄로 갔다. 자리를 아는 규칙이 그 자리를 말한다.
"""

from __future__ import annotations

from collections.abc import Iterator

from ...analysis.grammar import fitJosa
from ...fingerprint import DocumentPrint
from ..finding import ERROR, SENTENCE, Finding


def dictionaryFindings(doc: DocumentPrint, dictionary: str, ruleName: str, severity: str = ERROR) -> Iterator[Finding]:
    for sentence in doc.sentences:
        for match in sentence.matches:
            if match.dictionary != dictionary:
                continue
            fix = None
            if match.fix is not None:
                # 낱말만 갈아 끼우면 뒤에 붙은 조사가 틀어진다. `이슈로` 를 `쟁점로` 로 내밀던 자리다
                fix = sentence.text[: match.start] + match.fix + fitJosa(match.fix, sentence.text[match.end :])
            yield Finding(
                ruleName,
                sentence.line + sentence.text.count("\n", 0, match.start),
                sentence.text,
                f"`{match.text}` {match.why} ({match.source})",
                fix,
                severity,
                SENTENCE,
                sentence.index,
                match.text if match.fix is not None else None,
                match.fix,
            )
