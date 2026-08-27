"""지적 하나의 모양. 사람 평가자에게 요구하는 것과 같다. 인용, 이유, 가능하면 고친 문장."""

from __future__ import annotations

from dataclasses import dataclass

ERROR = "error"
NOTICE = "notice"

SENTENCE = "sentence"
PARAGRAPH = "paragraph"
SECTION = "section"
DOCUMENT = "document"


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
        return data
