"""한국어 위키백과 덤프를 문서 하나가 한 줄인 jsonl 로 떨군다. 말뭉치 재료다.

무엇을 받나: https://dumps.wikimedia.org/kowiki/latest/kowiki-latest-pages-articles.xml.bz2 (약 1.4 GB). 넘겨주기
(#넘겨주기, #REDIRECT) 는 뺀다. 위키 문법은 기준 말뭉치가 쓰는 normalizeWikitext 로 마크다운 비슷한 산문으로 바꾼다
(틀, 각주, 그림 링크, 표를 빼고 제목은 `#`, 목록은 `1.`). 색인 쪽 (usage/sentences.py) 이 제목과 목록 표시를 알아서 넘긴다.

**이름공간이 곧 장르다.** `--namespaces` 가 고른다. 덤프 하나에 여러 장르가 들어 있어 다시 받을 필요가 없다.

| 이름공간 | 무엇 | 문체 |
|---|---|---|
| 0 (기본) | 본문 | 백과체. 사실을 진술한다 |
| 4 | `위키백과:` 지침과 정책 | 설명체와 논설체. 독자에게 왜 그러는지를 풀어 말한다 |
| 12 | `도움말:` | 설명체. 하는 법을 알려 준다 |

한 사람 말뭉치 안에서 문체가 다른 자료를 얻는 자리다. 규칙 후보가 장르를 타는지 안 타는지를 가르려면 서로 다른
장르가 여럿 있어야 하고, 장르를 타는 후보는 임계를 정할 수 없어 규칙이 못 된다.

어디에 두나: `~/.cache/hanlint/corpus/wiki/kowiki.jsonl` (ns 0) 이거나 `kowiki.ns4-12.jsonl` (고른 이름공간).
줄마다 {"source": 글 제목, "text": 산문}. 저장소 안에는 두지 않는다.
그다음: `hanlint usage build encyclopedia ~/.cache/hanlint/corpus/wiki` (파이썬) 또는 `npx hanlint usage build …` (node 가
빠르다).

라이선스: 위키백과 글은 CC BY-SA 4.0 이다. 통계는 물론 문장도 출처 (글 제목) 를 붙여 나눌 수 있고 같은 조건으로 나눠야
한다. 이 스크립트가 만든 파일은 사용자 기계에만 있다.
"""

from __future__ import annotations

import argparse
import bz2
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ElementTree
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.fetch.corpus import normalizeWikitext  # noqa: E402

DUMP_URL = "https://dumps.wikimedia.org/kowiki/latest/kowiki-latest-pages-articles.xml.bz2"
NAMESPACE = "{http://www.mediawiki.org/xml/export-0.11/}"
REDIRECT = re.compile(r"^\s*#(?:넘겨주기|REDIRECT)", re.I)
MIN_KOREAN = 80
"""문서로 셀 최소 한글 글자 수. 그 아래는 표와 상자만 남은 껍데기다."""
KOREAN = re.compile(r"[가-힣]")


def defaultRoot() -> Path:
    return Path.home() / ".cache" / "hanlint" / "corpus" / "wiki"


def download(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    print(f"{DUMP_URL} → {target}", file=sys.stderr)
    urllib.request.urlretrieve(DUMP_URL, target)


def pages(dump: Path, namespaces: frozenset[str]):
    """(제목, 위키 문법 원문) 을 고른 이름공간의 글마다. 넘겨주기와 빈 글은 넘긴다."""
    with bz2.open(dump, "rb") as handle:
        for _, element in ElementTree.iterparse(handle, events=("end",)):
            if element.tag != f"{NAMESPACE}page":
                continue
            namespace = element.findtext(f"{NAMESPACE}ns")
            title = element.findtext(f"{NAMESPACE}title") or ""
            text = element.findtext(f"{NAMESPACE}revision/{NAMESPACE}text") or ""
            element.clear()
            if namespace not in namespaces or not text or REDIRECT.match(text):
                continue
            yield title, text


def outputName(namespaces: frozenset[str]) -> str:
    """이름공간 하나짜리 기본값은 이름을 안 바꾼다. 이미 만들어 둔 말뭉치를 덮어쓰거나 갈라 놓지 않는다."""
    if namespaces == frozenset({"0"}):
        return "kowiki.jsonl"
    return "kowiki.ns" + "-".join(sorted(namespaces, key=int)) + ".jsonl"


def convert(dump: Path, output: Path, namespaces: frozenset[str], limit: int | None) -> tuple[int, int]:
    """덤프를 jsonl 로. (쓴 문서 수, 넘긴 문서 수)."""
    written = skipped = 0
    started = time.perf_counter()
    with output.open("w", encoding="utf-8", newline="\n") as out:
        for title, wikitext in pages(dump, namespaces):
            prose = normalizeWikitext(wikitext)
            if len(KOREAN.findall(prose)) < MIN_KOREAN:
                skipped += 1
                continue
            out.write(json.dumps({"source": title, "text": prose}, ensure_ascii=False) + "\n")
            written += 1
            if written % 20000 == 0:
                print(f"{written:,}편 ({time.perf_counter() - started:.0f}초)", file=sys.stderr)
            if limit is not None and written >= limit:
                break
    return written, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--root", type=Path, default=defaultRoot(), help="덤프와 jsonl 을 둘 폴더. 기본 ~/.cache/hanlint/corpus/wiki"
    )
    parser.add_argument("--limit", type=int, default=None, help="앞에서부터 몇 편만 (시험용)")
    parser.add_argument(
        "--namespaces",
        default="0",
        help="쉼표로 나눈 이름공간 번호. 기본 0 (본문). 4 는 `위키백과:` 지침, 12 는 `도움말:` 이다",
    )
    args = parser.parse_args()
    namespaces = frozenset(one.strip() for one in args.namespaces.split(",") if one.strip())
    if not namespaces or not all(one.isdigit() for one in namespaces):
        raise SystemExit(f"--namespaces 는 쉼표로 나눈 숫자다. 받은 것: {args.namespaces!r}")
    dump = args.root / DUMP_URL.rsplit("/", 1)[1]
    download(dump)
    output = args.root / outputName(namespaces)
    written, skipped = convert(dump, output, namespaces, args.limit)
    print(f"{output}: 문서 {written:,}편 (한글 {MIN_KOREAN}자 미만 {skipped:,}편 넘김).")
    print(f"다음: hanlint usage build encyclopedia {args.root}")


if __name__ == "__main__":
    main()
