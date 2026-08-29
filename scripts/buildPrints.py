"""기준 말뭉치의 지문 표. 글마다 지문을 한 번 만들어 문장, 문단, 글을 한 행씩 Parquet 로 둔다.

기준선 (buildBaselines) 과 탐침이 글을 다시 세지 않고 이 표를 묻는다. 표는 저장소 밖 `../hanlint.out/corpus/prints/`
에 두고 제품은 읽지 않는다. polars 는 `corpus` extra 다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from hanlint import Config, fingerprint  # noqa: E402

CORPUS_ROOT = (REPO / "../hanlint.out/corpus").resolve()
PRINTS_ROOT = CORPUS_ROOT / "prints"
TABLES = ("documents", "paragraphs", "sentences")


def sentenceRows(entry: dict, doc) -> list[dict]:
    known: set[str] = set()
    rows = []
    for s in doc.sentences:
        fresh = s.topics - known
        known |= s.topics
        rows.append(
            {
                "docId": entry["id"],
                "type": entry["type"],
                "index": s.index,
                "line": s.line,
                "paragraphIndex": s.paragraphIndex,
                "sectionIndex": s.sectionIndex,
                "length": s.length,
                "ending": s.ending,
                "mood": s.mood,
                "register": s.register,
                "commas": s.commas,
                "connectorStart": s.connectorStart,
                "causal": s.causal,
                "deixis": len(s.deixis),
                "euiCount": s.euiCount,
                "nounRun": s.nounRun,
                "passives": len(s.passives),
                "hedges": s.hedges,
                "numbers": s.numbers,
                "topics": len(s.topics),
                "newTopics": len(fresh),
                "promises": len(s.promises),
                "recalls": len(s.recalls),
                "readerCall": s.readerCall,
            }
        )
    return rows


def paragraphRows(entry: dict, doc) -> list[dict]:
    return [
        {
            "docId": entry["id"],
            "type": entry["type"],
            "index": p.index,
            "sectionIndex": p.sectionIndex,
            "sentenceCount": p.sentenceCount,
            "meanLength": p.meanLength,
            "lengthStd": p.lengthStd,
            "causalTotal": p.causalTotal,
            "deixisTotal": p.deixisTotal,
            "topics": len(p.topics),
            "overlapWithPrevious": p.overlapWithPrevious,
            "followsProseDirectly": p.followsProseDirectly,
        }
        for p in doc.paragraphs
    ]


def documentRow(entry: dict, doc) -> dict:
    return {
        "docId": entry["id"],
        "type": entry["type"],
        "preset": entry["preset"],
        "source": entry["source"],
        "title": entry["title"],
        "sentences": len(doc.sentences),
        "paragraphs": len(doc.paragraphs),
        "sections": len(doc.sections),
        "headings": len(doc.headings),
        "codeBlocks": len(doc.codeBlocks),
        "wordCount": doc.wordCount,
        "questionCount": doc.questionCount,
        "readerCallCount": doc.readerCallCount,
        "register": doc.register,
        "registerShare": doc.registerShare,
    }


def build() -> dict[str, pl.DataFrame]:
    metadata = json.loads((CORPUS_ROOT / "metadata.json").read_text(encoding="utf-8"))["documents"]
    documents: list[dict] = []
    paragraphs: list[dict] = []
    sentences: list[dict] = []
    for entry in metadata:
        text = (CORPUS_ROOT / entry["path"]).read_text(encoding="utf-8")
        doc = fingerprint(text, Config(preset=entry["preset"]), path=entry["path"])
        documents.append(documentRow(entry, doc))
        paragraphs.extend(paragraphRows(entry, doc))
        sentences.extend(sentenceRows(entry, doc))
    return {
        "documents": pl.DataFrame(documents),
        "paragraphs": pl.DataFrame(paragraphs),
        "sentences": pl.DataFrame(sentences),
    }


def write(tables: dict[str, pl.DataFrame]) -> None:
    PRINTS_ROOT.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.write_parquet(PRINTS_ROOT / f"{name}.parquet")


def check() -> list[str]:
    errors: list[str] = []
    metadata = json.loads((CORPUS_ROOT / "metadata.json").read_text(encoding="utf-8"))["documents"]
    wanted = {entry["id"] for entry in metadata}
    path = PRINTS_ROOT / "documents.parquet"
    if not path.exists():
        return ["없음: prints/documents.parquet"]
    have = set(pl.read_parquet(path)["docId"].to_list())
    if have != wanted:
        errors.append(f"지문 표의 글이 말뭉치와 다르다: 표 {len(have)}편, 말뭉치 {len(wanted)}편")
    return errors


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="기준 말뭉치의 지문 표를 만든다")
    parser.add_argument("--check", action="store_true", help="표의 글 목록이 말뭉치와 같은지만 본다")
    return parser.parse_args()


def main() -> int:
    args = parseArgs()
    if args.check:
        errors = check()
        if errors:
            print("\n".join(errors))
            return 1
        print("지문 표가 말뭉치와 같은 글을 든다")
        return 0
    tables = build()
    write(tables)
    print(
        f"글 {tables['documents'].height}편, 문단 {tables['paragraphs'].height}개, 문장 {tables['sentences'].height}개를 "
        f"{PRINTS_ROOT} 에 썼다"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
