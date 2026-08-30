"""일곱 프리셋이 같은 블라인드 아레나 계약을 통과하는지 확인한다."""

from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRITING_LIFT = ROOT / "tests" / "_attempts" / "writingLift"
FACT_CONTRACT = ROOT / "tests" / "_attempts" / "factContract"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(WRITING_LIFT))
sys.path.insert(0, str(FACT_CONTRACT))

from probeFactContract import briefOf  # noqa: E402
from probeWritingLift import BRIEFS  # noqa: E402

from hanlint import Config, WritingTrial, aggregateResults, prepareBlind, recordEvaluation, revealTrial  # noqa: E402
from hanlint.rules import ruleNames  # noqa: E402


def generation(strategyId: str, text: str) -> dict:
    digest = sha256(text.encode()).hexdigest()
    return {
        "strategyId": strategyId,
        "modelId": "self-test",
        "modelSha256": "a" * 64,
        "promptSha256": "b" * 64,
        "outputSha256": digest,
        "text": text,
    }


def fittedText(brief, reverse: bool) -> str:
    facts = [fact.statement for fact in brief.facts]
    if reverse:
        facts.reverse()
    text = f"# {brief.task}\n\n" + "\n\n".join(facts)
    while len(text) < brief.minCharacters:
        text += "\n\n" + facts[0]
    if len(text) > brief.maxCharacters:
        raise ValueError(f"{brief.preset} fixture가 길이 범위를 넘는다")
    return text


def buildTrials() -> list[WritingTrial]:
    trials = []
    for task in BRIEFS:
        brief = briefOf(task)
        baseline = fittedText(brief, False)
        candidate = fittedText(brief, True)
        trials.append(
            WritingTrial.fromMapping(
                {
                    "version": 1,
                    "id": task["id"],
                    "brief": brief.asDict(),
                    "baseline": generation("plainBrief", baseline),
                    "candidate": generation("selfTestCandidate", candidate),
                }
            )
        )
    return trials


def selfTest() -> dict:
    config = Config(disable=set(ruleNames()))
    results = []
    for index, trial in enumerate(buildTrials(), start=1):
        blind = prepareBlind(trial, index, config)
        assert blind["eligibleForPreference"] and "selfTestCandidate" not in json.dumps(blind, ensure_ascii=False)
        evaluation = blind["evaluationTemplate"] | {
            "evaluatorId": "self-test-human",
            "decisions": {"naturalness": "tie", "taskUtility": "tie", "voice": "tie"},
            "note": "계약 배선만 확인하는 합성 평가다.",
        }
        recorded = recordEvaluation(blind, evaluation)
        results.append(revealTrial(trial, blind, recorded, config))
    aggregate = aggregateResults(results)
    assert aggregate["trials"] == 7
    assert aggregate["safety"]["bothSafe"] == 7
    assert aggregate["preferences"]["human"]["naturalness"]["tie"] == 7
    return aggregate


if __name__ == "__main__":
    result = selfTest()
    print("blindWritingArena self-test 통과")
    print(f"aggregate SHA256: {result['aggregateSha256']}")
