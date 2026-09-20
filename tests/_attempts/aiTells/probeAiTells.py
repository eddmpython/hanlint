"""aiTells. 위키백과 "Signs of AI writing" 규칙표의 한국어 대응이 실제로 사람 글과 AI 글을 가르는지 잰다.

**어디서 왔나.** 영어 위키백과의 `Wikipedia:Signs of AI writing` (CC BY-SA 4.0). 사람들이 모아 둔, AI 가 쓴 글에서
되풀이되는 표층 표지의 목록이다. 이것을 문장마다 맞춰 보고 문장과 글에 수를 매기는 도구들이 있는데, hanlint 는
점수를 내지 않으므로 **목록만** 가져오고 셈은 가져오지 않는다.

**왜 재야 하나.** 영어 규칙표의 항목을 한국어로 옮긴 것은 아직 짐작이다. `에도 불구하고` 나 `주목받고 있다` 는 사람도
쓴다. 사람 글에서 흔한 표현은 규칙이 될 수 없다. 규칙마다 사람 글의 비율을 먼저 재고, 그다음 AI 글과 견준다.

**미리 아는 위험.** 같은 재료로 한 번 실패했다. 낯선 어절 결합으로 AI 글을 가리려 했더니 사람 22.1%, AI 26~27% 로
갈리지 않았다 (tests/_attempts/usageLift). 통계량이 아니라 **어휘와 꼴** 이라 다를 것이라 보지만, 그 기대도 수로
확인해야 한다.

```console
python -X utf8 -B tests/_attempts/aiTells/probeAiTells.py human --wiki 20000 --reports 300
python -X utf8 -B tests/_attempts/aiTells/probeAiTells.py ai <글 폴더>
```
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.fetch.dartReports import defaultRoot, readCorpus  # noqa: E402

from hanlint.analysis import splitSentences  # noqa: E402

WIKI = Path.home() / ".cache" / "hanlint" / "corpus" / "wiki" / "kowiki.jsonl"

TELLS: dict[str, dict[str, str]] = {
    "부정 병렬": {
        "단순히~아니": r"단순히[^.!?]{0,40}아니",
        "단순한~아니": r"단순한[^.!?]{0,40}아니",
        "그저~아니": r"그저[^.!?]{0,40}아니",
        "에 그치지 않": r"에 그치지 않",
        "뿐만 아니라": r"뿐만 아니라",
        "이 아니라~이다": r"[이가] 아니라[^.!?]{0,40}(이다|입니다|다\.)",
    },
    "막연한 출처": {
        "전문가들": r"전문가들[은이의]",
        "업계에서는": r"업계에서는|업계에 따르면",
        "많은 사람들": r"많은 (사람들|이들)[이은]",
        "일각에서는": r"일각에서는",
        "로 평가받": r"[로으]로 평가(받|되)",
        "라는 분석/지적": r"[라다]는 (분석|지적|평가)[이가 ]",
        "알려져 있다": r"알려(져|졌) ?있",
    },
    "계사 회피": {
        "자리매김": r"자리매김",
        "역할을 한다": r"역할을 (한다|하고 있|합니다)",
        "자랑한다": r"자랑(한다|하는|합니다)",
        "선보인다": r"선보(인다|이는|입니다)",
        "꼽힌다": r"꼽(힌다|히는|히고)",
    },
    "의의 부풀리기": {
        "새로운 지평": r"새로운 지평",
        "한 획을 그": r"한 획을 그",
        "전환점": r"전환점",
        "획기적": r"획기적",
        "중추적": r"중추적",
        "핵심적인 역할": r"핵심적인 역할",
        "귀추가 주목": r"귀추가 주목",
        "주목받고 있": r"주목(받|되)고 있",
    },
    "공허한 이음절": {
        "며/면서 주목": r"(며|면서) (주목|각광)",
        "며/면서 의미를": r"(며|면서)[^.!?]{0,10}(의미를|가치를) (더|높)",
        "함으로써": r"함으로써",
    },
    "개요식 결론": {
        "에도 불구하고": r"에도 불구하고",
        "결론적으로": r"결론적으로",
        "이처럼 (문두)": r"(^|[.!?]\s*)이처럼",
        "앞으로~주목": r"앞으로[^.!?]{0,30}주목",
    },
    "AI 상용어": {
        "극대화": r"극대화",
        "시너지": r"시너지",
        "유기적": r"유기적",
        "아우르": r"아우르",
        "면밀": r"면밀",
        "정교한": r"정교한",
        "견고한": r"견고한",
        "다채로운": r"다채로운",
        "토대/발판을 마련": r"(토대|발판)를 마련",
        "뒷받침": r"뒷받침",
        "지형/지평 (비유)": r"(지형|지평)[을이가]",
    },
}
COMPILED = {group: {name: re.compile(pattern) for name, pattern in items.items()} for group, items in TELLS.items()}


def sentencesOf(text: str) -> list[str]:
    return [sentence.text for sentence in splitSentences(text)]


def wikiTexts(limit: int):
    if not WIKI.exists():
        raise SystemExit(f"{WIKI} 가 없다. scripts/fetch/koWikipedia.py 를 먼저 돌린다")
    with WIKI.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle):
            if number >= limit:
                break
            yield json.loads(line).get("text", "")


def folderTexts(folder: Path):
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() in (".txt", ".md") and path.is_file():
            yield path.read_text(encoding="utf-8")


def tally(texts) -> tuple[int, dict[str, dict[str, int]]]:
    """(문장 수, 무리별 패턴별 문장 수). 한 문장이 여러 패턴에 걸리면 각각 센다."""
    counts = {group: dict.fromkeys(items, 0) for group, items in COMPILED.items()}
    total = 0
    for text in texts:
        for sentence in sentencesOf(text):
            total += 1
            for group, items in COMPILED.items():
                for name, pattern in items.items():
                    if pattern.search(sentence):
                        counts[group][name] += 1
    return total, counts


def render(label: str, total: int, counts: dict[str, dict[str, int]]) -> str:
    lines = [f"{label}: 문장 {total:,}개", ""]
    for group, items in counts.items():
        lines.append(group)
        for name, hit in sorted(items.items(), key=lambda one: -one[1]):
            lines.append(f"  {name:<20}{hit:>8,}{hit / total * 1000:>10.2f} /천문장")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    human = sub.add_parser("human")
    human.add_argument("--wiki", type=int, default=20000)
    human.add_argument("--reports", type=int, default=300)
    ai = sub.add_parser("ai")
    ai.add_argument("folder", type=Path)
    args = parser.parse_args()
    if args.command == "human":
        parts = []
        if args.wiki:
            total, counts = tally(wikiTexts(args.wiki))
            parts.append(render(f"위키백과 {args.wiki:,}편 (사람)", total, counts))
        if args.reports:
            total, counts = tally(text for _, text in readCorpus(defaultRoot(), args.reports))
            parts.append(render(f"사업보고서 {args.reports}편 (사람)", total, counts))
        print("\n".join(parts))
    else:
        total, counts = tally(folderTexts(args.folder))
        print(render(f"{args.folder} (AI)", total, counts))


if __name__ == "__main__":
    main()
