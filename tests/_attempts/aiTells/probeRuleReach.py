"""ruleReach. 새로 넣은 규칙이 사람 글을 얼마나 잘못 짚고 기계 글을 얼마나 짚는가.

임계는 `probeDensity` 가 정했다. 여기서는 **실제 규칙을 돌려** 그 임계가 제품에서 그대로 나오는지 본다.
사전 항목 (cliche 의 이유가 여기, 그다음, 셈이다) 과 밀도 규칙 (phraseRepeat) 을 함께 센다. 설계 수와
실제 수가 다르면 설계가 아니라 구현이 틀린 것이다.

사람 쪽 수는 **오탐률**로 읽는다. 다만 사람 글에도 진짜 결함은 있으므로 0 이 목표는 아니다. 사람 쪽과
기계 쪽이 자릿수로 갈리는지, 그리고 사람 쪽에서 걸린 실물이 읽어 보아 정당한 용법인지를 본다.

```console
python -X utf8 -B tests/_attempts/aiTells/probeRuleReach.py --ai <기계 폴더> --plain <한다체 폴더>
```
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.fetch.dartReports import defaultRoot, readCorpus  # noqa: E402

from hanlint import Config, buildFingerprint  # noqa: E402
from hanlint.document import parseMarkdown  # noqa: E402
from hanlint.rules import runAll  # noqa: E402

WIKI = Path.home() / ".cache" / "hanlint" / "corpus" / "wiki" / "kowiki.jsonl"
GUIDE = Path.home() / ".cache" / "hanlint" / "corpus" / "wiki" / "kowiki.ns4-12.jsonl"
TALK = ("사랑방", "토론", "보존문서", "/보존")
NEW_CLICHES = ("이유가 여기", "그다음", "셈이다", "셈입니다")
"""이번에 넣은 사전 항목. cliche 지적 가운데 이 말이 든 것만 새 항목이다."""
KEYS = ("phraseRepeat", "cliche (새 항목)")


def jsonlTexts(path: Path, wantTalk=None, limit=None):
    seen = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if wantTalk is not None and any(one in row.get("source", "") for one in TALK) != wantTalk:
                continue
            seen += 1
            if limit is not None and seen > limit:
                return
            yield row.get("text", "")


def folderTexts(folder: Path):
    for path in sorted(folder.rglob("*.md")):
        yield path.read_text(encoding="utf-8")


def reach(texts, config: Config) -> dict:
    documents = 0
    hitDocs: Counter[str] = Counter()
    samples: dict[str, list[str]] = {}
    for text in texts:
        doc = buildFingerprint(parseMarkdown(text), config)
        documents += 1
        seen = set()
        for finding in runAll(doc, config):
            if finding.rule == "phraseRepeat":
                key = KEYS[0]
            elif finding.rule == "cliche" and any(one in finding.why for one in NEW_CLICHES):
                key = KEYS[1]
            else:
                continue
            seen.add(key)
            if len(samples.setdefault(key, [])) < 3:
                samples[key].append(" ".join(finding.quote.split())[:110])
        hitDocs.update(seen)
    return {"documents": documents, "hitDocs": hitDocs, "samples": samples}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai", type=Path, required=True)
    parser.add_argument("--plain", type=Path, default=None)
    parser.add_argument("--wiki", type=int, default=2000)
    parser.add_argument("--guide", type=int, default=1500)
    parser.add_argument("--reports", type=int, default=150)
    args = parser.parse_args()

    cases = [
        ("백과체", jsonlTexts(WIKI, limit=args.wiki), Config(preset="encyclopedia")),
        ("설명체", jsonlTexts(GUIDE, wantTalk=False, limit=args.guide), Config(preset="encyclopedia")),
        ("대화체", jsonlTexts(GUIDE, wantTalk=True, limit=args.guide), Config(preset="encyclopedia")),
        ("공문서체", (t for _, t in readCorpus(defaultRoot(), args.reports)), Config(preset="report")),
        ("기계 합니다체", folderTexts(args.ai), Config(preset="blog")),
    ]
    if args.plain:
        cases.append(("기계 한다체", folderTexts(args.plain), Config(preset="blog")))

    measured = []
    for label, texts, config in cases:
        found = reach(texts, config)
        measured.append((label, found))
        print(f"{label} {found['documents']:,}편", file=sys.stderr, flush=True)

    print("글 하나에 그 규칙이 한 번이라도 걸린 비율\n")
    print(f"{'말뭉치':<16}{'글':>8}" + "".join(f"{k:>18}" for k in KEYS))
    for label, found in measured:
        row = f"{label:<16}{found['documents']:>8,}"
        for key in KEYS:
            row += f"{found['hitDocs'][key] / found['documents']:>18.2%}"
        print(row)

    humanDocs = sum(f["documents"] for label, f in measured if not label.startswith("기계"))
    machineDocs = sum(f["documents"] for label, f in measured if label.startswith("기계"))
    print("\n사람 전체 대 기계 전체")
    for key in KEYS:
        human = sum(f["hitDocs"][key] for label, f in measured if not label.startswith("기계")) / humanDocs
        machine = sum(f["hitDocs"][key] for label, f in measured if label.startswith("기계")) / machineDocs
        ratio = machine / human if human else float("inf")
        shown = f"{ratio:.0f}배" if ratio != float("inf") else "사람 0"
        print(f"  {key:<18}사람 {human:.2%} 대 기계 {machine:.2%}  ({shown})")

    print("\n사람 글에서 걸린 실물 (오탐인지 정탐인지는 읽어서 판단한다)")
    for label, found in measured:
        if label.startswith("기계"):
            continue
        for key, rows in found["samples"].items():
            for one in rows[:2]:
                print(f"  [{label} {key}] {one}")


if __name__ == "__main__":
    main()
