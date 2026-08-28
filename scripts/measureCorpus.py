"""기준 말뭉치에서 규칙 발화와 문체 분포를 잰다.

발화 수는 전수로 센다. 정탐률은 규칙마다 종류와 문서에 걸쳐 최대 20건을 고르게 뽑아 사람이 읽는다.
표본은 tests/_attempts/corpus/reviewSample.json, 판정은 judgments.toml, 합친 수치는 ruleMetrics.json 이
소유한다. 판정 파일은 이 스크립트가 만들거나 고치지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from hanlint import Config, fingerprint, ruleNames  # noqa: E402
from hanlint.rules import runAll  # noqa: E402

CORPUS_ROOT = (REPO / "../hanlint.out/corpus").resolve()
ATTEMPT = REPO / "tests" / "_attempts" / "corpus"
REVIEW_SAMPLE = ATTEMPT / "reviewSample.json"
JUDGMENTS = ATTEMPT / "judgments.toml"
RULE_METRICS = ATTEMPT / "ruleMetrics.json"
SAMPLE_LIMIT = 20


def readJson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def writeJson(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def trackable(value):
    """외부 원문의 대시를 저장소 표기 계약에 맞춰 검토 표본에만 투영한다.

    원문과 해시와 판정 ID는 저장소 밖 고정 말뭉치가 그대로 소유한다. 추적 JSON은 사람이 읽는 표본이라
    부연 대시는 하이픈으로, 범위 대시는 물결표로 보인다.
    """
    if isinstance(value, str):
        return value.replace(chr(0x2014), "-").replace(chr(0x2013), "~")
    if isinstance(value, list):
        return [trackable(item) for item in value]
    if isinstance(value, dict):
        return {key: trackable(item) for key, item in value.items()}
    return value


def shareDistribution(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)

    def at(ratio: float) -> float:
        return round(ordered[round((len(ordered) - 1) * ratio)], 4)

    return {"min": at(0), "p05": at(0.05), "median": at(0.5), "p95": at(0.95), "max": at(1)}


def findingId(docId: str, rule: str, line: int, quote: str, why: str) -> str:
    value = f"{docId}\0{rule}\0{line}\0{quote}\0{why}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def contextOf(text: str, line: int) -> str:
    lines = text.splitlines()
    start = max(line - 2, 0)
    end = min(line + 1, len(lines))
    return "\n".join(f"{index + 1}: {lines[index]}" for index in range(start, end))


def observe() -> tuple[list[dict], dict]:
    metadata = readJson(CORPUS_ROOT / "metadata.json")["documents"]
    observations: list[dict] = []
    registers: dict[str, Counter] = defaultdict(Counter)
    registerShares: dict[str, list[float]] = defaultdict(list)
    sentences = Counter()
    for entry in metadata:
        text = (CORPUS_ROOT / entry["path"]).read_text(encoding="utf-8")
        config = Config(preset=entry["preset"])
        doc = fingerprint(text, config, path=entry["path"])
        registers[entry["type"]][doc.register] += 1
        registerShares[entry["type"]].append(doc.registerShare)
        sentences[entry["type"]] += len(doc.sentences)
        for finding in runAll(doc, config):
            observations.append(
                {
                    "id": findingId(entry["id"], finding.rule, finding.line, finding.quote, finding.why),
                    "document": entry["id"],
                    "type": entry["type"],
                    "preset": entry["preset"],
                    "title": entry["title"],
                    "url": entry["url"],
                    "rule": finding.rule,
                    "line": finding.line,
                    "severity": finding.severity,
                    "quote": finding.quote,
                    "why": finding.why,
                    "context": contextOf(text, finding.line),
                }
            )
    observations.sort(key=lambda item: (item["rule"], item["type"], item["document"], item["line"]))
    corpusStats = {
        "documents": len(metadata),
        "types": dict(sorted(Counter(entry["type"] for entry in metadata).items())),
        "sentences": dict(sorted(sentences.items())),
        "registers": {kind: dict(sorted(counts.items())) for kind, counts in sorted(registers.items())},
        "meanRegisterShare": {kind: round(sum(values) / len(values), 4) for kind, values in sorted(registerShares.items())},
        "registerShareDistribution": {kind: shareDistribution(values) for kind, values in sorted(registerShares.items())},
    }
    return observations, corpusStats


def evenly(items: list[dict], limit: int) -> list[dict]:
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[0]]
    return [items[round(index * (len(items) - 1) / (limit - 1))] for index in range(limit)]


def sampleOf(observations: list[dict]) -> list[dict]:
    byRule: dict[str, list[dict]] = defaultdict(list)
    for observation in observations:
        byRule[observation["rule"]].append(observation)
    return [item for name in ruleNames() for item in evenly(byRule[name], SAMPLE_LIMIT)]


def metrics(observations: list[dict], sample: list[dict], corpusStats: dict) -> dict:
    judgments = readJudgments(sample)
    byRule: dict[str, list[dict]] = defaultdict(list)
    for observation in observations:
        byRule[observation["rule"]].append(observation)
    sampleByRule: dict[str, list[dict]] = defaultdict(list)
    for observation in sample:
        sampleByRule[observation["rule"]].append(observation)
    rows = []
    for name in ruleNames():
        found = byRule[name]
        selected = sampleByRule[name]
        verdicts = judgments.get(name, {})
        verdicts = [verdicts[item["id"]] for item in selected if item["id"] in verdicts]
        correct = sum(verdict == "correct" for verdict in verdicts)
        falsePositive = sum(verdict == "falsePositive" for verdict in verdicts)
        if len(verdicts) != correct + falsePositive:
            raise ValueError(f"{name} 판정에 correct 또는 falsePositive 가 아닌 값이 있다")
        rows.append(
            {
                "rule": name,
                "occurrences": len(found),
                "documents": len({item["document"] for item in found}),
                "sampled": len(selected),
                "reviewed": len(verdicts),
                "correct": correct,
                "falsePositive": falsePositive,
                "precision": round(correct / len(verdicts), 4) if verdicts else None,
            }
        )
    return {"version": 1, "corpus": corpusStats, "rules": rows}


def readJudgments(sample: list[dict]) -> dict[str, dict[str, str]]:
    if not JUDGMENTS.exists():
        return {}
    with JUDGMENTS.open("rb") as file:
        rows = tomllib.load(file).get("rule", [])
    sampleByRule: dict[str, list[dict]] = defaultdict(list)
    for observation in sample:
        sampleByRule[observation["rule"]].append(observation)
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        name = row["name"]
        selected = sampleByRule[name]
        if name in result:
            raise ValueError(f"{name} 판정이 두 번 있다")
        if row["sampled"] != len(selected):
            raise ValueError(f"{name} 표본 수가 다르다: {row['sampled']} != {len(selected)}")
        if not row.get("note", "").strip():
            raise ValueError(f"{name} 판정 근거가 없다")
        default = row["default"]
        if default not in ("correct", "falsePositive"):
            raise ValueError(f"{name} 기본 판정이 잘못됐다: {default}")
        exceptions = "falsePositive" if default == "correct" else "correct"
        exceptionIds = set(row.get(exceptions, []))
        selectedIds = {item["id"] for item in selected}
        unknown = sorted(exceptionIds - selectedIds)
        if unknown:
            raise ValueError(f"{name} 현재 표본에 없는 판정 id: {', '.join(unknown[:3])}")
        result[name] = {item["id"]: exceptions if item["id"] in exceptionIds else default for item in selected}
    unknownRules = sorted(set(result) - set(ruleNames()))
    if unknownRules:
        raise ValueError(f"모르는 규칙 판정: {', '.join(unknownRules)}")
    missingRules = sorted(set(sampleByRule) - set(result))
    if rows and missingRules:
        raise ValueError(f"표본 판정이 없는 규칙: {', '.join(missingRules)}")
    return result


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="기준 말뭉치의 규칙 발화와 정탐률을 잰다")
    parser.add_argument("--check", action="store_true", help="기록을 다시 재어 글자 단위로 견준다")
    return parser.parse_args()


def main() -> int:
    args = parseArgs()
    observations, corpusStats = observe()
    sample = sampleOf(observations)
    sampleData = trackable({"version": 1, "limitPerRule": SAMPLE_LIMIT, "observations": sample})
    metricData = metrics(observations, sample, corpusStats)
    if args.check:
        expected = [(REVIEW_SAMPLE, sampleData), (RULE_METRICS, metricData)]
        changed = [str(path.relative_to(REPO)) for path, data in expected if readJson(path) != data]
        if changed:
            print("다시 재야 한다: " + ", ".join(changed))
            return 1
        print(f"기준 말뭉치 {corpusStats['documents']}편의 측정 기록이 같다")
        return 0
    writeJson(REVIEW_SAMPLE, sampleData)
    writeJson(RULE_METRICS, metricData)
    print(f"기준 말뭉치 {corpusStats['documents']}편에서 지적 {len(observations)}건, 검토 표본 {len(sample)}건을 쟀다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
