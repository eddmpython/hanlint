"""사양서 탐침. 규칙을 검출기에서 사양으로 뒤집으면 초안이 그 사양을 따르는가.

리듬 악보가 보인 것은 리듬이 아니라 원리다. 자연어 지시 (문장 길이를 다양하게) 는 안 먹히고 셀 수 있는
목표 (16어절, 16어절, 24어절) 는 먹힌다. 규칙 50개는 전부 다 쓴 글을 재는 검출기이므로, 같은 값을
쓰기 전으로 뒤집으면 사양이 된다. 검출기 "쉼표 4개, 상위 0.7%" 는 사양 "쉼표 3개 이하" 다.

순서가 있다. 사양으로 쓸 열이 종류마다 갈리지 않으면 사양서는 그 자리에서 죽는다. 그래서 spread 를
먼저 돌려 갈림을 재고, 갈리는 열만 sheet 에 넣고, 그 뒤에 글쓰기 실험을 한다. 판정하지 않고 수만 적는다.

```powershell
python -X utf8 -B tests/_attempts/specSheet/probeSpecSheet.py spread
python -X utf8 -B tests/_attempts/specSheet/probeSpecSheet.py sheet --preset blog --register 합니다 --target-chars 800
python -X utf8 -B tests/_attempts/specSheet/probeSpecSheet.py measure 초안.md --preset blog --register 합니다
```

지문 표 (scripts/derive/prints.py 가 만드는 Parquet, dependency group corpus) 만 읽는다. 원문은 안 읽는다.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.fetch.corpus import corpusRoot, readCatalogue  # noqa: E402

from hanlint.config import PRESETS, PROFILE_OF, Config  # noqa: E402
from hanlint.data.profiles import profileOf  # noqa: E402

CANDIDATES = (
    ("length", "문장 길이 (어절)", "mean"),
    ("commas", "문장당 쉼표", "mean"),
    ("euiCount", "문장당 의", "mean"),
    ("nounRun", "문장당 명사 연쇄 최대", "mean"),
    ("passives", "문장당 피동", "mean"),
    ("hedges", "문장당 헤지", "mean"),
    ("numbers", "문장당 숫자", "mean"),
    ("deixis", "문장당 지시어", "mean"),
    ("causal", "인과 표지가 있는 문장 비율", "rate"),
    ("connectorStart", "문두 접속 문장 비율", "presence"),
    ("readerCall", "독자 호명 문장 비율", "flag"),
    ("newTopics", "문장당 새 화제", "mean"),
)
"""사양 후보. 문장 지문의 열 가운데 쓰는 사람이 셀 수 있는 것만 골랐다. 화제 수 (topics) 처럼
세는 법이 모호한 것과 약속과 회수처럼 글 전체를 봐야 하는 것은 뺐다. mean 은 문장당 평균, rate 는
그 성질을 가진 문장의 비율이다. presence 는 문자열 열이 비지 않은 비율, flag 는 불리언 열의 비율이다."""

PARAGRAPH_CANDIDATES = (
    ("sentenceCount", "문단당 문장 수"),
    ("lengthStd", "문단 안 문장 길이 표준편차"),
    ("causalTotal", "문단당 인과 표지"),
    ("overlapWithPrevious", "앞 문단과의 화제 중첩"),
)

PAIRS = (
    ("blog", "합니다"),
    ("technicalDocs", "합니다"),
    ("technicalDocs", "한다"),
    ("guide", "한다"),
    ("report", "한다"),
    ("encyclopedia", "한다"),
    ("essay", "합니다"),
    ("essay", "한다"),
)
"""갈림을 잴 종류와 문체의 짝. 지문 표에서 문서 다섯 편 이상인 것만 넣었다."""

MIN_SENTENCES = 8
"""문서 단위 값을 낼 때 요구하는 최소 문장 수. 짧은 문서의 비율은 흔들린다."""

CHARS_PER_WORD = 6.0
"""어절 하나가 차지하는 글자 수. 리듬 악보 3회차의 초안 열두 편 실측 (blog 6.3~7.1, docs 5.6~5.9, report 4.6~5.3)."""


def printsRoot() -> Path:
    return corpusRoot(readCatalogue()) / "prints"


def perDocument(column: str, kind: str, how: str) -> tuple[list[float], list[str]]:
    """그 종류와 문체의 문서마다 그 열의 값 하나. mean 은 평균, rate 는 0 이 아닌 문장의 비율."""
    import polars as pl

    root = printsRoot()
    docs = pl.read_parquet(root / "documents.parquet")
    genre, register = kind
    ids = docs.filter((pl.col("type") == genre) & (pl.col("register") == register))["docId"].to_list()
    if not ids:
        return [], []
    sentences = pl.read_parquet(root / "sentences.parquet").filter(pl.col("docId").is_in(ids) & (pl.col("ending") != "없음"))
    # 열마다 자료형이 다르다. connectorStart 는 문자열 (없으면 null), readerCall 은 불리언, 나머지는 정수다.
    if how == "presence":
        value = pl.col(column).is_not_null().cast(pl.Float64)
    elif how == "flag":
        value = pl.col(column).cast(pl.Float64)
    elif how == "rate":
        value = (pl.col(column) > 0).cast(pl.Float64)
    else:
        value = pl.col(column).cast(pl.Float64)
    grouped = (
        sentences.group_by("docId")
        .agg([value.mean().alias("value"), pl.len().alias("n")])
        .filter(pl.col("n") >= MIN_SENTENCES)
        .sort("docId")
    )
    return grouped["value"].to_list(), grouped["docId"].to_list()


def separation(byPair: dict[tuple[str, str], list[float]]) -> float:
    """갈림. 종류 사이 중앙값의 폭을 종류 안 사분위 폭의 중앙값으로 나눈 값.

    1 보다 크면 종류 사이 차이가 종류 안 흔들림보다 크다는 뜻이고, 그때만 사양으로 쓸 값이 된다.
    분모가 0 이면 (그 열이 어디서나 같으면) 갈림을 0 으로 둔다.
    """
    medians = []
    spreads = []
    for values in byPair.values():
        if len(values) < 5:
            continue
        ordered = sorted(values)
        medians.append(statistics.median(ordered))
        spreads.append(ordered[int(0.75 * (len(ordered) - 1))] - ordered[int(0.25 * (len(ordered) - 1))])
    if len(medians) < 2:
        return 0.0
    within = statistics.median(spreads)
    return 0.0 if within == 0 else (max(medians) - min(medians)) / within


def spread(args: argparse.Namespace) -> int:
    """사양 후보마다 종류별 값과 갈림. 갈리지 않는 열은 사양서에 넣지 않는다."""
    rows = []
    for column, label, how in CANDIDATES:
        byPair = {}
        for pair in PAIRS:
            values, _ = perDocument(column, pair, how)
            if values:
                byPair[pair] = values
        rows.append(
            {
                "column": column,
                "label": label,
                "how": how,
                "separation": round(separation(byPair), 2),
                "byPair": {
                    f"{genre}/{register}": round(statistics.median(values), 3) for (genre, register), values in byPair.items()
                },
            }
        )
    rows.sort(key=lambda row: -row["separation"])
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False))
        return 0
    header = ["열", "갈림"] + [f"{genre[:6]}/{register[:2]}" for genre, register in PAIRS]
    print("  ".join(f"{name:>12}" for name in header))
    for row in rows:
        cells = [f"{row['label'][:12]:>12}", f"{row['separation']:>12.2f}"]
        for genre, register in PAIRS:
            value = row["byPair"].get(f"{genre}/{register}")
            cells.append(f"{value:>12.2f}" if value is not None else f"{'.':>12}")
        print("  ".join(cells))
    print("\n갈림은 종류 사이 중앙값 폭을 종류 안 사분위 폭 중앙값으로 나눈 값이다. 1 미만이면 그 열은 종류를 못 가른다.")
    return 0


def pct(histogram, level: int) -> int:
    """Histogram 은 percentile 메서드를, rates 의 값은 p50 같은 키를 가진 dict 다."""
    if hasattr(histogram, "percentile"):
        return histogram.percentile(level)
    return histogram[f"p{level}"]


def sheetRows(preset: str, targetChars: int | None) -> list[tuple[str, str]]:
    """사양서의 줄. 규칙이 값을 가진 자리는 규칙이 이기고, 없는 자리만 말뭉치 백분위가 채운다.

    말뭉치는 서술이고 규칙은 규범이라 둘이 어긋나는 자리가 있다. 실측 (2026-09-02): blog 말뭉치 열 편
    가운데 다섯 편, guide 백서른다섯 편 가운데 백열여덟 편이 절 둘 이상에 물음표가 0 이라 자기 프리셋의
    noQuestion 에 걸린다. 말뭉치 값을 그대로 사양으로 쓰면 규칙과 반대되는 지시를 낸다. 규칙을 먼저 놓는다.
    """
    kind = PROFILE_OF[preset]
    if kind is None:
        raise SystemExit(f"{preset} 은 종류 프로파일이 없어 사양서를 낼 수 없다")
    profile = profileOf(kind)
    config = Config(preset=preset)
    sentence = profile.sentence
    rates = profile.rates
    perParagraph = pct(profile.paragraph["sentenceCount"], 50)
    highParagraph = pct(profile.paragraph["sentenceCount"], 90)
    lengthP50 = pct(sentence["length"], 50)
    rows: list[tuple[str, str]] = []

    if targetChars:
        sentences = max(1, round(targetChars / CHARS_PER_WORD / lengthP50))
        paragraphs = max(1, round(sentences / perParagraph))
        rows.append(("분량", f"문단 {paragraphs}개, 문단마다 문장 {perParagraph}~{highParagraph}개, 문장 {sentences}개 안팎"))
    else:
        rows.append(("분량", f"문단마다 문장 {perParagraph}~{highParagraph}개"))

    rows.append(
        ("문장 길이", f"중앙 {lengthP50}어절, 대부분 {pct(sentence['length'], 90)} 이하, {config.longSentenceMax} 넘기지 않는다")
    )
    rows.append(("끝맺음", f"같은 끝맺음이 연속 {config.endingRun}개를 넘지 않는다"))
    rows.append(
        (
            "쉼표",
            f"문장당 {pct(sentence['commas'], 50)}~{pct(sentence['commas'], 90)}개, {pct(sentence['commas'], 99)} 넘기지 않는다",
        )
    )
    rows.append(("의", f"문장당 {pct(sentence['euiCount'], 50)}~{pct(sentence['euiCount'], 90)}개, 한 문장에 3 넘기지 않는다"))
    rows.append(("명사 연쇄", f"최대 {pct(sentence['nounRun'], 90)}개, {config.nounPileMin} 넘기지 않는다"))
    rows.append(
        ("문두 접속", f"문장의 {pct(rates['connector'], 50) * 100:.0f}%, {pct(rates['connector'], 90) * 100:.0f}% 넘기지 않는다")
    )
    rows.append(("지시어", f"문장의 {pct(rates['deixis'], 50) * 100:.0f}%, {pct(rates['deixis'], 90) * 100:.0f}% 넘기지 않는다"))
    numbers = (pct(sentence["numbers"], 50), pct(sentence["numbers"], 90))
    if numbers != (0, 0):
        # docs 는 두 값이 다 0 이라 이 줄이 아무것도 말하지 않는다. 말하지 않는 줄은 사양서에 두지 않는다.
        rows.append(("숫자", f"문장당 {numbers[0]}~{numbers[1]}개"))

    if "noQuestion" not in PRESETS[preset]:
        corpus = pct(rates["question"], 50)
        note = " (말뭉치 중앙값은 0% 라 규칙과 어긋난다. 규칙을 따른다)" if corpus == 0 else ""
        rows.append(("물음표", f"글 전체에 최소 1개{note}"))
    return rows


def sheet(args: argparse.Namespace) -> int:
    """쓰기 전에 읽는 숫자 사양서. 본보기도 산문 안내도 없다."""
    rows = sheetRows(args.preset, args.targetChars)
    if args.format == "json":
        print(json.dumps({"preset": args.preset, "register": args.register, "rows": dict(rows)}, ensure_ascii=False))
        return 0
    head = f"사양서 ({args.preset} 종류, {args.register}체"
    head += f", {args.targetChars}자)" if args.targetChars else ")"
    print(head + ". 아래 수를 지키고 쓴다. 본보기는 없다.")
    width = max(len(name) for name, _ in rows)
    for name, value in rows:
        print(f"  {name:<{width}}  {value}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    spreadParser = sub.add_parser("spread", help="사양 후보 열이 종류마다 갈리는지 잰다")
    spreadParser.add_argument("--format", default="text", choices=("text", "json"))
    spreadParser.set_defaults(run=spread)

    sheetParser = sub.add_parser("sheet", help="쓰기 전에 읽는 숫자 사양서")
    sheetParser.add_argument("--preset", default="blog", choices=[name for name, kind in PROFILE_OF.items() if kind])
    sheetParser.add_argument("--register", default="합니다", choices=("합니다", "한다", "해요"))
    sheetParser.add_argument("--target-chars", dest="targetChars", type=int, help="요구 길이 (공백 포함 글자)")
    sheetParser.add_argument("--format", default="text", choices=("text", "json"))
    sheetParser.set_defaults(run=sheet)

    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
