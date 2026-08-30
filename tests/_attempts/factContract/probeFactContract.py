"""구조화 brief 패킷의 결과를 제품 guard가 어떻게 드러내는지 잰다."""

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

from hanlint import WritingBrief, guardText, writingPacket  # noqa: E402
from hanlint.config import numberValues  # noqa: E402


def briefOf(task: dict) -> WritingBrief:
    contractText = "\n".join((task["reader"], task["task"], *task["facts"]))
    mustInclude = [literal for literal in task["mustInclude"] if literal in contractText]
    return WritingBrief.fromMapping(
        {
            "version": 1,
            "preset": task["preset"],
            "reader": task["reader"],
            "task": task["task"],
            "facts": [{"id": f"F{index}", "statement": fact} for index, fact in enumerate(task["facts"], start=1)],
            "mustInclude": mustInclude,
            "allowedNumbers": list(numberValues(contractText)),
            "forbidden": task["forbidden"],
            "length": {"min": task["length"][0], "max": task["length"][1]},
        }
    )


def promptFor(brief: WritingBrief) -> str:
    packet = writingPacket(brief, purpose="draft")
    return (
        "다음 hanlint writingPacket을 실행하라. JSON을 설명하지 말고 input.brief만 사실 재료로 사용한다. "
        "풀이, 점검표와 작성 과정 없이 완성된 한국어 마크다운만 출력하라.\n\n" + json.dumps(packet, ensure_ascii=False, indent=2)
    )


def buildManifest() -> dict:
    tasks = []
    for task in BRIEFS:
        brief = briefOf(task)
        prompt = promptFor(brief)
        tasks.append({"id": task["id"], "brief": brief.asDict(), "prompt": prompt, "promptSha256": sha256Text(prompt)})
    payload = {"version": 1, "generationOptions": GENERATION_OPTIONS, "tasks": tasks}
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def runManifest(manifest: dict, model: str, endpoint: str, timeout: int, output: Path) -> dict:
    modelInfo = ollamaInfo(endpoint, model, timeout)
    if output.exists():
        checkpoint = readJson(output)
        if checkpoint.get("manifestSha256") != manifest["contentSha256"]:
            raise ValueError("기존 factContract 응답의 manifest가 다르다")
    else:
        checkpoint = {
            "version": 1,
            "complete": False,
            "manifestSha256": manifest["contentSha256"],
            "runner": {"model": modelInfo, "think": False, "options": GENERATION_OPTIONS},
            "responses": [],
        }
    seen = {item["taskId"] for item in checkpoint["responses"]}
    for task in manifest["tasks"]:
        if task["id"] in seen:
            continue
        generated, metrics = ollamaGenerate(task["prompt"], model, endpoint, timeout, GENERATION_OPTIONS)
        checkpoint["responses"].append(
            {
                "taskId": task["id"],
                "output": generated,
                "outputSha256": sha256Text(generated),
                "metrics": metrics,
            }
        )
        seen.add(task["id"])
        writeJson(output, checkpoint)
        print(f"구조화 brief 응답 {len(seen)}/{len(manifest['tasks'])}: {task['id']}", flush=True)
    checkpoint["complete"] = True
    checkpoint["rawResponseSha256"] = sha256Text(stableJson(checkpoint["responses"]))
    writeJson(output, checkpoint)
    return checkpoint


def score(manifest: dict, responses: dict) -> dict:
    tasks = {task["id"]: task for task in manifest["tasks"]}
    results = []
    for response in responses["responses"]:
        task = tasks[response["taskId"]]
        guarded = guardText(task["brief"], response["output"], path=f"{response['taskId']}.md")
        result = guarded.asDict()
        result["taskId"] = response["taskId"]
        results.append(result)
    summary = {
        "tasks": len(results),
        "contractSatisfied": sum(item["contractSatisfied"] for item in results),
        "surfaceSatisfied": sum(not any(item["surface"].values()) for item in results),
        "lengthSatisfied": sum(item["length"]["satisfied"] for item in results),
        "errorFree": sum(item["lint"]["errorCount"] == 0 for item in results),
        "violations": sum(item["violationCount"] for item in results),
    }
    payload = {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "responsesSha256": responses["rawResponseSha256"],
        "summary": summary,
        "results": results,
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def selfTest() -> None:
    manifest = buildManifest()
    assert len(manifest["tasks"]) == 7
    for task in manifest["tasks"]:
        brief = WritingBrief.fromMapping(task["brief"])
        assert task["promptSha256"] == sha256Text(task["prompt"])
        assert brief.mustInclude and brief.allowedNumbers
        assert "comparison" not in writingPacket(brief, purpose="draft")


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="구조화 brief와 제품 guard의 완성 글 탐침")
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
        print("factContract self-test 통과")
        return 0
    args = parseArgs(argv)
    if args.command == "prepare":
        writeJson(args.output, buildManifest())
        print(f"factContract manifest SHA256: {sha256File(args.output)}")
    elif args.command == "run":
        runManifest(readJson(args.manifest), args.model, args.endpoint, args.timeout, args.output)
        print(f"factContract responses SHA256: {sha256File(args.output)}")
    else:
        result = score(readJson(args.manifest), readJson(args.responses))
        writeJson(args.output, result)
        print(result["summary"])
        print(f"factContract score SHA256: {sha256File(args.output)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
