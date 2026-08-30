"""지적 하나의 모양. 사람 평가자에게 요구하는 것과 같다. 인용, 이유, 가능하면 고친 문장."""

from __future__ import annotations

import re
from dataclasses import dataclass

ERROR = "error"
NOTICE = "notice"

SENTENCE = "sentence"
PARAGRAPH = "paragraph"
SECTION = "section"
DOCUMENT = "document"

MARKED = re.compile(r"`([^`\n]+)`")
MIN_LOCAL_CUE = 2


@dataclass(frozen=True)
class Candidate:
    text: str
    """사람이나 LLM이 고를 수 있는 꼴. 기계가 순위를 매기지 않는다."""
    why: str
    """이 꼴을 낸 표층 근거."""

    def asDict(self) -> dict:
        return {"text": self.text, "why": self.why}


@dataclass(frozen=True)
class Finding:
    rule: str
    line: int
    quote: str
    why: str
    fix: str | None = None
    """기계가 낼 수 있을 때만. 억지로 채우지 않는다."""
    severity: str = ERROR
    """error 는 규칙 위반, notice 는 정당한 용법이 많거나 근사 분석이라 확인이 필요한 것."""
    scope: str = SENTENCE
    """sentence, paragraph, section, document. 지도가 어디에 색을 칠할지 정한다."""
    at: int = -1
    """scope 가 가리키는 지문의 index."""
    fragment: str | None = None
    """원문에서 바꿀 조각. `hanlint fix` 가 이 조각을 찾아 replacement 로 바꾼다."""
    replacement: str | None = None
    candidates: tuple[Candidate, ...] = ()
    """뜻을 정하지 않고 형태로 좁힐 수 있을 때만. 순위와 점수는 없다."""

    @property
    def localCue(self) -> str:
        """규칙이 짚은 국소 표지. 너무 짧으면 오선택을 피하려고 인용 전체를 쓴다."""
        quote = " ".join(self.quote.split())
        if self.fragment:
            fragment = " ".join(self.fragment.split())
            if len(fragment) >= MIN_LOCAL_CUE:
                return fragment
        marked = [
            candidate
            for raw in MARKED.findall(self.why)
            if len(candidate := " ".join(raw.split())) >= MIN_LOCAL_CUE and candidate in quote
        ]
        return max(marked, key=lambda item: (len(item), item), default=quote)

    def asDict(self) -> dict:
        data = {
            "rule": self.rule,
            "line": self.line,
            "severity": self.severity,
            "scope": self.scope,
            "at": self.at,
            "quote": self.quote,
            "why": self.why,
        }
        if self.fix:
            data["fix"] = self.fix
        if self.replacement is not None:
            data["fragment"] = self.fragment
            data["replacement"] = self.replacement
        if self.candidates:
            data["candidates"] = [candidate.asDict() for candidate in self.candidates]
        return data
