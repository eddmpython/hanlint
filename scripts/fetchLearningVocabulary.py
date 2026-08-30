"""국립국어원 한국어 학습용 어휘 목록을 고정된 UTF-8 표로 투영한다.

자료원, 라이선스, 필드, 검증 수의 정본은 `data/learningVocabularySource.toml`이다. 원본은 CP949 탭
구분 파일이다. `--input`을 주면 이미 받은 원본으로 재생성하므로 네트워크 없이도 같은 투영을 만들 수 있다.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import tomllib
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "src" / "hanlint" / "data" / "learningVocabularySource.toml"
TARGET = ROOT / "src" / "hanlint" / "data" / "learningVocabulary.tsv"
HEADERS = ("순위", "단어", "품사", "풀이", "등급")
HOMONYM_NUMBER = re.compile(r"\d+$")


def metadata() -> dict:
    return tomllib.loads(METADATA.read_text(encoding="utf-8"))


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "hanlint vocabulary data builder"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def parseSource(raw: bytes) -> list[dict]:
    text = raw.decode("cp949").replace("\r\n", "\n").replace("\r", "\n")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    if tuple(reader.fieldnames or ()) != HEADERS:
        raise ValueError(f"원본 머리줄이 다르다: {reader.fieldnames}")
    entries: list[dict] = []
    for row in reader:
        if not any((value or "").strip() for value in row.values()):
            continue
        word = row["단어"].strip()
        entries.append(
            {
                "rank": int(row["순위"]) if row["순위"] else None,
                "word": word,
                "lexeme": HOMONYM_NUMBER.sub("", word),
                "partOfSpeech": row["품사"].strip(),
                "grade": row["등급"].strip(),
            }
        )
    validate(entries)
    return entries


def validate(entries: list[dict]) -> None:
    contract = metadata()["validation"]
    if len(entries) != metadata()["sourceFormat"]["rows"]:
        raise ValueError(f"행 수가 다르다: {len(entries)}")
    grades = Counter(entry["grade"] for entry in entries)
    expected = {grade: contract[f"grade{grade}"] for grade in ("A", "B", "C")}
    if grades != expected:
        raise ValueError(f"등급 수가 다르다: {dict(grades)}")
    unique = len({entry["lexeme"] for entry in entries})
    if unique != contract["uniqueLexemes"]:
        raise ValueError(f"표제어 수가 다르다: {unique}")


def render(entries: list[dict]) -> str:
    lines = ["rank\tword\tlexeme\tpartOfSpeech\tgrade"]
    for entry in entries:
        rank = "" if entry["rank"] is None else entry["rank"]
        lines.append(f"{rank}\t{entry['word']}\t{entry['lexeme']}\t{entry['partOfSpeech']}\t{entry['grade']}")
    return "\n".join(lines) + "\n"


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="한국어 학습용 어휘 목록을 UTF-8 제품 데이터로 만든다")
    parser.add_argument("--input", type=Path, help="내려받아 둔 CP949 원본. 없으면 공식 주소에서 받는다")
    parser.add_argument("--check", action="store_true", help="제품 데이터와 같은지만 확인한다")
    return parser.parse_args()


def main() -> int:
    args = parseArgs()
    raw = args.input.read_bytes() if args.input else download(metadata()["dataset"]["downloadUrl"])
    projected = render(parseSource(raw))
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != projected:
            print("learningVocabulary.tsv가 공식 원본의 투영과 다르다")
            return 1
        print("한국어 학습용 어휘 5,965개가 공식 원본의 투영과 같다")
        return 0
    TARGET.write_text(projected, encoding="utf-8", newline="\n")
    print(f"한국어 학습용 어휘 5,965개를 {TARGET}에 썼다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
