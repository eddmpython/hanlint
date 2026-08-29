"""승인된 글들의 지표 분포. 지표마다 평균과 표준편차를 든다. JSON 으로 저장하고 읽는다."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, pstdev

from ..fingerprint import DocumentPrint
from .metrics import metricsOf

PROFILE_VERSION = 1


@dataclass(frozen=True)
class Profile:
    documentCount: int
    stats: dict[str, tuple[float, float]] = field(default_factory=dict)
    """지표 이름 → (평균, 표준편차)."""
    sources: tuple[str, ...] = ()

    def asDict(self) -> dict:
        return {
            "version": PROFILE_VERSION,
            "documentCount": self.documentCount,
            "sources": list(self.sources),
            "stats": {name: {"mean": m, "std": s} for name, (m, s) in self.stats.items()},
        }


def buildProfile(docs: list[DocumentPrint]) -> Profile:
    """글 여러 편의 지표를 모아 분포를 만든다. 글이 하나면 표준편차는 0 이다."""
    if not docs:
        raise ValueError("프로파일을 만들 글이 없다. 마크다운 파일이 있는 폴더를 준다")
    perDoc = [metricsOf(doc.sentences, doc.paragraphs) for doc in docs]
    names = sorted({name for metrics in perDoc for name in metrics})
    stats: dict[str, tuple[float, float]] = {}
    for name in names:
        values = [metrics[name] for metrics in perDoc if name in metrics]
        stats[name] = (mean(values), pstdev(values) if len(values) > 1 else 0.0)
    return Profile(len(docs), stats, tuple(doc.path or "" for doc in docs))


def saveProfile(profile: Profile, path: str | Path) -> None:
    Path(path).write_text(json.dumps(profile.asDict(), ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def loadProfile(path: str | Path) -> Profile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != PROFILE_VERSION:
        raise ValueError(f"프로파일 버전이 다르다: {data.get('version')}. hanlint profile build 로 다시 만든다")
    stats = {name: (float(v["mean"]), float(v["std"])) for name, v in data["stats"].items()}
    return Profile(int(data["documentCount"]), stats, tuple(data.get("sources", [])))
