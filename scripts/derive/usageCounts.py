"""말뭉치에서 명사 연쇄 빈도표 `src/hanlint/data/usageCounts.<종류>.json` 을 만든다.

연쇄는 analysis/tokenize.py 의 nounRuns 로 뽑는다 (규칙이 쓰는 함수와 같다). 값은 그 연쇄가 나온 문서 수다. 한 문서
안의 반복은 한 번으로 세고, 문서 셋 미만에 나온 연쇄는 표에 넣지 않는다 (MIN_DOCUMENTS. 둘은 우연이고 셋부터 관용이라는
config.usageMin 의 기본과 같다. 둘까지 들면 3,193편에서 표가 275 KB 로 상한을 넘었다). 센 길이가 MIN_LENGTH 미만인
연쇄도 넣지 않는다. nounPile 이 짚는 것은 nounPileMin (기본 5, fixture 는 4) 이상이라 그 아래는 쓸 자리가 없다.
글자 하나짜리 어절만 이어진 연쇄 (`익 잉 여 금 처`, 글자를 띄어 쓴 제목의 잔해) 는 뺀다.

사전 항목 (patterns): 산문 사전 (PROSE_DICTIONARIES) 의 항목마다 그 pattern 원문을 키로 나온 문서 수를 든다. 사전 규칙이
그 종류의 문서 usageShare 이상에 나온 항목을 관용으로 보고 넘기는 근거다 (usage.conventional). 한 편에도 안 나온 항목은
넣지 않는다.

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
from hanlint.fingerprint.dictionaries import builtinEntries  # noqa: E402

TARGET = REPO / "src" / "hanlint" / "data"
MIN_LENGTH = 4
MIN_DOCUMENTS = 3
MAX_BYTES = 256 * 1024
"""빈도표 한 개의 상한. 패키지와 브라우저 묶음 (siteData.json) 에 그대로 실리므로 사전 파일들과 같은 자릿수를 지킨다.
실측: 사업보고서 3,193편의 report 표 (문서 셋 이상의 연쇄와 사전 항목) 가 이 안에 든다 (2026-09-19)."""
PROSE_DICTIONARIES = ("translationese", "cliches", "redundantPair", "japaneseLoan", "easyWords")
"""표에 드는 사전. 화면 사전과 맞춤법 사전은 종류의 관용이 아니라 규약과 표기라 세지 않는다."""
SOURCES = {
    "report": "OpenDART 사업보고서 (pblntf_detail_ty A001), 회사마다 한 편. scripts/fetch/dartReports.py",
}


def artifact(chain: tuple[str, ...]) -> bool:
    return all(len(word) == 1 for word in chain)


def countChains(root: Path, limit: int | None) -> tuple[int, dict[str, int], dict[str, dict[str, int]]]:
    """(문서 수, 연쇄 → 문서 수, 사전 → pattern 원문 → 문서 수). 문서 순서와 무관하게 같은 결과다."""
    documentsOf: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
    entries = [entry for entry in builtinEntries() if entry.dictionary in PROSE_DICTIONARIES]
    patternDocumentsOf: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    documents = 0
    for rceptNo, text in readCorpus(root, limit):
        documents += 1
        pending = set(entries)
        for paragraph in text.splitlines():
            for sentence in splitSentences(paragraph):
                for chain, length in nounRuns(sentence.text):
                    if length >= MIN_LENGTH and not artifact(tuple(chain)):
                        documentsOf[tuple(chain)].add(rceptNo)
                # 한 문서에서 한 번 맞은 항목은 다시 찾지 않는다. 문서 수만 세므로 첫 자리면 충분하다.
                for entry in [entry for entry in pending if entry.pattern.search(sentence.text)]:
                    patternDocumentsOf[(entry.dictionary, entry.raw)].add(rceptNo)
                    pending.discard(entry)
    chains = {" ".join(chain): len(found) for chain, found in documentsOf.items() if len(found) >= MIN_DOCUMENTS}
    patterns: dict[str, dict[str, int]] = {}
    for (dictionary, raw), found in sorted(patternDocumentsOf.items()):
        patterns.setdefault(dictionary, {})[raw] = len(found)
    return documents, dict(sorted(chains.items())), patterns


def render(kind: str, documents: int, chains: dict[str, int], patterns: dict[str, dict[str, int]]) -> str:
    table = {
        "kind": kind,
        "source": SOURCES[kind],
        "documents": documents,
        "minLength": MIN_LENGTH,
        "minDocuments": MIN_DOCUMENTS,
        "chains": chains,
        "patterns": patterns,
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
    chains = table.get("chains")
    if not isinstance(chains, dict) or not chains:
        found.append(f"{path.name} 에 연쇄가 없다")
        return found
    if list(chains) != sorted(chains):
        found.append(f"{path.name} 의 연쇄가 정렬되어 있지 않다")
    for chain, count in chains.items():
        if " ".join(chain.split()) != chain:
            found.append(f"{chain!r}: 어절 사이가 빈칸 하나가 아니다")
        elif not isinstance(count, int) or count < MIN_DOCUMENTS:
            found.append(f"{chain}: 문서 수 {count!r} 는 {MIN_DOCUMENTS} 이상의 정수여야 한다")
        elif len(chain.split()) < MIN_LENGTH:
            found.append(f"{chain}: 어절 {len(chain.split())}개는 {MIN_LENGTH} 미만이다")
        elif artifact(tuple(chain.split())):
            found.append(f"{chain}: 글자 하나짜리 어절만 이어진 연쇄다")
    patterns = table.get("patterns")
    if not isinstance(patterns, dict):
        found.append(f"{path.name} 에 patterns 가 없다")
        return found
    known = {(entry.dictionary, entry.raw) for entry in builtinEntries()}
    for dictionary, items in patterns.items():
        if dictionary not in PROSE_DICTIONARIES:
            found.append(f"{dictionary}: 표에 드는 사전이 아니다")
            continue
        if list(items) != sorted(items):
            found.append(f"{dictionary}: 항목이 정렬되어 있지 않다")
        for pattern, count in items.items():
            if (dictionary, pattern) not in known:
                found.append(f"{dictionary}: {pattern!r} 는 사전에 없는 항목이다")
            elif not isinstance(count, int) or not 1 <= count <= table.get("documents", 0):
                found.append(f"{dictionary}: {pattern!r} 의 문서 수 {count!r} 가 1 과 문서 수 사이가 아니다")
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--kind", choices=sorted(SOURCES), default="report")
    parser.add_argument("--root", type=Path, default=None, help="말뭉치 폴더. 기본은 종류의 기본 자리")
    parser.add_argument("--limit", type=int, default=None, help="앞에서부터 몇 편만 (시험용)")
    args = parser.parse_args()
    root = args.root or defaultRoot()
    documents, chains, patterns = countChains(root, args.limit)
    text = render(args.kind, documents, chains, patterns)
    path = tablePath(args.kind)
    path.write_text(text, encoding="utf-8", newline="\n")
    entryCount = sum(len(items) for items in patterns.values())
    print(
        f"{path.relative_to(REPO)}: 문서 {documents}편, 연쇄 {len(chains):,}종, 사전 항목 {entryCount}개, "
        f"{len(text.encode('utf-8')):,} 바이트"
    )
    for problem in problems(path):
        print(f"  ! {problem}")


if __name__ == "__main__":
    main()
