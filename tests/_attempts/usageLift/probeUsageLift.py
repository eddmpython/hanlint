"""usageLift. 같은 수정 과제에서 용례 유무만 바꿔 결과를 잰다. 2회차까지의 결함을 고친 3회차 설계다.

1, 2회차의 결함 둘. (1) 표본 45쌍은 방향을 말하기에 작았다 (회차마다 뒤집혔다). (2) 지표가 순환이었다. 프롬프트로 준
용례의 낱말을 썼는지를 같은 말뭉치로 채점하면 베끼기만 해도 점수가 오른다.

3회차 설계. 말뭉치를 문서 단위로 반으로 가른다 (짝수 번째가 A, 홀수 번째가 B). **근거는 A 색인에서 주고 채점은 B
색인으로 한다.** A 에서 본 결합이 B 에도 있으면 그것은 그 종류의 관용이고, A 에만 있으면 베낀 것이라 점수가 안 된다.
과제 문장은 A 문서에서 고르므로 원문 자체는 채점 말뭉치 밖에 있다.

주 지표 genreHit: 고친 문장의 이웃 어절 쌍 (조사를 뗀 core 의 인접 쌍) 가운데 **원문에 없던 새 쌍** 만 골라, 그것이
B 색인의 문서 MIN_PAIR_DOCUMENTS 편 이상에 나오는 비율. 모델이 새로 고른 결합이 그 종류의 실제 글에도 있는지를 묻는다.
쌍은 표본이 아니라 두 낱말의 postings 교집합으로 확인한다.
부 지표는 규칙 해결, 새 error, 명사 보존, 길이 비다.

판정 조건은 돌리기 전에 못박는다 (probeUsageLift_log.md 의 사전 등록). 짝 부호 검정 p 와 중앙값 차이를 둘 다 본다.

```console
python -X utf8 -B tests/_attempts/usageLift/probeUsageLift.py split --root <색인 폴더>
python -X utf8 -B tests/_attempts/usageLift/probeUsageLift.py prepare --root <색인 폴더> --output manifest.json --per-rule 100
python -X utf8 -B tests/_attempts/usageLift/probeUsageLift.py prompts manifest.json --output-dir <폴더>
python -X utf8 -B tests/_attempts/usageLift/probeUsageLift.py run manifest.json --ollama-model qwen3:8b --output responses.json
python -X utf8 -B tests/_attempts/usageLift/probeUsageLift.py score manifest.json responses.json --root <색인 폴더>
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.fetch.dartReports import defaultRoot as corpusRoot  # noqa: E402
from scripts.fetch.dartReports import readCorpus  # noqa: E402

from hanlint import Config, fingerprint, lintText  # noqa: E402
from hanlint.analysis import nounRuns  # noqa: E402
from hanlint.analysis.tokenize import isBareNoun, stripJosa, words  # noqa: E402
from hanlint.usage import buildIndex, loadIndex, queryCores  # noqa: E402
from hanlint.usage.sentences import TERMINAL  # noqa: E402

CONDITIONS = ("reasonOnly", "withUsage", "withWords")
"""reasonOnly 는 규칙과 이유만, withUsage 는 문장 다섯, withWords 는 문장 다섯에 함께 쓰는 말까지."""
RULES = ("nounPile", "euiChain", "translationese")
INDEX_A = "reportA"
INDEX_B = "reportB"
OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
OLLAMA_OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 512}
GLUE = re.compile(r"[.。][가-힣(]|[가-힣]{13,}|[①-⑳※■]|(?:(?<!\S)[가-힣] ){3}")
"""DART 원문이 문장 사이 빈칸을 잃은 자리와 항목 표시. 과제로 쓰지 않는다."""
MAX_WORDS = 45
EVIDENCE = 5
QUERY_WORDS = 3
MIN_PAIR_DOCUMENTS = 2
"""이웃 쌍이 채점 말뭉치의 몇 편에 나와야 그 종류의 결합으로 보는가. 한 편은 한 회사의 버릇이다."""
PAIR_CHECK = 400
"""쌍 하나를 확인할 때 읽을 문장 수 상한. 두 낱말이 함께 든 문장만 읽고 MIN_PAIR_DOCUMENTS 편을 찾으면 바로 멈춘다."""
CACHE_POSTINGS = 4_000_000
"""기억할 postings 항목 수 상한. 넘으면 비운다 (문장 55만 개 색인에서 몇백 MB)."""


def promptFor(sentence: str, rule: str, why: str, evidence: list[dict] | None = None, wordsUsed: list[dict] | None = None) -> str:
    lines = [
        "사업보고서의 한국어 문장 하나를 고친다.",
        "원문의 뜻과 사실과 숫자와 고유명사와 전문 용어를 보존한다.",
        "원문에 없는 정보는 만들지 않는다.",
        "확실하게 고칠 수 없으면 원문을 그대로 출력한다.",
        "설명과 따옴표 없이 고친 문장만 출력한다.",
        f"규칙: {rule}",
        f"이유: {why}",
    ]
    if wordsUsed:
        lines.append("다른 사업보고서에서 이 낱말과 함께 쓰인 말 (문서 수. 결합을 고를 때 참고한다):")
        for item in wordsUsed:
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


def neighbourPairs(sentence: str) -> set[tuple[str, str]]:
    """문장에서 붙어 있는 두 어절의 (core, core). 절이 끊기는 자리와 조사 어절은 잇지 않는다."""
    found: set[tuple[str, str]] = set()
    tokens = words(sentence)
    for index in range(len(tokens) - 1):
        left, right = tokens[index], tokens[index + 1]
        if left.endsClause or left.particle or right.particle or right.opens:
            continue
        a, b = stripJosa(left.core), stripJosa(right.core)
        if len(a) >= 2 and len(b) >= 2:
            found.add((a, b))
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


def halves(root: Path) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """말뭉치를 문서 단위로 반씩. 짝수 번째가 A (근거), 홀수 번째가 B (채점)."""
    documents = list(readCorpus(root))
    return documents[0::2], documents[1::2]


def splitIndexes(corpus: Path, root: Path) -> None:
    first, second = halves(corpus)
    for kind, chosen in ((INDEX_A, first), (INDEX_B, second)):
        result = buildIndex(kind, chosen, root)
        print(f"{root / kind}: 문서 {result.documents}편, 문장 {result.sentences}개, 토큰 {result.terms}종", flush=True)


class PairOracle:
    """이웃 쌍이 채점 말뭉치의 문서 둘 이상에 나오나. 두 낱말의 postings 를 교집합해 그 문장만 읽고 일찍 멈춘다.

    표본이 아니라 교집합이라 `없음` 은 진짜 없음이다 (PAIR_CHECK 안에서 못 찾은 경우만 예외이고 그때는 흔한 쌍이
    아니라는 뜻이다). 한 번 본 쌍과 낱말의 postings 는 기억한다."""

    def __init__(self, index) -> None:
        self.index = index
        self.pairs: dict[tuple[str, str], bool] = {}
        self.postings: dict[str, list[int]] = {}
        self.cached = 0

    def sentencesFor(self, term: str) -> list[int]:
        known = self.postings.get(term)
        if known is not None:
            return known
        found = self.index.lookup(term)
        ids = [sentenceId for sentenceId, _ in self.index.postingsAt(found[1], found[2])] if found else []
        if self.cached > CACHE_POSTINGS:
            self.postings.clear()
            self.cached = 0
        self.postings[term] = ids
        self.cached += len(ids)
        return ids

    def attested(self, pair: tuple[str, str]) -> bool:
        known = self.pairs.get(pair)
        if known is not None:
            return known
        left, right = pair
        leftIds, rightIds = self.sentencesFor(left), self.sentencesFor(right)
        found = False
        if leftIds and rightIds:
            smaller, larger = (leftIds, set(rightIds)) if len(leftIds) <= len(rightIds) else (rightIds, set(leftIds))
            sources: set[str] = set()
            checked = 0
            for sentenceId in smaller:
                if sentenceId not in larger:
                    continue
                checked += 1
                if checked > PAIR_CHECK:
                    break
                _, source, text = self.index.sentence(sentenceId)
                if pair in neighbourPairs(text):
                    sources.add(source)
                    if len(sources) >= MIN_PAIR_DOCUMENTS:
                        found = True
                        break
        self.pairs[pair] = found
        return found


def collectTasks(config: Config, perRule: int, root: Path, corpus: Path) -> list[dict]:
    """근거 색인 (A) 이 있는 문서에서 과제를 고른다. 문장 해시 순이라 문서 앞쪽에 몰리지 않는다."""
    index = loadIndex(INDEX_A, root)
    if index is None:
        raise SystemExit(f"{root / INDEX_A} 색인이 없다. split 을 먼저 돌린다")
    first, _ = halves(corpus)
    candidates: dict[str, dict[str, dict]] = {rule: {} for rule in RULES}
    for rceptNo, text in first:
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
            candidates[finding.rule].setdefault(
                identifier,
                {"id": identifier, "source": rceptNo, "rule": finding.rule, "why": finding.why, "sentence": sentence},
            )
    tasks: list[dict] = []
    for rule in RULES:
        for _, task in sorted(candidates[rule].items())[:perRule]:
            query = queryFor(task["sentence"], rule)
            hits = [hit for hit in index.search(query, EVIDENCE + 1) if hit.text != task["sentence"]][:EVIDENCE]
            evidence = [{"text": hit.text, "documents": hit.documents, "source": hit.source} for hit in hits]
            wordsUsed = []
            for core in queryCores(query)[:QUERY_WORDS]:
                found = index.collocations(core)
                if found is not None and (found.predicates or found.following or found.preceding):
                    wordsUsed.append(
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
                    "words": wordsUsed,
                    "prompts": {
                        "reasonOnly": promptFor(task["sentence"], rule, task["why"]),
                        "withUsage": promptFor(task["sentence"], rule, task["why"], evidence),
                        "withWords": promptFor(task["sentence"], rule, task["why"], evidence, wordsUsed),
                    },
                }
            )
    return tasks


def readJson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def writeJson(path: Path, data) -> None:
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
            if len(responses) % 25 == 0:
                if checkpoint:
                    writeJson(checkpoint, {"version": 1, "complete": False, "runner": runner, "responses": responses})
                print(f"응답 {len(responses)}/{total}", flush=True)
    return {"version": 1, "complete": True, "runner": runner, "responses": responses}


def termRetention(sentence: str, output: str) -> float:
    cores = nounCores(sentence)
    if not cores:
        return 1.0
    return sum(core in output for core in cores) / len(cores)


def resultOf(task: dict, response: dict, config: Config, oracle: PairOracle) -> dict:
    output = response["output"]
    before = Counter(f.rule for f in lintText(task["sentence"], config) if f.severity == "error")
    after = lintText(output, config)
    afterErrors = Counter(f.rule for f in after if f.severity == "error")
    newPairs = neighbourPairs(output) - neighbourPairs(task["sentence"])
    attested = sum(1 for pair in newPairs if oracle.attested(pair))
    return {
        "resolved": bool(output) and all(f.rule != task["rule"] for f in after),
        "unchanged": output == task["sentence"],
        "newErrors": sum(max(0, count - before[rule]) for rule, count in afterErrors.items()),
        "newPairs": len(newPairs),
        "attestedPairs": attested,
        "genreHit": round(attested / len(newPairs), 4) if newPairs else None,
        "termRetention": round(termRetention(task["sentence"], output), 4),
        "lengthRatio": round(len(output) / len(task["sentence"]), 3) if task["sentence"] else 0,
    }


def signTest(wins: int, losses: int) -> float:
    """짝 부호 검정의 양쪽 p 값. 같은 짝은 세지 않는다."""
    total = wins + losses
    if total == 0:
        return 1.0
    extreme = max(wins, losses)
    tail = sum(math.comb(total, k) for k in range(extreme, total + 1)) / 2**total
    return min(1.0, 2 * tail)


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def scoreResponses(manifest: dict, responses: dict, config: Config, root: Path) -> str:
    index = loadIndex(INDEX_B, root)
    if index is None:
        raise SystemExit(f"{root / INDEX_B} 색인이 없다. split 을 먼저 돌린다")
    oracle = PairOracle(index)
    tasks = {task["id"]: task for task in manifest["tasks"]}
    results: dict[tuple[str, str], dict] = {}
    for number, response in enumerate(responses["responses"], 1):
        task = tasks[response["taskId"]]
        results[(task["id"], response["condition"])] = resultOf(task, response, config, oracle)
        if number % 100 == 0:
            print(f"채점 {number}/{len(responses['responses'])}", file=sys.stderr, flush=True)
    counts = ", ".join(f"{rule} {sum(t['rule'] == rule for t in tasks.values())}" for rule in RULES)
    lines = [f"과제 {len(tasks)}개 ({counts}), 채점 말뭉치 {INDEX_B} 문서 {index.documents}편", ""]
    for condition in CONDITIONS:
        chosen = [result for (_, kind), result in results.items() if kind == condition]
        hits = [result["genreHit"] for result in chosen if result["genreHit"] is not None]
        if not chosen or not hits:
            lines.append(f"  {condition:10} 응답 없음")
            continue
        lines.append(
            f"  {condition:10} 규칙 해결 {sum(r['resolved'] for r in chosen)}/{len(chosen)}, "
            f"원문 그대로 {sum(r['unchanged'] for r in chosen)}, 새 error {sum(r['newErrors'] for r in chosen)}건, "
            f"genreHit 평균 {sum(hits) / len(hits):.3f} (문장 {len(hits)}개), "
            f"새 쌍 {sum(r['newPairs'] for r in chosen)}개 중 {sum(r['attestedPairs'] for r in chosen)}개 확인, "
            f"명사 보존 {sum(r['termRetention'] for r in chosen) / len(chosen):.3f}"
        )
    lines.extend(["", "짝 비교 (reasonOnly 대)"])
    for condition in CONDITIONS[1:]:
        pairs = [
            (results[(t, "reasonOnly")], results[(t, condition)])
            for t in tasks
            if (t, "reasonOnly") in results and (t, condition) in results
        ]
        both = [(a, b) for a, b in pairs if a["genreHit"] is not None and b["genreHit"] is not None]
        if not both:
            lines.append(f"  {condition:10} 짝 없음")
            continue
        deltas = [b["genreHit"] - a["genreHit"] for a, b in both]
        wins = sum(1 for delta in deltas if delta > 0)
        losses = sum(1 for delta in deltas if delta < 0)
        resolvedWins = sum(not a["resolved"] and b["resolved"] for a, b in pairs)
        resolvedLosses = sum(a["resolved"] and not b["resolved"] for a, b in pairs)
        lines.append(
            f"  {condition:10} genreHit 높음 {wins} 낮음 {losses} 같음 {len(both) - wins - losses}, "
            f"중앙값 차 {median(deltas):+.3f}, 평균 차 {sum(deltas) / len(deltas):+.3f} (짝 {len(both)}), "
            f"부호검정 p {signTest(wins, losses):.4f}"
        )
        lines.append(
            f"             규칙 해결 {resolvedWins} 대 {resolvedLosses} "
            f"(부호검정 p {signTest(resolvedWins, resolvedLosses):.4f}), "
            f"새 error 차 {sum(b['newErrors'] - a['newErrors'] for a, b in pairs):+d}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    split = sub.add_parser("split")
    split.add_argument("--root", type=Path, required=True)
    split.add_argument("--corpus", type=Path, default=corpusRoot())
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--root", type=Path, required=True)
    prepare.add_argument("--corpus", type=Path, default=corpusRoot())
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--per-rule", dest="perRule", type=int, default=100)
    prompts = sub.add_parser("prompts")
    prompts.add_argument("manifest", type=Path)
    prompts.add_argument("--output-dir", dest="outputDir", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("manifest", type=Path)
    run.add_argument("--ollama-model", dest="model", required=True)
    run.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    run.add_argument("--timeout", type=int, default=600)
    run.add_argument("--output", type=Path, required=True)
    score = sub.add_parser("score")
    score.add_argument("manifest", type=Path)
    score.add_argument("responses", type=Path)
    score.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    config = Config(preset="report")
    if args.command == "split":
        splitIndexes(args.corpus, args.root)
    elif args.command == "prepare":
        tasks = collectTasks(config, args.perRule, args.root, args.corpus)
        writeJson(args.output, {"version": 2, "preset": config.preset, "conditions": list(CONDITIONS), "tasks": tasks})
        counts = ", ".join(f"{rule} {sum(t['rule'] == rule for t in tasks)}" for rule in RULES)
        print(f"{args.output}: 과제 {len(tasks)}개, {counts}")
    elif args.command == "prompts":
        manifest = readJson(args.manifest)
        args.outputDir.mkdir(parents=True, exist_ok=True)
        for condition in CONDITIONS:
            path = args.outputDir / f"prompts_{condition}.json"
            writeJson(path, [{"taskId": task["id"], "prompt": task["prompts"][condition]} for task in manifest["tasks"]])
            print(f"{path}: {len(manifest['tasks'])}개")
    elif args.command == "run":
        manifest = readJson(args.manifest)
        responses = runOllama(manifest, args.model, args.endpoint, args.timeout, args.output)
        writeJson(args.output, responses)
        print(f"{args.output}: 응답 {len(responses['responses'])}개")
    else:
        print(scoreResponses(readJson(args.manifest), readJson(args.responses), config, args.root))


if __name__ == "__main__":
    main()
