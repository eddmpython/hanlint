"""새 글을 프로파일과 견준다. 절마다 지표를 내고 분포에서 얼마나 벗어나는지 z 로 짚는다.

편차는 사실이다. 좋다 나쁘다가 아니라 "이 구간이 참조 글들과 이 지표에서 이만큼 다르다" 다.

참조 글이 적으면 표준편차가 0 에 가까워 z 가 폭발한다 (실측: 다섯 편으로 만든 프로파일이 한 편에 57건을 냈다).
그래서 표준편차의 바닥값을 표본 크기에서 구한다. 비율 지표는 문장 (또는 문단) 수 n 의 표준오차 sqrt(0.25/n) 이라
문장 여섯 개짜리 절에서 문장 하나 차이 (0.17) 를 짚지 않고, 밀도 지표는 어절 수에서 한 번 나온 것에 해당하는
1000/어절 이다. 임계는 2.5 다.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from ..fingerprint import DocumentPrint, SectionPrint
from .build import Profile
from .metrics import metricsOf

Z_THRESHOLD = 2.5
"""이보다 벗어나면 짚는다."""
MIN_SENTENCES = 5
"""절이 이보다 짧으면 지표가 흔들려 견주지 않는다."""
RATIO_METRICS = frozenset({"commaRatio", "questionRate", "readerCallRate"})
PARAGRAPH_RATIO_METRICS = frozenset({"shortParagraphRatio"})
DENSITY_METRICS = frozenset({"hedgeDensity", "emphasisDensity"})
FIXED_FLOORS = {"sentenceLength": 1.0, "burstiness": 0.05, "paragraphSentences": 0.5}
LABELS = {
    "sentenceLength": "문장 길이",
    "burstiness": "길이 변동",
    "commaRatio": "쉼표 비율",
    "questionRate": "질문 비율",
    "readerCallRate": "독자 호출 비율",
    "hedgeDensity": "헤지 밀도",
    "emphasisDensity": "강조 낱말 밀도",
    "paragraphSentences": "문단당 문장 수",
    "shortParagraphRatio": "짧은 문단 비율",
}


@dataclass(frozen=True)
class Deviation:
    scope: str
    """section 또는 document."""
    index: int
    line: int
    metric: str
    value: float
    mean: float
    z: float

    @property
    def label(self) -> str:
        if self.metric.startswith("ending:"):
            return f"종결어미 {self.metric.split(':', 1)[1]} 비율"
        return LABELS.get(self.metric, self.metric)

    def describe(self) -> str:
        direction = "높다" if self.z > 0 else "낮다"
        return f"{self.label} 이 참조 글보다 {direction} ({self.value:.2f}, 참조 평균 {self.mean:.2f}, z {self.z:+.1f})"


@dataclass(frozen=True)
class SampleSize:
    sentences: int
    paragraphs: int
    words: int


def floorOf(metric: str, size: SampleSize) -> float:
    if metric in RATIO_METRICS or metric.startswith("ending:"):
        return sqrt(0.25 / max(1, size.sentences))
    if metric in PARAGRAPH_RATIO_METRICS:
        return sqrt(0.25 / max(1, size.paragraphs))
    if metric in DENSITY_METRICS:
        return 1000 / max(1, size.words)
    return FIXED_FLOORS.get(metric, 0.0)


def zScore(value: float, meanValue: float, std: float, metric: str, size: SampleSize) -> float:
    spread = max(std, floorOf(metric, size))
    if spread < 1e-9:
        return 0.0 if abs(value - meanValue) < 1e-9 else (3.0 if value > meanValue else -3.0)
    return (value - meanValue) / spread


def deviationsFor(
    metrics: dict[str, float], profile: Profile, scope: str, index: int, line: int, size: SampleSize
) -> list[Deviation]:
    found = []
    for name, value in metrics.items():
        if name not in profile.stats:
            continue
        meanValue, std = profile.stats[name]
        z = zScore(value, meanValue, std, name, size)
        if abs(z) >= Z_THRESHOLD:
            found.append(Deviation(scope, index, line, name, value, meanValue, z))
    return found


def sizeOf(sentences, paragraphs) -> SampleSize:
    return SampleSize(len(sentences), len(paragraphs), sum(s.length for s in sentences))


def sectionMetrics(section: SectionPrint) -> dict[str, float]:
    sentences = tuple(s for p in section.paragraphs for s in p.sentences)
    return metricsOf(sentences, section.paragraphs)


def compareToProfile(doc: DocumentPrint, profile: Profile) -> list[Deviation]:
    deviations = deviationsFor(
        metricsOf(doc.sentences, doc.paragraphs), profile, "document", -1, 1, sizeOf(doc.sentences, doc.paragraphs)
    )
    for section in doc.sections:
        sentences = tuple(s for p in section.paragraphs for s in p.sentences)
        if len(sentences) < MIN_SENTENCES:
            continue
        size = sizeOf(sentences, section.paragraphs)
        deviations.extend(deviationsFor(sectionMetrics(section), profile, "section", section.index, section.startLine, size))
    return deviations
