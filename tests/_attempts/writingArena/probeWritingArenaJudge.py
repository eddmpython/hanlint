"""일곱 장르의 양방향 글 쌍으로 자동 심사기의 순서 일관성만 실측한다.

사람 합의가 없으므로 선호 정확도와 작법 전략 향상은 계산하지 않는다. manifest, 모델 원응답과 결과
JSON은 저장소 밖 공통 실행 공간에만 쓴다.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRITING_LIFT = ROOT / "tests" / "_attempts" / "writingLift"
PILOT = ROOT / "src" / "hanlint" / "data" / "writingArenaPilotV1.json"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(WRITING_LIFT))

from probeWritingLift import (  # noqa: E402
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
    PANEL_DIMENSIONS,
    loadPanelTrialSet,
    preparePanelJudgeCases,
    preparePanelSuite,
    summarizePanelJudgeConsistency,
)

GENERATION_OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 1024}
PROMPT_PROTOCOL = (
    "당신은 한국어 글 A/B 심사기다. 생성 전략, 모델이나 작성자를 추측하지 않는다. context의 독자, 과업, "
    "원자 사실, 필수 표면, 허용 숫자와 금지 주장을 기준으로 왼쪽과 오른쪽 content를 먼저 각각 판정한다. "
    "뜻을 바꾸거나 지어낸 내용이 있으면 fail, 확실히 판단할 수 없으면 abstain이다. 한쪽이라도 pass가 아니면 "
    "모든 preference를 abstain과 confidence 0으로 둔다. 둘 다 pass면 naturalness, clarity, taskUtility를 "
    "left, right, tie 가운데 고른다. 차이가 없으면 tie다. voiceReference가 없으면 voice는 반드시 abstain과 "
    "confidence 0이다. confidence는 선택의 확신을 0부터 1까지 적는다. 설명은 쓰지 않는다."
)
DECISION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["contentChecks", "preferences"],
    "properties": {
        "contentChecks": {
            "type": "object",
            "additionalProperties": False,
            "required": ["left", "right"],
            "properties": {
                side: {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["choice", "confidence"],
                    "properties": {
                        "choice": {"enum": ["pass", "fail", "abstain"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                }
                for side in ("left", "right")
            },
        },
        "preferences": {
            "type": "object",
            "additionalProperties": False,
            "required": list(PANEL_DIMENSIONS),
            "properties": {
                dimension: {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["choice", "confidence"],
                    "properties": {
                        "choice": {"enum": ["left", "right", "tie", "abstain"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                }
                for dimension in PANEL_DIMENSIONS
            },
        },
    },
}


def promptFor(presentation: dict) -> str:
    visible = {
        "context": presentation["context"],
        "comparison": presentation["comparison"],
    }
    return PROMPT_PROTOCOL + "\n\n" + json.dumps(visible, ensure_ascii=False, indent=2)


def buildManifest() -> dict:
    trialSet = loadPanelTrialSet(PILOT)
    suite = preparePanelSuite(trialSet["trials"], trialSet["studyId"], 20260831)
    judgeCases = preparePanelJudgeCases(suite)
    presentations = []
    for item in judgeCases["presentations"]:
        prompt = promptFor(item)
        presentations.append(
            {
                "presentationId": item["presentationId"],
                "presentationSha256": item["presentationSha256"],
                "prompt": prompt,
                "promptSha256": sha256Text(prompt),
            }
        )
    payload = {
        "version": 1,
        "trialSetSha256": trialSet["trialSetSha256"],
        "suite": suite,
        "judgeCases": judgeCases,
        "promptProtocolSha256": sha256Text(PROMPT_PROTOCOL),
        "generationOptions": GENERATION_OPTIONS,
        "decisionSchema": DECISION_SCHEMA,
        "presentations": presentations,
        "claimBoundary": "사람 합의가 없는 순서 일관성 탐침이며 선호 정확도나 글 품질 평가가 아니다",
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def runManifest(manifest: dict, model: str, endpoint: str, timeout: int, output: Path) -> dict:
    modelInfo = ollamaInfo(endpoint, model, timeout)
    if output.exists():
        checkpoint = readJson(output)
        if checkpoint.get("manifestSha256") != manifest["contentSha256"]:
            raise ValueError("기존 writingArena judge 응답의 manifest가 다르다")
    else:
        checkpoint = {
            "version": 1,
            "complete": False,
            "manifestSha256": manifest["contentSha256"],
            "runner": {"model": modelInfo, "think": False, "options": GENERATION_OPTIONS},
            "responses": [],
        }
    seen = {item["presentationId"] for item in checkpoint["responses"]}
    total = len(manifest["presentations"])
    for item in manifest["presentations"]:
        if item["presentationId"] in seen:
            continue
        generated, metrics = ollamaGenerate(
            item["prompt"],
            model,
            endpoint,
            timeout,
            GENERATION_OPTIONS,
            DECISION_SCHEMA,
        )
        json.loads(generated)
        checkpoint["responses"].append(
            {
                "presentationId": item["presentationId"],
                "promptSha256": item["promptSha256"],
                "output": generated,
                "outputSha256": sha256Text(generated),
                "metrics": metrics,
            }
        )
        seen.add(item["presentationId"])
        writeJson(output, checkpoint)
        print(f"writingArena judge 응답 {len(seen)}/{total}: {item['presentationId']}", flush=True)
    checkpoint["complete"] = True
    checkpoint["rawResponseSha256"] = sha256Text(stableJson(checkpoint["responses"]))
    writeJson(output, checkpoint)
    return checkpoint


def evaluateRun(manifest: dict, response: dict) -> dict:
    if response.get("manifestSha256") != manifest["contentSha256"]:
        raise ValueError("writingArena judge 응답의 manifest가 다르다")
    if not response.get("complete"):
        raise ValueError("writingArena judge 응답이 아직 끝나지 않았다")
    expected = {item["presentationId"]: item for item in manifest["judgeCases"]["presentations"]}
    promptHashes = {item["presentationId"]: item["promptSha256"] for item in manifest["presentations"]}
    predictions = []
    contractViolations = []
    for responseItem in response["responses"]:
        identifier = responseItem["presentationId"]
        if responseItem["promptSha256"] != promptHashes.get(identifier):
            raise ValueError(f"writingArena judge prompt SHA256가 다르다: {identifier}")
        if responseItem["outputSha256"] != sha256Text(responseItem["output"]):
            raise ValueError(f"writingArena judge 원응답 SHA256가 다르다: {identifier}")
        decision = json.loads(responseItem["output"])
        presentation = expected[identifier]
        violations = decisionViolations(presentation, decision)
        contractViolations.extend({"presentationId": identifier, "violation": value} for value in violations)
        if violations:
            decision = failClosedDecision()
        predictions.append(
            {
                "presentationId": identifier,
                "presentationSha256": expected[identifier]["presentationSha256"],
                "contentChecks": decision["contentChecks"],
                "preferences": decision["preferences"],
            }
        )
    model = response["runner"]["model"]
    predictionBundle = {
        "version": 1,
        "kind": "hanlint.panelJudgePredictions",
        "judgeCasesSha256": manifest["judgeCases"]["judgeCasesSha256"],
        "evaluatorId": model["name"],
        "evaluatorRevision": model["digest"],
        "promptSha256": manifest["promptProtocolSha256"],
        "predictions": predictions,
    }
    result = summarizePanelJudgeConsistency(manifest["suite"], manifest["judgeCases"], predictionBundle)
    payload = {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "responseSha256": sha256Text(stableJson(response)),
        "model": model,
        "rawContract": {
            "presentations": len(response["responses"]),
            "valid": len(response["responses"]) - len({item["presentationId"] for item in contractViolations}),
            "invalid": len({item["presentationId"] for item in contractViolations}),
            "violations": dict(sorted(Counter(item["violation"] for item in contractViolations).items())),
            "invalidPresentationIds": sorted({item["presentationId"] for item in contractViolations}),
            "handling": "위반 presentation 전체를 fail-closed abstain으로 바꾼 사본만 일관성 계산에 사용했다",
        },
        "result": result,
        "limits": [
            "사람 합의가 없어 선호 정확도와 calibration을 계산하지 않았다",
            "자체 작성한 일곱 쌍은 작법 전략의 향상 정답이 아니다",
            "순서 일관성은 같은 오류를 두 번 낸 심사기도 높을 수 있다",
        ],
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def decisionViolations(presentation: dict, decision: dict) -> list[str]:
    violations = []
    content = decision["contentChecks"]
    preferences = decision["preferences"]
    for side in ("left", "right"):
        if content[side]["choice"] == "abstain" and content[side]["confidence"] != 0:
            violations.append("contentAbstainConfidence")
    for dimension in PANEL_DIMENSIONS:
        if preferences[dimension]["choice"] == "abstain" and preferences[dimension]["confidence"] != 0:
            violations.append("preferenceAbstainConfidence")
    if any(content[side]["choice"] != "pass" for side in ("left", "right")) and any(
        preferences[dimension]["choice"] != "abstain" for dimension in PANEL_DIMENSIONS
    ):
        violations.append("preferenceAfterContentFailure")
    if presentation["context"]["voiceReference"] is None and preferences["voice"]["choice"] != "abstain":
        violations.append("voiceWithoutReference")
    return sorted(set(violations))


def failClosedDecision() -> dict:
    return {
        "contentChecks": {
            "left": {"choice": "abstain", "confidence": 0.0},
            "right": {"choice": "abstain", "confidence": 0.0},
        },
        "preferences": {dimension: {"choice": "abstain", "confidence": 0.0} for dimension in PANEL_DIMENSIONS},
    }


def selfTest() -> None:
    manifest = buildManifest()
    assert len(manifest["presentations"]) == 14
    shown = stableJson(manifest["judgeCases"])
    assert "contextFirstV1" not in shown and "plainBrief" not in shown and "consensus" not in shown
    assert all(":forward" not in item["prompt"] and ":reversed" not in item["prompt"] for item in manifest["presentations"])


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="writingArena 자동 심사기 순서 일관성 탐침")
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
        print("writingArena judge self-test 완료")
        return 0
    args = parseArgs(argv)
    if args.command == "prepare":
        writeJson(args.output, buildManifest())
        print(f"writingArena manifest SHA256: {sha256File(args.output)}")
    elif args.command == "run":
        response = runManifest(readJson(args.manifest), args.model, args.endpoint, args.timeout, args.output)
        print(f"writingArena response SHA256: {sha256Text(stableJson(response))}")
    else:
        result = evaluateRun(readJson(args.manifest), readJson(args.response))
        writeJson(args.output, result)
        print(json.dumps(result["result"]["positionConsistency"], ensure_ascii=False, indent=2))
        print(f"writingArena result SHA256: {sha256File(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
