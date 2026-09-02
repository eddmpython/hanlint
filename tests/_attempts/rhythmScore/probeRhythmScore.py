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


def printsRoot() -> Path:
    return corpusRoot(readCatalogue()) / "prints"


def paragraphShapes(kind: str, register: str, minSentences: int, maxSentences: int) -> list[dict]:
    """그 종류와 문체의 편집 문단마다 (어절 수 목록, 끝맺음 목록). 문서와 문단 순서로 정렬해 결정적이다.

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
    grouped = sentences.group_by(["docId", "paragraphIndex"], maintain_order=True).agg(
        [pl.col("length").alias("lengths"), pl.col("ending").alias("endings"), pl.col("fits").all().alias("sameRegister")]
    )
    rows = [
        {"docId": row["docId"], "paragraphIndex": row["paragraphIndex"], "lengths": row["lengths"], "endings": row["endings"]}
        for row in grouped.iter_rows(named=True)
        if row["sameRegister"] and minSentences <= len(row["lengths"]) <= maxSentences
    ]
    rows.sort(key=lambda row: (row["docId"], row["paragraphIndex"]))
    return rows


def renderScore(shapes: list[dict], preset: str, register: str) -> str:
    """모델이 읽는 악보. 문단마다 한 줄, 문장마다 어절 수와 끝맺음."""
    lines = [
        f"리듬 악보 ({preset} 종류, {register}체). 편집된 실제 글에서 뽑은 문단 {len(shapes)}개의 모양이다. "
        "내용은 없고 문장마다 어절 수와 끝맺음만 있다.",
        ENDING_LEGEND,
        "",
    ]
    for number, shape in enumerate(shapes, start=1):
        beats = " · ".join(f"{length}어절 ({ending})" for length, ending in zip(shape["lengths"], shape["endings"], strict=True))
        lines.append(f"문단 {number}: {beats}")
    lines.append("")
    lines.append(
        "쓰는 법: 본문 문단을 이 순서의 모양으로 쓴다. 문단마다 문장 수를 맞추고, 문장 길이는 어절 수의 ±3 안에서 따르고, "
        "끝맺음의 종류를 그 자리에 둔다. 문단이 더 필요하면 악보를 처음부터 다시 쓴다. "
        "악보는 모양일 뿐이고 사실과 순서는 요구를 따른다."
    )
    return "\n".join(lines)


def score(args: argparse.Namespace) -> int:
    kind = PROFILE_OF[args.preset]
    if kind is None:
        raise SystemExit(f"{args.preset} 은 종류 프로파일이 없어 악보를 뽑을 수 없다")
    shapes = paragraphShapes(kind, args.register, args.minSentences, args.maxSentences)
    if len(shapes) < args.paragraphs:
        raise SystemExit(f"{kind} {args.register} 문단이 {len(shapes)}개뿐이다. 요청 {args.paragraphs}")
    picked = random.Random(args.seed).sample(shapes, args.paragraphs)
    print(renderScore(picked, args.preset, args.register))
    documents = len({shape["docId"] for shape in shapes})
    print(f"(출처 문단 {len(shapes)}개 가운데 seed {args.seed} 로 뽑음. 문서 {documents}편)", file=sys.stderr)
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
    scoreParser.set_defaults(run=score)
    measureParser = sub.add_parser("measure", help="초안 하나의 리듬 수를 JSON 한 줄로")
    measureParser.add_argument("file")
    measureParser.add_argument("--preset", default="blog")
    measureParser.set_defaults(run=measure)
    args = parser.parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
