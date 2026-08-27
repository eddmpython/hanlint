"""새 글을 프로파일과 견준다. 절마다 지표를 내고 분포에서 얼마나 벗어나는지 z 로 짚는다.

편차는 사실이다. 좋다 나쁘다가 아니라 "이 구간이 참조 글들과 이 지표에서 이만큼 다르다" 다.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..fingerprint import DocumentPrint, SectionPrint
from .build import Profile
from .metrics import metricsOf

Z_THRESHOLD = 2.0
"""이보다 벗어나면 짚는다. 정규분포에서 바깥 5% 다."""
MIN_SENTENCES = 5
"""절이 이보다 짧으면 지표가 흔들려 견주지 않는다."""
LABELS = {
    "sentenceLength": "문장 길이",
    "burstiness": "길이 변동",
    "commaRatio": "쉼표 비율",
    "questionRate": "질문 비율",
    "readerCallRate": "독자 호출 비율",
    "connectorDensity": "접속사 밀도",
    "deixisDensity": "지시어 밀도",
    "hedgeDensity": "헤지 밀도",
    "emphasisDensity": "강조 낱말 밀도",
    "causalDensity": "인과 표지 밀도",
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


def zScore(value: float, meanValue: float, std: float) -> float:
    if std < 1e-9:
        return 0.0 if abs(value - meanValue) < 1e-9 else (3.0 if value > meanValue else -3.0)
    return (value - meanValue) / std


def deviationsFor(metrics: dict[str, float], profile: Profile, scope: str, index: int, line: int) -> list[Deviation]:
    found = []
    for name, value in metrics.items():
        if name not in profile.stats:
            continue
        meanValue, std = profile.stats[name]
        z = zScore(value, meanValue, std)
        if abs(z) >= Z_THRESHOLD:
            found.append(Deviation(scope, index, line, name, value, meanValue, z))
    return found


def sectionMetrics(section: SectionPrint) -> dict[str, float]:
    sentences = tuple(s for p in section.paragraphs for s in p.sentences)
    return metricsOf(sentences, section.paragraphs)


def compareToProfile(doc: DocumentPrint, profile: Profile) -> list[Deviation]:
    deviations = deviationsFor(metricsOf(doc.sentences, doc.paragraphs), profile, "document", -1, 1)
    for section in doc.sections:
        sentenceCount = sum(p.sentenceCount for p in section.paragraphs)
        if sentenceCount < MIN_SENTENCES:
            continue
        deviations.extend(deviationsFor(sectionMetrics(section), profile, "section", section.index, section.startLine))
    return deviations
