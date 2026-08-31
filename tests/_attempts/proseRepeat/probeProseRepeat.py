"""산문 되풀이를 표층으로 가려낼 수 있나. 그리고 겹침 측정 자체가 신호를 잴 수 있나.

사람 평가자가 못 집힌 지적의 18%가 되풀이다 (2026-08-31 실측). `duplicateBlock` 이 코드 블록의
되풀이를 잡지만 산문은 아무도 안 본다. `ParagraphPrint.overlapWithPrevious` 는 같은 절 안 바로 앞
문단 하나만 보는데 사람은 절을 넘어서, 도입까지 거슬러 본다.

두 신호를 잰다.
  A. 문단 대 앞선 모든 문단의 화제 중첩 최댓값
  B. 표 블록의 화제가 바로 앞 산문 문단들에 이미 있는가

그리고 **무작위 기준선**을 함께 낸다. 대상 세 편은 문단 123개에 사람 지적 156건이라 밀도가 높다.
아무 문단에나 찍어도 coverageOf 의 줄 +-1 판정에 걸리므로, 기준선 없이 "새로 덮은 수" 를 보면
신호가 없는 것을 신호로 읽는다. 새 축을 이 지표로 재는 사람은 반드시 기준선을 같이 봐야 한다.

판정하지 않는다. 분포를 적는다. 저장소 밖에 아무것도 쓰지 않는다.
"""

from __future__ import annotations

import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import measureCoverage as mc  # noqa: E402
from hanlint import Config  # noqa: E402
from hanlint.coverage import coverageOf  # noqa: E402
from hanlint.document import parseMarkdown  # noqa: E402
from hanlint.document.model import TABLE  # noqa: E402
from hanlint.fingerprint import buildFingerprint  # noqa: E402
from hanlint.fingerprint.topics import overlap, topicsOf  # noqa: E402
from hanlint.rules import runAll  # noqa: E402
from hanlint.rules.finding import NOTICE, PARAGRAPH, Finding  # noqa: E402

MIN_TOPICS = 4
"""화제어가 이보다 적으면 견주지 않는다. 짧은 문단은 우연히 겹친다."""

WINDOW = 3
"""표가 되풀이하는지 볼 때 거슬러 보는 앞 문단 수."""

TRIALS = 400

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z0-9]+|[A-Za-z_][A-Za-z0-9_]{2,}")


def richTopics(text: str) -> frozenset[str]:
    """화제어에 식별자와 파일 이름을 더한다.

    topicsOf 의 정규식이 점과 밑줄을 막아 `make_qr`, `link.png` 를 버린다. 그런데 나란한 지시문을
    가르는 것이 바로 그 토큰이다. 맨몸 화제어로 재면 `python make_many.py 를 실행하면` 과
    `python make_print.py 를 실행하면` 이 100% 같은 문단으로 나온다 (2026-08-31 실측).
    """
    return topicsOf(text) | frozenset(m.group(0).lower() for m in IDENT.finditer(text))


def paragraphEchoes(doc, threshold: float) -> list[tuple]:
    """(뒤 문단, 앞 문단, 중첩). 절을 넘어 앞선 모든 산문 문단과 견준다."""
    found = []
    topicsFor = {p.index: richTopics(p.text) for p in doc.paragraphs}
    for later in doc.paragraphs:
        if len(topicsFor[later.index]) < MIN_TOPICS:
            continue
        best = None
        for earlier in doc.paragraphs:
            if earlier.index >= later.index or len(topicsFor[earlier.index]) < MIN_TOPICS:
                continue
            score = overlap(topicsFor[earlier.index], topicsFor[later.index])
            if best is None or score > best[1]:
                best = (earlier, score)
        if best and best[1] >= threshold:
            found.append((later, best[0], best[1]))
    return found


def tableEchoes(doc, threshold: float) -> list[tuple]:
    """(표 블록, 첫 자료 행 줄, 앞 문단에 이미 있던 화제 비율)."""
    found = []
    for block in doc.blocks:
        if block.kind != TABLE:
            continue
        rows = block.text.split("\n")
        firstRow = next((i for i, line in enumerate(rows) if i >= 2 and line.strip().startswith("|")), None)
        if firstRow is None:
            continue
        topics = richTopics(block.text)
        if len(topics) < MIN_TOPICS:
            continue
        before = [p for p in doc.paragraphs if p.endLine < block.startLine][-WINDOW:]
        if not before:
            continue
        known: set[str] = set()
        for paragraph in before:
            known |= richTopics(paragraph.text)
        share = len(topics & known) / len(topics)
        if share >= threshold:
            found.append((block, block.startLine + firstRow, share))
    return found


def asFindings(doc, paragraphThreshold: float, tableThreshold: float) -> list[Finding]:
    """두 신호를 Finding 꼴로. coverageOf 에 그대로 먹이려는 것이지 규칙이 아니다."""
    out = []
    for later, earlier, score in paragraphEchoes(doc, paragraphThreshold):
        out.append(
            Finding(
                "proseRepeat",
                later.startLine,
                later.sentences[0].text[:40] if later.sentences else "",
                f"{earlier.startLine}행 문단과 화제가 {score:.0%} 겹친다",
                None,
                NOTICE,
                PARAGRAPH,
                later.index,
            )
        )
    for block, line, share in tableEchoes(doc, tableThreshold):
        out.append(
            Finding(
                "tableRepeat",
                line,
                "|",
                f"표의 화제 {share:.0%} 가 바로 앞 문단 {WINDOW}개에 이미 있다",
                None,
                NOTICE,
                PARAGRAPH,
                block.index,
            )
        )
    return out


def prepare() -> list[tuple]:
    config = Config(preset="blog")
    prepared = []
    for post in mc.POSTS:
        text = mc.atRevision(f"blog/posts/{post}/index.md")
        raw = mc.atRevision(f"blog/posts/{post}/review.json")
        tmp = mc.ATTEMPT / "probeReview.json"
        tmp.write_text(raw, encoding="utf-8")
        try:
            review = mc.loadReview(tmp)
        finally:
            tmp.unlink()
        doc = buildFingerprint(parseMarkdown(text, path=post), config)
        base = list(runAll(doc, config))
        prepared.append((post, text, review, doc, base, coverageOf(text, base, review).covered))
    return prepared


def randomBaseline(prepared, fireCount: int, rng: random.Random) -> tuple[float, int]:
    """발화 N 개를 문단 첫 줄에 무작위로 찍었을 때 덮는 지적 수. (평균, 95분위)."""
    totalParagraphs = sum(len(d.paragraphs) for _, _, _, d, _, _ in prepared)
    gains = []
    for _ in range(TRIALS):
        gain = 0
        for _post, text, review, doc, base, baseCovered in prepared:
            take = round(fireCount * len(doc.paragraphs) / totalParagraphs)
            if not take:
                continue
            lines = rng.sample([p.startLine for p in doc.paragraphs], min(take, len(doc.paragraphs)))
            extra = [Finding("random", line, "", "무작위", None, NOTICE, PARAGRAPH, 0) for line in lines]
            gain += coverageOf(text, base + extra, review).covered - baseCovered
        gains.append(gain)
    gains.sort()
    return sum(gains) / len(gains), gains[int(TRIALS * 0.95) - 1]


def main() -> int:
    prepared = prepare()
    located = sum(coverageOf(t, b, r).located for _p, t, r, _d, b, _c in prepared)
    paragraphs = sum(len(d.paragraphs) for _, _, _, d, _, _ in prepared)
    print(f"대상 {len(prepared)}편. 산문 문단 {paragraphs}개, 본문에서 찾은 사람 지적 {located}건.")
    print("지적 밀도가 문단 수보다 높다. 그래서 무작위 기준선을 같이 낸다.\n")

    rng = random.Random(101)
    print("=== 신호 대 무작위 ===")
    print(f"{'신호':>22s} {'발화':>4s} {'덮음':>4s} {'무작위평균':>10s} {'무작위95분위':>12s} {'넘나':>4s}")
    # (이름, 문단 문턱, 표 문턱). 1.01 은 그 신호를 끈다.
    rows = [
        ("문단 중첩 0.30", 0.30, 1.01),
        ("문단 중첩 0.35", 0.35, 1.01),
        ("문단 중첩 0.40", 0.40, 1.01),
        ("표 되풀이 0.45", 1.01, 0.45),
    ]
    for label, paragraphThreshold, tableThreshold in rows:
        fired = gain = 0
        for _post, text, review, doc, base, baseCovered in prepared:
            extra = asFindings(doc, paragraphThreshold, tableThreshold)
            fired += len(extra)
            gain += coverageOf(text, base + extra, review).covered - baseCovered
        mean, p95 = randomBaseline(prepared, fired, rng) if fired else (0.0, 0)
        beats = "예" if gain > p95 else "아니오"
        print(f"{label:>22s} {fired:4d} {gain:4d} {mean:10.1f} {p95:12d} {beats:>4s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
