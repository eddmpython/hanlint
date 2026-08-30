"""exemplarLift. 같은 수정 과제에서 본보기 유무만 바꿔 결과를 잰다.

외부 모델을 제품이나 기본 게이트에 묶지 않는다. `prepare` 가 실제 지적에서 짝 프롬프트를 만들고, `run` 이
사용자가 명시한 실행기를 부르며, `score` 가 결과를 다시 hanlint 에 넣는다. 뜻 보존은 사람이 응답 JSON의
`meaningPreserved` 에 표시한 것만 따로 센다.

```powershell
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/exemplarLift/probeExemplarLift.py prepare <글들> --output manifest.json
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/exemplarLift/probeExemplarLift.py run manifest.json `
  --runner ollama run <model> --output responses.json
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/exemplarLift/probeExemplarLift.py score manifest.json responses.json
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from hanlint import Config, fingerprint, lintText, loadConfig  # noqa: E402
from hanlint.data import exemplarFor  # noqa: E402

CONDITIONS = ("reasonOnly", "withExemplar")


def promptFor(sentence: str, rule: str, why: str, exemplar: dict | None = None) -> str:
    lines = [
        "한국어 문장 하나를 고친다.",
        "원문의 뜻과 사실과 고유명사를 보존한다.",
        "설명과 따옴표 없이 고친 문장만 출력한다.",
        f"규칙: {rule}",
        f"이유: {why}",
    ]
    if exemplar:
        lines.extend(
            [
                "같은 결함의 검증된 본보기:",
                f"전: {exemplar['before']}",
                f"후: {exemplar['after']}",
                f"달라진 것: {exemplar['moved']}",
            ]
        )
    lines.append(f"고칠 문장: {sentence}")
    return "\n".join(lines)


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
                    "preset": config.preset,
                    "exemplar": exemplarData,
                    "prompts": {
                        "reasonOnly": promptFor(sentence, finding.rule, finding.why),
                        "withExemplar": promptFor(sentence, finding.rule, finding.why, exemplarData),
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


def resultOf(task: dict, response: dict, config: Config) -> dict:
    beforeErrors = Counter(finding.rule for finding in lintText(task["sentence"], config) if finding.severity == "error")
    afterErrors = Counter(finding.rule for finding in lintText(response["output"], config) if finding.severity == "error")
    result = {
        "resolved": afterErrors[task["rule"]] == 0,
        "newErrors": sum(max(0, count - beforeErrors[rule]) for rule, count in afterErrors.items()),
    }
    if "meaningPreserved" in response:
        result["meaningPreserved"] = bool(response["meaningPreserved"])
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
        meaningText = f", 뜻 보존 {meaning}/{len(judged)}" if judged else ", 뜻 보존 미판정"
        lines.append(f"  {condition:12} 규칙 해결 {resolved}/{len(selected)}, 새 error {newErrors}건{meaningText}")
    paired = [
        (results[(taskId, "reasonOnly")], results[(taskId, "withExemplar")])
        for taskId in tasks
        if (taskId, "reasonOnly") in results and (taskId, "withExemplar") in results
    ]
    exemplarWins = sum(not base["resolved"] and shown["resolved"] for base, shown in paired)
    reasonWins = sum(base["resolved"] and not shown["resolved"] for base, shown in paired)
    ties = len(paired) - exemplarWins - reasonWins
    lines.extend(
        [
            "",
            "짝 비교",
            f"  본보기만 해결 {exemplarWins}개, 이유만 해결 {reasonWins}개, 같은 결과 {ties}개",
            "  뜻 보존 표시는 사람이 원문과 결과를 읽은 응답만 센다",
        ]
    )
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
            {"taskId": task["id"], "condition": "reasonOnly", "output": task["sentence"]},
            {"taskId": task["id"], "condition": "withExemplar", "output": "설계를 알아야 합니다."},
        ]
    }
    report = scoreResponses(manifest, responses, Config())
    assert "본보기만 해결 1개" in report


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
    run.add_argument("--runner", nargs="+", required=True)
    run.add_argument("--timeout", type=int, default=120)
    run.add_argument("--output", type=Path, required=True)
    score = subparsers.add_parser("score")
    score.add_argument("manifest", type=Path)
    score.add_argument("responses", type=Path)
    score.add_argument("--config", type=Path)
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
        writeJson(args.output, runManifest(readJson(args.manifest), args.runner, args.timeout))
        print(f"{args.output} 에 응답을 썼다")
    else:
        config = loadConfig(args.config)
        print(scoreResponses(readJson(args.manifest), readJson(args.responses), config))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
