"""기준 말뭉치에서 후보 생성 범위와 사람이 후보를 고른 비율을 잰다.

표본은 candidateSample.json, 사람 판정은 candidateJudgments.toml, 합친 수치는 candidateMetrics.json이
소유한다. 이 스크립트는 판정 파일을 만들거나 고치지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from hanlint import Config, fingerprint  # noqa: E402
from hanlint.rules import runAll  # noqa: E402
from hanlint.rules.shared import endingRepeatCandidates, nounPileCandidates  # noqa: E402

CORPUS_ROOT = (REPO / "../hanlint.out/corpus").resolve()
ATTEMPT = REPO / "tests" / "_attempts" / "corpus"
SAMPLE_PATH = ATTEMPT / "candidateSample.json"
JUDGMENTS_PATH = ATTEMPT / "candidateJudgments.toml"
METRICS_PATH = ATTEMPT / "candidateMetrics.json"
TARGETS = ("longSentence", "danglingDeixis", "nounPile", "endingRepeat", "doublePassive")
SAMPLE_LIMIT = 10


def readJson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def writeJson(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def observationId(document: str, rule: str, line: int, quote: str) -> str:
    raw = f"{document}\0{rule}\0{line}\0{quote}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def contextOf(text: str, line: int) -> str:
    lines = text.splitlines()
    start = max(line - 2, 0)
    end = min(line + 1, len(lines))
    return "\n".join(f"{index + 1}: {lines[index]}" for index in range(start, end))


def observe() -> list[dict]:
    metadata = readJson(CORPUS_ROOT / "metadata.json")["documents"]
    observations = []
    for entry in metadata:
        text = (CORPUS_ROOT / entry["path"]).read_text(encoding="utf-8")
        config = Config(preset=entry["preset"])
        doc = fingerprint(text, config, path=entry["path"])
        for finding in runAll(doc, config):
            if finding.rule not in TARGETS:
                continue
            candidates = finding.candidates
            if finding.rule == "nounPile":
                candidates = nounPileCandidates(finding.quote)
            elif finding.rule == "endingRepeat":
                candidates = endingRepeatCandidates(doc.register)
            observations.append(
                {
                    "id": observationId(entry["id"], finding.rule, finding.line, finding.quote),
                    "document": entry["id"],
                    "type": entry["type"],
                    "title": entry["title"],
                    "url": entry["url"],
                    "rule": finding.rule,
                    "line": finding.line,
                    "quote": finding.quote,
                    "context": contextOf(text, finding.line),
                    "candidates": [candidate.asDict() for candidate in candidates],
                }
            )
    return sorted(observations, key=lambda item: (item["rule"], item["type"], item["document"], item["line"]))


def evenly(items: list[dict], limit: int) -> list[dict]:
    if len(items) <= limit:
        return items
    return [items[round(index * (len(items) - 1) / (limit - 1))] for index in range(limit)]


def sampleOf(observations: list[dict]) -> list[dict]:
    byRule: dict[str, list[dict]] = defaultdict(list)
    for observation in observations:
        if observation["candidates"]:
            byRule[observation["rule"]].append(observation)
    return [item for rule in TARGETS for item in evenly(byRule[rule], SAMPLE_LIMIT)]


def readJudgments(sample: list[dict]) -> dict[str, bool]:
    if not JUDGMENTS_PATH.exists():
        return {}
    rows = tomllib.loads(JUDGMENTS_PATH.read_text(encoding="utf-8")).get("rule", [])
    byRule: dict[str, list[dict]] = defaultdict(list)
    for item in sample:
        byRule[item["rule"]].append(item)
    judgments = {}
    seen = set()
    for row in rows:
        rule = row["name"]
        if rule in seen:
            raise ValueError(f"{rule} 후보 판정이 두 번 있다")
        seen.add(rule)
        selected = set(row.get("selected", []))
        notSelected = set(row.get("notSelected", []))
        if selected & notSelected:
            raise ValueError(f"{rule} 후보 판정이 양쪽에 있다")
        expected = {item["id"] for item in byRule[rule]}
        if selected | notSelected != expected:
            raise ValueError(f"{rule} 후보 판정 id가 현재 표본과 다르다")
        if row["sampled"] != len(expected) or not row.get("note", "").strip():
            raise ValueError(f"{rule} 후보 판정 수나 근거가 없다")
        judgments.update({item: True for item in selected})
        judgments.update({item: False for item in notSelected})
    unknown = sorted(seen - set(TARGETS))
    if unknown:
        raise ValueError("모르는 후보 규칙: " + ", ".join(unknown))
    return judgments


def metrics(observations: list[dict], sample: list[dict]) -> dict:
    judgments = readJudgments(sample)
    byRule: dict[str, list[dict]] = defaultdict(list)
    sampleByRule: dict[str, list[dict]] = defaultdict(list)
    for item in observations:
        byRule[item["rule"]].append(item)
    for item in sample:
        sampleByRule[item["rule"]].append(item)
    rows = []
    for rule in TARGETS:
        found = byRule[rule]
        withCandidates = [item for item in found if item["candidates"]]
        selected = sampleByRule[rule]
        verdicts = [judgments[item["id"]] for item in selected if item["id"] in judgments]
        chosen = sum(verdicts)
        rows.append(
            {
                "rule": rule,
                "findings": len(found),
                "withCandidates": len(withCandidates),
                "candidateCoverage": round(len(withCandidates) / len(found), 4) if found else None,
                "candidates": sum(len(item["candidates"]) for item in withCandidates),
                "sampled": len(selected),
                "reviewed": len(verdicts),
                "selected": chosen,
                "notSelected": len(verdicts) - chosen,
                "selectionRate": round(chosen / len(verdicts), 4) if verdicts else None,
                "published": rule not in ("nounPile", "endingRepeat"),
            }
        )
    return {"version": 1, "documents": 390, "sampleLimitPerRule": SAMPLE_LIMIT, "rules": rows}


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="기준 말뭉치의 후보 범위와 사람 선택률을 잰다")
    parser.add_argument("--check", action="store_true", help="기록을 다시 재어 글자 단위로 견준다")
    parser.add_argument("--sample-only", action="store_true", help="후보 생성기를 바꾼 뒤 판정 전 표본만 갱신한다")
    return parser.parse_args()


def main() -> int:
    args = parseArgs()
    observations = observe()
    sample = sampleOf(observations)
    sampleData = {"version": 1, "limitPerRule": SAMPLE_LIMIT, "observations": sample}
    if args.sample_only:
        writeJson(SAMPLE_PATH, sampleData)
        print(f"후보 지적 {len(observations)}건에서 판정할 표본 {len(sample)}건을 뽑았다")
        return 0
    metricData = metrics(observations, sample)
    if args.check:
        expected = ((SAMPLE_PATH, sampleData), (METRICS_PATH, metricData))
        changed = [str(path.relative_to(REPO)) for path, data in expected if readJson(path) != data]
        if changed:
            print("다시 재야 한다: " + ", ".join(changed))
            return 1
        print(f"후보 지적 {len(observations)}건의 측정 기록이 같다")
        return 0
    writeJson(SAMPLE_PATH, sampleData)
    writeJson(METRICS_PATH, metricData)
    print(f"후보 지적 {len(observations)}건에서 사람 검토 표본 {len(sample)}건을 뽑았다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
