"""글 여러 편의 지문에서 프로파일을 만든다. 자료형과 읽기는 data/profiles.py 가, 견줌은 규칙 outsideProfile 이 한다.

종류별 프로파일 (scripts/buildProfiles.py) 과 사용자 프로파일 (hanlint profile build) 이 같은 함수로 만들어지므로 같은
글에 같은 표가 나온다. 처음 나온 화제어의 셈은 독자 상태 (fingerprint/readerState.py) 의 known 과 같은 정의다.
"""

from __future__ import annotations

from collections import Counter

from ..data.profiles import PERCENTILES, Profile, histogram
from ..fingerprint import DocumentPrint

SENTENCE_FEATURES = ("length", "commas", "euiCount", "nounRun", "deixis", "hedges", "numbers", "newTopics", "causal")
NO_ENDING = "없음"
RATES = ("connector", "question", "readerCall", "deixis")


def sentenceValues(doc: DocumentPrint) -> dict[str, list[int]]:
    values: dict[str, list[int]] = {name: [] for name in SENTENCE_FEATURES}
    for sentence in doc.sentences:
        known = doc.reader.beforeSentence[sentence.index].known
        values["length"].append(sentence.length)
        values["commas"].append(sentence.commas)
        values["euiCount"].append(sentence.euiCount)
        values["nounRun"].append(sentence.nounRun)
        values["deixis"].append(len(sentence.deixis))
        values["hedges"].append(sentence.hedges)
        values["numbers"].append(sentence.numbers)
        values["newTopics"].append(len(sentence.topics - known))
        values["causal"].append(sentence.causal)
    return values


def endingRunsOf(doc: DocumentPrint) -> list[int]:
    runs: list[int] = []
    for paragraph in doc.paragraphs:
        current, length = None, 0
        for sentence in paragraph.sentences:
            if sentence.ending == current:
                length += 1
            else:
                if current not in (None, NO_ENDING):
                    runs.append(length)
                current, length = sentence.ending, 1
        if current not in (None, NO_ENDING):
            runs.append(length)
    return runs


def endingTransitionsOf(doc: DocumentPrint) -> Counter:
    counts: Counter = Counter()
    for paragraph in doc.paragraphs:
        endings = [sentence.ending for sentence in paragraph.sentences]
        for before, after in zip(endings, endings[1:], strict=False):
            counts[f"{before}|{after}"] += 1
    return counts


def rateOf(doc: DocumentPrint, name: str) -> float:
    total = len(doc.sentences)
    if not total:
        return 0.0
    if name == "connector":
        hits = sum(1 for s in doc.sentences if s.connectorStart)
    elif name == "question":
        hits = sum(1 for s in doc.sentences if s.mood == "의문")
    elif name == "readerCall":
        hits = sum(1 for s in doc.sentences if s.readerCall)
    else:
        hits = sum(len(s.deixis) for s in doc.sentences)
    return hits / total


def documentPercentiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {f"p{p}": round(ordered[min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1)))], 4) for p in PERCENTILES}


def buildProfile(docs: list[DocumentPrint], kind: str = "custom") -> Profile:
    """글 여러 편의 지문에서 참조 분포를 만든다. 글이 없으면 만들 것이 없다."""
    if not docs:
        raise ValueError("프로파일을 만들 글이 없다. 마크다운 파일이 있는 폴더를 준다")
    sentence: dict[str, list[int]] = {name: [] for name in SENTENCE_FEATURES}
    paragraphCounts: list[int] = []
    runs: list[int] = []
    transitions: Counter = Counter()
    rates: dict[str, list[float]] = {name: [] for name in RATES}
    for doc in docs:
        for name, values in sentenceValues(doc).items():
            sentence[name].extend(values)
        paragraphCounts.extend(p.sentenceCount for p in doc.paragraphs if p.sentenceCount)
        runs.extend(endingRunsOf(doc))
        transitions.update(endingTransitionsOf(doc))
        for name in rates:
            rates[name].append(rateOf(doc, name))
    return Profile(
        kind=kind,
        documents=len(docs),
        sentences=sum(len(doc.sentences) for doc in docs),
        paragraphs=sum(len(doc.paragraphs) for doc in docs),
        sentence={name: histogram(values) for name, values in sentence.items()},
        paragraph={"sentenceCount": histogram(paragraphCounts)},
        endingRuns=histogram(runs),
        endingTransitions=dict(sorted(transitions.items())),
        rates={name: documentPercentiles(values) for name, values in rates.items()},
    )
