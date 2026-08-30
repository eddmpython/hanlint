"""원문 없는 수사 구조 청사진을 같은 WritingBrief의 기본 패킷과 짝 비교한다.

모델 원응답, trial과 blind packet은 저장소 밖 실행 루트에만 쓴다. 사람 평가를 만들거나 자연스러움
향상을 주장하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRITING_LIFT = ROOT / "tests" / "_attempts" / "writingLift"
FACT_CONTRACT = ROOT / "tests" / "_attempts" / "factContract"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(WRITING_LIFT))
sys.path.insert(0, str(FACT_CONTRACT))

from probeFactContract import briefOf  # noqa: E402
from probeWritingLift import (  # noqa: E402
    BRIEFS,
    GENERATION_OPTIONS,
    OLLAMA_ENDPOINT,
    ollamaGenerate,
    ollamaInfo,
    readJson,
    sha256File,
    sha256Text,
    stableJson,
    writeJson,
)

from hanlint import Config, WritingBrief, WritingTrial, guardText, prepareBlind, writingPacket  # noqa: E402
from hanlint.blueprint import STRATEGY_ID  # noqa: E402

CONDITIONS = ("plainBrief", STRATEGY_ID)


def promptFor(brief: WritingBrief, strategy: str | None = None) -> str:
    packet = writingPacket(brief, purpose="draft", strategy=strategy)
    return (
        "다음 hanlint writingPacket을 실행하라. contract를 최우선으로 지키고 input.brief만 사실 재료로 "
        "사용한다. strategy가 있으면 사실이나 문장을 가져오지 말고 구조 예산으로만 쓴다. 풀이, 점검표와 "
        "작성 과정 없이 완성된 한국어 마크다운만 출력하라.\n\n" + json.dumps(packet, ensure_ascii=False, indent=2)
    )


def buildManifest() -> dict:
    tasks = []
    for source in BRIEFS:
        brief = briefOf(source)
        prompts = {
            "plainBrief": promptFor(brief),
            STRATEGY_ID: promptFor(brief, STRATEGY_ID),
        }
        tasks.append(
            {
                "id": source["id"],
                "brief": brief.asDict(),
                "prompts": prompts,
                "promptSha256": {name: sha256Text(prompt) for name, prompt in prompts.items()},
            }
        )
    payload = {
        "version": 1,
        "conditions": list(CONDITIONS),
        "generationOptions": GENERATION_OPTIONS,
        "tasks": tasks,
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def runManifest(manifest: dict, model: str, endpoint: str, timeout: int, output: Path) -> dict:
    modelInfo = ollamaInfo(endpoint, model, timeout)
    if output.exists():
        checkpoint = readJson(output)
        if checkpoint.get("manifestSha256") != manifest["contentSha256"]:
            raise ValueError("기존 rhetoricalBlueprint 응답의 manifest가 다르다")
    else:
        checkpoint = {
            "version": 1,
            "complete": False,
            "manifestSha256": manifest["contentSha256"],
            "runner": {"model": modelInfo, "think": False, "options": GENERATION_OPTIONS},
            "responses": [],
        }
    seen = {(item["taskId"], item["condition"]) for item in checkpoint["responses"]}
    total = len(manifest["tasks"]) * len(CONDITIONS)
    for task in manifest["tasks"]:
        for condition in CONDITIONS:
            key = task["id"], condition
            if key in seen:
                continue
            generated, metrics = ollamaGenerate(task["prompts"][condition], model, endpoint, timeout, GENERATION_OPTIONS)
            checkpoint["responses"].append(
                {
                    "taskId": task["id"],
                    "condition": condition,
                    "output": generated,
                    "outputSha256": sha256Text(generated),
                    "metrics": metrics,
                }
            )
            seen.add(key)
            writeJson(output, checkpoint)
            print(f"수사 구조 응답 {len(seen)}/{total}: {task['id']} {condition}", flush=True)
    checkpoint["complete"] = True
    checkpoint["rawResponseSha256"] = sha256Text(stableJson(checkpoint["responses"]))
    writeJson(output, checkpoint)
    return checkpoint


def generation(response: dict, strategyId: str, model: dict, promptSha256: str) -> dict:
    return {
        "strategyId": strategyId,
        "modelId": model["name"],
        "modelSha256": model["digest"],
        "promptSha256": promptSha256,
        "outputSha256": response["outputSha256"],
        "text": response["output"],
    }


def score(manifest: dict, responses: dict) -> dict:
    byKey = {(item["taskId"], item["condition"]): item for item in responses["responses"]}
    trials = []
    blinds = []
    details = []
    for index, task in enumerate(manifest["tasks"], start=1):
        brief = WritingBrief.fromMapping(task["brief"])
        baseline = byKey[(task["id"], "plainBrief")]
        candidate = byKey[(task["id"], STRATEGY_ID)]
        trial = WritingTrial.fromMapping(
            {
                "version": 1,
                "id": f"{task['id']}-rhetorical-blueprint-v1",
                "brief": task["brief"],
                "baseline": generation(
                    baseline,
                    "plainBrief",
                    responses["runner"]["model"],
                    task["promptSha256"]["plainBrief"],
                ),
                "candidate": generation(
                    candidate,
                    STRATEGY_ID,
                    responses["runner"]["model"],
                    task["promptSha256"][STRATEGY_ID],
                ),
            }
        )
        blind = prepareBlind(trial, 42 + index, Config(preset=brief.preset))
        baselineGuard = guardText(brief, baseline["output"], Config(preset=brief.preset)).asDict()
        candidateGuard = guardText(brief, candidate["output"], Config(preset=brief.preset)).asDict()
        trials.append(trial.asDict())
        blinds.append(blind)
        details.append(
            {
                "taskId": task["id"],
                "safetyOutcome": blind["safetyOutcome"],
                "eligibleForPreference": blind["eligibleForPreference"],
                "baseline": baselineGuard,
                "candidate": candidateGuard,
            }
        )
    outcomes = Counter(item["safetyOutcome"] for item in details)
    summary = {
        "tasks": len(details),
        "baselineContractSatisfied": sum(item["baseline"]["contractSatisfied"] for item in details),
        "candidateContractSatisfied": sum(item["candidate"]["contractSatisfied"] for item in details),
        "baselineSurfaceSatisfied": sum(not any(item["baseline"]["surface"].values()) for item in details),
        "candidateSurfaceSatisfied": sum(not any(item["candidate"]["surface"].values()) for item in details),
        "baselineLengthSatisfied": sum(item["baseline"]["length"]["satisfied"] for item in details),
        "candidateLengthSatisfied": sum(item["candidate"]["length"]["satisfied"] for item in details),
        "baselineErrorFree": sum(item["baseline"]["lint"]["errorCount"] == 0 for item in details),
        "candidateErrorFree": sum(item["candidate"]["lint"]["errorCount"] == 0 for item in details),
        "safety": {name: outcomes[name] for name in ("candidateSafeWin", "baselineSafeWin", "bothSafe", "bothUnsafe")},
        "blindPacketsAwaitingHumanEvaluation": sum(item["eligibleForPreference"] for item in details),
    }
    payload = {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "responsesSha256": responses["rawResponseSha256"],
        "summary": summary,
        "details": details,
        "trials": trials,
        "blinds": blinds,
        "claimBoundary": "사람 평가가 없으므로 자연스러움, 독자 과업과 목소리의 향상을 주장하지 않는다",
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def selfTest() -> None:
    manifest = buildManifest()
    assert len(manifest["tasks"]) == 7
    for task in manifest["tasks"]:
        brief = WritingBrief.fromMapping(task["brief"])
        plain = writingPacket(brief, purpose="draft")
        candidate = writingPacket(brief, purpose="draft", strategy=STRATEGY_ID)
        assert "strategy" not in plain and candidate["strategy"]["strategyId"] == STRATEGY_ID
        assert task["promptSha256"] == {name: sha256Text(prompt) for name, prompt in task["prompts"].items()}
        assert task["prompts"]["plainBrief"] != task["prompts"][STRATEGY_ID]


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="수사 구조 청사진 짝 생성과 블라인드 안전 탐침")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--output", type=Path, required=True)
    run = subparsers.add_parser("run")
    run.add_argument("manifest", type=Path)
    run.add_argument("--model", required=True)
    run.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    run.add_argument("--timeout", type=int, default=300)
    run.add_argument("--output", type=Path, required=True)
    scoreParser = subparsers.add_parser("score")
    scoreParser.add_argument("manifest", type=Path)
    scoreParser.add_argument("responses", type=Path)
    scoreParser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        selfTest()
        print("rhetoricalBlueprint self-test 통과")
        return 0
    args = parseArgs(argv)
    if args.command == "prepare":
        writeJson(args.output, buildManifest())
        print(f"rhetoricalBlueprint manifest SHA256: {sha256File(args.output)}")
    elif args.command == "run":
        runManifest(readJson(args.manifest), args.model, args.endpoint, args.timeout, args.output)
        print(f"rhetoricalBlueprint responses SHA256: {sha256File(args.output)}")
    else:
        result = score(readJson(args.manifest), readJson(args.responses))
        writeJson(args.output, result)
        print(result["summary"])
        print(f"rhetoricalBlueprint score SHA256: {sha256File(args.output)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
