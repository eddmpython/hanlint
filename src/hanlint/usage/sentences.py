"""문장 역인덱스. 글 종류마다 폴더 하나 (`~/.cache/hanlint/usage/<종류>/`) 이고 질의에 BM25 로 문장을 돌려준다.

무엇을 위해: 검사기가 짚은 자리를 고치는 사람과 LLM 이 "그 종류의 실제 글은 이 낱말을 어떻게 쓰나" 를 같은 질의에
같은 순서로 받는다. 좋은 문장을 고르는 것이 아니라 쓰인 문장을 보이는 것이다. 판정은 읽는 쪽의 몫이다.

토큰: 어절에서 앞뒤 부호와 조사를 뗀 것 (core) 과, 한글 core 가 세 글자 이상이면 그 글자 두 개짜리 조각 (bigram).
core 는 낱말 그대로를 맞히고 bigram 은 `금융리스부채` 와 `리스부채`, `적용되며` 와 `적용된다` 처럼 붙고 활용한 자리를
맞힌다. 빈도가 높은 bigram 은 IDF 가 낮아 제 무게만큼만 들고, 문장 절반 넘게 나오는 토큰은 조회에서 뺀다
(MAX_DF_SHARE). 형태소 분석기는 쓰지 않는다 (제품 원칙).

파일 (전부 결정적이라 같은 글에서 같은 바이트가 나온다. npm 판이 같은 파일을 읽고 같은 파일을 만든다):
- meta.json: format, kind, documents, sentences, tokens (전체 토큰 수. 평균 길이는 조회 때 나눈다), terms
- sentences.tsv: 문장마다 `문서 수 \\t 출처 \\t 글`. 줄 번호가 문장 번호다. 같은 문장 (공백을 모으고 숫자를 0 으로
  바꾼 꼴이 같은 것) 은 하나로 접고 처음 본 글과 출처를 둔다. 실측: 사업보고서 961편에서 문장의 47.4% 가 다른
  문서에도 있었다.
- offsets.bin: 문장마다 sentences.tsv 안의 바이트 위치 (8바이트 little endian). 번호로 바로 읽는다.
- lengths.bin: 문장마다 토큰 수 (4바이트 little endian). BM25 의 길이 보정에 쓰므로 통째로 든다.
- terms.tsv: `토큰 \\t 문서 빈도 \\t postings.bin 위치 \\t 바이트 수`. 토큰 순 (코드 포인트 순).
- postings.bin: 토큰마다 (문장 번호 차이, 빈도) 를 LEB128 부호 없는 varint 로 이어 쓴 것.

순서: BM25 (k1 1.5, b 0.75) 값 내림차순, 같으면 문장 번호 오름차순. 이 값은 질의와 문장의 낱말 겹침이지 글의 좋고 나쁨이
아니다. 두 판의 log 가 마지막 자리에서 다를 수 있어 값을 SCORE_SCALE 배의 정수로 내린 뒤 견준다 (npm 판과 같은 셈).
"""

from __future__ import annotations

import json
import math
import re
from array import array
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from ..analysis import splitSentences
from ..analysis.tokenize import COPULA, EDGE_PUNCTUATION, josaSet, stripJosa

FORMAT = 1
K1 = 1.5
B = 0.75
SCORE_SCALE = 1_000_000
MAX_DF_SHARE = 0.5
MIN_FILTER_SENTENCES = 1000
"""이보다 문장이 적은 색인은 흔한 토큰도 거르지 않는다. 걸러 얻는 것은 큰 postings 를 안 읽는 시간뿐인데 작은 색인에서는
그 시간이 없고, 문장 몇 개짜리 색인에서는 모든 토큰이 절반을 넘어 아무것도 안 나온다 (검증 실측, 2026-09-19)."""
HANGUL = re.compile(r"[가-힣]")
ASCII_WORD = re.compile(r"[A-Za-z0-9]+")
"""한글이 없는 어절의 토큰. `K-IFRS` 는 k 와 ifrs, `12%` 는 12 다."""
DIGITS = re.compile(r"[0-9]+")
SPACE = re.compile(r"\s+")
LINE_BREAK = re.compile(r"\r\n|\r|\n")
"""줄 나누기. 파이썬 splitlines 는 \x1c 와 \x85 와 \v 에서도 나누지만 npm 판 (splitLines) 은 셋에서만 나눈다. 같은 줄을
읽어야 같은 색인이 나온다."""
STRAY = re.compile(r"[\x1c-\x1f\x85]")
"""파이썬은 빈칸으로 보고 JS 는 아닌 글자. 빈칸으로 바꿔 두 판을 맞춘다. U+FEFF (BOM) 는 반대라 지운다 (BOM 은 메모장이
저장한 파일 첫머리에 흔하다. 검증 실측, 2026-09-19)."""
BULLET = re.compile(r"^(?:(?:[-*·•※]|\([0-9a-z]{1,2}\)|[0-9]{1,2}[.)])\s+|(?:\([가-힣]\)|[가-힣][.)])\s*)")
"""줄 머리의 목록 표시와 항목 번호 (`- `, `(1) `, `3. `, `(가) `, `나. `). 문장이 아니라 떼고 읽는다. 한글 항목은 뒤에
빈칸이 없어도 뗀다 (DART 원문이 `나.최대주주의 변동` 처럼 붙인 자리가 있다). 숫자는 `3.5 초` 를 지키려 빈칸을 요구한다."""
TERMINAL = re.compile(r"(?<![0-9])[.!?][\"'”’)\]]*$")
"""문장으로 셀 조건. 마침표나 물음표나 느낌표로 끝나야 한다 (닫는 따옴표와 괄호는 뒤에 와도 된다). 제목과 항목 이름
(`리스부채의 최초 측정금액`) 은 낱말의 쓰임이 아니라 이름이라 색인하지 않는다. 그런 연쇄는 빈도표 (counts) 가 든다.
숫자 뒤의 마침표 (`평가 보고6.`, DART 원문에서 항목 번호가 붙은 제목) 도 문장 끝이 아니다."""
FENCE = "```"
TEXT_SUFFIXES = (".txt", ".md")
FILES = ("meta.json", "sentences.tsv", "offsets.bin", "lengths.bin", "terms.tsv", "postings.bin")


def defaultRoot() -> Path:
    return Path.home() / ".cache" / "hanlint" / "usage"


def normalized(text: str) -> str:
    """두 판이 같은 글자를 보게 한다. BOM 을 지우고 빈칸 판정이 갈리는 제어 문자를 빈칸으로."""
    return STRAY.sub(" ", text.replace("\ufeff", ""))


def indexTokens(text: str) -> list[str]:
    """BM25 토큰. 조사를 뗀 어절과 한글 어절의 글자 두 개짜리 조각. 영문과 숫자는 부호에서 갈라 소문자로."""
    found: list[str] = []
    for raw in normalized(text).split():
        core = raw.strip(EDGE_PUNCTUATION)
        if not core or core in josaSet() or COPULA.match(core):
            continue
        core = stripJosa(core)
        if HANGUL.search(core):
            found.append(core)
            if len(core) >= 3:
                found.extend(core[i : i + 2] for i in range(len(core) - 1))
        else:
            found.extend(piece.lower() for piece in ASCII_WORD.findall(core))
    return found


def sentenceKey(text: str) -> str:
    """같은 문장으로 접는 꼴. 공백을 하나로, 숫자를 0 으로."""
    return DIGITS.sub("0", SPACE.sub(" ", text).strip())


def paragraphsOf(text: str) -> Iterator[str]:
    """글의 산문 줄. 코드 펜스 안, 제목, 표 줄은 넘기고 목록 표시는 뗀다."""
    inFence = False
    for line in LINE_BREAK.split(normalized(text)):
        stripped = line.strip()
        if stripped.startswith(FENCE):
            inFence = not inFence
            continue
        if inFence or not stripped or stripped.startswith(("#", "|")):
            continue
        yield BULLET.sub("", stripped)


def sentencesOf(text: str) -> Iterator[str]:
    for paragraph in paragraphsOf(text):
        for sentence in splitSentences(paragraph):
            if HANGUL.search(sentence.text) and TERMINAL.search(sentence.text):
                yield SPACE.sub(" ", sentence.text).strip()


def encodeVarint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def decodeVarints(data: bytes) -> list[int]:
    values: list[int] = []
    value = shift = 0
    for byte in data:
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
        else:
            values.append(value)
            value = shift = 0
    return values


def readDocuments(folder: Path) -> Iterator[tuple[str, str]]:
    """폴더 (하위 포함) 의 txt 와 md. (출처 = 파일 이름에서 확장자를 뗀 것, 글). 폴더 기준 posix 경로의 코드 포인트 순이라
    OS 와 판이 달라도 같은 차례다 (Windows 의 Path 비교는 대소문자를 접는다)."""
    paths = [path for path in folder.rglob("*") if path.suffix.lower() in TEXT_SUFFIXES and path.is_file()]
    paths.sort(key=lambda path: path.relative_to(folder).as_posix())
    for path in paths:
        yield path.stem, path.read_text(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class BuildResult:
    documents: int
    sentences: int
    terms: int


def buildIndex(kind: str, documents: Iterable[tuple[str, str]], root: Path) -> BuildResult:
    """(출처, 글) 들로 색인을 만들어 root/<kind>/ 에 쓴다. 있던 파일은 덮는다."""
    target = root / kind
    target.mkdir(parents=True, exist_ok=True)
    sentenceIds: dict[str, int] = {}
    texts: list[str] = []
    sources: list[str] = []
    lengths = array("I")
    documentSets: list[set[str]] = []
    postingIds: dict[str, array] = {}
    postingTfs: dict[str, array] = {}
    documentCount = 0
    tokenTotal = 0
    for source, text in documents:
        documentCount += 1
        for sentence in sentencesOf(text):
            key = sentenceKey(sentence)
            sentenceId = sentenceIds.get(key)
            if sentenceId is not None:
                documentSets[sentenceId].add(source)
                continue
            tokens = indexTokens(sentence)
            if not tokens:
                continue
            sentenceId = len(texts)
            sentenceIds[key] = sentenceId
            texts.append(sentence)
            sources.append(source)
            lengths.append(len(tokens))
            documentSets.append({source})
            tokenTotal += len(tokens)
            counts: dict[str, int] = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            for token, count in counts.items():
                if token not in postingIds:
                    postingIds[token] = array("I")
                    postingTfs[token] = array("H")
                postingIds[token].append(sentenceId)
                postingTfs[token].append(min(count, 65535))
    offsets = bytearray()
    with (target / "sentences.tsv").open("wb") as handle:
        for sentenceId, text in enumerate(texts):
            offsets += handle.tell().to_bytes(8, "little")
            handle.write(f"{len(documentSets[sentenceId])}\t{sources[sentenceId]}\t{text}\n".encode())
    (target / "offsets.bin").write_bytes(bytes(offsets))
    (target / "lengths.bin").write_bytes(b"".join(length.to_bytes(4, "little") for length in lengths))
    termLines: list[str] = []
    with (target / "postings.bin").open("wb") as handle:
        for term in sorted(postingIds):
            chunk = bytearray()
            previous = 0
            for sentenceId, tf in zip(postingIds[term], postingTfs[term], strict=True):
                chunk += encodeVarint(sentenceId - previous)
                chunk += encodeVarint(tf)
                previous = sentenceId
            offset = handle.tell()
            handle.write(chunk)
            termLines.append(f"{term}\t{len(postingIds[term])}\t{offset}\t{len(chunk)}\n")
    (target / "terms.tsv").write_bytes("".join(termLines).encode("utf-8"))
    meta = {
        "format": FORMAT,
        "kind": kind,
        "documents": documentCount,
        "sentences": len(texts),
        "tokens": tokenTotal,
        "terms": len(termLines),
    }
    (target / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return BuildResult(documentCount, len(texts), len(termLines))


@dataclass(frozen=True)
class Hit:
    text: str
    documents: int
    """이 문장이 나온 문서 수."""
    source: str
    """처음 본 문서의 출처 (파일 이름)."""
    score: int
    """BM25 값을 SCORE_SCALE 배 해 내린 정수. 낱말 겹침의 크기이지 글의 판정이 아니다."""


class UsageIndex:
    """폴더 하나의 색인. terms.tsv 와 lengths.bin 은 통째로 들고 문장과 postings 는 자리로 읽는다."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        if self.meta.get("format") != FORMAT:
            raise ValueError(f"{folder} 의 색인 format 이 {self.meta.get('format')} 이다. {FORMAT} 으로 다시 만든다")
        self.terms: dict[str, tuple[int, int, int]] = {}
        for line in (folder / "terms.tsv").read_text(encoding="utf-8").split("\n"):
            if not line:
                continue
            term, df, offset, size = line.split("\t")
            self.terms[term] = (int(df), int(offset), int(size))
        self.lengths = array("I")
        self.lengths.frombytes((folder / "lengths.bin").read_bytes())

    @property
    def kind(self) -> str:
        return self.meta["kind"]

    @property
    def documents(self) -> int:
        return self.meta["documents"]

    @property
    def sentences(self) -> int:
        return self.meta["sentences"]

    def postings(self, term: str) -> list[tuple[int, int]]:
        found = self.terms.get(term)
        if not found:
            return []
        _, offset, size = found
        with (self.folder / "postings.bin").open("rb") as handle:
            handle.seek(offset)
            values = decodeVarints(handle.read(size))
        result: list[tuple[int, int]] = []
        sentenceId = 0
        for index in range(0, len(values), 2):
            sentenceId += values[index]
            result.append((sentenceId, values[index + 1]))
        return result

    def sentence(self, sentenceId: int) -> tuple[int, str, str]:
        """(문서 수, 출처, 글)."""
        with (self.folder / "offsets.bin").open("rb") as handle:
            handle.seek(sentenceId * 8)
            offset = int.from_bytes(handle.read(8), "little")
        with (self.folder / "sentences.tsv").open("rb") as handle:
            handle.seek(offset)
            line = handle.readline().decode("utf-8").rstrip("\n")
        documents, source, text = line.split("\t", 2)
        return int(documents), source, text

    def search(self, query: str, limit: int) -> list[Hit]:
        tokens = sorted(set(indexTokens(query)))
        if not tokens or not self.sentences:
            return []
        averageLength = self.meta["tokens"] / self.sentences
        scores: dict[int, float] = {}
        for token in tokens:
            found = self.terms.get(token)
            if not found or (self.sentences >= MIN_FILTER_SENTENCES and found[0] > self.sentences * MAX_DF_SHARE):
                continue
            df = found[0]
            idf = math.log(1 + (self.sentences - df + 0.5) / (df + 0.5))
            for sentenceId, tf in self.postings(token):
                norm = tf + K1 * (1 - B + B * self.lengths[sentenceId] / averageLength)
                scores[sentenceId] = scores.get(sentenceId, 0.0) + idf * (tf * (K1 + 1)) / norm
        scaled = ((math.floor(score * SCORE_SCALE), sentenceId) for sentenceId, score in scores.items())
        ranked = sorted(scaled, key=lambda item: (-item[0], item[1]))
        hits = []
        for score, sentenceId in ranked[:limit]:
            documents, source, text = self.sentence(sentenceId)
            hits.append(Hit(text, documents, source, score))
        return hits


def loadIndex(kind: str, root: Path) -> UsageIndex | None:
    folder = root / kind
    if not all((folder / name).exists() for name in FILES):
        return None
    return UsageIndex(folder)
