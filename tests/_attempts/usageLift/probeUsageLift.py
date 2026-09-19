"""usageLift. 같은 수정 과제에서 용례 (hanlint usage 의 문장) 유무만 바꿔 결과를 잰다.

exemplarLift 의 짝실험 계약을 그대로 쓴다. `prepare` 가 사업보고서 말뭉치의 실제 지적에서 짝 프롬프트를 만들고 (reasonOnly,
withUsage), `run` 이 결정적 Ollama 호출로 두 조건을 돌리며, `score` 가 결과를 다시 hanlint 에 넣어 목표 규칙이 사라졌는지,
새 error 가 생겼는지, 원문의 명사 어절이 얼마나 남았는지 (termRetention) 를 센다. 뜻 보존은 검토자가 judgments JSON 에
표시한 것만 따로 센다. 외부 모델을 제품이나 게이트에 묶지 않는다.

```powershell
python -X utf8 -B tests/_attempts/usageLift/probeUsageLift.py prepare --output manifest.json
python -X utf8 -B tests/_attempts/usageLift/probeUsageLift.py run manifest.json --ollama-model qwen3:8b --output responses.json
python -X utf8 -B tests/_attempts/usageLift/probeUsageLift.py score manifest.json responses.json --judgments judgments.json
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts.fetch.dartReports import defaultRoot as corpusRoot  # noqa: E402
from scripts.fetch.dartReports import readCorpus  # noqa: E402

from hanlint import Config, fingerprint, lintText  # noqa: E402
from hanlint.analysis import nounRuns  # noqa: E402
from hanlint.analysis.tokenize import isBareNoun, stripJosa, words  # noqa: E402
from hanlint.usage import defaultUsageRoot, loadIndex, queryCores  # noqa: E402
from hanlint.usage.sentences import TERMINAL  # noqa: E402

CONDITIONS = ("reasonOnly", "withUsage", "withWords")
"""withUsage 는 문장 다섯, withWords 는 거기에 함께 쓰는 말 (뒤 용언, 앞뒤 명사, 문서 수) 을 더 받는다."""
RULES = ("nounPile", "euiChain", "translationese")
OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
OLLAMA_OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 512}
GLUE = re.compile(r"[.。][가-힣(]|[가-힣]{13,}|[①-⑳※■]|(?:(?<!\S)[가-힣] ){3}")
"""DART 원문이 문장 사이 빈칸을 잃은 자리 (`없습니다.기타`, `불확실성한국채택국제회계기준은`) 와 항목 표시. 그런 문장은
과제로 쓰지 않는다. 한글 13자 넘게 붙은 어절은 실제 낱말 (`한국채택국제회계기준`, 10자) 보다 길어 붙은 자리로 본다."""
MAX_WORDS = 45
EVIDENCE = 5


def promptFor(sentence: str, rule: str, why: str, evidence: list[dict] | None = None, words: list[dict] | None = None) -> str:
    lines = [
        "사업보고서의 한국어 문장 하나를 고친다.",
        "원문의 뜻과 사실과 숫자와 고유명사와 전문 용어를 보존한다.",
        "원문에 없는 정보는 만들지 않는다.",
        "확실하게 고칠 수 없으면 원문을 그대로 출력한다.",
        "설명과 따옴표 없이 고친 문장만 출력한다.",
        f"규칙: {rule}",
        f"이유: {why}",
    ]
    if words:
        lines.append("다른 사업보고서에서 이 낱말과 함께 쓰인 말 (문서 수. 결합을 고를 때 참고한다):")
        for item in words:
            for label, key in (("뒤 용언", "predicates"), ("뒤 명사", "following"), ("앞 명사", "preceding")):
                if item[key]:
                    lines.append(f"- {item['term']} {label}: " + ", ".join(f"{term} {count}편" for term, count in item[key]))
    if evidence:
        lines.append("같은 낱말이 다른 사업보고서에서 쓰인 문장 (참고만 한다. 사실과 숫자는 옮기지 않는다):")
        lines.extend(f"- {item['text']} (문서 {item['documents']}편)" for item in evidence)
    lines.append(f"고칠 문장: {sentence}")
    return "\n".join(lines)


def nounCores(sentence: str) -> list[str]:
    """문장의 명사 어절 (조사를 뗀 것). 순서대로, 겹치지 않게."""
    found: list[str] = []
    for word in words(sentence):
        core = stripJosa(word.core)
        if core and isBareNoun(core) and len(core) >= 2 and core not in found:
            found.append(core)
    return found


def queryFor(sentence: str, rule: str) -> str:
    """용례를 물을 낱말. nounPile 은 가장 긴 연쇄, 나머지는 명사 어절 앞 여섯."""
    if rule == "nounPile":
        runs = nounRuns(sentence)
        if runs:
            chain, _ = max(runs, key=lambda item: item[1])
            return " ".join(chain)
    return " ".join(nounCores(sentence)[:6])


def taskId(rule: str, sentence: str) -> str:
    digest = hashlib.sha256(f"{rule}\0{sentence}".encode()).hexdigest()[:12]
    return f"{rule}-{digest}"


def collectTasks(config: Config, perRule: int, documentLimit: int) -> list[dict]:
    """말뭉치를 접수번호 순으로 걸으며 규칙마다 perRule 개. 문장 해시 순으로 골라 문서 앞쪽에 몰리지 않게 한다."""
    index = loadIndex("report", defaultUsageRoot())
    if index is None:
        raise SystemExit("report 색인이 없다. hanlint usage build report ~/.cache/hanlint/corpus/dart 를 먼저 돌린다")
    candidates: dict[str, list[tuple[str, dict]]] = {rule: [] for rule in RULES}
    for rceptNo, text in readCorpus(corpusRoot(), documentLimit):
        markdown = "\n\n".join(text.splitlines())
        document = fingerprint(markdown, config)
        for finding in lintText(markdown, config):
            if finding.rule not in RULES or finding.scope != "sentence" or finding.at < 0:
                continue
            sentence = document.sentences[finding.at].text.strip()
            if GLUE.search(sentence) or not TERMINAL.search(sentence) or len(sentence.split()) > MAX_WORDS:
                continue
            if "(주" in sentence or sentence[0] in "(*-":
                continue
            identifier = taskId(finding.rule, sentence)
            candidates[finding.rule].append(
                (
                    identifier,
                    {"id": identifier, "source": rceptNo, "rule": finding.rule, "why": finding.why, "sentence": sentence},
                )
            )
    tasks: list[dict] = []
    for rule in RULES:
        chosen = sorted({identifier: task for identifier, task in candidates[rule]}.items())[:perRule]
        for _, task in chosen:
            query = queryFor(task["sentence"], rule)
            hits = [hit for hit in index.search(query, EVIDENCE + 1) if hit.text != task["sentence"]][:EVIDENCE]
            evidence = [{"text": hit.text, "documents": hit.documents, "source": hit.source} for hit in hits]
            words = []
            for core in queryCores(query)[:3]:
                found = index.collocations(core)
                if found is not None and (found.predicates or found.following or found.preceding):
                    words.append(
                        {
                            "term": core,
                            "predicates": list(found.predicates),
                            "following": list(found.following),
                            "preceding": list(found.preceding),
                        }
                    )
            tasks.append(
                {
                    **task,
                    "preset": config.preset,
                    "query": query,
                    "evidence": evidence,
                    "words": words,
                    "prompts": {
                        "reasonOnly": promptFor(task["sentence"], rule, task["why"]),
                        "withUsage": promptFor(task["sentence"], rule, task["why"], evidence),
                        "withWords": promptFor(task["sentence"], rule, task["why"], evidence, words),
                    },
                }
            )
    return tasks


def readJson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def writeJson(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def ollamaJson(endpoint: str, route: str, timeout: int, data: dict | None = None) -> dict:
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
    tags = ollamaJson(endpoint, "/api/tags", timeout)
    found = next((item for item in tags.get("models", []) if item.get("name") == model), None)
    if found is None:
        raise RuntimeError(f"Ollama 에 {model} 모델이 없다")
    return {key: found[key] for key in ("name", "digest", "size", "modified_at") if key in found}


def ollamaGenerate(prompt: str, model: str, endpoint: str, timeout: int) -> tuple[str, dict]:
    result = ollamaJson(
        endpoint,
        "/api/generate",
        timeout,
        {"model": model, "prompt": prompt, "stream": False, "think": False, "keep_alive": "10m", "options": OLLAMA_OPTIONS},
    )
    output = result.get("response", "").strip().splitlines()
    metrics = {key: result[key] for key in ("done_reason", "total_duration", "prompt_eval_count", "eval_count") if key in result}
    return (output[0].strip() if output else ""), metrics


def runOllama(manifest: dict, model: str, endpoint: str, timeout: int, checkpoint: Path | None) -> dict:
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
            if checkpoint:
                writeJson(checkpoint, {"version": 1, "complete": False, "runner": runner, "responses": responses})
            print(f"응답 {len(responses)}/{total}: {task['id']} {condition}", flush=True)
    return {"version": 1, "complete": True, "runner": runner, "responses": responses}


def termRetention(sentence: str, output: str) -> float:
    """원문의 명사 어절 가운데 고친 문장에도 있는 비율. 용례가 낱말을 바꿔 치우게 하는지 본다."""
    cores = nounCores(sentence)
    if not cores:
        return 1.0
    return sum(core in output for core in cores) / len(cores)


def resultOf(task: dict, response: dict, config: Config) -> dict:
    output = response["output"]
    before = Counter(f.rule for f in lintText(task["sentence"], config) if f.severity == "error")
    after = lintText(output, config)
    afterErrors = Counter(f.rule for f in after if f.severity == "error")
    result = {
        "resolved": bool(output) and all(f.rule != task["rule"] for f in after),
        "unchanged": output == task["sentence"],
        "newErrors": sum(max(0, count - before[rule]) for rule, count in afterErrors.items()),
        "termRetention": round(termRetention(task["sentence"], output), 3),
        "lengthRatio": round(len(output) / len(task["sentence"]), 2) if task["sentence"] else 0,
    }
    if "meaningPreserved" in response:
        result["meaningPreserved"] = bool(response["meaningPreserved"])
        result["threeChecks"] = result["resolved"] and result["newErrors"] == 0 and result["meaningPreserved"]
    return result


def applyJudgments(responses: dict, judgments: dict) -> dict:
    labels = {(item["taskId"], item["condition"]): item for item in judgments.get("judgments", [])}
    merged = []
    for response in responses["responses"]:
        item = dict(response)
        judgment = labels.get((response["taskId"], response["condition"]))
        if judgment is not None:
            item["meaningPreserved"] = bool(judgment["meaningPreserved"])
            if judgment.get("note"):
                item["meaningNote"] = judgment["note"]
        merged.append(item)
    return {**responses, "responses": merged}


def scoreResponses(manifest: dict, responses: dict, config: Config) -> str:
    tasks = {task["id"]: task for task in manifest["tasks"]}
    results: dict[tuple[str, str], dict] = {}
    for response in responses["responses"]:
        task = tasks[response["taskId"]]
        results[(task["id"], response["condition"])] = resultOf(task, response, config)
    lines = [
        f"과제 {len(tasks)}개 (" + ", ".join(f"{rule} {sum(t['rule'] == rule for t in tasks.values())}" for rule in RULES) + ")",
        "",
    ]
    for condition in CONDITIONS:
        selected = [result for (_, kind), result in results.items() if kind == condition]
        judged = [result for result in selected if "meaningPreserved" in result]
        retention = sum(result["termRetention"] for result in selected) / len(selected)
        ratio = sum(result["lengthRatio"] for result in selected) / len(selected)
        line = (
            f"  {condition:10} 규칙 해결 {sum(r['resolved'] for r in selected)}/{len(selected)}, "
            f"원문 그대로 {sum(r['unchanged'] for r in selected)}, 새 error {sum(r['newErrors'] for r in selected)}건, "
            f"명사 보존 평균 {retention:.2f}, 길이 비 평균 {ratio:.2f}"
        )
        if judged:
            line += (
                f", 뜻 보존 {sum(r['meaningPreserved'] for r in judged)}/{len(judged)}, "
                f"세 조건 충족 {sum(r['threeChecks'] for r in judged)}/{len(judged)}"
            )
        lines.append(line)
    for rule in RULES:
        lines.append(f"  [{rule}]")
        for condition in CONDITIONS:
            selected = [
                result for (taskId, kind), result in results.items() if kind == condition and tasks[taskId]["rule"] == rule
            ]
            if selected:
                resolved = sum(r["resolved"] for r in selected)
                errors = sum(r["newErrors"] for r in selected)
                retention = sum(r["termRetention"] for r in selected) / len(selected)
                lines.append(f"    {condition:10} 해결 {resolved}/{len(selected)}, 새 error {errors}, 명사 보존 {retention:.2f}")
    lines.append("")
    lines.append("짝 비교 (reasonOnly 대)")
    for condition in CONDITIONS[1:]:
        paired = [
            (results[(t, "reasonOnly")], results[(t, condition)])
            for t in tasks
            if (t, "reasonOnly") in results and (t, condition) in results
        ]
        if not paired:
            continue
        wins = sum(not a["resolved"] and b["resolved"] for a, b in paired)
        losses = sum(a["resolved"] and not b["resolved"] for a, b in paired)
        up = sum(b["termRetention"] > a["termRetention"] for a, b in paired)
        down = sum(b["termRetention"] < a["termRetention"] for a, b in paired)
        lines.append(
            f"  {condition:10} 해결 {wins} 대 {losses} (같음 {len(paired) - wins - losses}), "
            f"명사 보존 높음 {up} 낮음 {down} 같음 {len(paired) - up - down}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--per-rule", dest="perRule", type=int, default=15)
    prepare.add_argument("--documents", type=int, default=200, help="말뭉치 앞에서부터 볼 문서 수")
    run = sub.add_parser("run")
    run.add_argument("manifest", type=Path)
    run.add_argument("--ollama-model", dest="model", required=True)
    run.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    run.add_argument("--timeout", type=int, default=600)
    run.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("score")
    score.add_argument("manifest", type=Path)
    score.add_argument("responses", type=Path)
    score.add_argument("--judgments", type=Path)
    args = parser.parse_args()
    config = Config(preset="report")
    if args.command == "prepare":
        tasks = collectTasks(config, args.perRule, args.documents)
        writeJson(args.output, {"version": 1, "preset": config.preset, "conditions": list(CONDITIONS), "tasks": tasks})
        print(
            f"{args.output}: 과제 {len(tasks)}개, "
            + ", ".join(f"{rule} {sum(t['rule'] == rule for t in tasks)}" for rule in RULES)
        )
    elif args.command == "run":
        manifest = readJson(args.manifest)
        responses = runOllama(manifest, args.model, args.endpoint, args.timeout, args.output)
        writeJson(args.output, responses)
        print(f"{args.output}: 응답 {len(responses['responses'])}개")
    else:
        manifest = readJson(args.manifest)
        responses = readJson(args.responses)
        if args.judgments:
            responses = applyJudgments(responses, readJson(args.judgments))
        print(scoreResponses(manifest, responses, config))


if __name__ == "__main__":
    main()
