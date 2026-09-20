"""craftLift. 실측으로 뽑은 작법서를 읽은 에이전트가 실제로 더 나은 한국어를 쓰는지 잰다.

`aiTells` 가 사람 155만 문장과 기계 360편을 견줘 일곱 줄을 뽑았다. 줄마다 배수가 붙어 있다. 그런데 **표지를
잡는 것과 글이 나아지는 것은 다르다.** 그 함정이 직전 기능 (`jointCatalog`) 을 통째로 폐기시켰다. 계약 지표는
완벽했는데 (새 지적 0, 명사 보존 1.000) 블라인드 선호에서 24 대 95 로 졌다.

그래서 순서를 못박는다. **준수를 먼저 보고 선호를 나중에 본다.**

1. `follow`: `craft` 쪽에서 일곱 줄의 표지가 실제로 줄었나. 안 줄었으면 에이전트가 지침을 안 따른 것이라
   실험이 성립하지 않는다 (무효). 이 단계에서 선호를 보지 않는다.
2. `judge`, `score`: 블라인드 선호. 주 지표다. 표지 감소는 성공이 아니다.

사전 등록과 판정 조건은 probeCraftLift_log.md 가 소유한다.

```console
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py follow <시험 폴더>
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py judge <시험 폴더> --output-dir <묶음 폴더>
python -X utf8 -B tests/_attempts/craftLift/probeCraftLift.py score <시험 폴더> --judgments <답 폴더>
```
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from hanlint import Config, buildFingerprint  # noqa: E402
from hanlint.document import parseMarkdown  # noqa: E402

ARMS = ("plain", "craft")
SEED = 42
LONG = 30
"""긴 문장의 어절 수. 사람은 4.6~15.5%, 기계는 0.2~0.3% 였다 (aiTells 4회차)."""
HUMAN_LONG = 0.046
"""사람 네 장르의 긴 문장 비율 최소치 (백과체). craft 가 이 위로 올라가야 1번 줄을 따른 것이다."""

TELLS = {
    "이유가 여기": r"이유[가는]? 여기",
    "그다음": r"그다음",
    "n 번째는": r"[첫두세네] ?번째[는,]",
    "편이 낫/좋": r"편이 [낫좋]",
    "셈이다": r"셈(이다|입니다)",
    "X가 아니라 Y다": r"[이가] 아니라[^.!?]{0,40}(이다|입니다|다\.)",
}
"""작법서 여섯 줄에 대응하는 표지. 일곱째 줄 (과하게 피하지 마라) 은 세는 것이 아니라 선호가 판정한다."""
COMPILED = {name: re.compile(pattern) for name, pattern in TELLS.items()}


def arms(root: Path) -> dict[str, dict[str, str]]:
    """{갈래: {과제 이름: 글}}. 두 갈래에 다 있는 과제만 남긴다."""
    found = {arm: {p.stem: p.read_text(encoding="utf-8") for p in sorted((root / arm).glob("*.md"))} for arm in ARMS}
    shared = set(found[ARMS[0]]) & set(found[ARMS[1]])
    return {arm: {name: text for name, text in texts.items() if name in shared} for arm, texts in found.items()}


def measure(texts: dict[str, str]) -> dict:
    """표지 비율 (천문장당) 과 긴 문장 비율."""
    config = Config(preset="blog")
    counts: Counter[str] = Counter()
    sentences = longs = 0
    lengths: list[int] = []
    for text in texts.values():
        doc = buildFingerprint(parseMarkdown(text), config)
        prose = [one for one in doc.sentences if one.length > 0 and one.ending != "없음"]
        sentences += len(prose)
        lengths.extend(one.length for one in prose)
        longs += sum(one.length >= LONG for one in prose)
        for one in prose:
            for name, pattern in COMPILED.items():
                if pattern.search(one.text):
                    counts[name] += 1
    mean = statistics.fmean(lengths) if lengths else 0.0
    return {
        "글": len(texts),
        "문장": sentences,
        "표지": {name: counts[name] / sentences * 1000 if sentences else 0.0 for name in TELLS},
        "긴 문장": longs / sentences if sentences else 0.0,
        "길이 평균": mean,
        "길이 고름": statistics.pstdev(lengths) / mean if mean else 0.0,
    }


def follow(root: Path) -> str:
    found = arms(root)
    measured = {arm: measure(texts) for arm, texts in found.items()}
    lines = [f"과제 {measured['plain']['글']}개. " + ", ".join(f"{arm} 문장 {measured[arm]['문장']:,}개" for arm in ARMS), ""]
    lines.append(f"{'표지 (천문장당)':<20}{'plain':>10}{'craft':>10}{'줄었나':>12}")
    kept = 0
    for name in TELLS:
        before, after = measured["plain"]["표지"][name], measured["craft"]["표지"][name]
        mark = "줄었다" if after < before else ("같다" if after == before else "늘었다")
        kept += after < before or before == 0
        lines.append(f"{name:<20}{before:>10.2f}{after:>10.2f}{mark:>12}")
    lines.append("")
    longPlain, longCraft = measured["plain"]["긴 문장"], measured["craft"]["긴 문장"]
    lines.append(f"{'긴 문장 비율':<20}{longPlain:>9.1%}{longCraft:>10.1%}   사람 최소 {HUMAN_LONG:.1%}")
    lines.append(f"{'길이 평균 (어절)':<20}{measured['plain']['길이 평균']:>10.2f}{measured['craft']['길이 평균']:>10.2f}")
    lines.append(f"{'길이 고름':<20}{measured['plain']['길이 고름']:>10.2f}{measured['craft']['길이 고름']:>10.2f}")
    lines.append("")
    followed = kept >= len(TELLS) - 1 and measured["craft"]["긴 문장"] >= HUMAN_LONG
    lines.append("지침을 따랐다. 선호 판정으로 간다" if followed else "**지침을 안 따랐다. 사전 등록에 따라 무효다**")
    return "\n".join(lines)


def judgePrompts(root: Path, outDir: Path, batch: int) -> str:
    found = arms(root)
    names = sorted(found["plain"])
    outDir.mkdir(parents=True, exist_ok=True)
    order = []
    made = []
    for start in range(0, len(names), batch):
        chunk = names[start : start + batch]
        label = f"judge-{start // batch + 1:02d}"
        body = [
            f"# {label}",
            "",
            "같은 주제로 쓴 한국어 글 두 편을 견준다. 각 과제에서 **더 나은 한국어 산문** 하나를 고른다.",
            "내용의 정확함이 비슷하다면 읽기와 글의 힘으로 고른다. 둘이 사실상 같으면 `same` 을 낸다.",
            "글의 길이나 형식을 짐작해서 고르지 않는다. 읽어서 판단한다.",
            "",
            '답은 JSON 배열 하나로만 낸다. 항목은 {"taskId": ..., "best": "A"|"B"|"same", "why": "한 문장"} 이다.',
            "",
        ]
        for name in chunk:
            rng = random.Random(f"{SEED}-{name}")
            pair = list(ARMS)
            rng.shuffle(pair)
            order.append({"taskId": name, "order": pair})
            body.append(f"## {name}")
            body.append("")
            for tag, arm in zip("AB", pair, strict=True):
                body.append(f"### {tag}")
                body.append(" ".join(found[arm][name].split()))
                body.append("")
        (outDir / f"{label}.md").write_text("\n".join(body), encoding="utf-8", newline="\n")
        made.append(label)
    key = json.dumps({"orders": order}, ensure_ascii=False, indent=2)
    (outDir / "order.json").write_text(key, encoding="utf-8", newline="\n")
    return f"{outDir} 에 묶음 {len(made)}개와 order.json 을 썼다"


def signTest(wins: int, losses: int) -> float:
    total = wins + losses
    if total == 0:
        return 1.0
    extreme = max(wins, losses)
    return min(1.0, 2 * sum(math.comb(total, k) for k in range(extreme, total + 1)) / (2**total))


def score(root: Path, judgments: Path, orders: Path) -> str:
    order = {one["taskId"]: one["order"] for one in json.loads(orders.read_text(encoding="utf-8"))["orders"]}
    verdicts: dict[str, str] = {}
    for path in sorted(judgments.glob("*.json")):
        if path.name == "order.json":
            continue
        for item in json.loads(path.read_text(encoding="utf-8")):
            verdicts[item["taskId"]] = item["best"]
    tally: Counter[str] = Counter()
    for taskId, best in verdicts.items():
        tally[best if best == "same" else order[taskId]["AB".index(best)]] += 1
    total = sum(tally.values())
    craft, plain = tally["craft"], tally["plain"]
    lines = [f"심판 {total}건: craft {craft}, plain {plain}, same {tally['same']}"]
    if total:
        lines.append(f"승률 craft {craft / total:.1%} 대 plain {plain / total:.1%} (차 {(craft - plain) / total * 100:+.1f}%p)")
    lines.append(f"부호검정 p {signTest(craft, plain):.4f}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("follow")
    one.add_argument("root", type=Path)
    two = sub.add_parser("judge")
    two.add_argument("root", type=Path)
    two.add_argument("--output-dir", dest="outputDir", type=Path, required=True)
    two.add_argument("--batch", type=int, default=24)
    three = sub.add_parser("score")
    three.add_argument("root", type=Path)
    three.add_argument("--judgments", type=Path, required=True)
    three.add_argument("--orders", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "follow":
        print(follow(args.root))
    elif args.command == "judge":
        print(judgePrompts(args.root, args.outputDir, args.batch))
    else:
        print(score(args.root, args.judgments, args.orders))


if __name__ == "__main__":
    main()
