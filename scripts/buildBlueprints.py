"""고정 말뭉치에서 원문 없이 종류별 수사 구조 백분위만 만든다."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections import defaultdict
from hashlib import sha256
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from hanlint import Config, fingerprint  # noqa: E402

CORPUS_ROOT = (REPO / "../hanlint.out/corpus").resolve()
TARGET = REPO / "src" / "hanlint" / "data" / "blueprints.json"
PERCENTILES = (10, 25, 50, 75, 90)


def fileSha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def percentiles(values: list[int]) -> dict[str, int]:
    ordered = sorted(values)
    if not ordered:
        return {f"p{percentile}": 0 for percentile in PERCENTILES}
    return {
        f"p{percentile}": ordered[min(len(ordered) - 1, round(percentile / 100 * (len(ordered) - 1)))]
        for percentile in PERCENTILES
    }


def documentShape(doc) -> dict[str, int]:
    proseSections = [section for section in doc.sections if section.paragraphs]
    proseCharacters = sum(len(sentence.text) for sentence in doc.sentences)
    openingCharacters = (
        sum(len(sentence.text) for paragraph in proseSections[0].paragraphs for sentence in paragraph.sentences)
        if proseSections
        else 0
    )
    closingCharacters = (
        sum(len(sentence.text) for paragraph in proseSections[-1].paragraphs for sentence in paragraph.sentences)
        if proseSections
        else 0
    )
    return {
        "proseCharacters": proseCharacters,
        "sections": len(proseSections),
        "paragraphs": len(doc.paragraphs),
        "sentences": len(doc.sentences),
        "openingSharePermille": openingCharacters * 1000 // proseCharacters if proseCharacters else 0,
        "closingSharePermille": closingCharacters * 1000 // proseCharacters if proseCharacters else 0,
    }


def verifiedMetadata() -> tuple[list[dict], Path]:
    """고정 manifest, 외부 metadata와 원문의 해시·출처 허가가 모두 같은 항목만 돌려준다."""
    metadataPath = CORPUS_ROOT / "metadata.json"
    metadata = json.loads(metadataPath.read_text(encoding="utf-8"))["documents"]
    manifest = json.loads((REPO / "corpus" / "documents.json").read_text(encoding="utf-8"))["documents"]
    catalogue = tomllib.loads((REPO / "corpus" / "catalogue.toml").read_text(encoding="utf-8"))
    sources = {source["id"]: source for source in catalogue["source"]}
    expected = {entry["id"]: entry for entry in manifest}
    if len(metadata) != len(manifest) or len(expected) != len(manifest):
        raise ValueError("말뭉치 metadata와 고정 manifest의 문서 수가 다르다")
    compared = ("source", "type", "preset", "revision", "textSha256", "license", "licenseUrl")
    for entry in metadata:
        identifier = entry["id"]
        if identifier not in expected or any(entry.get(key) != expected[identifier].get(key) for key in compared):
            raise ValueError(f"고정 manifest와 다른 말뭉치 metadata다: {identifier}")
        source = sources.get(entry["source"])
        if source is None or source["license"] != entry["license"] or source["licenseUrl"] != entry["licenseUrl"]:
            raise ValueError(f"카탈로그의 출처 허가와 다른 말뭉치 문서다: {identifier}")
        path = CORPUS_ROOT / entry["path"]
        if sha256(path.read_text(encoding="utf-8").encode()).hexdigest() != entry["textSha256"]:
            raise ValueError(f"고정 원문 해시와 다른 말뭉치 문서다: {identifier}")
    return metadata, metadataPath


def render() -> str:
    metadata, metadataPath = verifiedMetadata()
    byType: dict[str, dict[str, list[int] | set[str]]] = defaultdict(
        lambda: {
            "sources": set(),
            "proseCharacters": [],
            "sections": [],
            "paragraphs": [],
            "sentences": [],
            "openingSharePermille": [],
            "closingSharePermille": [],
            "sectionParagraphs": [],
            "sectionSentences": [],
            "paragraphCharacters": [],
            "paragraphSentences": [],
            "sentenceCharacters": [],
            "adjacentSentenceCharacterDelta": [],
        }
    )
    for entry in metadata:
        text = (CORPUS_ROOT / entry["path"]).read_text(encoding="utf-8")
        doc = fingerprint(text, Config(preset=entry["preset"]), path=entry["path"])
        values = byType[entry["type"]]
        values["sources"].add(entry["source"])
        for name, value in documentShape(doc).items():
            values[name].append(value)
        proseSections = [section for section in doc.sections if section.paragraphs]
        values["sectionParagraphs"].extend(len(section.paragraphs) for section in proseSections)
        values["sectionSentences"].extend(
            sum(paragraph.sentenceCount for paragraph in section.paragraphs) for section in proseSections
        )
        values["paragraphCharacters"].extend(len(paragraph.text) for paragraph in doc.paragraphs)
        values["paragraphSentences"].extend(paragraph.sentenceCount for paragraph in doc.paragraphs)
        values["sentenceCharacters"].extend(len(sentence.text) for sentence in doc.sentences)
        for paragraph in doc.paragraphs:
            lengths = [len(sentence.text) for sentence in paragraph.sentences]
            values["adjacentSentenceCharacterDelta"].extend(
                abs(right - left) for left, right in zip(lengths, lengths[1:], strict=False)
            )
    types = {}
    for kind, values in sorted(byType.items()):
        sources = sorted(values.pop("sources"))
        types[kind] = {
            "documents": len(values["proseCharacters"]),
            "sourceIds": sources,
            "metrics": {name: percentiles(items) for name, items in sorted(values.items())},
        }
    payload = {
        "version": 1,
        "corpus": {
            "documents": len(metadata),
            "catalogueSha256": fileSha(REPO / "corpus" / "catalogue.toml"),
            "manifestSha256": fileSha(REPO / "corpus" / "documents.json"),
            "metadataSha256": fileSha(metadataPath),
            "containsSourceText": False,
        },
        "types": types,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="종류별 수사 구조 청사진 데이터를 만든다")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    text = render()
    if parseArgs().check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != text:
            print("다시 만들어야 한다: data/blueprints.json")
            return 1
        print("수사 구조 청사진이 고정 말뭉치와 같다")
        return 0
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(f"{TARGET} 에 원문 없는 종류별 수사 구조를 썼다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
