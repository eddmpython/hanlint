"""사업보고서 말뭉치 (scripts/fetch/dartReports.py 가 받은 것) 에서 문장 프로파일과 규칙 지적률과 명사 연쇄 빈도를 잰다.

용례 엔진 (usage) 의 1단계 실측이다. 숫자는 mainPlan 과 규칙 docstring 에 옮겨 적고, 이 스크립트는 그 숫자를 다시
낼 수 있게 남는다. 무엇을 재나:

- 프로파일: 문장 길이 (어절), 쉼표, 명사 연속 길이, `의` 수의 분포.
- 지적률: report 프리셋으로 규칙을 돌려 1,000문장당 지적 수. 용례를 보지 않는 설정 (usageKind "") 으로도 한 번 더 돌려
  같은 문서에서 용례가 접은 만큼을 보인다.
- 명사 연쇄: `nounRuns` 가 뽑은 연쇄의 출현 수와 문서 수. nounPileMin 이상인 연쇄는 따로 센다.
- 용례 접기 예상: 연쇄가 다른 문서 몇 편에 나오면 (leave-one-out) nounPile 지적 가운데 몇 건이 접히는지.
- 중복: 같은 문장이 둘 이상의 문서에 나오는 비율. 정형 문장은 색인에서 눌러야 한다.
- 사전 항목: 산문 사전 (translationese, cliches, redundantPair, japaneseLoan, easyWords) 의 항목마다 나온 문서 수와
  문장 수. 어느 항목이 그 종류의 관용인지 (문서 절반 넘게 나오는지) 가 여기서 보인다.

결과 JSON 은 --output 으로 준 자리 (저장소 밖) 에 쓰고 요약을 표준 출력에 찍는다.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.fetch.dartReports import defaultRoot, readCorpus  # noqa: E402

from hanlint import Config, fingerprint  # noqa: E402
from hanlint.analysis import nounRuns  # noqa: E402
from hanlint.fingerprint.dictionaries import builtinEntries  # noqa: E402
from hanlint.rules import runAll  # noqa: E402

SPACE = re.compile(r"\s+")
TOP = 50
ATTEST_LEVELS = (2, 3, 5, 10, 20)
PROSE_DICTIONARIES = ("translationese", "cliches", "redundantPair", "japaneseLoan", "easyWords")
"""연쇄가 다른 문서 몇 편에 나와야 용례로 볼지 견줄 후보. 결과가 usageMin 의 기본값을 정한다."""


def percentile(values: list[int], share: float) -> int:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * share))] if ordered else 0


def normalized(text: str) -> str:
    return SPACE.sub(" ", text).strip()


def measure(root: Path, limit: int | None) -> dict:
    config = Config(preset="report", enforceStyle=["nounPile"])
    plain = Config(preset="report", enforceStyle=["nounPile"], usageKind="")
    lengths: list[int] = []
    commas: list[int] = []
    nounRunHistogram: Counter[int] = Counter()
    euiHistogram: Counter[int] = Counter()
    ruleCounts: Counter[str] = Counter()
    plainCounts: Counter[str] = Counter()
    ruleDocuments: defaultdict[str, set[str]] = defaultdict(set)
    chainCounts: Counter[tuple[str, ...]] = Counter()
    chainDocuments: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
    pileChains: list[tuple[str, tuple[str, ...]]] = []
    sentenceDocuments: defaultdict[str, set[str]] = defaultdict(set)
    sentenceOccurrences: Counter[str] = Counter()
    ruleSamples: defaultdict[str, list[str]] = defaultdict(list)
    entries = [entry for entry in builtinEntries() if entry.dictionary in PROSE_DICTIONARIES]
    patternDocuments: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    patternSentences: Counter[tuple[str, str]] = Counter()
    documents = 0
    paragraphs = 0
    started = time.perf_counter()
    for rceptNo, text in readCorpus(root, limit):
        documents += 1
        lines = text.splitlines()
        paragraphs += len(lines)
        doc = fingerprint("\n\n".join(lines), config)
        for sentence in doc.sentences:
            lengths.append(sentence.length)
            commas.append(sentence.commas)
            nounRunHistogram[min(sentence.nounRun, 10)] += 1
            euiHistogram[min(sentence.euiCount, 5)] += 1
            key = normalized(sentence.text)
            sentenceDocuments[key].add(rceptNo)
            sentenceOccurrences[key] += 1
            for entry in entries:
                if entry.pattern.search(sentence.text):
                    key = (entry.dictionary, entry.pattern.pattern)
                    patternDocuments[key].add(rceptNo)
                    patternSentences[key] += 1
            for chain, length in nounRuns(sentence.text):
                if length < 2:
                    continue
                key = tuple(chain)
                chainCounts[key] += 1
                chainDocuments[key].add(rceptNo)
                if length >= config.nounPileMin:
                    pileChains.append((rceptNo, key))
        for finding in runAll(doc, plain):
            plainCounts[finding.rule] += 1
        for finding in runAll(doc, config):
            ruleCounts[finding.rule] += 1
            ruleDocuments[finding.rule].add(rceptNo)
            if len(ruleSamples[finding.rule]) < 5:
                ruleSamples[finding.rule].append(finding.quote[:120])
        print(f"{documents} {rceptNo} 문장 {len(doc.sentences)}", file=sys.stderr)
    sentences = len(lengths)
    perThousand = {rule: round(count * 1000 / sentences, 1) for rule, count in ruleCounts.most_common()}
    duplicatedOccurrences = sum(count for key, count in sentenceOccurrences.items() if len(sentenceDocuments[key]) >= 2)
    folded = {}
    for level in ATTEST_LEVELS:
        kept = sum(1 for rceptNo, chain in pileChains if len(chainDocuments[chain] - {rceptNo}) >= level)
        folded[str(level)] = {"folded": kept, "share": round(kept / len(pileChains), 3) if pileChains else 0}
    topChains = [
        {"chain": " ".join(chain), "count": count, "documents": len(chainDocuments[chain])}
        for chain, count in chainCounts.most_common(TOP)
    ]
    pileCounter = Counter(chain for _, chain in pileChains)
    topPiles = [
        {"chain": " ".join(chain), "count": count, "documents": len(chainDocuments[chain])}
        for chain, count in pileCounter.most_common(TOP)
    ]
    return {
        "documents": documents,
        "paragraphs": paragraphs,
        "sentences": sentences,
        "seconds": round(time.perf_counter() - started, 1),
        "length": {
            "mean": round(statistics.fmean(lengths), 1),
            "median": statistics.median(lengths),
            "p90": percentile(lengths, 0.9),
            "max": max(lengths),
            "overLongSentenceMax": round(sum(1 for value in lengths if value > config.longSentenceMax) / sentences, 3),
        },
        "commas": {"mean": round(statistics.fmean(commas), 2), "p90": percentile(commas, 0.9)},
        "nounRun": {str(key): value for key, value in sorted(nounRunHistogram.items())},
        "nounRunAtLeastMin": round(sum(v for k, v in nounRunHistogram.items() if k >= config.nounPileMin) / sentences, 3),
        "eui": {str(key): value for key, value in sorted(euiHistogram.items())},
        "rules": {
            rule: {
                "count": ruleCounts[rule],
                "perThousand": perThousand[rule],
                "documents": len(ruleDocuments[rule]),
                "withoutUsage": round(plainCounts[rule] * 1000 / sentences, 1),
            }
            for rule in sorted(set(perThousand) | set(plainCounts), key=lambda rule: -plainCounts[rule])
        },
        "ruleSamples": dict(ruleSamples),
        "chains": {"distinct": len(chainCounts), "top": topChains},
        "piles": {"occurrences": len(pileChains), "distinct": len(pileCounter), "top": topPiles, "foldedByLevel": folded},
        "patterns": {
            f"{dictionary}: {pattern}": {
                "documents": len(patternDocuments[(dictionary, pattern)]),
                "documentShare": round(len(patternDocuments[(dictionary, pattern)]) / documents, 3),
                "sentences": patternSentences[(dictionary, pattern)],
                "perThousand": round(patternSentences[(dictionary, pattern)] * 1000 / sentences, 2),
            }
            for dictionary, pattern in sorted(patternDocuments, key=lambda key: -len(patternDocuments[key]))
        },
        "duplicates": {
            "distinctSentences": len(sentenceOccurrences),
            "occurrencesInTwoOrMoreDocuments": duplicatedOccurrences,
            "share": round(duplicatedOccurrences / sentences, 3),
        },
    }


def summary(result: dict) -> str:
    length = result["length"]
    patterns = list(result["patterns"].items())
    rules = list(result["rules"].items())
    lines = [
        f"문서 {result['documents']}편, 문단 {result['paragraphs']:,}개, 문장 {result['sentences']:,}개 ({result['seconds']}초)",
        f"길이 평균 {length['mean']} 중앙 {length['median']} p90 {length['p90']} 최대 {length['max']} 어절,"
        f" longSentenceMax 초과 {length['overLongSentenceMax']:.1%}",
        f"쉼표 평균 {result['commas']['mean']} p90 {result['commas']['p90']}",
        f"명사 연속 분포 {result['nounRun']}, nounPileMin 이상 {result['nounRunAtLeastMin']:.1%}",
        f"의 분포 {result['eui']}",
        "규칙 (1,000문장당, 용례 없이 → 있이): "
        + ", ".join(f"{rule} {item['withoutUsage']} → {item['perThousand']}" for rule, item in rules[:12]),
        f"연쇄 종류 {result['chains']['distinct']:,}, 상위: "
        + ", ".join(f"{item['chain']} ({item['count']}/{item['documents']}편)" for item in result["chains"]["top"][:10]),
        f"nounPileMin 이상 연쇄 {result['piles']['occurrences']:,}건 {result['piles']['distinct']:,}종, 상위: "
        + ", ".join(f"{item['chain']} ({item['count']}/{item['documents']}편)" for item in result["piles"]["top"][:10]),
        "다른 문서 N편에 나온 연쇄를 접으면: "
        + ", ".join(f"N={level} {item['share']:.1%}" for level, item in result["piles"]["foldedByLevel"].items()),
        f"둘 이상의 문서에 같은 문장 {result['duplicates']['share']:.1%} (종류 {result['duplicates']['distinctSentences']:,})",
        "사전 항목 (문서 비율, 1,000문장당): "
        + ", ".join(f"{key} {item['documentShare']:.0%}/{item['perThousand']}" for key, item in patterns[:15]),
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--root", type=Path, default=defaultRoot(), help="말뭉치 폴더. 기본 ~/.cache/hanlint/corpus/dart")
    parser.add_argument("--limit", type=int, default=None, help="앞에서부터 몇 편만")
    parser.add_argument("--output", type=Path, default=None, help="결과 JSON 을 쓸 자리 (저장소 밖)")
    args = parser.parse_args()
    result = measure(args.root, args.limit)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(summary(result))


if __name__ == "__main__":
    main()
