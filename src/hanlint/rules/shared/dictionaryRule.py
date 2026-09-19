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
from ...config import Config
from ...fingerprint import DocumentPrint
from ...usage import conventional, usageKindOf
from ..finding import ERROR, SENTENCE, Finding


def matchFinding(sentence, match, ruleName: str, severity: str) -> Finding:
    fix = None
    if match.fix is not None:
        # 낱말만 갈아 끼우면 뒤에 붙은 조사가 틀어진다. `이슈로` 를 `쟁점로` 로 내밀던 자리다
        fix = sentence.text[: match.start] + match.fix + fitJosa(match.fix, sentence.text[match.end :])
    return Finding(
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


def dictionaryFindings(
    doc: DocumentPrint, dictionary: str, ruleName: str, severity: str = ERROR, config: Config | None = None
) -> Iterator[Finding]:
    """사전의 매치를 지적으로. config 를 주면 그 종류의 관용 항목 (usage.conventional) 은 넘긴다.

    사업보고서 200편에서 translationese 항목 8개가 문서의 100% 에, `에 대한` 하나가 1,000문장당 88번 나왔다. 그 종류의
    모든 글이 쓰는 표현을 그 종류에서 짚는 것은 결함이 아니라 문체를 짚는 것이다. 종류는 프리셋이 정하고 (config.USAGE_OF)
    비율은 config.usageShare 다. 설정의 dictionary 로 더한 항목은 표에 없어 늘 짚는다."""
    kind = usageKindOf(config) if config is not None else None
    for sentence in doc.sentences:
        for match in sentence.matches:
            if match.dictionary != dictionary:
                continue
            if kind and conventional(dictionary, match.pattern, kind, config.usageShare):
                continue
            yield matchFinding(sentence, match, ruleName, severity)


def overridingFindings(doc: DocumentPrint, dictionary: str, ruleName: str, severity: str = ERROR) -> Iterator[Finding]:
    """같은 자리에 항목이 둘이면 뒤의 것이 이긴다.

    기본 사전 뒤에 설정의 항목이 오므로 프로젝트가 기본 항목의 낱말을 다른 고침으로 덮는 자리다 (컴포넌트 → 차트).
    자리가 다르면 둘 다 낸다.
    """
    for sentence in doc.sentences:
        chosen = {}
        for match in sentence.matches:
            if match.dictionary == dictionary:
                chosen[(match.start, match.end)] = match
        for match in sorted(chosen.values(), key=lambda m: m.start):
            yield matchFinding(sentence, match, ruleName, severity)


def firstMatchFindings(doc: DocumentPrint, dictionary: str, ruleName: str, severity: str = ERROR) -> Iterator[Finding]:
    """문장마다 가장 앞의 매치 하나만 지적한다.

    구체 무늬 (진행, 실패) 와 종결어미 전체가 한 사전에 같이 사는 화면 사전에 쓴다. 한 문장이 둘 다에 걸리면 지적이 둘이
    되고 사용자는 같은 자리를 두 번 읽는다. 가장 앞의 것이 가장 구체적인 것이다 (구체 무늬는 종결어미보다 앞에서 시작한다).
    항목에 to 규칙이 있으면 (진행, 실패, 요구, 완료) 문장 전체를 낱말로 다시 쓴 제안을 fix 로 낸다. 사람이 칸에서 지우거나
    고쳐 쓰는 제안이다. 일반 종결어미처럼 뜻을 골라야 하는 자리는 to 가 없어 fix 도 없다. 실측: 표 146칸이 전부 비어
    사람이 다 타이핑하던 것이 검토로 바뀐다 (2026-09-18).
    """
    for sentence in doc.sentences:
        match = next((m for m in sentence.matches if m.dictionary == dictionary), None)
        if match is None:
            continue
        fragment, replacement = changedSpan(sentence.text, match.rewrite) if match.rewrite else (None, None)
        yield Finding(
            ruleName,
            sentence.line + sentence.text.count("\n", 0, match.start),
            sentence.text,
            f"`{match.text}` {match.why} ({match.source})",
            match.rewrite,
            severity,
            SENTENCE,
            sentence.index,
            fragment,
            replacement,
        )


def changedSpan(before: str, after: str) -> tuple[str, str]:
    """두 글의 공통 앞뒤를 뺀 바뀐 조각. 편집기의 `이대로 고치기` 가 이 조각만 바꾼다."""
    head = 0
    while head < min(len(before), len(after)) and before[head] == after[head]:
        head += 1
    tail = 0
    while tail < min(len(before), len(after)) - head and before[-1 - tail] == after[-1 - tail]:
        tail += 1
    return before[head : len(before) - tail], after[head : len(after) - tail]
