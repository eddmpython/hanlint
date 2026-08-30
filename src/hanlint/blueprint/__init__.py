"""글 종류의 편집 말뭉치 분포를 원문 없는 구조 예산으로 컴파일한다."""

from __future__ import annotations

from ..config import PROFILE_OF, WritingBrief
from ..data.blueprints import BLUEPRINT_VERSION, referenceOf

STRATEGY_ID = "rhetoricalBlueprintV1"
STRATEGIES = (STRATEGY_ID,)


def _allocate(total: int, weights: list[int], minimums: list[int] | None = None) -> list[int]:
    """합계를 가중치에 나누되 자리별 최솟값과 전체 합계를 정확히 보존한다."""
    minimums = minimums or [1] * len(weights)
    if not weights or len(weights) != len(minimums) or any(weight < 1 for weight in weights):
        raise ValueError("가중치와 최솟값은 같은 수의 양의 자리여야 한다")
    if total < sum(minimums):
        raise ValueError("나눌 합계는 자리별 최솟값의 합 이상이어야 한다")
    weightTotal = sum(weights)
    remainderTotal = total - sum(minimums)
    allocated = [minimum + remainderTotal * weight // weightTotal for minimum, weight in zip(minimums, weights, strict=True)]
    order = sorted(
        range(len(weights)),
        key=lambda item: (-(remainderTotal * weights[item] % weightTotal), item),
    )
    for index in order[: total - sum(allocated)]:
        allocated[index] += 1
    return allocated


def rhetoricalBlueprint(brief: WritingBrief | dict) -> dict:
    """brief의 종류와 길이에 맞는 원문 없는 수사 구조 예산을 낸다."""
    if isinstance(brief, dict):
        brief = WritingBrief.fromMapping(brief)
    kind = PROFILE_OF[brief.preset]
    corpus, reference = referenceOf(kind)
    metrics = reference.metrics
    targetCharacters = (brief.minCharacters + brief.maxCharacters) // 2
    typicalParagraph = max(1, metrics["paragraphCharacters"]["p50"])
    typicalSentence = max(1, metrics["sentenceCharacters"]["p50"])
    referenceSections = max(1, metrics["sections"]["p50"])
    sectionCount = min(referenceSections, max(1, targetCharacters // 180))
    paragraphCount = max(sectionCount, round(targetCharacters / typicalParagraph))
    sentenceCount = max(paragraphCount, round(targetCharacters / typicalSentence))
    opening = min(300, max(50, metrics["openingSharePermille"]["p50"]))
    closing = min(300, max(50, metrics["closingSharePermille"]["p50"]))
    if targetCharacters < 180:
        names = ["whole"]
        roleWeights = [1000]
    else:
        names = ["opening", "body", "closing"]
        roleWeights = [opening, 1000 - opening - closing, closing]
    paragraphCount = max(paragraphCount, len(names))
    sentenceCount = max(sentenceCount, paragraphCount)
    paragraphBudgets = _allocate(paragraphCount, roleWeights)
    sentenceBudgets = _allocate(sentenceCount, roleWeights, paragraphBudgets)
    characterBudgets = _allocate(targetCharacters, roleWeights, sentenceBudgets)
    position = 0
    roles = []
    for name, characters, paragraphs, sentences in zip(
        names,
        characterBudgets,
        paragraphBudgets,
        sentenceBudgets,
        strict=True,
    ):
        end = position + characters * 1000 // targetCharacters
        roles.append(
            {
                "role": name,
                "startPermille": position,
                "endPermille": end,
                "characters": characters,
                "paragraphs": paragraphs,
                "sentences": sentences,
            }
        )
        position = end
    roles[-1]["endPermille"] = 1000
    if sectionCount == 1:
        sectionWeights = [1000]
    elif sectionCount == 2:
        sectionWeights = [opening, closing]
    else:
        sectionWeights = [opening, *_allocate(1000 - opening - closing, [1] * (sectionCount - 2)), closing]
    sectionParagraphs = _allocate(paragraphCount, sectionWeights)
    sectionSentences = _allocate(sentenceCount, sectionWeights, sectionParagraphs)
    sectionCharacters = _allocate(targetCharacters, sectionWeights, sectionSentences)
    sectionBudgets = [
        {
            "index": index,
            "characters": characters,
            "paragraphs": paragraphs,
            "sentences": sentences,
        }
        for index, (characters, paragraphs, sentences) in enumerate(
            zip(sectionCharacters, sectionParagraphs, sectionSentences, strict=True), start=1
        )
    ]
    return {
        "version": BLUEPRINT_VERSION,
        "kind": "hanlint.rhetoricalBlueprint",
        "strategyId": STRATEGY_ID,
        "input": {
            "briefSha256": brief.digest,
            "preset": brief.preset,
            "targetCharacters": targetCharacters,
        },
        "budget": {
            "sections": sectionCount,
            "paragraphs": paragraphCount,
            "sentences": sentenceCount,
            "sectionBudgets": sectionBudgets,
            "roles": roles,
        },
        "reference": {
            "kind": kind,
            "documents": reference.documents,
            "sourceIds": list(reference.sourceIds),
            "corpus": corpus,
            "observed": {
                name: metrics[name]
                for name in (
                    "proseCharacters",
                    "sections",
                    "paragraphs",
                    "sentences",
                    "paragraphCharacters",
                    "paragraphSentences",
                    "sentenceCharacters",
                    "sectionParagraphs",
                    "sectionSentences",
                    "adjacentSentenceCharacterDelta",
                    "openingSharePermille",
                    "closingSharePermille",
                )
            },
        },
        "limits": [
            "이 청사진은 사실, 문장, 제목, 표현과 품질 점수를 포함하지 않는다",
            "budget은 같은 종류 편집 글의 구조 백분위에서 잡은 초안 예산이지 정답이나 합격 기준이 아니다",
            "brief만 사실 재료로 쓰고 글의 의미와 자연스러움은 guard와 블라인드 평가로 따로 확인한다",
        ],
    }


def blueprintFor(brief: WritingBrief | dict, strategy: str = STRATEGY_ID) -> dict:
    """이름을 검증한 뒤 선택한 구조 전략을 컴파일한다."""
    if strategy not in STRATEGIES:
        raise ValueError(f"모르는 작법 전략이다: {strategy}. 가능한 값: {', '.join(STRATEGIES)}")
    return rhetoricalBlueprint(brief)


__all__ = ["STRATEGIES", "STRATEGY_ID", "blueprintFor", "rhetoricalBlueprint"]
