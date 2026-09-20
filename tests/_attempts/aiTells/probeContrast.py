"""contrast. 사람 글과 기계 글의 어절 n-gram 비율을 견줘 한국어 표지를 **직접 캔다.**

영어 목록 (`Wikipedia:Signs of AI writing`) 을 한국어로 옮기는 방식은 2회차에서 닫혔다. 어휘 항목에 대응시킨
`극대화`, `정교한`, `시너지`, `면밀` 이 기계 글에서 전부 0.00 이었다. 영어 낱말의 한국어 짝은 내가 정할 일이
아니라 세어서 알아낼 일이다.

**설계 둘.**

1. **사람 말뭉치를 장르 넷으로 둔다.** 기계 비율을 사람 최대 비율로 나눈다. 한 장르에서만 드문 말은 표지가
   아니라 그 장르의 버릇이다. 넷 모두보다 높아야 표지다.
2. **주제어를 문서 수로 거른다.** 1회차가 26편에서 실패한 것은 주제어가 표지를 덮어서였다 (`신호가`, `온도`,
   `성분`). 기계 글 240편이 주제 240개를 다루면 주제어는 한두 편에만 나오고 문체어는 여러 편에 걸쳐 나온다.
   `--min-ai` 가 그 문턱이다. 문서 수로 세므로 한 글이 같은 말을 열 번 써도 한 번이다.

이 탐침은 판정하지 않는다. 후보를 내고 고르는 것은 사람이 한다.

```console
python -X utf8 -B tests/_attempts/aiTells/probeContrast.py --ai <기계 글 폴더> --min-ai 12 --top 40
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

from hanlint.analysis import splitSentences  # noqa: E402
from hanlint.analysis.tokenize import stripJosa, words  # noqa: E402

WIKI = Path.home() / ".cache" / "hanlint" / "corpus" / "wiki" / "kowiki.jsonl"
GUIDE = Path.home() / ".cache" / "hanlint" / "corpus" / "wiki" / "kowiki.ns4-12.jsonl"
TALK = ("사랑방", "토론", "보존문서", "/보존")
MAX_N = 3
MIN_AI_DOCUMENTS = 12
"""기계 글 몇 편 이상에 나와야 후보인가. 주제어를 거르는 문턱이다.

240편이 주제 240개를 다루면 주제어는 한두 편에만, 문체어는 수십 편에 걸쳐 나온다. 12 는 전체의 5% 다."""


def grams(text: str) -> set[str]:
    """한 글의 n-gram 집합. 어절 그대로와 조사를 뗀 핵, 둘 다 센다. 문서 단위라 되풀이는 한 번이다."""
    found: set[str] = set()
    for sentence in splitSentences(text):
        surface = [word.core for word in words(sentence.text) if word.core]
        cores = [stripJosa(one) for one in surface]
        for row in (surface, cores):
            for size in range(1, MAX_N + 1):
                for start in range(len(row) - size + 1):
                    found.add(" ".join(row[start : start + size]))
    return found


def jsonlTexts(path: Path, wantTalk: bool | None = None, limit: int | None = None):
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


def census(texts) -> tuple[int, Counter]:
    counts: Counter = Counter()
    total = 0
    for text in texts:
        total += 1
        counts.update(grams(text))
    return total, counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai", type=Path, required=True)
    parser.add_argument("--wiki", type=int, default=3000)
    parser.add_argument("--guide", type=int, default=2000)
    parser.add_argument("--reports", type=int, default=200)
    parser.add_argument("--top", type=int, default=40)
    parser.add_argument("--min-ai", dest="minAi", type=int, default=MIN_AI_DOCUMENTS)
    args = parser.parse_args()

    aiTotal, aiCounts = census(folderTexts(args.ai))
    print(f"기계 {aiTotal}편, 꼴 {len(aiCounts):,}종", file=sys.stderr, flush=True)
    humans = []
    for label, texts in (
        ("백과체", jsonlTexts(WIKI, limit=args.wiki)),
        ("설명체", jsonlTexts(GUIDE, wantTalk=False, limit=args.guide)),
        ("대화체", jsonlTexts(GUIDE, wantTalk=True, limit=args.guide)),
        ("공문서체", (text for _, text in readCorpus(defaultRoot(), args.reports))),
    ):
        total, counts = census(texts)
        humans.append((label, total, counts))
        print(f"{label} {total:,}편", file=sys.stderr, flush=True)

    rows = []
    for gram, hit in aiCounts.items():
        if hit < args.minAi:
            continue
        aiShare = hit / aiTotal
        shares = [counts.get(gram, 0) / total for _, total, counts in humans]
        worst = max(shares)
        lift = aiShare / worst if worst else float("inf")
        rows.append((lift, aiShare, shares, gram))
    rows.sort(key=lambda one: (-one[0], -one[1]))

    print(f"기계 {aiTotal}편 대 사람 " + ", ".join(f"{label} {total:,}편" for label, total, _ in humans))
    print(f"기계 {args.minAi}편 이상에 나온 꼴만. 배수는 기계 비율을 사람 **최대** 비율로 나눈 값\n")
    print(f"{'꼴':<24}{'기계':>8}" + "".join(f"{label:>9}" for label, _, _ in humans) + f"{'배수':>9}")
    for lift, aiShare, shares, gram in rows[: args.top]:
        shown = f"{lift:.1f}배" if lift != float("inf") else "사람 0"
        print(f"{gram:<24}{aiShare:>7.0%}" + "".join(f"{one:>8.1%}" for one in shares) + f"{shown:>9}")


if __name__ == "__main__":
    main()
