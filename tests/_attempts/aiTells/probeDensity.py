"""density. 표지 여섯을 규칙으로 만들려면 임계가 얼마여야 하는가. 그리고 낱낱으로 잡을지 밀도로 잡을지.

집계 비율은 임계가 못 된다. 사람 7.05 대 기계 65.55 (천문장당) 는 말뭉치 전체를 하나로 뭉갠 수다. 규칙은 글
하나를 보고 판정하므로 **글마다의 분포**를 알아야 한다.

**가르는 물음 둘.**

1. 사람 글에서 이 꼴이 얼마나 드문가. 십만 문장에 한 번이면 한 번 나온 것만으로도 짚을 만하다.
   백 문장에 한 번이면 낱낱으로 짚는 것은 정당한 용법을 때리는 짓이고 밀도로 가야 한다.
2. 밀도로 간다면 임계가 어디인가. 사람 쪽 위 꼬리와 기계 쪽 아래 꼬리가 겹치지 않는 자리다.

문장이 MIN_SENTENCES 개 아래인 글은 비율이 튀어 빼고, 제목과 항목명은 산문이 아니라 뺀다.

```console
python -X utf8 -B tests/_attempts/aiTells/probeDensity.py --ai <기계 폴더> --plain <한다체 폴더>
```
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.fetch.dartReports import defaultRoot, readCorpus  # noqa: E402

from hanlint import Config, buildFingerprint  # noqa: E402
from hanlint.document import parseMarkdown  # noqa: E402

WIKI = Path.home() / ".cache" / "hanlint" / "corpus" / "wiki" / "kowiki.jsonl"
GUIDE = Path.home() / ".cache" / "hanlint" / "corpus" / "wiki" / "kowiki.ns4-12.jsonl"
TALK = ("사랑방", "토론", "보존문서", "/보존")
MIN_SENTENCES = 8
"""글 하나가 이 수보다 적으면 비율이 튄다. 문장 셋 가운데 하나가 걸리면 33% 다."""
MIN_HITS = 2
"""되풀이로 세려면 몇 번 나와야 하는가. 비율만 보면 아홉 문장짜리 글의 한 번이 11% 라 임계를 넘는다.
한 번은 버릇이 아니다. 실측에서 이 조건 없이 재다가 규칙이 한 번 나온 자리를 짚어 고쳤다 (2026-09-20)."""

TELLS = {
    "이유가 여기": r"이유[가는]? 여기",
    "그다음": r"그다음",
    "n 번째는": r"[첫두세네] ?번째[는,]",
    "편이 낫/좋": r"편이 [낫좋]",
    "셈이다": r"셈(이다|입니다)",
    "X가 아니라 Y다": r"[이가] 아니라[^.!?]{0,40}(이다|입니다|다\.)",
}
COMPILED = {name: re.compile(pattern) for name, pattern in TELLS.items()}
CUTS = (0.02, 0.04, 0.06, 0.08, 0.10, 0.15)
"""후보 임계. 글 안에서 그 꼴이 든 산문 문장의 비율이다."""


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


def profile(texts, config: Config) -> dict:
    """{표지: [글마다의 비율]} 과 {표지: 그 꼴이 한 번이라도 든 글의 수}."""
    shares = {name: [] for name in TELLS}
    seenAny = dict.fromkeys(TELLS, 0)
    documents = 0
    sentences = 0
    for text in texts:
        doc = buildFingerprint(parseMarkdown(text), config)
        prose = [one for one in doc.sentences if one.length > 0 and one.ending != "없음"]
        if len(prose) < MIN_SENTENCES:
            continue
        documents += 1
        sentences += len(prose)
        for name, pattern in COMPILED.items():
            hit = sum(bool(pattern.search(one.text)) for one in prose)
            # 되풀이는 2회부터다. 한 번 나온 것은 짧은 글에서 비율만 높고 버릇이 아니다.
            shares[name].append(hit / len(prose) if hit >= MIN_HITS else 0.0)
            seenAny[name] += hit > 0
    return {"documents": documents, "sentences": sentences, "shares": shares, "any": seenAny}


def quantile(values, cut: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if cut >= 1:
        return ordered[-1]
    place = (len(ordered) - 1) * cut
    low = int(place)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (place - low)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai", type=Path, required=True)
    parser.add_argument("--plain", type=Path, default=None)
    parser.add_argument("--wiki", type=int, default=3000)
    parser.add_argument("--guide", type=int, default=2000)
    parser.add_argument("--reports", type=int, default=200)
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
        found = profile(texts, config)
        measured.append((label, found))
        print(f"{label} {found['documents']:,}편", file=sys.stderr, flush=True)

    humanDocs = sum(f["documents"] for label, f in measured if not label.startswith("기계"))
    machineDocs = sum(f["documents"] for label, f in measured if label.startswith("기계"))
    print(f"사람 {humanDocs:,}편, 기계 {machineDocs:,}편 (산문 문장 {MIN_SENTENCES}개 이상인 글만)\n")

    print("## 낱낱으로 짚어도 되나. 그 꼴이 한 번이라도 든 글의 비율")
    print(f"{'표지':<16}{'사람':>10}{'기계':>10}{'배수':>9}   판단")
    for name in TELLS:
        human = sum(f["any"][name] for label, f in measured if not label.startswith("기계")) / humanDocs
        machine = sum(f["any"][name] for label, f in measured if label.startswith("기계")) / machineDocs
        ratio = machine / human if human else float("inf")
        call = "낱낱으로" if human < 0.02 else ("밀도로" if human > 0.08 else "경계")
        shown = f"{ratio:.0f}배" if ratio != float("inf") else "사람 0"
        print(f"{name:<16}{human:>10.2%}{machine:>10.2%}{shown:>9}   {call}")

    print("\n## 밀도로 간다면 임계. 그 임계를 넘는 글의 비율 (사람 / 기계)")
    print(f"{'표지':<16}" + "".join(f"{str(round(c * 100)) + '%':>16}" for c in CUTS))
    for name in TELLS:
        human = [one for label, f in measured if not label.startswith("기계") for one in f["shares"][name]]
        machine = [one for label, f in measured if label.startswith("기계") for one in f["shares"][name]]
        row = f"{name:<16}"
        for cut in CUTS:
            wrong = sum(one > cut for one in human) / len(human)
            caught = sum(one > cut for one in machine) / len(machine)
            row += f"{wrong:>7.2%}/{caught:<8.0%}"
        print(row)

    print("\n## 사람 쪽 위 꼬리 (분위수)")
    print(f"{'표지':<16}{'평균':>9}{'95%':>9}{'99%':>9}{'99.9%':>9}{'최대':>9}")
    for name in TELLS:
        human = [one for label, f in measured if not label.startswith("기계") for one in f["shares"][name]]
        mean = statistics.fmean(human) if human else 0.0
        print(
            f"{name:<16}{mean:>9.2%}{quantile(human, 0.95):>9.2%}{quantile(human, 0.99):>9.2%}"
            f"{quantile(human, 0.999):>9.2%}{quantile(human, 1):>9.2%}"
        )


if __name__ == "__main__":
    main()
