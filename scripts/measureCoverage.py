"""사람 평가자의 지적과 hanlint 의 지적이 같은 자리를 짚는 비율을 잰다.

`start.product` 의 성공 지표 1번 ("사람 평가자가 집은 지적 가운데 hanlint 가 먼저 집었던 비율") 의
정본 측정이다. 기준 말뭉치가 재는 것 (편집이 끝난 글에서의 오탐률) 과 다른 축이다. hanlint 가 겨냥하는
것은 초안이므로 초안에서 사람과 얼마나 겹치는지를 따로 재야 한다.

대상은 형제 저장소 `eddmpython` 의 블로그 글 가운데 `POSTS` 가 드는 것이다. 살아 있는 저장소라 계속
고쳐지므로 작업 트리가 아니라 **고정한 판**을 `git show` 로 읽는다
(`memory/evidence/dogfoodRound3.md` 의 관례).

`--check` 는 다시 재어 기록과 글자 단위로 견준다. 형제 저장소가 없으면 잴 수 없다고 알리고 건너뛴다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from hanlint import Config  # noqa: E402
from hanlint.coverage import coverageOf, loadReview  # noqa: E402
from hanlint.document import parseMarkdown  # noqa: E402
from hanlint.fingerprint import buildFingerprint  # noqa: E402
from hanlint.rules import runAll  # noqa: E402

BLOG = (REPO / ".." / "eddmpython").resolve()
REVISION = "b6c3b075f8d8e05cb6bbd9826ffbf2511e9b6a4a"
"""고정한 판. 작업 트리가 아니라 이 판을 읽는다. 판을 올릴 때는 기록도 같이 다시 만든다."""
PRESET = "blog"
POSTS = (
    "001-ai-needs-an-environment",
    "003-python-qr",
    "005-python-history",
)
"""002 는 review 파일 꼴이 다르다 (rounds 가 아니라 edits). 004 는 고정한 판에서 rounds 가 비어 있다.
평가자 지적 114건이 형제 저장소의 커밋되지 않은 작업 트리에만 있어 고정 판으로 잴 수 없다. 그 저장소가
그것을 커밋하면 여기 다시 넣고 판을 올린다."""
ATTEMPT = REPO / "tests" / "_attempts" / "coverage"
METRICS = ATTEMPT / "coverageMetrics.json"


def readJson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def writeJson(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def atRevision(relative: str) -> str:
    """고정한 판의 파일 내용. 작업 트리의 수정을 보지 않는다."""
    done = subprocess.run(
        ["git", "-C", str(BLOG), "show", f"{REVISION}:{relative}"],
        capture_output=True,
        encoding="utf-8",
    )
    if done.returncode != 0:
        raise SystemExit(f"{relative} 을 {REVISION[:12]} 에서 읽지 못했다: {done.stderr.strip()}")
    return done.stdout


def measureOne(post: str) -> dict:
    text = atRevision(f"blog/posts/{post}/index.md")
    reviewText = atRevision(f"blog/posts/{post}/review.json")
    reviewPath = ATTEMPT / f"{post}.review.json"
    reviewPath.parent.mkdir(parents=True, exist_ok=True)
    reviewPath.write_text(reviewText, encoding="utf-8", newline="\n")
    try:
        review = loadReview(reviewPath)
    finally:
        reviewPath.unlink()
    # 지적이 빈 글을 조용히 세면 측정이 줄어든 것을 아무도 모른다. 고정한 판에 평가 기록이 없으면
    # 그 사실을 알리고 멈춘다. 실측: 004 가 고정 판에서 rounds 가 비어 0건으로 섞여 들어왔다.
    if not review:
        raise SystemExit(f"{post} 의 review 가 {REVISION[:12]} 에서 비어 있다. POSTS 에서 빼거나 판을 올린다")
    config = Config(preset=PRESET)
    doc = buildFingerprint(parseMarkdown(text, path=f"{post}/index.md"), config)
    result = coverageOf(text, runAll(doc, config), review)
    return {
        "post": post,
        "reviewFindings": result.total,
        "located": result.located,
        "covered": result.covered,
        "coveredByError": result.coveredByError,
        "byRule": [{"rule": rule, "covered": count} for rule, count in result.byRule],
        "uncaughtKinds": [
            {"kind": kind, "count": count} for kind, count in sorted(Counter(item.kind for item in result.uncaught).items())
        ],
    }


def measure() -> dict:
    posts = [measureOne(post) for post in POSTS]
    located = sum(item["located"] for item in posts)
    covered = sum(item["covered"] for item in posts)
    byRule: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    for item in posts:
        for entry in item["byRule"]:
            byRule[entry["rule"]] += entry["covered"]
        for entry in item["uncaughtKinds"]:
            kinds[entry["kind"]] += entry["count"]
    return {
        "version": 1,
        "source": {
            "repository": "eddmpython",
            "revision": REVISION,
            "preset": PRESET,
            "posts": list(POSTS),
        },
        "totals": {
            "reviewFindings": sum(item["reviewFindings"] for item in posts),
            "located": located,
            "covered": covered,
            "coveredByError": sum(item["coveredByError"] for item in posts),
            # 겹침은 줄 자리가 같다는 뜻이지 이유가 같다는 뜻이 아니다. 사람이 읽은 판정은
            # memory/evidence/coverageRound2.md 가 소유한다.
            "ratioPerMille": covered * 1000 // located if located else 0,
        },
        "posts": posts,
        "byRule": [
            {"rule": rule, "covered": count} for rule, count in sorted(byRule.items(), key=lambda item: (-item[1], item[0]))
        ],
        "uncaughtKinds": [
            {"kind": kind, "count": count} for kind, count in sorted(kinds.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="사람 평가 지적과 hanlint 지적의 겹침을 잰다")
    parser.add_argument("--check", action="store_true", help="다시 재어 기록과 글자 단위로 견준다")
    return parser.parse_args()


def main() -> int:
    args = parseArgs()
    if not (BLOG / ".git").exists():
        print(f"형제 저장소 {BLOG} 가 없어 겹침을 잴 수 없다. 건너뛴다")
        return 0
    data = measure()
    if args.check:
        if not METRICS.exists() or readJson(METRICS) != data:
            print(f"다시 재야 한다: {METRICS.relative_to(REPO)}")
            return 1
        print(f"블로그 {len(POSTS)}편의 겹침 기록이 같다")
        return 0
    writeJson(METRICS, data)
    totals = data["totals"]
    print(
        f"블로그 {len(POSTS)}편, 사람 지적 {totals['reviewFindings']}건 가운데 본문에서 찾은 인용 "
        f"{totals['located']}건, 겹침 {totals['covered']}건 ({totals['ratioPerMille'] / 10:.1f}%)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
