"""두 초안에서 지적이 사라진 문장 짝을 보수적으로 찾는다.

뜻을 추측하지 않는다. 문장 변경 구간이 일대일이거나 한 문장이 여러 문장으로 갈라졌을 때만 짝을
만든다. 여러 문장을 한꺼번에 다시 쓴 구간은 어느 문장이 어느 문장으로 갔는지 결정할 수 없으므로
버린다.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from ..fingerprint import DocumentPrint, SentencePrint
from ..rules import Finding
from ..rules.finding import SENTENCE


@dataclass(frozen=True)
class LearnedExemplar:
    rule: str
    before: str
    after: str
    moved: str
    why: str
    beforeLine: int
    afterLines: tuple[int, ...]
    presets: tuple[str, ...] = ()

    def asDict(self) -> dict:
        data = {
            "rule": self.rule,
            "before": self.before,
            "after": self.after,
            "moved": self.moved,
            "why": self.why,
            "beforeLine": self.beforeLine,
            "afterLines": list(self.afterLines),
        }
        if self.presets:
            data["presets"] = list(self.presets)
        return data


def changedSentencePairs(
    beforeSentences: tuple[SentencePrint, ...], afterSentences: tuple[SentencePrint, ...]
) -> dict[int, tuple[SentencePrint, ...]]:
    """앞 문장 index → 대응된 고친 문장들. 모호한 변경 구간은 넣지 않는다."""
    matcher = SequenceMatcher(
        None,
        [sentence.text for sentence in beforeSentences],
        [sentence.text for sentence in afterSentences],
        autojunk=False,
    )
    pairs: dict[int, tuple[SentencePrint, ...]] = {}
    for tag, beforeStart, beforeEnd, afterStart, afterEnd in matcher.get_opcodes():
        if tag != "replace":
            continue
        beforeCount = beforeEnd - beforeStart
        afterCount = afterEnd - afterStart
        if beforeCount == afterCount:
            for offset in range(beforeCount):
                beforeSentence = beforeSentences[beforeStart + offset]
                pairs[beforeSentence.index] = (afterSentences[afterStart + offset],)
        elif beforeCount == 1 and afterCount > 0:
            beforeSentence = beforeSentences[beforeStart]
            pairs[beforeSentence.index] = afterSentences[afterStart:afterEnd]
    return pairs


def learnExemplars(
    beforeDoc: DocumentPrint,
    afterDoc: DocumentPrint,
    beforeFindings: list[Finding],
    afterFindings: list[Finding],
    preset: str | None = None,
) -> tuple[LearnedExemplar, ...]:
    """사라진 문장 지적의 전후 짝. 같은 규칙이 고친 문장에 남으면 배우지 않는다."""
    pairs = changedSentencePairs(beforeDoc.sentences, afterDoc.sentences)
    remaining = {(finding.rule, finding.at) for finding in afterFindings if finding.scope == SENTENCE and finding.at >= 0}
    beforeByIndex = {sentence.index: sentence for sentence in beforeDoc.sentences}
    seen: set[tuple[str, int]] = set()
    learned: list[LearnedExemplar] = []
    for finding in beforeFindings:
        key = (finding.rule, finding.at)
        if finding.scope != SENTENCE or finding.at < 0 or key in seen:
            continue
        afterSentences = pairs.get(finding.at)
        beforeSentence = beforeByIndex.get(finding.at)
        if not afterSentences or beforeSentence is None:
            continue
        if any((finding.rule, sentence.index) in remaining for sentence in afterSentences):
            continue
        afterText = " ".join(sentence.text.strip() for sentence in afterSentences if sentence.text.strip())
        if not afterText or beforeSentence.text.strip() == afterText:
            continue
        seen.add(key)
        learned.append(
            LearnedExemplar(
                rule=finding.rule,
                before=beforeSentence.text.strip(),
                after=afterText,
                moved="실제 수정본의 문장으로 바꿈",
                why=finding.why,
                beforeLine=beforeSentence.line,
                afterLines=tuple(dict.fromkeys(sentence.line for sentence in afterSentences)),
                presets=(preset,) if preset else (),
            )
        )
    return tuple(learned)
