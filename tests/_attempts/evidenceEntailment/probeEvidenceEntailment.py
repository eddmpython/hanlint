"""gold 없는 KLUE-NLI 파생 36개로 외부 평가기의 3분류와 기권을 재현한다.

manifest, 모델 원응답과 집계 JSON은 저장소 밖 실행 루트에만 쓴다. 저장소에는 실행 절차와 집계 기록만
남긴다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRITING_LIFT = ROOT / "tests" / "_attempts" / "writingLift"
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

from hanlint import entailmentCases, evaluateEntailment  # noqa: E402

GENERATION_OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 4096}
OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["predictions"],
    "properties": {
        "predictions": {
            "type": "array",
            "minItems": 36,
            "maxItems": 36,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["caseId", "label", "confidence"],
                "properties": {
                    "caseId": {"type": "string", "pattern": "^KEN[0-9]{3}$"},
                    "label": {"enum": ["supported", "contradicted", "insufficient", "abstain"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        }
    },
}


def promptFor(cases: dict) -> str:
    return (
        "당신은 한국어 자연어 함의 평가기다. 각 evidenceExcerpt가 참이라고 가정하고 atomicFact와의 "
        "문맥상 관계만 분류하라. supported는 fact가 반드시 참, contradicted는 반드시 거짓, "
        "insufficient는 참과 거짓을 정할 수 없음이다. 세상 지식이나 문장 자체의 진위를 보태지 않는다. "
        "확실히 고를 수 없으면 abstain과 confidence 0을 쓴다. 모든 caseId를 정확히 한 번씩 내고 설명은 "
        "쓰지 않는다. confidence는 선택한 관계를 확신하는 0부터 1까지의 수다.\n\n" + json.dumps(cases, ensure_ascii=False)
    )


def buildManifest() -> dict:
    cases = entailmentCases()
    prompt = promptFor(cases)
    payload = {
        "version": 1,
        "benchmarkId": cases["benchmarkId"],
        "benchmarkSha256": cases["benchmarkSha256"],
        "casesSha256": cases["contentSha256"],
        "prompt": prompt,
        "promptSha256": sha256Text(prompt),
        "generationOptions": GENERATION_OPTIONS,
        "outputSchema": OUTPUT_SCHEMA,
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def runManifest(manifest: dict, model: str, endpoint: str, timeout: int, output: Path) -> dict:
    modelInfo = ollamaInfo(endpoint, model, timeout)
    generated, metrics = ollamaGenerate(
        manifest["prompt"],
        model,
        endpoint,
        timeout,
        manifest["generationOptions"],
        manifest["outputSchema"],
    )
    response = {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "runner": {"model": modelInfo, "think": False, "options": manifest["generationOptions"]},
        "output": generated,
        "outputSha256": sha256Text(generated),
        "metrics": metrics,
    }
    response["contentSha256"] = sha256Text(stableJson(response))
    writeJson(output, response)
    return response


def evaluateRun(manifest: dict, response: dict) -> dict:
    if response.get("manifestSha256") != manifest["contentSha256"]:
        raise ValueError("함의 평가 응답의 manifest가 다르다")
    if response.get("outputSha256") != sha256Text(response.get("output", "")):
        raise ValueError("함의 평가 모델 원응답 해시가 다르다")
    parsed = json.loads(response["output"])
    model = response["runner"]["model"]
    predictions = {
        "version": 1,
        "kind": "hanlint.entailmentPredictions",
        "benchmarkId": manifest["benchmarkId"],
        "benchmarkSha256": manifest["benchmarkSha256"],
        "evaluator": {
            "id": model["name"],
            "kind": "llm",
            "revision": model["digest"],
            "promptSha256": manifest["promptSha256"],
        },
        "predictions": parsed["predictions"],
    }
    result = evaluateEntailment(predictions).asDict()
    payload = {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "responseSha256": response["contentSha256"],
        "model": model,
        "result": result,
        "limits": [
            "공개 KLUE 사례가 모델 학습에 포함됐는지 알 수 없다",
            "36개 고정 사례 결과는 다른 자료나 사실의 진실과 글 품질을 보장하지 않는다",
            "confidence는 모델 자기보고이며 보정 확률로 검증하지 않았다",
        ],
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def selfTest() -> None:
    manifest = buildManifest()
    assert manifest["benchmarkId"] == "klue-nli-v1.1-dev-balanced-36"
    assert "goldLabel" not in manifest["prompt"] and "validatorLabels" not in manifest["prompt"]
    cases = entailmentCases()
    abstentions = {
        "version": 1,
        "kind": "hanlint.entailmentPredictions",
        "benchmarkId": cases["benchmarkId"],
        "benchmarkSha256": cases["benchmarkSha256"],
        "evaluator": {"id": "self-test", "kind": "rule", "revision": "v1", "promptSha256": "0" * 64},
        "predictions": [{"caseId": case["caseId"], "label": "abstain", "confidence": 0} for case in cases["cases"]],
    }
    metrics = evaluateEntailment(abstentions).metrics
    assert metrics["coverage"] == 0 and metrics["macroF1"] == 0


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="사람 합의 한국어 근거 함의 평가기 탐침")
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
        print("evidenceEntailment self-test 완료")
        return 0
    args = parseArgs(argv)
    if args.command == "prepare":
        writeJson(args.output, buildManifest())
        print(f"entailment manifest SHA256: {sha256File(args.output)}")
    elif args.command == "run":
        response = runManifest(readJson(args.manifest), args.model, args.endpoint, args.timeout, args.output)
        print(f"entailment response SHA256: {response['contentSha256']}")
    else:
        result = evaluateRun(readJson(args.manifest), readJson(args.response))
        writeJson(args.output, result)
        print(json.dumps(result["result"]["metrics"], ensure_ascii=False, indent=2))
        print(f"entailment evaluation SHA256: {sha256File(args.output)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
