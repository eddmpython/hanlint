"""고정 KLUE-NLI dev 판에서 source·label 균형 함의 평가판을 만든다.

원본은 저장소 밖에서 내려받는다. 이 스크립트는 원본 SHA256을 먼저 확인하고, 각 source·label 묶음에서
GUID SHA256 순으로 합의가 높은 두 사례를 고른다. 전제와 가설은 평가판 전체에서 중복되지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from hashlib import sha256
from pathlib import Path

SOURCE_REVISION = "3efd98708a40ff49251fddde35453f8fbb11f536"
SOURCE_SHA256 = "0699db82be17766b26e199864e6260443e17ec6e91d1870e876419e388f245b1"
SOURCE_URL = (
    f"https://raw.githubusercontent.com/KLUE-benchmark/KLUE/{SOURCE_REVISION}/klue_benchmark/klue-nli-v1.1/klue-nli-v1.1_dev.json"
)
REPOSITORY_URL = "https://github.com/KLUE-benchmark/KLUE"
PAPER_URL = "https://arxiv.org/html/2105.09680v4"
LICENSE = "CC-BY-SA-4.0"
SOURCES = ("NSMC", "airbnb", "policy", "wikinews", "wikipedia", "wikitree")
SOURCE_LABELS = ("contradiction", "entailment", "neutral")
LABEL_MAP = {
    "contradiction": "contradicted",
    "entailment": "supported",
    "neutral": "insufficient",
}
CASES_PER_BUCKET = 2
MINIMUM_AGREEMENT = 4


def stableJson(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: object) -> str:
    return sha256(stableJson(value).encode()).hexdigest()


def sourceRows(path: Path) -> list[dict]:
    if sha256(path.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError(f"KLUE-NLI 원본 SHA256이 다르다: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) != 3000:
        raise ValueError("KLUE-NLI dev 원본은 사례 3,000개 배열이어야 한다")
    return data


def selectedRows(rows: list[dict]) -> list[dict]:
    selected = []
    usedPremises: set[str] = set()
    usedHypotheses: set[str] = set()
    for source in SOURCES:
        for sourceLabel in SOURCE_LABELS:
            candidates = []
            for row in rows:
                if row.get("source") != source or row.get("gold_label") != sourceLabel:
                    continue
                votes = [row.get(name) for name in ("author", "label2", "label3", "label4", "label5")]
                agreement = sum(label == sourceLabel for label in votes)
                if agreement >= MINIMUM_AGREEMENT:
                    candidates.append((sha256(row["guid"].encode()).hexdigest(), row, votes, agreement))
            for _, row, votes, agreement in sorted(candidates):
                premiseHash = sha256(row["premise"].encode()).hexdigest()
                hypothesisHash = sha256(row["hypothesis"].encode()).hexdigest()
                if premiseHash in usedPremises or hypothesisHash in usedHypotheses:
                    continue
                selected.append({"row": row, "votes": votes, "agreement": agreement})
                usedPremises.add(premiseHash)
                usedHypotheses.add(hypothesisHash)
                if (
                    sum(item["row"]["source"] == source and item["row"]["gold_label"] == sourceLabel for item in selected)
                    == CASES_PER_BUCKET
                ):
                    break
    expected = len(SOURCES) * len(SOURCE_LABELS) * CASES_PER_BUCKET
    if len(selected) != expected:
        raise ValueError(f"선택한 사례가 {expected}개여야 한다: {len(selected)}")
    return selected


def build(path: Path) -> dict:
    cases = []
    for index, selected in enumerate(selectedRows(sourceRows(path)), start=1):
        row = selected["row"]
        label = LABEL_MAP[row["gold_label"]]
        case = {
            "id": f"KEN{index:03d}",
            "sourceGuid": row["guid"],
            "domain": row["source"],
            "evidenceExcerpt": row["premise"],
            "atomicFact": row["hypothesis"],
            "goldLabel": label,
            "annotation": {
                "authorLabel": LABEL_MAP[row["author"]],
                "validatorLabels": [LABEL_MAP[value] for value in selected["votes"][1:]],
                "agreeingVotes": selected["agreement"],
                "totalVotes": 5,
            },
            "sourceUrl": SOURCE_URL,
            "revision": SOURCE_REVISION,
            "locator": row["guid"],
            "excerptSha256": sha256(row["premise"].encode()).hexdigest(),
            "factSha256": sha256(row["hypothesis"].encode()).hexdigest(),
            "license": LICENSE,
        }
        case["caseSha256"] = digest(case)
        cases.append(case)
    payload = {
        "version": 1,
        "kind": "hanlint.evidenceEntailmentBenchmark",
        "benchmarkId": "klue-nli-v1.1-dev-balanced-36",
        "source": {
            "name": "KLUE-NLI v1.1 dev",
            "repositoryUrl": REPOSITORY_URL,
            "paperUrl": PAPER_URL,
            "sourceUrl": SOURCE_URL,
            "revision": SOURCE_REVISION,
            "sourceSha256": SOURCE_SHA256,
            "license": LICENSE,
            "attribution": "KLUE Benchmark contributors",
        },
        "selection": {
            "method": "source와 원본 label별 GUID SHA256 오름차순에서 합의·중복 조건을 만족한 앞의 두 사례",
            "sources": list(SOURCES),
            "sourceLabels": list(SOURCE_LABELS),
            "labelMap": LABEL_MAP,
            "casesPerSourceLabel": CASES_PER_BUCKET,
            "minimumAgreement": MINIMUM_AGREEMENT,
            "premiseDuplicates": 0,
            "hypothesisDuplicates": 0,
        },
        "cases": cases,
    }
    payload["contentSha256"] = digest(payload)
    counts = Counter((case["domain"], case["goldLabel"]) for case in cases)
    if set(counts.values()) != {CASES_PER_BUCKET}:
        raise ValueError("source·label 묶음이 같은 수로 선택되지 않았다")
    return payload


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="고정 KLUE-NLI 판에서 hanlint 함의 평가판을 만든다")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = build(args.source)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"사례 {len(payload['cases'])}개, contentSha256 {payload['contentSha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
