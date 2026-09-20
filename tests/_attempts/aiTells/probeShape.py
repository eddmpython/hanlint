"""shape. 어휘가 아니라 **문장의 꼴**로 사람 글과 기계 글이 갈리는지 잰다.

앞선 회차가 어휘에서 답을 찾았다. 영어 목록의 낱말은 한국어로 안 옮겨졌고 (2회차), 직접 캐니 낱말이 아니라
담화 수법이 나왔다 (3회차). 그러면 한 겹 더 아래, **문장을 짓는 꼴** 자체도 볼 만하다.

재는 것 여섯. 전부 주제와 문체를 안 탄다.

| 지표 | 무엇 | 왜 |
|---|---|---|
| 길이 평균 | 문장의 어절 수 | 기본 눈금 |
| 길이 고름 | 어절 수의 변동계수 (표준편차 / 평균) | **기계가 문장 길이를 고르게 쓰는가.** 사람은 한 어절과 서른 어절을 섞는다 |
| 짧은 문장 비율 | 어절 다섯 이하 | 리듬을 끊는 자리를 쓰는가 |
| 긴 문장 비율 | 어절 서른 이상 | 늘어뜨리는가 |
| 종결 고름 | 종결어미 부류의 엔트로피 | 끝을 같은 꼴로만 맺는가 |
| 문단당 문장 | 문단 하나에 문장 몇 개 | 문단을 쪼개는가 |

길이 고름이 이 탐침의 핵심 가설이다. 사람 글의 리듬은 길이의 **분산**에서 나온다는 것이 글쓰기 책들의 공통된
말인데 (`짧은 문장과 긴 문장을 섞어라`), 그 말이 실제로 사람과 기계를 가르는지는 아무도 수로 안 적었다.

```console
python -X utf8 -B tests/_attempts/aiTells/probeShape.py --ai <기계 글 폴더> --plain <한다체 폴더>
```
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
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
SHORT = 5
"""어절 몇 개 이하를 짧은 문장으로 보는가. 한 숨에 읽히는 길이다."""
LONG = 30
"""어절 몇 개 이상을 긴 문장으로 보는가. longSentence 규칙의 기본 임계와 같은 자리다."""
MIN_SENTENCES = 5
"""글 하나가 이 수보다 적으면 꼴을 재지 않는다. 문장 둘로는 고름을 못 잰다."""


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


def entropy(counts: Counter) -> float:
    """종결어미 부류의 섀넌 엔트로피 (bit). 한 꼴로만 맺으면 0 이다."""
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    return -sum((n / total) * math.log2(n / total) for n in counts.values() if n)


def shapeOf(text: str, config: Config) -> dict | None:
    """글 하나의 꼴. 산문 문장만 본다. 문장이 모자라면 None.

    종결어미가 없는 줄 (제목, 항목명, 표의 칸) 을 뺀다. 짧은 제목과 긴 산문을 한 분포에 넣으면 길이 변동이
    부풀려져 리듬이 아니라 문서 구조를 재게 된다. 실측: 안 빼고 쟀을 때 사람 변동계수가 0.57~0.89 였는데
    앞선 리듬 탐침 (tests/_attempts/rhythmScore) 이 편집된 글에서 잰 값은 0.38~0.51 이었다. 그 차이가 제목이다.
    """
    doc = buildFingerprint(parseMarkdown(text), config)
    prose = [one for one in doc.sentences if one.length > 0 and one.ending != "없음"]
    if len(prose) < MIN_SENTENCES:
        return None
    lengths = [one.length for one in prose]
    mean = statistics.fmean(lengths)
    perParagraph = Counter(one.paragraphIndex for one in prose)
    return {
        "mean": mean,
        "even": statistics.pstdev(lengths) / mean if mean else 0.0,
        "short": sum(one <= SHORT for one in lengths) / len(lengths),
        "long": sum(one >= LONG for one in lengths) / len(lengths),
        "endings": entropy(Counter(one.ending for one in prose)),
        "perParagraph": statistics.fmean(perParagraph.values()) if perParagraph else 0.0,
    }


def profile(label: str, texts, config: Config) -> tuple[str, int, dict]:
    rows = [found for text in texts if (found := shapeOf(text, config)) is not None]
    if not rows:
        return label, 0, {}
    return label, len(rows), {key: statistics.fmean(row[key] for row in rows) for key in rows[0]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai", type=Path, required=True, help="기계 글 폴더 (합니다체)")
    parser.add_argument("--plain", type=Path, default=None, help="기계 글 폴더 (한다체). 문체 교란을 가르는 자리")
    parser.add_argument("--wiki", type=int, default=2000)
    parser.add_argument("--guide", type=int, default=1200)
    parser.add_argument("--reports", type=int, default=150)
    args = parser.parse_args()

    cases = [
        ("백과체", jsonlTexts(WIKI, limit=args.wiki), Config(preset="encyclopedia")),
        ("설명체", jsonlTexts(GUIDE, wantTalk=False, limit=args.guide), Config(preset="encyclopedia")),
        ("대화체", jsonlTexts(GUIDE, wantTalk=True, limit=args.guide), Config(preset="encyclopedia")),
        ("공문서체", (text for _, text in readCorpus(defaultRoot(), args.reports)), Config(preset="report")),
        ("기계 합니다체", folderTexts(args.ai), Config(preset="blog")),
    ]
    if args.plain:
        cases.append(("기계 한다체", folderTexts(args.plain), Config(preset="blog")))

    measured = []
    for label, texts, config in cases:
        found = profile(label, texts, config)
        measured.append(found)
        print(f"{found[0]} {found[1]:,}편", file=sys.stderr, flush=True)

    titles = {
        "mean": "길이 평균 (어절)",
        "even": "길이 고름 (변동계수)",
        "short": f"짧은 문장 ({SHORT}어절 이하)",
        "long": f"긴 문장 ({LONG}어절 이상)",
        "endings": "종결 엔트로피 (bit)",
        "perParagraph": "문단당 문장",
    }
    print("말뭉치: " + ", ".join(f"{label} {count:,}편" for label, count, _ in measured) + "\n")
    print(f"{'지표':<24}" + "".join(f"{label:>14}" for label, _, _ in measured))
    for key, title in titles.items():
        line = f"{title:<24}"
        for _, _, found in measured:
            value = found.get(key, 0.0)
            line += f"{value:>14.1%}" if key in ("short", "long") else f"{value:>14.2f}"
        print(line)
    print("\n길이 고름은 작을수록 문장 길이가 고르다는 뜻이다. 사람 글이 크고 기계 글이 작으면 가설이 맞는다.")


if __name__ == "__main__":
    main()
