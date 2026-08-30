"""현재 brief 직접 생성과 writingArena v1 독자 과업 절차를 실제 모델로 짝 생성한다.

모델 원응답, trial과 suite는 저장소 밖 공통 실행 공간에만 둔다. 자동 안전 계약만 계산하며 사람 선호나
자연스러움 향상을 만들지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRITING_LIFT = ROOT / "tests" / "_attempts" / "writingLift"
PILOT = ROOT / "src" / "hanlint" / "data" / "writingArenaPilotV1.json"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(WRITING_LIFT))

from probeWritingLift import (  # noqa: E402
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

from hanlint import (  # noqa: E402
    Config,
    WritingBrief,
    WritingTrial,
    guardText,
    loadPanelTrialSet,
    preparePanelSuite,
    writingPacket,
)

CONDITIONS = ("plainBrief", "readerTaskDraftV1")
BASELINE_PROTOCOL = (
    "다음 writingBrief만 사실 재료로 사용해 완성된 한국어 마크다운을 써라. reader가 task를 끝낼 수 있게 "
    "facts, mustInclude, allowedNumbers, forbidden과 length를 지킨다. 풀이와 점검표 없이 결과 글만 출력한다."
)
CANDIDATE_PROTOCOL = (
    "다음 hanlint writingPacket으로 완성된 한국어 마크다운을 써라. 먼저 내부에서 독자가 글을 읽은 뒤 "
    "알아야 하거나 느끼거나 해야 할 한 가지를 정한다. 각 원자 사실을 그 목적에 필요한 자리에서 한 번씩만 "
    "쓴다. 사실 목록을 순서대로 되풀이하지 말고 문장 사이 원인, 시간, 행동이나 장면의 관계를 드러낸다. "
    "장르에 맞지 않는 목록과 상투적인 도입을 피하고, 길고 짧은 문장을 내용에 따라 배치한다. comparison의 "
    "수치는 문장 재료나 품질 정답이 아니다. contract를 최우선으로 지키며 내부 검토와 설명은 내지 않는다."
)


def promptsFor(brief: WritingBrief) -> dict[str, str]:
    briefJson = json.dumps(brief.asDict(), ensure_ascii=False, indent=2)
    packetJson = json.dumps(writingPacket(brief, purpose="draft"), ensure_ascii=False, indent=2)
    return {
        "plainBrief": BASELINE_PROTOCOL + "\n\n" + briefJson,
        "readerTaskDraftV1": CANDIDATE_PROTOCOL + "\n\n" + packetJson,
    }


def buildManifest() -> dict:
    trialSet = loadPanelTrialSet(PILOT)
    tasks = []
    for trial in trialSet["trials"]:
        brief = WritingBrief.fromMapping(trial["brief"])
        prompts = promptsFor(brief)
        tasks.append(
            {
                "taskId": trial["id"],
                "brief": brief.asDict(),
                "prompts": prompts,
                "promptSha256": {name: sha256Text(prompt) for name, prompt in prompts.items()},
            }
        )
    payload = {
        "version": 1,
        "trialSetSha256": trialSet["trialSetSha256"],
        "conditions": list(CONDITIONS),
        "generationOptions": GENERATION_OPTIONS,
        "tasks": tasks,
        "claimBoundary": "자동 안전 계약 탐침이며 자연스러움이나 작법 전략 향상의 사람 정답이 아니다",
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def runManifest(manifest: dict, model: str, endpoint: str, timeout: int, output: Path) -> dict:
    modelInfo = ollamaInfo(endpoint, model, timeout)
    if output.exists():
        checkpoint = readJson(output)
        if checkpoint.get("manifestSha256") != manifest["contentSha256"]:
            raise ValueError("기존 writingArena generation 응답의 manifest가 다르다")
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
            key = task["taskId"], condition
            if key in seen:
                continue
            generated, metrics = ollamaGenerate(
                task["prompts"][condition],
                model,
                endpoint,
                timeout,
                GENERATION_OPTIONS,
            )
            checkpoint["responses"].append(
                {
                    "taskId": task["taskId"],
                    "condition": condition,
                    "output": generated,
                    "outputSha256": sha256Text(generated),
                    "metrics": metrics,
                }
            )
            seen.add(key)
            writeJson(output, checkpoint)
            print(f"writingArena generation 응답 {len(seen)}/{total}: {task['taskId']} {condition}", flush=True)
    checkpoint["complete"] = True
    checkpoint["rawResponseSha256"] = sha256Text(stableJson(checkpoint["responses"]))
    writeJson(output, checkpoint)
    return checkpoint


def generationRecord(strategyId: str, model: dict, promptSha256: str, text: str) -> dict:
    return {
        "strategyId": strategyId,
        "modelId": model["name"],
        "modelSha256": model["digest"],
        "promptSha256": promptSha256,
        "outputSha256": sha256(text.encode()).hexdigest(),
        "text": text,
    }


def evaluateRun(manifest: dict, response: dict) -> dict:
    if response.get("manifestSha256") != manifest["contentSha256"] or not response.get("complete"):
        raise ValueError("writingArena generation 응답이 manifest와 다르거나 끝나지 않았다")
    byKey = {(item["taskId"], item["condition"]): item for item in response["responses"]}
    model = response["runner"]["model"]
    trials = []
    details = []
    for task in manifest["tasks"]:
        baseline = byKey[(task["taskId"], "plainBrief")]
        candidate = byKey[(task["taskId"], "readerTaskDraftV1")]
        for item in (baseline, candidate):
            if item["outputSha256"] != sha256Text(item["output"]):
                raise ValueError(f"writingArena generation 원응답 SHA256가 다르다: {task['taskId']}")
        trial = WritingTrial.fromMapping(
            {
                "version": 1,
                "id": task["taskId"],
                "brief": task["brief"],
                "baseline": generationRecord(
                    "plainBrief",
                    model,
                    task["promptSha256"]["plainBrief"],
                    baseline["output"],
                ),
                "candidate": generationRecord(
                    "readerTaskDraftV1",
                    model,
                    task["promptSha256"]["readerTaskDraftV1"],
                    candidate["output"],
                ),
            }
        )
        baselineGuard = guardText(trial.brief, trial.baseline.text, Config(preset=trial.brief.preset)).asDict()
        candidateGuard = guardText(trial.brief, trial.candidate.text, Config(preset=trial.brief.preset)).asDict()
        trials.append(trial)
        details.append(
            {
                "taskId": task["taskId"],
                "genre": trial.brief.preset,
                "baseline": baselineGuard,
                "candidate": candidateGuard,
            }
        )
    suite = preparePanelSuite(trials, "qwen3-writing-arena-generation-v1", 20260831)
    outcomes = Counter(item["safetyOutcome"] for item in suite["excluded"])
    outcomes["bothSafe"] = len(suite["cases"])
    summary = {
        "tasks": len(trials),
        "baselineContractSatisfied": sum(item["baseline"]["contractSatisfied"] for item in details),
        "candidateContractSatisfied": sum(item["candidate"]["contractSatisfied"] for item in details),
        "baselineSurfaceSatisfied": sum(not any(item["baseline"]["surface"].values()) for item in details),
        "candidateSurfaceSatisfied": sum(not any(item["candidate"]["surface"].values()) for item in details),
        "baselineErrorFree": sum(item["baseline"]["lint"]["errorCount"] == 0 for item in details),
        "candidateErrorFree": sum(item["candidate"]["lint"]["errorCount"] == 0 for item in details),
        "safetyOutcomes": dict(sorted(outcomes.items())),
        "humanPreferenceEligible": len(suite["cases"]),
    }
    payload = {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "responseSha256": sha256Text(stableJson(response)),
        "model": model,
        "summary": summary,
        "details": details,
        "trialSha256": [trial.digest for trial in trials],
        "suiteSha256": suite["suiteSha256"],
        "limits": [
            "자동 계약은 사실 관계, 자연스러움과 독자 효용을 판정하지 않는다",
            "사람 패널 합의가 없으므로 후보 전략의 향상을 주장하지 않는다",
            "일곱 개 자체 작성 brief는 실제 사용 분포를 대표하지 않는다",
        ],
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def selfTest() -> None:
    manifest = buildManifest()
    assert len(manifest["tasks"]) == 7 and manifest["conditions"] == list(CONDITIONS)
    assert all("comparison" in task["prompts"]["readerTaskDraftV1"] for task in manifest["tasks"])


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="writingArena 실제 생성 전략 탐침")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--output", type=Path, required=True)
    run = subparsers.add_parser("run")
    run.add_argument("manifest", type=Path)
    run.add_argument("--model", required=True)
    run.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    run.add_argument("--timeout", type=int, default=600)
    run.add_argument("--output", type=Path, required=True)
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("manifest", type=Path)
    evaluate.add_argument("response", type=Path)
    evaluate.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        selfTest()
        print("writingArena generation self-test 완료")
        return 0
    args = parseArgs(argv)
    if args.command == "prepare":
        writeJson(args.output, buildManifest())
        print(f"writingArena generation manifest SHA256: {sha256File(args.output)}")
    elif args.command == "run":
        response = runManifest(readJson(args.manifest), args.model, args.endpoint, args.timeout, args.output)
        print(f"writingArena generation response SHA256: {sha256Text(stableJson(response))}")
    else:
        result = evaluateRun(readJson(args.manifest), readJson(args.response))
        writeJson(args.output, result)
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
        print(f"writingArena generation result SHA256: {sha256File(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
