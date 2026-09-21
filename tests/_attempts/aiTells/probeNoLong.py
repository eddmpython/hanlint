"""noLong. 긴 문장이 하나도 없는 글을 규칙으로 짚으려면 임계가 얼마여야 하는가.

4회차에서 산 구조 표지 하나가 이것이다. 사람은 서른 어절 넘는 문장을 4.6~15.5% 쓰고 기계는 0.2~0.3% 다.
그런데 집계 비율은 임계가 못 된다. 규칙은 글 하나를 보므로 **글마다 긴 문장이 몇 개인지의 분포**를 알아야 한다.

가르는 물음 둘.

1. 짧은 글은 긴 문장이 없는 것이 정상이다. 문장 몇 개부터 `하나도 없다` 가 뜻을 갖는가.
2. 그 길이에서 사람 글 가운데 긴 문장이 0인 것이 얼마나 되는가. 그 비율이 곧 오탐률이다.

`longSentence` 규칙과 거울이라 같은 임계 (config.longSentenceMax) 를 쓴다. 한 규칙이 벌하는 것을 다른 규칙이
요구하면 안 되므로 경계도 같이 본다.

```console
python -X utf8 -B tests/_attempts/aiTells/probeNoLong.py --ai <기계 폴더> --plain <한다체 폴더>
```
"""

from __future__ import annotations

import argparse
import json
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
SIZES = (8, 12, 16, 20, 30)
"""후보 최소 문장 수. 이보다 짧은 글은 긴 문장이 없어도 정상이라 안 짚는다."""


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


def profile(texts, config: Config) -> list[tuple[int, int]]:
    """글마다 (산문 문장 수, 긴 문장 수)."""
    found = []
    for text in texts:
        doc = buildFingerprint(parseMarkdown(text), config)
        prose = [one for one in doc.sentences if one.length > 0 and one.ending != "없음"]
        if not prose:
            continue
        found.append((len(prose), sum(one.length > config.longSentenceMax for one in prose)))
    return found


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
        rows = profile(texts, config)
        measured.append((label, rows))
        print(f"{label} {len(rows):,}편", file=sys.stderr, flush=True)

    print("긴 문장이 0개인 글의 비율. 가로는 최소 산문 문장 수 (그보다 짧은 글은 세지 않는다)\n")
    print(f"{'말뭉치':<16}" + "".join(f"{str(n) + '문장+':>14}" for n in SIZES))
    for label, rows in measured:
        line = f"{label:<16}"
        for size in SIZES:
            kept = [one for one in rows if one[0] >= size]
            zero = sum(one[1] == 0 for one in kept) / len(kept) if kept else 0.0
            line += f"{zero:>9.1%}({len(kept):>3})"
        print(line)

    humans = [one for label, rows in measured if not label.startswith("기계") for one in rows]
    machines = [one for label, rows in measured if label.startswith("기계") for one in rows]
    print("\n사람 전체 대 기계 전체. 오탐률은 사람 쪽 0개 비율이다")
    print(f"{'최소 문장':<12}{'사람 글':>10}{'사람 0개':>12}{'기계 글':>10}{'기계 0개':>12}{'배수':>9}")
    for size in SIZES:
        h = [one for one in humans if one[0] >= size]
        m = [one for one in machines if one[0] >= size]
        hz = sum(one[1] == 0 for one in h) / len(h) if h else 0.0
        mz = sum(one[1] == 0 for one in m) / len(m) if m else 0.0
        ratio = mz / hz if hz else float("inf")
        shown = f"{ratio:.1f}배" if ratio != float("inf") else "사람 0"
        print(f"{str(size) + '문장 이상':<12}{len(h):>10,}{hz:>12.1%}{len(m):>10,}{mz:>12.1%}{shown:>9}")


if __name__ == "__main__":
    main()
