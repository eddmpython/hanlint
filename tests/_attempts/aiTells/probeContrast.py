"""contrast. 사람 글과 AI 글의 어절 n-gram 비율을 견줘 한국어 표지를 직접 캐낸다.

영어 목록 (`Wikipedia:Signs of AI writing`) 을 한국어로 옮기는 것은 짐작이다. `delve` 에 해당하는 한국어 낱말이
무엇인지 내가 정할 일이 아니다. 두 말뭉치를 세어 **한쪽에만 몰리는 꼴**을 찾으면 옮기지 않고 알아낼 수 있다.

세는 것. 문장을 어절로 가르고 조사를 뗀 핵과 원래 어절을 둘 다 n-gram 으로 센다 (n=1,2,3). 문서 수로 세므로 한
글이 같은 말을 열 번 써도 한 번이다. AI 쪽 문서 수가 적으므로 비율로 견주고, 최소 문서 수를 넘는 것만 남긴다.

읽는 법. 비율 배수가 크고 사람 쪽 비율이 낮은 꼴이 규칙 후보다. 사람 쪽이 이미 흔하면 (천문장당 여러 건) 규칙이
될 수 없다. 이 탐침은 판정하지 않는다. 후보를 내고 고르는 것은 사람이 한다.

```console
python -X utf8 -B tests/_attempts/aiTells/probeContrast.py --ai <AI 글 폴더> --wiki 8000 --top 40
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

from hanlint.analysis import splitSentences, stripJosa, words  # noqa: E402

WIKI = Path.home() / ".cache" / "hanlint" / "corpus" / "wiki" / "kowiki.jsonl"
MAX_N = 3
MIN_AI_DOCUMENTS = 4
"""AI 글 몇 편 이상에 나와야 후보인가. 한두 편은 그 글의 주제어다."""


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


def wikiTexts(limit: int):
    with WIKI.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle):
            if number >= limit:
                break
            yield json.loads(line).get("text", "")


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
    parser.add_argument("--wiki", type=int, default=8000)
    parser.add_argument("--top", type=int, default=40)
    parser.add_argument("--min-ai", type=int, default=MIN_AI_DOCUMENTS)
    args = parser.parse_args()

    aiTotal, aiCounts = census(folderTexts(args.ai))
    print(f"AI 글 {aiTotal}편, 꼴 {len(aiCounts):,}종", file=sys.stderr, flush=True)
    humanTotal, humanCounts = census(wikiTexts(args.wiki))
    print(f"사람 글 {humanTotal:,}편, 꼴 {len(humanCounts):,}종", file=sys.stderr, flush=True)

    rows = []
    for gram, hit in aiCounts.items():
        if hit < args.min_ai:
            continue
        aiShare = hit / aiTotal
        humanShare = humanCounts.get(gram, 0) / humanTotal
        ratio = aiShare / humanShare if humanShare else float("inf")
        rows.append((ratio, aiShare, humanShare, hit, humanCounts.get(gram, 0), gram))
    rows.sort(key=lambda one: (-one[0], -one[1], one[5]))

    print(f"AI {aiTotal}편 대 사람 {humanTotal:,}편. AI {args.min_ai}편 이상에 나온 꼴만\n")
    print(f"{'꼴':<28}{'AI':>8}{'사람':>10}{'배수':>10}")
    for ratio, aiShare, humanShare, hit, humanHit, gram in rows[: args.top]:
        shown = f"{ratio:.0f}배" if ratio != float("inf") else "사람 0"
        print(f"{gram:<28}{hit}/{aiTotal:<5}{humanHit:>7,}{shown:>12}   AI {aiShare:.0%} 사람 {humanShare:.2%}")


if __name__ == "__main__":
    main()
