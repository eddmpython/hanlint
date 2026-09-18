"""말뭉치에서 명사 연쇄 빈도표 `src/hanlint/data/usageCounts.<종류>.json` 을 만든다.

연쇄는 analysis/tokenize.py 의 nounRuns 로 뽑는다 (규칙이 쓰는 함수와 같다). 값은 그 연쇄가 나온 문서 수다. 한 문서
안의 반복은 한 번으로 세고, 한 문서에만 나온 연쇄는 표에 넣지 않는다 (MIN_DOCUMENTS). 센 길이가 MIN_LENGTH 미만인
연쇄도 넣지 않는다. nounPile 이 짚는 것은 nounPileMin (기본 5, fixture 는 4) 이상이라 그 아래는 쓸 자리가 없다.
글자 하나짜리 어절만 이어진 연쇄 (`익 잉 여 금 처`, 글자를 띄어 쓴 제목의 잔해) 는 뺀다.

종류 report 의 말뭉치는 scripts/fetch/dartReports.py 가 받은 사업보고서다. 문장은 패키지에 싣지 않고 이 통계만 싣는다.
표 크기는 MAX_BYTES 를 넘지 않는다. tests/gates/testUsageCounts.py 가 같은 상수로 지킨다.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from scripts.fetch.dartReports import defaultRoot, readCorpus  # noqa: E402

from hanlint.analysis import nounRuns, splitSentences  # noqa: E402

TARGET = REPO / "src" / "hanlint" / "data"
MIN_LENGTH = 4
MIN_DOCUMENTS = 2
MAX_BYTES = 256 * 1024
"""빈도표 한 개의 상한. 패키지와 브라우저 묶음 (siteData.json) 에 그대로 실리므로 사전 파일들과 같은 자릿수를 지킨다.
실측: 사업보고서 1,000편의 report 표가 이 안에 든다 (2026-09-19)."""
SOURCES = {
    "report": "OpenDART 사업보고서 (pblntf_detail_ty A001), 회사마다 한 편. scripts/fetch/dartReports.py",
}


def artifact(chain: tuple[str, ...]) -> bool:
    return all(len(word) == 1 for word in chain)


def countChains(root: Path, limit: int | None) -> tuple[int, dict[str, int]]:
    """(문서 수, 연쇄 → 문서 수). 문서 순서와 무관하게 같은 결과다."""
    documentsOf: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
    documents = 0
    for rceptNo, text in readCorpus(root, limit):
        documents += 1
        for paragraph in text.splitlines():
            for sentence in splitSentences(paragraph):
                for chain, length in nounRuns(sentence.text):
                    if length >= MIN_LENGTH and not artifact(tuple(chain)):
                        documentsOf[tuple(chain)].add(rceptNo)
    chains = {" ".join(chain): len(found) for chain, found in documentsOf.items() if len(found) >= MIN_DOCUMENTS}
    return documents, dict(sorted(chains.items()))


def render(kind: str, documents: int, chains: dict[str, int]) -> str:
    table = {
        "kind": kind,
        "source": SOURCES[kind],
        "documents": documents,
        "minLength": MIN_LENGTH,
        "minDocuments": MIN_DOCUMENTS,
        "chains": chains,
    }
    return json.dumps(table, ensure_ascii=False, indent=1) + "\n"


def tablePath(kind: str) -> Path:
    return TARGET / f"usageCounts.{kind}.json"


def problems(path: Path) -> list[str]:
    """표가 계약을 어긴 자리. 비어 있어야 정상이다. 게이트가 부른다."""
    found = []
    size = path.stat().st_size
    if size > MAX_BYTES:
        found.append(f"{path.name} 이 {size:,} 바이트다. 상한 {MAX_BYTES:,}")
    table = json.loads(path.read_text(encoding="utf-8"))
    if table.get("kind") != path.stem.split(".")[1]:
        found.append(f"{path.name} 의 kind 가 파일 이름과 다르다")
    if table.get("minLength") != MIN_LENGTH or table.get("minDocuments") != MIN_DOCUMENTS:
        found.append(f"{path.name} 의 minLength 와 minDocuments 가 스크립트와 다르다")
    chains = table.get("chains", {})
    if list(chains) != sorted(chains):
        found.append(f"{path.name} 의 연쇄가 정렬되어 있지 않다")
    for chain, count in chains.items():
        if not isinstance(count, int) or count < MIN_DOCUMENTS:
            found.append(f"{chain}: 문서 수 {count!r} 는 {MIN_DOCUMENTS} 이상의 정수여야 한다")
        elif len(chain.split()) < MIN_LENGTH:
            found.append(f"{chain}: 어절 {len(chain.split())}개는 {MIN_LENGTH} 미만이다")
        elif artifact(tuple(chain.split())):
            found.append(f"{chain}: 글자 하나짜리 어절만 이어진 연쇄다")
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--kind", choices=sorted(SOURCES), default="report")
    parser.add_argument("--root", type=Path, default=None, help="말뭉치 폴더. 기본은 종류의 기본 자리")
    parser.add_argument("--limit", type=int, default=None, help="앞에서부터 몇 편만 (시험용)")
    args = parser.parse_args()
    root = args.root or defaultRoot()
    documents, chains = countChains(root, args.limit)
    text = render(args.kind, documents, chains)
    path = tablePath(args.kind)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"{path.relative_to(REPO)}: 문서 {documents}편, 연쇄 {len(chains):,}종, {len(text.encode('utf-8')):,} 바이트")
    for problem in problems(path):
        print(f"  ! {problem}")


if __name__ == "__main__":
    main()
