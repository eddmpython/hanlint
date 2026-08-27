"""평가자 지적과 hanlint 지적의 자리 겹침.

평가자 지적은 (quote, why, fix) 꼴이다 (eddmpython 의 review.json). 인용문의 앞 글자로 본문 줄을 찾고 그 줄 ±1 에
hanlint 지적이 있으면 겹친 것이다. 본문이 바뀌어 인용이 사라진 지적은 잴 수 없어 따로 센다. 못 집은 지적은
data/coverageTypes.txt 의 표지로 유형을 갈라 다음 규칙 후보로 보인다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from ..data import loadLines
from ..rules import Finding

KEY_LENGTH = 24
MIN_KEY = 6
NOISE = re.compile(r"[\s`*_\"'“”‘’]")
DEFAULT_TYPE = "기타"


@dataclass(frozen=True)
class ReviewFinding:
    round: int
    role: str
    quote: str
    why: str


@dataclass(frozen=True)
class Uncaught:
    line: int
    round: int
    role: str
    kind: str
    why: str


@dataclass(frozen=True)
class Coverage:
    total: int
    located: int
    covered: int
    coveredByError: int
    """error 급 지적이 같은 자리에 있던 것. notice 만 겹친 것은 covered 에만 든다."""
    byRule: tuple[tuple[str, int], ...]
    uncaught: tuple[Uncaught, ...]

    @property
    def ratio(self) -> float:
        return self.covered / self.located if self.located else 0.0


@cache
def coverageTypes() -> tuple[tuple[str, re.Pattern[str]], ...]:
    found = []
    for line in loadLines("coverageTypes.txt"):
        kind, _, pattern = line.partition("\t")
        found.append((kind, re.compile(pattern)))
    return tuple(found)


def kindOf(why: str) -> str:
    for kind, pattern in coverageTypes():
        if pattern.search(why):
            return kind
    return DEFAULT_TYPE


def loadReview(path: str | Path) -> list[ReviewFinding]:
    """review.json 을 읽는다. rounds 안의 reviewers 안의 findings, 또는 findings 목록, 또는 목록 자체."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    findings: list[ReviewFinding] = []
    if isinstance(data, dict) and "rounds" in data:
        for index, roundData in enumerate(data["rounds"], start=1):
            for reviewer in roundData.get("reviewers", []):
                for item in reviewer.get("findings", []):
                    findings.append(ReviewFinding(index, reviewer.get("role", ""), item.get("quote", ""), item.get("why", "")))
        return findings
    items = data.get("findings", []) if isinstance(data, dict) else data
    for item in items:
        findings.append(ReviewFinding(1, item.get("role", ""), item.get("quote", ""), item.get("why", "")))
    return findings


def normalize(text: str) -> str:
    return NOISE.sub("", text)


def locate(lines: list[str], quote: str) -> int | None:
    """인용문의 앞 글자가 있는 줄 (1 부터). 줄이 바뀐 인용은 이웃 줄을 붙여 다시 찾는다."""
    key = normalize(quote)[:KEY_LENGTH]
    if len(key) < MIN_KEY:
        return None
    normalized = [normalize(line) for line in lines]
    for index, line in enumerate(normalized):
        if key in line:
            return index + 1
    for index in range(len(normalized) - 1):
        if key in normalized[index] + normalized[index + 1]:
            return index + 1
    return None


def coverageOf(text: str, findings: list[Finding], reviews: list[ReviewFinding]) -> Coverage:
    lines = text.splitlines()
    byLine: dict[int, set[tuple[str, str]]] = {}
    for finding in findings:
        byLine.setdefault(finding.line, set()).add((finding.rule, finding.severity))
    located = covered = coveredByError = 0
    ruleCounts: dict[str, int] = {}
    uncaught: list[Uncaught] = []
    for review in reviews:
        line = locate(lines, review.quote)
        if line is None:
            continue
        located += 1
        hits = set().union(*(byLine.get(near, set()) for near in (line - 1, line, line + 1)))
        if hits:
            covered += 1
            if any(severity == "error" for _, severity in hits):
                coveredByError += 1
            for rule in sorted({rule for rule, _ in hits}):
                ruleCounts[rule] = ruleCounts.get(rule, 0) + 1
        else:
            uncaught.append(Uncaught(line, review.round, review.role, kindOf(review.why), review.why))
    ordered = tuple(sorted(ruleCounts.items(), key=lambda item: (-item[1], item[0])))
    return Coverage(
        len(reviews), located, covered, coveredByError, ordered, tuple(sorted(uncaught, key=lambda u: (u.kind, u.line)))
    )


def renderCoverage(coverage: Coverage) -> str:
    lines = [
        f"평가자 지적 {coverage.total}건. 본문에서 찾은 인용 {coverage.located}건"
        + (f" (본문이 바뀐 {coverage.total - coverage.located}건은 잴 수 없다)" if coverage.total > coverage.located else ""),
        f"hanlint 가 같은 자리를 집은 것 {coverage.covered}건 ({coverage.ratio:.0%}). "
        f"error 로 {coverage.coveredByError}건, notice 로만 {coverage.covered - coverage.coveredByError}건"
        + (". 규칙: " + ", ".join(f"{rule} {count}" for rule, count in coverage.byRule) if coverage.byRule else ""),
    ]
    if coverage.uncaught:
        lines.append(f"못 집은 {len(coverage.uncaught)}건. 다음 규칙 후보다")
        currentKind = None
        for item in coverage.uncaught:
            if item.kind != currentKind:
                currentKind = item.kind
                count = sum(1 for u in coverage.uncaught if u.kind == currentKind)
                lines.append(f"  [{currentKind} {count}]")
            role = f"{item.round}라운드 {item.role}".strip()
            lines.append(f"    {item.line}행 ({role}) {item.why[:90]}")
    return "\n".join(lines)


def coverageDict(coverage: Coverage) -> dict:
    return {
        "total": coverage.total,
        "located": coverage.located,
        "covered": coverage.covered,
        "coveredByError": coverage.coveredByError,
        "ratio": round(coverage.ratio, 4),
        "byRule": {rule: count for rule, count in coverage.byRule},
        "uncaught": [{"line": u.line, "round": u.round, "role": u.role, "type": u.kind, "why": u.why} for u in coverage.uncaught],
    }
