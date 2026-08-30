"""exemplarLift. 같은 수정 과제에서 본보기 유무만 바꿔 결과를 잰다.

외부 모델을 제품이나 기본 게이트에 묶지 않는다. `prepare` 가 실제 지적에서 짝 프롬프트를 만들고, `run` 이
사용자가 명시한 실행기나 결정적 Ollama 호출을 쓰며, `score` 가 결과를 다시 hanlint 에 넣는다. 뜻 보존은
검토자가 응답 JSON의 `meaningPreserved` 에 표시한 것만 따로 센다.

```powershell
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/exemplarLift/probeExemplarLift.py prepare <글들> --output manifest.json
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/exemplarLift/probeExemplarLift.py run manifest.json `
  --ollama-model <model> --output responses.json
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/exemplarLift/probeExemplarLift.py score manifest.json responses.json `
  --judgments judgments.json
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from hanlint import Config, fingerprint, lintText, loadConfig  # noqa: E402
from hanlint.data import exemplarFor  # noqa: E402

CONDITIONS = ("reasonOnly", "withExemplar")
OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
OLLAMA_OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 512}


def promptFor(
    sentence: str,
    rule: str,
    why: str,
    context: dict[str, list[str]],
    exemplar: dict | None = None,
) -> str:
    lines = [
        "한국어 문장 하나를 고친다.",
        "원문의 뜻과 사실과 고유명사를 보존한다.",
        "원문과 문맥에 없는 정보는 만들지 않는다.",
        "확실하게 고칠 수 없으면 원문을 그대로 출력한다.",
        "설명과 따옴표 없이 고친 문장만 출력한다.",
        f"규칙: {rule}",
        f"이유: {why}",
    ]
    if context["before"] or context["after"]:
        lines.append("앞뒤 문맥은 사실을 확인할 때만 쓰고 고치거나 출력하지 않는다.")
        lines.extend(f"앞 문장: {item}" for item in context["before"])
        lines.extend(f"뒤 문장: {item}" for item in context["after"])
    if exemplar:
        lines.extend(
            [
                "같은 결함의 검증된 본보기:",
                "본보기는 수정 방법만 보여 준다. 본보기의 이름과 숫자와 사실은 옮기지 않는다.",
                f"전: {exemplar['before']}",
                f"후: {exemplar['after']}",
                f"달라진 것: {exemplar['moved']}",
            ]
        )
    lines.append(f"고칠 문장: {sentence}")
    return "\n".join(lines)


def contextFor(document, index: int) -> dict[str, list[str]]:
    """대상 앞 세 문장과 뒤 한 문장. 두 조건에 똑같이 주어 추측을 줄인다."""
    return {
        "before": [item.text.strip() for item in document.sentences[max(0, index - 3) : index]],
        "after": [item.text.strip() for item in document.sentences[index + 1 : index + 2]],
    }


def taskId(rule: str, sentence: str) -> str:
    digest = hashlib.sha256(f"{rule}\0{sentence}".encode()).hexdigest()[:12]
    return f"{rule}-{digest}"


def collectTasks(folder: Path, config: Config, perRule: int, limit: int) -> list[dict]:
    tasks: list[dict] = []
    counts: Counter = Counter()
    seen: set[str] = set()
    for path in sorted(folder.rglob("*.md"), key=str):
        text = path.read_text(encoding="utf-8")
        document = fingerprint(text, config, path=str(path))
        for finding in lintText(text, config, path=str(path)):
            if finding.scope != "sentence" or finding.at < 0 or counts[finding.rule] >= perRule:
                continue
            exemplar = exemplarFor(finding.rule, config.preset, config.exemplars)
            if not exemplar:
                continue
            sentence = document.sentences[finding.at].text.strip()
            context = contextFor(document, finding.at)
            identifier = taskId(finding.rule, sentence)
            if identifier in seen or sentence == exemplar.before:
                continue
            exemplarData = exemplar.asDict()
            tasks.append(
                {
                    "id": identifier,
                    "source": str(path.relative_to(folder)),
                    "rule": finding.rule,
                    "why": finding.why,
                    "sentence": sentence,
                    "context": context,
                    "preset": config.preset,
                    "exemplar": exemplarData,
                    "prompts": {
                        "reasonOnly": promptFor(sentence, finding.rule, finding.why, context),
                        "withExemplar": promptFor(sentence, finding.rule, finding.why, context, exemplarData),
                    },
                }
            )
            counts[finding.rule] += 1
            seen.add(identifier)
            if len(tasks) >= limit:
                return tasks
    return tasks


def readJson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def writeJson(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def ollamaJson(endpoint: str, route: str, timeout: int, data: dict | None = None) -> dict:
    """로컬 Ollama JSON API 한 번. 외부 의존성 없이 UTF-8 계약을 고정한다."""
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    request = urllib.request.Request(
        endpoint.rstrip("/") + route,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ollamaInfo(endpoint: str, model: str, timeout: int) -> dict:
    """재현할 수 있게 실행한 모델의 digest와 크기를 남긴다."""
    tags = ollamaJson(endpoint, "/api/tags", timeout)
    found = next((item for item in tags.get("models", []) if item.get("name") == model), None)
    if found is None:
        raise RuntimeError(f"Ollama 에 {model} 모델이 없다")
    return {key: found[key] for key in ("name", "digest", "size", "modified_at") if key in found}


def ollamaGenerate(prompt: str, model: str, endpoint: str, timeout: int) -> tuple[str, dict]:
    """추론문을 숨기고 탐침 두 조건에 같은 결정적 생성 설정을 쓴다."""
    result = ollamaJson(
        endpoint,
        "/api/generate",
        timeout,
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": OLLAMA_OPTIONS,
        },
    )
    output = result.get("response", "").strip()
    metrics = {
        key: result[key]
        for key in ("done_reason", "total_duration", "load_duration", "prompt_eval_count", "eval_count")
        if key in result
    }
    return output, metrics


def runManifest(manifest: dict, runner: list[str], timeout: int) -> dict:
    responses: list[dict] = []
    for task in manifest["tasks"]:
        for condition in CONDITIONS:
            completed = subprocess.run(
                runner,
                input=task["prompts"][condition],
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            if completed.returncode:
                raise RuntimeError(
                    f"실행기가 {task['id']} {condition} 에서 {completed.returncode} 로 끝났다: {completed.stderr.strip()}"
                )
            responses.append({"taskId": task["id"], "condition": condition, "output": completed.stdout.strip()})
    return {"version": 1, "runner": runner, "responses": responses}


def runOllamaManifest(
    manifest: dict,
    model: str,
    endpoint: str,
    timeout: int,
    checkpoint: Path | None = None,
) -> dict:
    """고정한 Ollama 모델과 생성 설정으로 순서대로 실행하고 응답마다 회수 지점을 쓴다."""
    responses: list[dict] = []
    runner = {
        "kind": "ollama",
        "endpoint": endpoint,
        "model": ollamaInfo(endpoint, model, timeout),
        "think": False,
        "options": OLLAMA_OPTIONS,
    }
    total = len(manifest["tasks"]) * len(CONDITIONS)
    for task in manifest["tasks"]:
        for condition in CONDITIONS:
            output, metrics = ollamaGenerate(task["prompts"][condition], model, endpoint, timeout)
            responses.append({"taskId": task["id"], "condition": condition, "output": output, "metrics": metrics})
            partial = {"version": 1, "complete": False, "runner": runner, "responses": responses}
            if checkpoint:
                writeJson(checkpoint, partial)
            print(f"응답 {len(responses)}/{total}: {task['id']} {condition}", flush=True)
    return {"version": 1, "complete": True, "runner": runner, "responses": responses}


def applyJudgments(responses: dict, judgments: dict) -> dict:
    """모델 원시 응답은 그대로 두고 검토자가 읽은 뜻 보존 판정을 별도 파일에서 합친다."""
    expected = {(item["taskId"], item["condition"]) for item in responses["responses"]}
    labels: dict[tuple[str, str], dict] = {}
    for judgment in judgments.get("judgments", []):
        key = (judgment["taskId"], judgment["condition"])
        if key in labels:
            raise ValueError(f"뜻 보존 판정이 겹친다: {key[0]} {key[1]}")
        labels[key] = judgment
    missing = expected - labels.keys()
    unknown = labels.keys() - expected
    if missing or unknown:
        raise ValueError(f"뜻 보존 판정 키가 맞지 않는다: 빠짐 {len(missing)}, 모름 {len(unknown)}")
    merged = []
    for response in responses["responses"]:
        key = (response["taskId"], response["condition"])
        judgment = labels[key]
        item = dict(response)
        item["meaningPreserved"] = bool(judgment["meaningPreserved"])
        if judgment.get("note"):
            item["meaningNote"] = judgment["note"]
        merged.append(item)
    return {**responses, "judgments": {key: value for key, value in judgments.items() if key != "judgments"}, "responses": merged}


def resultOf(task: dict, response: dict, config: Config) -> dict:
    beforeFindings = lintText(task["sentence"], config)
    afterFindings = lintText(response["output"], config)
    beforeErrors = Counter(finding.rule for finding in beforeFindings if finding.severity == "error")
    afterErrors = Counter(finding.rule for finding in afterFindings if finding.severity == "error")
    result = {
        "resolved": all(finding.rule != task["rule"] for finding in afterFindings),
        "newErrors": sum(max(0, count - beforeErrors[rule]) for rule, count in afterErrors.items()),
    }
    if "meaningPreserved" in response:
        result["meaningPreserved"] = bool(response["meaningPreserved"])
        result["threeChecks"] = result["resolved"] and result["newErrors"] == 0 and result["meaningPreserved"]
    return result


def scoreResponses(manifest: dict, responses: dict, config: Config) -> str:
    tasks = {task["id"]: task for task in manifest["tasks"]}
    results: dict[tuple[str, str], dict] = {}
    for response in responses["responses"]:
        task = tasks[response["taskId"]]
        condition = response["condition"]
        results[(task["id"], condition)] = resultOf(task, response, config)
    lines = [f"과제 {len(tasks)}개", "", "조건별"]
    for condition in CONDITIONS:
        selected = [result for (task, kind), result in results.items() if kind == condition]
        resolved = sum(result["resolved"] for result in selected)
        newErrors = sum(result["newErrors"] for result in selected)
        judged = [result for result in selected if "meaningPreserved" in result]
        meaning = sum(result["meaningPreserved"] for result in judged)
        checks = sum(result["threeChecks"] for result in judged)
        meaningText = f", 뜻 보존 {meaning}/{len(judged)}, 세 조건 충족 {checks}/{len(judged)}" if judged else ", 뜻 보존 미판정"
        lines.append(f"  {condition:12} 규칙 해결 {resolved}/{len(selected)}, 새 error {newErrors}건{meaningText}")
    paired = [
        (results[(taskId, "reasonOnly")], results[(taskId, "withExemplar")])
        for taskId in tasks
        if (taskId, "reasonOnly") in results and (taskId, "withExemplar") in results
    ]
    exemplarWins = sum(not base["resolved"] and shown["resolved"] for base, shown in paired)
    reasonWins = sum(base["resolved"] and not shown["resolved"] for base, shown in paired)
    ties = len(paired) - exemplarWins - reasonWins
    judgedPairs = [(base, shown) for base, shown in paired if "threeChecks" in base and "threeChecks" in shown]
    exemplarCheckWins = sum(not base["threeChecks"] and shown["threeChecks"] for base, shown in judgedPairs)
    reasonCheckWins = sum(base["threeChecks"] and not shown["threeChecks"] for base, shown in judgedPairs)
    checkTies = len(judgedPairs) - exemplarCheckWins - reasonCheckWins
    lines.extend(["", "짝 비교", f"  본보기만 해결 {exemplarWins}개, 이유만 해결 {reasonWins}개, 같은 결과 {ties}개"])
    if judgedPairs:
        lines.append(
            f"  본보기만 세 조건 충족 {exemplarCheckWins}개, 이유만 세 조건 충족 {reasonCheckWins}개, 같은 결과 {checkTies}개"
        )
    else:
        lines.append("  세 조건 미판정")
    lines.append("  세 조건은 목표 규칙 해결, 새 error 0, 검토자가 표시한 뜻 보존이다")
    return "\n".join(lines)


def selfTest() -> None:
    task = {
        "id": "translationese-test",
        "rule": "translationese",
        "sentence": "설계에 대한 이해가 필요합니다.",
    }
    manifest = {"tasks": [task]}
    responses = {
        "responses": [
            {"taskId": task["id"], "condition": "reasonOnly", "output": task["sentence"], "meaningPreserved": True},
            {
                "taskId": task["id"],
                "condition": "withExemplar",
                "output": "설계를 알아야 합니다.",
                "meaningPreserved": True,
            },
        ]
    }
    report = scoreResponses(manifest, responses, Config())
    assert "본보기만 해결 1개" in report
    assert "본보기만 세 조건 충족 1개" in report
    noticeTask = {
        "rule": "endingRepeat",
        "sentence": "파일을 엽니다. 값을 넣습니다. 표를 만듭니다. 화면을 봅니다.",
    }
    assert not resultOf(noticeTask, {"output": noticeTask["sentence"]}, Config())["resolved"]
    context = {"before": ["파일을 만들었습니다."], "after": ["화면에서 확인합니다."]}
    basePrompt = promptFor("이것을 엽니다.", "deixis", "가리키는 이름을 쓴다", context)
    shownPrompt = promptFor(
        "이것을 엽니다.",
        "deixis",
        "가리키는 이름을 쓴다",
        context,
        {"before": "이것을 엽니다.", "after": "파일을 엽니다.", "moved": "대상을 밝혔다"},
    )
    assert "앞 문장: 파일을 만들었습니다." in basePrompt
    assert "뒤 문장: 화면에서 확인합니다." in basePrompt
    assert basePrompt in shownPrompt.replace(
        "같은 결함의 검증된 본보기:\n"
        "본보기는 수정 방법만 보여 준다. 본보기의 이름과 숫자와 사실은 옮기지 않는다.\n"
        "전: 이것을 엽니다.\n후: 파일을 엽니다.\n달라진 것: 대상을 밝혔다\n",
        "",
    )


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="본보기 유무만 바꾼 수정 결과를 다시 hanlint 로 잰다")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("folder", type=Path)
    prepare.add_argument("--config", type=Path)
    prepare.add_argument("--per-rule", dest="perRule", type=int, default=2)
    prepare.add_argument("--limit", type=int, default=30)
    prepare.add_argument("--output", type=Path, required=True)
    run = subparsers.add_parser("run")
    run.add_argument("manifest", type=Path)
    runner = run.add_mutually_exclusive_group(required=True)
    runner.add_argument("--runner", nargs="+")
    runner.add_argument("--ollama-model", dest="ollamaModel")
    run.add_argument("--ollama-endpoint", dest="ollamaEndpoint", default=OLLAMA_ENDPOINT)
    run.add_argument("--timeout", type=int, default=120)
    run.add_argument("--output", type=Path, required=True)
    score = subparsers.add_parser("score")
    score.add_argument("manifest", type=Path)
    score.add_argument("responses", type=Path)
    score.add_argument("--config", type=Path)
    score.add_argument("--judgments", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        selfTest()
        return 0
    args = parseArgs(argv)
    if args.command == "prepare":
        config = loadConfig(args.config, start=args.folder)
        tasks = collectTasks(args.folder, config, args.perRule, args.limit)
        writeJson(args.output, {"version": 1, "tasks": tasks})
        print(f"{args.output} 에 짝 프롬프트 {len(tasks)}개를 썼다")
    elif args.command == "run":
        manifest = readJson(args.manifest)
        responses = (
            runOllamaManifest(manifest, args.ollamaModel, args.ollamaEndpoint, args.timeout, args.output)
            if args.ollamaModel
            else runManifest(manifest, args.runner, args.timeout)
        )
        writeJson(args.output, responses)
        print(f"{args.output} 에 응답을 썼다")
    else:
        config = loadConfig(args.config)
        responses = readJson(args.responses)
        if args.judgments:
            responses = applyJudgments(responses, readJson(args.judgments))
        print(scoreResponses(readJson(args.manifest), responses, config))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
