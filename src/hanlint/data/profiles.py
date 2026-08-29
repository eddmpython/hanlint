"""참조 분포 (프로파일) 의 자료형과 읽기. 같은 종류의 글 여러 편에서 문장과 문단의 정수 지표를 값마다 세어 둔 표다.

hanlint 가 싣는 종류별 프로파일 (`profiles.json`, `scripts/buildProfiles.py` 가 기준 말뭉치에서 만든다) 과 사용자가
`hanlint profile build 글들/` 로 만드는 파일이 같은 꼴이다. 정수 지표는 정확한 계수 히스토그램이라 오차가 없고 백분위는
그 히스토그램에서 나온다. 만드는 쪽은 `profile/build.py` 이고 견주는 쪽은 규칙 outsideProfile 이다.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from .load import loadJson

PROFILE_VERSION = 1
CAP = 200
"""히스토그램의 상한. 이 값보다 큰 것은 상한에 합친다. 어절 200 을 넘는 문장은 백분위로 가를 것이 없다."""
PERCENTILES = (50, 90, 95, 99)
TYPE_LABELS = {
    "blog": "블로그",
    "technicalDocs": "기술 문서",
    "guide": "안내서",
    "report": "뉴스와 보고문",
    "essay": "수필 (1930년대)",
    "fiction": "소설 (1930년대)",
    "encyclopedia": "백과",
}
"""기준 말뭉치 종류의 이름. 지적문에 적는다. 종류의 정본은 corpus/catalogue.toml 의 types 다."""


@dataclass(frozen=True)
class Histogram:
    total: int
    counts: dict[int, int]
    """값 → 수. 값은 CAP 에서 잘린다."""
    percentiles: dict[int, int]
    """백분위 → 값. 누적 수가 전체의 p% 에 처음 닿는 값이다."""

    def percentile(self, p: int) -> int:
        return self.percentiles[p]

    def shareAtOrAbove(self, value: int) -> int:
        """값이 이 이상인 것의 몫을 천분율 정수로. 정수 셈이라 두 판의 글자가 같다."""
        capped = min(value, CAP)
        above = sum(count for seen, count in self.counts.items() if seen >= capped)
        return above * 1000 // self.total if self.total else 0

    def asDict(self) -> dict:
        return {
            "total": self.total,
            "counts": {str(value): self.counts[value] for value in sorted(self.counts)},
            **{f"p{p}": value for p, value in self.percentiles.items()},
        }


def histogram(values: list[int]) -> Histogram:
    counts = Counter(min(int(value), CAP) for value in values)
    total = sum(counts.values())
    running = 0
    percentiles: dict[int, int] = {}
    wanted = list(PERCENTILES)
    for value in sorted(counts):
        running += counts[value]
        while wanted and running * 100 >= total * wanted[0]:
            percentiles[wanted[0]] = value
            wanted.pop(0)
    for p in wanted:
        percentiles[p] = 0
    return Histogram(total, dict(sorted(counts.items())), percentiles)


def histogramFromDict(data: dict) -> Histogram:
    counts = {int(value): int(count) for value, count in data["counts"].items()}
    percentiles = {p: int(data[f"p{p}"]) for p in PERCENTILES if f"p{p}" in data}
    return Histogram(int(data["total"]), counts, percentiles)


@dataclass(frozen=True)
class Profile:
    kind: str
    """기준 말뭉치의 종류 이름이거나 사용자 프로파일의 `custom`."""
    documents: int
    sentences: int
    paragraphs: int
    sentence: dict[str, Histogram] = field(default_factory=dict)
    paragraph: dict[str, Histogram] = field(default_factory=dict)
    endingRuns: Histogram | None = None
    """문단 안에서 같은 종결어미 부류가 이어진 길이."""
    endingTransitions: dict[str, int] = field(default_factory=dict)
    """`앞|뒤` → 수. 문단 안에서 앞 문장의 부류가 다음 문장의 부류로 이어진 횟수."""
    rates: dict[str, dict[str, float]] = field(default_factory=dict)
    """글마다의 비율 (문장당 접속부사, 물음, 독자 호출, 지시어) 의 글 단위 백분위."""

    @property
    def label(self) -> str:
        return TYPE_LABELS.get(self.kind, f"참조 글 {self.documents}편")

    def asDict(self) -> dict:
        return {
            "documents": self.documents,
            "sentences": self.sentences,
            "paragraphs": self.paragraphs,
            "sentence": {name: hist.asDict() for name, hist in self.sentence.items()},
            "paragraph": {name: hist.asDict() for name, hist in self.paragraph.items()},
            "endingRuns": self.endingRuns.asDict() if self.endingRuns else None,
            "endingTransitions": self.endingTransitions,
            "rates": self.rates,
        }


def profileFromDict(kind: str, data: dict) -> Profile:
    return Profile(
        kind=kind,
        documents=int(data["documents"]),
        sentences=int(data["sentences"]),
        paragraphs=int(data["paragraphs"]),
        sentence={name: histogramFromDict(value) for name, value in data["sentence"].items()},
        paragraph={name: histogramFromDict(value) for name, value in data["paragraph"].items()},
        endingRuns=histogramFromDict(data["endingRuns"]) if data.get("endingRuns") else None,
        endingTransitions=dict(data.get("endingTransitions", {})),
        rates=dict(data.get("rates", {})),
    )


def renderProfiles(profiles: dict[str, Profile]) -> str:
    """종류별 프로파일 파일 (profiles.json) 의 글자. 결정적이다."""
    data = {
        "version": PROFILE_VERSION,
        "cap": CAP,
        "types": {kind: profile.asDict() for kind, profile in sorted(profiles.items())},
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"


def saveProfile(profile: Profile, path: str | Path) -> None:
    data = {"version": PROFILE_VERSION, "cap": CAP, "profile": profile.asDict()}
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def loadProfile(path: str | Path) -> Profile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != PROFILE_VERSION or "profile" not in data:
        raise ValueError(f"프로파일 파일이 아니다: {path}. hanlint profile build 로 다시 만든다")
    return profileFromDict("custom", data["profile"])


@cache
def shippedProfiles() -> dict[str, Profile]:
    data = loadJson("profiles.json")
    return {kind: profileFromDict(kind, value) for kind, value in data["types"].items()}


@cache
def userProfile(path: str) -> Profile:
    return loadProfile(path)


def profileOf(kind: str) -> Profile | None:
    return shippedProfiles().get(kind)
