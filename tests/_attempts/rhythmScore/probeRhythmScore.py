"""리듬 악보 탐침. 편집된 실제 문단의 모양만 모델에게 채우게 하면 초안의 리듬이 사람 글의 분포로 옮겨 가는가.

모양이란 문단의 문장 수, 문장마다의 어절 수, 끝맺음 (다, 니다, 것이다, 요, 의문, 명령) 이다. 내용은 없다.
예시 문장을 주면 모델이 그 문장과 숫자를 결과에 옮기는 것을 writingLift 실측이 보였으므로, 베낄 것이 없는
모양만 준다. 같은 요구로 쓴 두 초안 (악보 없이 / 악보 있이) 을 재고 수만 적는다. 판정하지 않는다.

```powershell
python -X utf8 -B tests/_attempts/rhythmScore/probeRhythmScore.py score --preset blog --register 합니다 --seed 42
python -X utf8 -B tests/_attempts/rhythmScore/probeRhythmScore.py measure 초안.md --preset blog
```

악보는 말뭉치 지문 표 (scripts/derive/prints.py 가 만드는 Parquet, dependency group corpus) 에서 읽는다.
원문은 읽지 않는다. 지문 표는 말뭉치 뿌리 (corpus/catalogue.toml 의 root) 아래 prints/ 에 있다.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.fetch.corpus import corpusRoot, readCatalogue  # noqa: E402

from hanlint.config import PROFILE_OF, Config  # noqa: E402
from hanlint.document import parseMarkdown  # noqa: E402
from hanlint.fingerprint import buildFingerprint  # noqa: E402
from hanlint.report import fingerprintDict  # noqa: E402
from hanlint.rules import runAll  # noqa: E402

ENDING_LEGEND = (
    "끝맺음: 니다 = ~합니다 ~입니다, 다 = ~한다 ~이다, 것이다 = ~것입니다 ~것이다, 요 = ~해요, 의문 = 물음, 명령 = 명령이나 청유"
)
WATCHED_RULES = ("endingRepeat", "outsideProfile", "factListParagraph", "paraFragment", "longSentence")
"""리듬과 관련해 세어 보는 규칙. 악보가 바꿀 것으로 기대하는 것과 나빠질 수도 있는 것."""
ENDINGS_OF_REGISTER = {
    "합니다": {"니다", "것이다", "의문", "명령"},
    "한다": {"다", "것이다", "의문", "명령"},
    "해요": {"요", "죠", "의문", "명령"},
}
"""문체마다 악보에 들 수 있는 끝맺음. 지문 표에는 끝맺음 니다 에 문체 한다 로 찍힌 문장이 있어 (technicalDocs 33개) 문체
열만으로는 한다체 악보에 니다 문장이 섞였다."""
SHAPE_SLACK = 3
"""악보가 허용하는 어절 수 오차. 쓰는 법의 ±3 과 같은 값이다. 문장 길이 상한은 longSentenceMax 에서 이만큼 뺀다."""
MAX_ATTEMPTS = 5000
"""변동 계수 띠에 드는 문단 묶음을 찾는 뽑기 횟수 상한. 실측에서 수십 번 안에 찾았다."""


def printsRoot() -> Path:
    return corpusRoot(readCatalogue()) / "prints"


def paragraphShapes(
    kind: str,
    register: str,
    minSentences: int,
    maxSentences: int,
    low: float,
    high: float,
    spreadBand: tuple[float, float] | None = None,
    maxLength: int | None = None,
) -> tuple[list[dict], tuple[int, int]]:
    """그 종류와 문체의 편집 문단마다 (어절 수 목록, 끝맺음 목록) 과 문장 길이 경계. 문서와 문단 순서로 정렬해 결정적이다.

    1회차에서 악보에 든 꼬리 문장 (35어절) 이 그대로 옮겨져 error 를 만들었다. 그래서 그 종류 문장 길이의 low~high
    백분위 안에 모든 문장이 드는 문단만 남긴다. 경계는 같은 문체의 문장 전체에서 잰다.

    문서의 다수 문체가 맞아도 다른 문체의 문단이 섞여 있다. 그 문단을 악보로 주면 문체를 바꾸라는 지시가 되므로
    평서문의 문체가 전부 요청한 문체인 문단만 남긴다 (의문과 명령은 문체가 없음 으로 찍힌다).
    """
    import polars as pl

    root = printsRoot()
    docs = pl.read_parquet(root / "documents.parquet").filter((pl.col("type") == kind) & (pl.col("register") == register))
    ids = docs["docId"].to_list()
    sentences = (
        pl.read_parquet(root / "sentences.parquet")
        .filter(pl.col("docId").is_in(ids) & (pl.col("ending") != "없음"))
        .sort(["docId", "index"])
        .with_columns(pl.col("register").is_in([register, "없음"]).alias("fits"))
    )
    fitting = sentences.filter(pl.col("fits"))["length"]
    upper = int(fitting.quantile(high))
    if maxLength is not None:
        # report 의 p95 는 33어절로 longSentenceMax 30 을 넘는다. 악보가 시키는 문장을 hanlint 가 잡으면 안 된다.
        upper = min(upper, maxLength)
    bounds = (int(fitting.quantile(low)), upper)
    grouped = sentences.group_by(["docId", "paragraphIndex"], maintain_order=True).agg(
        [pl.col("length").alias("lengths"), pl.col("ending").alias("endings"), pl.col("fits").all().alias("sameRegister")]
    )
    rows = [
        {"docId": row["docId"], "paragraphIndex": row["paragraphIndex"], "lengths": row["lengths"], "endings": row["endings"]}
        for row in grouped.iter_rows(named=True)
        if row["sameRegister"]
        and set(row["endings"]) <= ENDINGS_OF_REGISTER[register]
        and minSentences <= len(row["lengths"]) <= maxSentences
        and all(bounds[0] <= length <= bounds[1] for length in row["lengths"])
    ]
    rows.sort(key=lambda row: (row["docId"], row["paragraphIndex"]))
    if spreadBand is not None:
        # 2회차에서 꼬리를 자르자 다양성도 잘렸다 (변동 계수 0.31, 사람 띠 0.36~0.51). 문단 안 문장 길이의 퍼짐 (표준편차) 이
        # 그 종류 문단들 가운데 가운데 띠에 드는 문단만 남겨, 고른 문단도 들쭉날쭉한 문단도 빼고 전형적인 퍼짐을 준다.
        spreads = sorted(statistics.pstdev(row["lengths"]) for row in rows)
        lowSpread = spreads[int(spreadBand[0] * (len(spreads) - 1))]
        highSpread = spreads[int(spreadBand[1] * (len(spreads) - 1))]
        rows = [row for row in rows if lowSpread <= statistics.pstdev(row["lengths"]) <= highSpread]
    return rows, bounds


def documentCvBand(kind: str, register: str, minSentences: int = 8) -> tuple[float, float]:
    """편집된 문서들의 문장 길이 변동 계수 25~75 백분위. 사람 띠다.

    문단 하나의 퍼짐을 가운데 띠로 맞춰도 (spreadBand) 악보 전체의 변동 계수는 사람 띠 아래였다 (3회차 악보 여섯 가운데
    넷이 0.19~0.30). 변동 계수는 문단 사이의 차이에서도 나오므로 뽑은 문단 묶음 전체를 이 띠에 맞춘다.
    """
    import polars as pl

    root = printsRoot()
    docs = pl.read_parquet(root / "documents.parquet").filter((pl.col("type") == kind) & (pl.col("register") == register))
    perDoc = (
        pl.read_parquet(root / "sentences.parquet")
        .filter(pl.col("docId").is_in(docs["docId"].to_list()) & (pl.col("ending") != "없음"))
        .group_by("docId")
        .agg([pl.col("length").std(ddof=0).alias("sd"), pl.col("length").mean().alias("mean"), pl.len().alias("n")])
        .filter(pl.col("n") >= minSentences)
    )
    cvs = sorted((perDoc["sd"] / perDoc["mean"]).to_list())
    return cvs[int(0.25 * (len(cvs) - 1))], cvs[int(0.75 * (len(cvs) - 1))]


def fillBudget(shapes: list[dict], budget: float, rng: random.Random) -> list[dict]:
    """요구 길이를 어절 예산으로 바꿔 채워질 때까지 문단을 뽑는다. 2회차에서 문단 다섯을 고정하자 한 편이 요구 길이를 넘었다."""
    pool = shapes[:]
    rng.shuffle(pool)
    picked: list[dict] = []
    total = 0
    for shape in pool:
        if total >= budget:
            break
        picked.append(shape)
        total += sum(shape["lengths"])
    # 넘치는 쪽으로만 맞추면 예산을 크게 넘는다 (첫 생성에서 blog 한 악보가 202/125). 마지막 문단을 넣어 넘친 폭이
    # 빼서 모자란 폭보다 크면 뺀다.
    last = sum(picked[-1]["lengths"])
    if len(picked) > 1 and total - budget > budget - (total - last):
        picked.pop()
    return picked


def renderScore(shapes: list[dict], preset: str, register: str, bounds: tuple[int, int], targetChars: int | None = None) -> str:
    """모델이 읽는 악보. 문단마다 한 줄, 문장마다 어절 수와 끝맺음."""
    words = sum(sum(shape["lengths"]) for shape in shapes)
    lines = [
        f"리듬 악보 ({preset} 종류, {register}체). 편집된 실제 글에서 뽑은 문단 {len(shapes)}개의 모양이다. "
        f"내용은 없고 문장마다 어절 수와 끝맺음만 있다. 문장 길이는 이 종류의 흔한 범위 ({bounds[0]}~{bounds[1]}어절) 안이다.",
    ]
    if targetChars:
        lines.append(f"문단 수와 총 어절 (약 {words}어절) 은 요구 길이 {targetChars}자에 맞춰 놓았다. 문단을 더 만들지 않는다.")
    lines += [ENDING_LEGEND, ""]
    for number, shape in enumerate(shapes, start=1):
        beats = " · ".join(f"{length}어절 ({ending})" for length, ending in zip(shape["lengths"], shape["endings"], strict=True))
        lines.append(f"문단 {number}: {beats}")
    lines.append("")
    lines.append(
        "쓰는 법: 본문 문단을 이 순서의 모양으로 쓴다. 문단마다 문장 수를 맞추고, 문장 길이는 어절 수의 ±3 안에서 따르고, "
        "끝맺음의 종류를 그 자리에 둔다. "
        + ("본문 문단은 악보의 문단 수와 같게 쓴다. " if targetChars else "문단이 더 필요하면 악보를 처음부터 다시 쓴다. ")
        + "악보는 모양일 뿐이고 사실과 순서는 요구를 따른다."
    )
    return "\n".join(lines)


def score(args: argparse.Namespace) -> int:
    kind = PROFILE_OF[args.preset]
    if kind is None:
        raise SystemExit(f"{args.preset} 은 종류 프로파일이 없어 악보를 뽑을 수 없다")
    band = (args.spreadBand[0], args.spreadBand[1]) if args.spreadBand else None
    maxLength = Config(preset=args.preset).longSentenceMax - SHAPE_SLACK
    shapes, bounds = paragraphShapes(
        kind, args.register, args.minSentences, args.maxSentences, args.low, args.high, band, maxLength
    )
    if len(shapes) < args.paragraphs:
        raise SystemExit(f"{kind} {args.register} 문단이 {len(shapes)}개뿐이다. 요청 {args.paragraphs}")
    rng = random.Random(args.seed)
    cvBand = None
    if args.cvBand is not None:
        cvBand = (args.cvBand[0], args.cvBand[1]) if args.cvBand else documentCvBand(kind, args.register)
    attempts = 0
    while True:
        attempts += 1
        if args.targetChars:
            picked = fillBudget(shapes, args.targetChars / args.charsPerWord, rng)
        else:
            picked = rng.sample(shapes, args.paragraphs)
        if cvBand is None:
            break
        lengths = [length for shape in picked for length in shape["lengths"]]
        cv = statistics.pstdev(lengths) / statistics.mean(lengths)
        if cvBand[0] <= cv <= cvBand[1]:
            break
        if attempts >= MAX_ATTEMPTS:
            raise SystemExit(f"{MAX_ATTEMPTS}번 뽑아도 변동 계수 {cvBand[0]:.2f}~{cvBand[1]:.2f} 에 드는 묶음이 없다")
    print(renderScore(picked, args.preset, args.register, bounds, args.targetChars))
    documents = len({shape["docId"] for shape in shapes})
    note = f"(문장 길이 {bounds[0]}~{bounds[1]}어절 안 문단 {len(shapes)}개, 문서 {documents}편, seed {args.seed}"
    if cvBand is not None:
        note += f", 변동 계수 띠 {cvBand[0]:.2f}~{cvBand[1]:.2f} 에 {attempts}번째 뽑기"
    note += ")"
    print(note, file=sys.stderr)
    return 0


def longestRun(values: list[str]) -> int:
    best = run = 0
    previous = None
    for value in values:
        run = run + 1 if value == previous else 1
        previous = value
        best = max(best, run)
    return best


def measure(args: argparse.Namespace) -> int:
    """초안 하나의 리듬 수. 문장 길이 분포, 끝맺음 다양성, 관련 규칙의 지적 수."""
    text = Path(args.file).read_text(encoding="utf-8")
    config = Config(preset=args.preset)
    doc = buildFingerprint(parseMarkdown(text), config)
    sentences = fingerprintDict(doc, "sentences")["sentences"]
    lengths = [s["length"] for s in sentences]
    endings = [s["ending"] for s in sentences]
    findings = runAll(doc, config)
    counts = {rule: sum(1 for f in findings if f.rule == rule) for rule in WATCHED_RULES}
    result = {
        "file": Path(args.file).name,
        "preset": args.preset,
        "chars": len(text),
        "sentences": len(lengths),
        "paragraphs": len({s["paragraphIndex"] for s in sentences}),
        "lengthMedian": statistics.median(lengths) if lengths else 0,
        "lengthCv": round(statistics.pstdev(lengths) / statistics.mean(lengths), 3) if len(lengths) > 1 else 0,
        "lengthP90": sorted(lengths)[int(0.9 * (len(lengths) - 1))] if lengths else 0,
        "longestEndingRun": longestRun(endings),
        "endingKinds": len(set(endings)),
        "questions": sum(1 for s in sentences if s["mood"] == "의문"),
        "errors": sum(1 for f in findings if f.severity == "error"),
        "notices": sum(1 for f in findings if f.severity != "error"),
        **counts,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="리듬 악보 탐침")
    sub = parser.add_subparsers(dest="command", required=True)
    scoreParser = sub.add_parser("score", help="편집 문단의 모양을 악보로 뽑는다")
    scoreParser.add_argument("--preset", default="blog", choices=[name for name, kind in PROFILE_OF.items() if kind])
    scoreParser.add_argument("--register", default="합니다", choices=("합니다", "한다", "해요"))
    scoreParser.add_argument("--paragraphs", type=int, default=5)
    scoreParser.add_argument("--min-sentences", dest="minSentences", type=int, default=2)
    scoreParser.add_argument("--max-sentences", dest="maxSentences", type=int, default=6)
    scoreParser.add_argument("--seed", type=int, default=42)
    scoreParser.add_argument("--low", type=float, default=0.10, help="문장 길이 하한 백분위. 1회차의 꼬리 전달을 막는다")
    scoreParser.add_argument("--high", type=float, default=0.90, help="문장 길이 상한 백분위")
    scoreParser.add_argument(
        "--spread-band", dest="spreadBand", type=float, nargs=2, help="문단 안 문장 길이 퍼짐의 백분위 띠. 예 0.25 0.75"
    )
    scoreParser.add_argument(
        "--cv-band",
        dest="cvBand",
        type=float,
        nargs="*",
        help="뽑은 문단 묶음 전체의 문장 길이 변동 계수 띠. 값 없이 주면 그 종류 편집 문서의 25~75 백분위",
    )
    scoreParser.add_argument(
        "--target-chars", dest="targetChars", type=int, help="요구 길이 (공백 포함 글자). 주면 문단 수를 여기서 역산한다"
    )
    scoreParser.add_argument(
        "--chars-per-word",
        dest="charsPerWord",
        type=float,
        default=6.0,
        help="어절 하나가 차지하는 글자 수. 실측 초안 5.1~8.2, 말뭉치 report 4.6 blog 7.1 (코드 블록 포함)",
    )
    scoreParser.set_defaults(run=score)
    measureParser = sub.add_parser("measure", help="초안 하나의 리듬 수를 JSON 한 줄로")
    measureParser.add_argument("file")
    measureParser.add_argument("--preset", default="blog")
    measureParser.set_defaults(run=measure)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
