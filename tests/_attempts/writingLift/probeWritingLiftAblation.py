"""실패한 writingPacket의 입력 길이, 예시 오염, JSON 해석 원인을 분해한다.

첫 writingLift 탐침의 같은 brief와 plainBrief 원시 출력을 재사용한다. full packet에서 하나씩 덜어 낸 네
조건만 새로 생성하므로 baseline을 다시 뽑아 생기는 분산이 없다.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from probeWritingLift import (  # noqa: E402
    GENERATION_OPTIONS,
    JUDGE_OPTIONS,
    JUDGE_SCHEMA,
    JUDGE_SEEDS,
    OLLAMA_ENDPOINT,
    automaticResult,
    consensusPreference,
    judgePrompt,
    ollamaGenerate,
    ollamaInfo,
    packetPrompt,
    pairOutcome,
    readJson,
    responseKey,
    sha256File,
    sha256Text,
    stableJson,
    writeJson,
)

from hanlint import Config, writingPacket  # noqa: E402

BASELINE = "plainBrief"
ABLATION_CONDITIONS = ("sourceTail", "dropPatterns", "minimalJson", "compiledBrief")
CONDITIONS = (BASELINE,) + ABLATION_CONDITIONS


def sourceTailPrompt(task: dict, packet: dict) -> str:
    return (
        packetPrompt(task, packet)
        + "\n\n위 JSON 자체를 요약하거나 설명하지 말라. patterns의 예시와 comparison의 숫자는 결과 글의 "
        "재료가 아니다. 다음 source만 글의 사실 재료다. 지금 source의 요구를 충족한 완성 글만 출력하라.\n\n"
        "<source>\n" + task["briefMarkdown"] + "</source>"
    )


def dropPatternsPrompt(task: dict, packet: dict) -> str:
    reduced = copy.deepcopy(packet)
    reduced.pop("patterns", None)
    return (
        "다음 hanlint writingPacket의 input.text만 글의 사실 재료로 삼아 완결된 한국어 글을 써라. "
        "comparison은 진단 수치일 뿐 결과에 쓰지 않는다. JSON을 설명하거나 필드 이름을 출력하지 않는다. "
        "풀이, 자기평가, 작성 과정, 바깥 코드 펜스 없이 완성된 마크다운만 출력하라.\n\n"
        + json.dumps(reduced, ensure_ascii=False, indent=2)
    )


def minimalJsonPrompt(task: dict) -> str:
    packet = {
        "kind": "hanlint.executionPacket",
        "purpose": "draft",
        "operation": "source의 사실만 사용해 독자의 과업을 끝내는 한국어 마크다운을 쓴다",
        "preset": task["preset"],
        "constraints": [
            "source에 없는 사실, 인과, 수치, 이름, 기능을 만들지 않는다",
            "source의 반드시 담을 사실을 하나도 빠뜨리지 않는다",
            "관찰과 해석, 사실과 권고를 구분한다",
            "메타 설명, JSON 설명, 작성 과정, 자기평가를 출력하지 않는다",
            "상투적인 도입과 맺음, 같은 접속어와 종결의 기계적 반복을 피한다",
            "출력은 완성된 한국어 마크다운 하나다",
        ],
        "source": task["briefMarkdown"],
    }
    return "아래 실행 packet을 수행하라. packet을 설명하지 말고 source가 요구한 결과만 출력하라.\n\n" + json.dumps(
        packet, ensure_ascii=False, indent=2
    )


def compiledBriefPrompt(task: dict) -> str:
    return (
        "완성된 한국어 글 하나를 쓴다. 아래 원칙은 작성 절차이고 결과에 언급하지 않는다.\n"
        "1. 요구에 적힌 모든 사실, 숫자, 이름, 명령, 링크를 먼저 확인한다.\n"
        "2. 요구 밖의 원인, 배경, 인물, 기능, 수치를 만들지 않는다.\n"
        "3. 독자가 하려는 일을 도입에서 세우고, 본문 한 부분에 한 가지 일을 진행한다.\n"
        "4. 사실과 해석을 구분하고 번역투, 상투구, 같은 접속어와 종결의 반복을 피한다.\n"
        "5. 요구한 글자 수 안에서 마지막 사실과 독자의 다음 행동까지 쓴다.\n"
        "6. 쓰고 난 뒤 요구의 사실을 하나씩 대조하되 점검 과정은 출력하지 않는다.\n"
        "결과에는 풀이, 자기평가, JSON 설명, 작성 과정, 바깥 코드 펜스를 넣지 않는다.\n\n"
        "<작성 요구>\n" + task["briefMarkdown"] + "</작성 요구>\n\n이제 완성된 마크다운 본문만 출력하라."
    )


def buildAblationManifest(baseManifest: dict) -> dict:
    tasks = []
    for original in baseManifest["tasks"]:
        task = {key: value for key, value in original.items() if key != "prompts"}
        packet = writingPacket(
            task["briefMarkdown"],
            Config(preset=task["preset"]),
            path=f"{task['id']}.md",
            purpose="draft",
        )
        task["prompts"] = {
            "sourceTail": sourceTailPrompt(task, packet),
            "dropPatterns": dropPatternsPrompt(task, packet),
            "minimalJson": minimalJsonPrompt(task),
            "compiledBrief": compiledBriefPrompt(task),
        }
        tasks.append(task)
    payload = {
        "version": 1,
        "baseline": BASELINE,
        "conditions": list(CONDITIONS),
        "generationOptions": GENERATION_OPTIONS,
        "baseManifestSha256": baseManifest["contentSha256"],
        "tasks": tasks,
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def checkpointBase(manifest: dict, baseResponses: dict, modelInfo: dict) -> dict:
    baselineResponses = [item for item in baseResponses["responses"] if item["condition"] == manifest["baseline"]]
    return {
        "version": 1,
        "complete": False,
        "manifestSha256": manifest["contentSha256"],
        "baseResponsesSha256": baseResponses["rawResponseSha256"],
        "runner": {
            "kind": "ollama",
            "model": modelInfo,
            "think": False,
            "options": GENERATION_OPTIONS,
        },
        "responses": baselineResponses,
    }


def runGeneration(
    manifest: dict,
    baseResponses: dict,
    model: str,
    endpoint: str,
    timeout: int,
    output: Path,
) -> dict:
    modelInfo = ollamaInfo(endpoint, model, timeout)
    if output.exists():
        checkpoint = readJson(output)
        if checkpoint.get("manifestSha256") != manifest["contentSha256"]:
            raise ValueError("기존 ablation 응답의 manifest가 다르다")
    else:
        checkpoint = checkpointBase(manifest, baseResponses, modelInfo)
    if checkpoint["runner"]["model"].get("digest") != modelInfo.get("digest"):
        raise ValueError("기존 ablation 응답의 모델 digest가 다르다")
    seen = {responseKey(item) for item in checkpoint["responses"]}
    candidateConditions = tuple(condition for condition in manifest["conditions"] if condition != manifest["baseline"])
    schedule = []
    for index, task in enumerate(manifest["tasks"]):
        rotated = (
            candidateConditions[index % len(candidateConditions) :] + candidateConditions[: index % len(candidateConditions)]
        )
        schedule.extend((task, condition) for condition in rotated)
    total = len(manifest["tasks"]) * len(manifest["conditions"])
    for task, condition in schedule:
        key = (task["id"], condition)
        if key in seen:
            continue
        prompt = task["prompts"][condition]
        generated, metrics = ollamaGenerate(prompt, model, endpoint, timeout, GENERATION_OPTIONS)
        checkpoint["responses"].append(
            {
                "taskId": task["id"],
                "condition": condition,
                "promptSha256": sha256Text(prompt),
                "output": generated,
                "outputSha256": sha256Text(generated),
                "metrics": metrics,
            }
        )
        seen.add(key)
        writeJson(output, checkpoint)
        print(f"ablation 생성 {len(seen)}/{total}: {task['id']} {condition}", flush=True)
    expected = {(task["id"], condition) for task in manifest["tasks"] for condition in manifest["conditions"]}
    if seen != expected:
        raise ValueError("ablation 응답 키가 완전하지 않다")
    checkpoint["complete"] = True
    checkpoint["rawResponseSha256"] = sha256Text(stableJson(checkpoint["responses"]))
    writeJson(output, checkpoint)
    return checkpoint


def scoreAutomatic(manifest: dict, responses: dict) -> dict:
    tasks = {task["id"]: task for task in manifest["tasks"]}
    results = [automaticResult(tasks[item["taskId"]], item) for item in responses["responses"]]
    payload = {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "responsesSha256": responses["rawResponseSha256"],
        "results": results,
    }
    payload["contentSha256"] = sha256Text(stableJson(results))
    return payload


def judgmentKey(item: dict) -> tuple[str, str, int, bool]:
    return item["taskId"], item["candidate"], item["seed"], item["swapped"]


def runJudgments(
    manifest: dict,
    responses: dict,
    model: str,
    endpoint: str,
    timeout: int,
    output: Path,
) -> dict:
    modelInfo = ollamaInfo(endpoint, model, timeout)
    if output.exists():
        checkpoint = readJson(output)
        if checkpoint.get("responsesSha256") != responses["rawResponseSha256"]:
            raise ValueError("기존 ablation 판정의 응답 hash가 다르다")
    else:
        checkpoint = {
            "version": 1,
            "complete": False,
            "manifestSha256": manifest["contentSha256"],
            "responsesSha256": responses["rawResponseSha256"],
            "judge": {
                "kind": "ollama",
                "model": modelInfo,
                "think": False,
                "seeds": list(JUDGE_SEEDS),
                "options": JUDGE_OPTIONS,
                "orderSwap": True,
                "blindConditionLabels": True,
                "sameModelAsGenerator": modelInfo.get("digest") == responses["runner"]["model"].get("digest"),
            },
            "judgments": [],
        }
    seen = {judgmentKey(item) for item in checkpoint["judgments"]}
    tasks = {task["id"]: task for task in manifest["tasks"]}
    responseMap = {responseKey(item): item["output"] for item in responses["responses"]}
    baseline = manifest["baseline"]
    candidateConditions = tuple(condition for condition in manifest["conditions"] if condition != baseline)
    schedule = [
        (taskId, candidate, seed, swapped)
        for taskId in tasks
        for candidate in candidateConditions
        for seed in JUDGE_SEEDS
        for swapped in (False, True)
    ]
    for taskId, candidate, seed, swapped in schedule:
        key = (taskId, candidate, seed, swapped)
        if key in seen:
            continue
        baselineOutput = responseMap[(taskId, baseline)]
        candidateOutput = responseMap[(taskId, candidate)]
        outputA, outputB = (candidateOutput, baselineOutput) if swapped else (baselineOutput, candidateOutput)
        prompt = judgePrompt(tasks[taskId], outputA, outputB)
        raw, metrics = ollamaGenerate(
            prompt,
            model,
            endpoint,
            timeout,
            {**JUDGE_OPTIONS, "seed": seed},
            JUDGE_SCHEMA,
        )
        decision = json.loads(raw)
        checkpoint["judgments"].append(
            {
                "taskId": taskId,
                "candidate": candidate,
                "seed": seed,
                "swapped": swapped,
                "aIs": candidate if swapped else baseline,
                "bIs": baseline if swapped else candidate,
                "promptSha256": sha256Text(prompt),
                "decision": decision,
                "rawSha256": sha256Text(raw),
                "metrics": metrics,
            }
        )
        seen.add(key)
        writeJson(output, checkpoint)
        print(f"ablation 판정 {len(seen)}/{len(schedule)}: {taskId} {candidate} {seed} {swapped}", flush=True)
    if seen != set(schedule):
        raise ValueError("ablation 판정 키가 완전하지 않다")
    checkpoint["complete"] = True
    checkpoint["judgmentSha256"] = sha256Text(stableJson(checkpoint["judgments"]))
    writeJson(output, checkpoint)
    return checkpoint


def scoreAll(manifest: dict, responses: dict, automatic: dict, judgments: dict) -> dict:
    autoMap = {(item["taskId"], item["condition"]): item for item in automatic["results"]}
    baseline = manifest["baseline"]
    grouped: dict[tuple[str, str], list[dict]] = {}
    for item in judgments["judgments"]:
        grouped.setdefault((item["taskId"], item["candidate"]), []).append(item)
    dimensions = ("factFidelity", "taskUtility", "naturalKorean", "organization", "concision", "overall")
    pairs = []
    for (taskId, candidate), items in sorted(grouped.items()):
        pair = {
            "taskId": taskId,
            "candidate": candidate,
            "consensus": {dimension: consensusPreference(items, dimension, candidate) for dimension in dimensions},
        }
        pair["safeOutcome"] = pairOutcome(pair, autoMap[(taskId, baseline)], autoMap[(taskId, candidate)])
        pairs.append(pair)
    summary = {}
    for condition in manifest["conditions"]:
        selected = [item for item in automatic["results"] if item["condition"] == condition]
        paired = [item for item in pairs if item["candidate"] == condition]
        summary[condition] = {
            "factSurfacePass": sum(item["factSurfacePass"] for item in selected),
            "lengthPass": sum(item["lengthPass"] for item in selected),
            "errorFree": sum(item["errorCount"] == 0 for item in selected),
            "errors": sum(item["errorCount"] for item in selected),
            "meanCharacters": round(sum(item["characterCount"] for item in selected) / len(selected), 1),
            "safeWins": sum(item["safeOutcome"] == "candidate" for item in paired),
            "safeLosses": sum(item["safeOutcome"] == "baseline" for item in paired),
            "unsafePreferences": sum(item["safeOutcome"].startswith("unsafe") for item in paired),
            "unstableOrTies": sum(item["safeOutcome"] == "unstableOrTie" for item in paired),
            "naturalConsensusWins": sum(item["consensus"]["naturalKorean"] == "candidate" for item in paired),
            "taskConsensusWins": sum(item["consensus"]["taskUtility"] == "candidate" for item in paired),
        }
    payload = {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "responsesSha256": responses["rawResponseSha256"],
        "automaticSha256": automatic["contentSha256"],
        "judgmentSha256": judgments["judgmentSha256"],
        "baseline": baseline,
        "conditions": manifest["conditions"],
        "conditionSummary": summary,
        "pairs": pairs,
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def renderScore(score: dict) -> str:
    lines = []
    for condition in score["conditions"]:
        item = score["conditionSummary"][condition]
        lines.append(
            f"{condition}: facts {item['factSurfacePass']}/7, length {item['lengthPass']}/7, "
            f"error0 {item['errorFree']}/7, errors {item['errors']}, chars {item['meanCharacters']}, "
            f"safe W/L {item['safeWins']}/{item['safeLosses']}, unstable {item['unstableOrTies']}, "
            f"unsafe {item['unsafePreferences']}, natural wins {item['naturalConsensusWins']}, "
            f"task wins {item['taskConsensusWins']}"
        )
    lines.append(f"score SHA256: {score['contentSha256']}")
    return "\n".join(lines)


def selfTest() -> None:
    base = {"contentSha256": "base", "tasks": [{"id": "a", "briefMarkdown": "# 요구", "preset": "blog"}]}
    manifest = buildAblationManifest(base)
    assert manifest["conditions"] == list(CONDITIONS)
    prompts = manifest["tasks"][0]["prompts"]
    assert set(prompts) == set(ABLATION_CONDITIONS)
    assert prompts["compiledBrief"].endswith("이제 완성된 마크다운 본문만 출력하라.")


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="writingPacket 실패 원인 ablation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("baseManifest", type=Path)
    prepare.add_argument("--output", type=Path, required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("manifest", type=Path)
    generate.add_argument("baseResponses", type=Path)
    generate.add_argument("--model", required=True)
    generate.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    generate.add_argument("--timeout", type=int, default=300)
    generate.add_argument("--output", type=Path, required=True)
    auto = subparsers.add_parser("score-auto")
    auto.add_argument("manifest", type=Path)
    auto.add_argument("responses", type=Path)
    auto.add_argument("--output", type=Path, required=True)
    judge = subparsers.add_parser("judge")
    judge.add_argument("manifest", type=Path)
    judge.add_argument("responses", type=Path)
    judge.add_argument("--model", required=True)
    judge.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    judge.add_argument("--timeout", type=int, default=300)
    judge.add_argument("--output", type=Path, required=True)
    score = subparsers.add_parser("score")
    score.add_argument("manifest", type=Path)
    score.add_argument("responses", type=Path)
    score.add_argument("automatic", type=Path)
    score.add_argument("judgments", type=Path)
    score.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        selfTest()
        print("writingLift ablation self-test 통과")
        return 0
    args = parseArgs(argv)
    if args.command == "prepare":
        manifest = buildAblationManifest(readJson(args.baseManifest))
        writeJson(args.output, manifest)
        print(f"ablation manifest SHA256: {sha256File(args.output)}")
    elif args.command == "generate":
        runGeneration(
            readJson(args.manifest),
            readJson(args.baseResponses),
            args.model,
            args.endpoint,
            args.timeout,
            args.output,
        )
        print(f"ablation responses SHA256: {sha256File(args.output)}")
    elif args.command == "score-auto":
        automatic = scoreAutomatic(readJson(args.manifest), readJson(args.responses))
        writeJson(args.output, automatic)
        print(f"ablation automatic SHA256: {sha256File(args.output)}")
    elif args.command == "judge":
        runJudgments(
            readJson(args.manifest),
            readJson(args.responses),
            args.model,
            args.endpoint,
            args.timeout,
            args.output,
        )
        print(f"ablation judgments SHA256: {sha256File(args.output)}")
    else:
        score = scoreAll(
            readJson(args.manifest),
            readJson(args.responses),
            readJson(args.automatic),
            readJson(args.judgments),
        )
        writeJson(args.output, score)
        print(renderScore(score))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
