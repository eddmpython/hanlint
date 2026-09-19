"""한국어 위키백과 덤프를 문서 하나가 한 줄인 jsonl 로 떨군다. 용례 엔진 (usage) 의 encyclopedia 말뭉치 재료다.

무엇을 받나: https://dumps.wikimedia.org/kowiki/latest/kowiki-latest-pages-articles.xml.bz2 (약 1.4 GB). 표준 이름공간
(ns 0) 의 글만 두고 넘겨주기 (#넘겨주기, #REDIRECT) 는 뺀다. 위키 문법은 기준 말뭉치가 쓰는 normalizeWikitext 로 마크다운
비슷한 산문으로 바꾼다 (틀, 각주, 그림 링크, 표를 빼고 제목은 `#`, 목록은 `1.`). 색인 쪽 (usage/sentences.py) 이 제목과
목록 표시를 알아서 넘긴다.

어디에 두나: `~/.cache/hanlint/corpus/wiki/kowiki.jsonl`. 줄마다 {"source": 글 제목, "text": 산문}. 저장소 안에는 두지 않는다.
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


def pages(dump: Path):
    """(제목, 위키 문법 원문) 을 표준 이름공간의 글마다. 넘겨주기와 빈 글은 넘긴다."""
    with bz2.open(dump, "rb") as handle:
        for _, element in ElementTree.iterparse(handle, events=("end",)):
            if element.tag != f"{NAMESPACE}page":
                continue
            namespace = element.findtext(f"{NAMESPACE}ns")
            title = element.findtext(f"{NAMESPACE}title") or ""
            text = element.findtext(f"{NAMESPACE}revision/{NAMESPACE}text") or ""
            element.clear()
            if namespace != "0" or not text or REDIRECT.match(text):
                continue
            yield title, text


def convert(dump: Path, output: Path, limit: int | None) -> tuple[int, int]:
    """덤프를 jsonl 로. (쓴 문서 수, 넘긴 문서 수)."""
    written = skipped = 0
    started = time.perf_counter()
    with output.open("w", encoding="utf-8", newline="\n") as out:
        for title, wikitext in pages(dump):
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
    args = parser.parse_args()
    dump = args.root / DUMP_URL.rsplit("/", 1)[1]
    download(dump)
    output = args.root / "kowiki.jsonl"
    written, skipped = convert(dump, output, args.limit)
    print(f"{output}: 문서 {written:,}편 (한글 {MIN_KOREAN}자 미만 {skipped:,}편 넘김).")
    print(f"다음: hanlint usage build encyclopedia {args.root}")


if __name__ == "__main__":
    main()
