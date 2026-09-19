"""문장 역인덱스. 글 종류마다 폴더 하나 (`~/.cache/hanlint/usage/<종류>/`) 이고 질의에 BM25 로 문장을 돌려준다.

무엇을 위해: 검사기가 짚은 자리를 고치는 사람과 LLM 이 "그 종류의 실제 글은 이 낱말을 어떻게 쓰나" 를 같은 질의에
같은 순서로 받는다. 좋은 문장을 고르는 것이 아니라 쓰인 문장을 보이는 것이다. 판정은 읽는 쪽의 몫이다. 색인이 유일한
구조다. 임베딩도 예측 모델도 두지 않는다 (agipath 가 위키 1,475만 문장에서 그 길을 다 가 보고 역인덱스로 돌아왔다).

토큰: 어절에서 앞뒤 부호와 조사를 뗀 것 (core) 과, 한글 core 가 세 글자 이상이면 그 글자 두 개짜리 조각 (bigram).
core 는 낱말 그대로를 맞히고 bigram 은 `금융리스부채` 와 `리스부채`, `적용되며` 와 `적용된다` 처럼 붙고 활용한 자리를
맞힌다. 빈도가 높은 bigram 은 IDF 가 낮아 제 무게만큼만 들고, 문장 절반 넘게 나오는 토큰은 조회에서 뺀다
(MAX_DF_SHARE). 형태소 분석기는 쓰지 않는다 (제품 원칙).

만들기: 문서를 차례로 읽으며 문장 표와 위치 표는 바로 파일에 쓰고, postings 는 SHARD_SENTENCES 문장마다 조각 파일로
내린 뒤 토큰 순으로 병합한다. 그래서 위키백과 1,300만 문장도 메모리에 다 들지 않고 만든다. 결과는 한 번에 만든 것과
바이트 단위로 같다 (조각 경계는 파일에 남지 않는다).

파일 (전부 결정적이라 같은 글에서 같은 바이트가 나온다. npm 판이 같은 파일을 읽고 같은 파일을 만든다):
- meta.json: format, kind, documents, sentences, tokens (전체 토큰 수. 평균 길이는 조회 때 나눈다), terms
- sentences.tsv: 문장마다 `출처 \\t 글`. 줄 번호가 문장 번호다. 같은 문장 (공백을 모으고 숫자를 0 으로 바꾼 꼴이 같은
  것) 은 하나로 접고 처음 본 글과 출처를 둔다. 실측: 사업보고서 961편에서 문장의 47.4% 가 다른 문서에도 있었다.
- offsets.bin: 문장마다 sentences.tsv 안의 바이트 위치 (8바이트 little endian). 번호로 바로 읽는다.
- lengths.bin: 문장마다 토큰 수 (4바이트 little endian). BM25 의 길이 보정에 쓰므로 통째로 든다.
- documents.bin: 문장마다 그 문장이 나온 문서 수 (4바이트 little endian). 결과에 `문서 N편` 으로 보인다.
- terms.tsv: `토큰 \\t 문서 빈도 \\t postings.bin 위치 \\t 바이트 수`. 토큰 순 (코드 포인트 순).
- termOffsets.bin: 토큰마다 terms.tsv 안의 바이트 위치 (8바이트 little endian). 토큰 표를 통째로 읽지 않고 이 위치로
  이분 탐색한다. 실측: 961편 색인의 토큰 표 12 MB 를 읽는 데 조회 시간 1.5초 가운데 1초가 들었다 (2026-09-19).
- postings.bin: 토큰마다 (문장 번호 차이, 빈도) 를 LEB128 부호 없는 varint 로 이어 쓴 것.

순서: BM25 (k1 1.5, b 0.75) 값 내림차순, 같으면 문장 번호 오름차순. 이 값은 질의와 문장의 낱말 겹침이지 글의 좋고 나쁨이
아니다. 두 판의 log 가 마지막 자리에서 다를 수 있어 값을 SCORE_SCALE 배의 정수로 내린 뒤 견준다 (npm 판과 같은 셈).

함께 쓰는 말 (collocations): 표를 따로 만들지 않고 조회 때 그 낱말의 postings 에서 COLLOCATION_SAMPLE 문장을 읽어 바로
앞뒤 어절을 센다. 뒤에 오는 용언 (꼬리 사전으로 어간을 뗀 것), 뒤에 오는 명사, 앞에 오는 명사를 문서 수로 세어 상위만
보인다. 원시 횟수가 아니라 문서 수인 까닭은 한 문서의 되풀이가 관용이 아니기 때문이고, 표본을 자르는 까닭은 `회사` 같은
흔한 낱말의 postings 가 수십만이기 때문이다. 앞에서부터가 아니라 일정 간격으로 (stride) 고르므로 말뭉치 앞쪽 문서에
쏠리지 않는다. 간격은 postings 수로 정해지니 표본은 여전히 결정적이다.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import math
import re
import sys
from array import array
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from ..analysis import splitSentences
from ..analysis.tokenize import COPULA, EDGE_PUNCTUATION, isBareNoun, josaSet, nonNouns, stripJosa, tailOf, words
from ..data import loadLines

FORMAT = 3
K1 = 1.5
B = 0.75
SCORE_SCALE = 1_000_000
MAX_DF_SHARE = 0.5
MIN_FILTER_SENTENCES = 1000
"""이보다 문장이 적은 색인은 흔한 토큰도 거르지 않는다. 걸러 얻는 것은 큰 postings 를 안 읽는 시간뿐인데 작은 색인에서는
그 시간이 없고, 문장 몇 개짜리 색인에서는 모든 토큰이 절반을 넘어 아무것도 안 나온다 (검증 실측, 2026-09-19)."""
SHARD_SENTENCES = 250_000
"""postings 를 조각 파일로 내리는 문장 수. 조각 하나가 토큰 1천만 개 안팎이라 메모리 몇백 MB 다."""
COLLOCATION_SAMPLE = 4000
"""함께 쓰는 말을 셀 때 읽는 문장 수 상한. 문장 하나 읽기가 디스크 자리 이동이라 수백 µs 다. 위키백과 색인 (문장
884만, 문장 파일 1.4 GB) 에서 4,000이 2초 안팎이다 (2026-09-19)."""
COLLOCATION_TOP = 8
PREDICATE_STEMS = ("하였", "되었", "시켰", "했", "됐", "하", "되")
"""꼬리를 뗀 뒤 남는 활용 조각. `감소하였습니다` 는 꼬리 `습니다` 를 떼면 `감소하였` 이라 `하였` 을 더 떼어 `감소` 로 센다."""
PREDICATE_TAILS = ("하지", "되지", "하거나", "되거나", "하기", "되기")
"""꼬리 사전 (verbTails.txt) 에 없지만 이웃으로 셀 때 용언인 꼴. `인식하지 않는다` 의 인식하지 가 명사로 세어존 자리다."""
HANGUL_WORD = re.compile(r"^[가-힣]+$")
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
JSONL_SUFFIX = ".jsonl"
"""큰 말뭉치의 꼴. 줄마다 {"source": 출처, "text": 글} 하나가 문서 하나다. 위키백과처럼 문서가 수십만이면 파일 하나로 둔다."""
FILES = (
    "meta.json",
    "sentences.tsv",
    "offsets.bin",
    "lengths.bin",
    "documents.bin",
    "terms.tsv",
    "termOffsets.bin",
    "postings.bin",
)


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


def queryCores(text: str) -> list[str]:
    """함께 쓰는 말을 물을 낱말. 질의의 한글 어절 (조사를 뗀 것) 가운데 두 글자 이상, 차례대로 겹치지 않게."""
    found: list[str] = []
    for raw in normalized(text).split():
        core = stripJosa(raw.strip(EDGE_PUNCTUATION))
        if len(core) >= 2 and HANGUL.search(core) and core not in found:
            found.append(core)
    return found


def sentenceKey(text: str) -> str:
    """같은 문장으로 접는 꼴. 공백을 하나로, 숫자를 0 으로."""
    return DIGITS.sub("0", SPACE.sub(" ", text).strip())


def keyHash(key: str) -> int:
    """접는 꼴의 64비트 해시. 문장 1,300만 개의 키를 글자 그대로 들면 메모리가 수 GB 라 해시로 든다. 두 판이 같은 SHA-256."""
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "little")


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
    """폴더 (하위 포함) 의 txt 와 md 는 파일 하나가 문서 하나 (출처 = 파일 이름), jsonl 은 줄 하나가 문서 하나. 폴더 기준
    posix 경로의 코드 포인트 순이라 OS 와 판이 달라도 같은 차례다 (Windows 의 Path 비교는 대소문자를 접는다)."""
    paths = [
        path
        for path in folder.rglob("*")
        if (path.suffix.lower() in TEXT_SUFFIXES or path.suffix.lower() == JSONL_SUFFIX) and path.is_file()
    ]
    paths.sort(key=lambda path: path.relative_to(folder).as_posix())
    for path in paths:
        if path.suffix.lower() == JSONL_SUFFIX:
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.strip():
                        record = json.loads(line)
                        yield str(record["source"]), str(record["text"])
        else:
            yield path.stem, path.read_text(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class BuildResult:
    documents: int
    sentences: int
    terms: int


def littleEndian(values: array) -> bytes:
    """4바이트 부호 없는 정수 배열을 little endian 바이트로. 파일 꼴은 기계의 byte order 와 무관하다."""
    if values.itemsize != 4:
        return b"".join(value.to_bytes(4, "little") for value in values)
    if sys.byteorder == "big":
        values = array("I", values)
        values.byteswap()
    return values.tobytes()


def writeShard(work: Path, index: int, postingIds: dict[str, array], postingTfs: dict[str, array]) -> Path:
    """조각 하나. 토큰 순 terms 줄과 (절대 문장 번호, 빈도) varint 덩어리. 병합이 다시 읽는다."""
    lines: list[str] = []
    with (work / f"shard{index}.bin").open("wb") as handle:
        for term in sorted(postingIds):
            chunk = bytearray()
            for sentenceId, tf in zip(postingIds[term], postingTfs[term], strict=True):
                chunk += encodeVarint(sentenceId)
                chunk += encodeVarint(tf)
            offset = handle.tell()
            handle.write(chunk)
            lines.append(f"{term}\t{len(postingIds[term])}\t{offset}\t{len(chunk)}\n")
    path = work / f"shard{index}.tsv"
    path.write_bytes("".join(lines).encode("utf-8"))
    return path


def mergeShards(work: Path, shards: list[Path], target: Path) -> int:
    """조각들을 토큰 순으로 병합해 postings.bin, terms.tsv, termOffsets.bin 을 쓴다. 토큰 수를 돌려준다.

    조각 안의 문장 번호는 절대값이라 조각을 순서대로 이으면 문장 번호가 오르기만 한다. 그 차이를 다시 varint 로 쓰면
    한 번에 만든 것과 같은 바이트다."""
    handles = [(path.open(encoding="utf-8"), (work / path.name.replace(".tsv", ".bin")).open("rb")) for path in shards]
    heap: list[tuple[str, int, int, int, int]] = []
    for shardIndex, (lines, _) in enumerate(handles):
        line = lines.readline()
        if line:
            term, df, offset, size = line.rstrip("\n").split("\t")
            heapq.heappush(heap, (term, shardIndex, int(df), int(offset), int(size)))
    termCount = 0
    with (target / "postings.bin").open("wb") as postings, (target / "terms.tsv").open("wb") as terms:
        termOffsets = bytearray()
        termPosition = 0
        while heap:
            term = heap[0][0]
            pieces: list[tuple[int, int, int, int]] = []
            while heap and heap[0][0] == term:
                _, shardIndex, df, offset, size = heapq.heappop(heap)
                pieces.append((shardIndex, df, offset, size))
                line = handles[shardIndex][0].readline()
                if line:
                    nextTerm, nextDf, nextOffset, nextSize = line.rstrip("\n").split("\t")
                    heapq.heappush(heap, (nextTerm, shardIndex, int(nextDf), int(nextOffset), int(nextSize)))
            chunk = bytearray()
            previous = 0
            total = 0
            for shardIndex, df, offset, size in sorted(pieces):
                data = handles[shardIndex][1]
                data.seek(offset)
                values = decodeVarints(data.read(size))
                for index in range(0, len(values), 2):
                    chunk += encodeVarint(values[index] - previous)
                    chunk += encodeVarint(values[index + 1])
                    previous = values[index]
                total += df
            start = postings.tell()
            postings.write(chunk)
            line = f"{term}\t{total}\t{start}\t{len(chunk)}\n".encode()
            termOffsets += termPosition.to_bytes(8, "little")
            terms.write(line)
            termPosition += len(line)
            termCount += 1
    (target / "termOffsets.bin").write_bytes(bytes(termOffsets))
    for lines, data in handles:
        lines.close()
        data.close()
    return termCount


def buildIndex(kind: str, documents: Iterable[tuple[str, str]], root: Path, shardSentences: int = SHARD_SENTENCES) -> BuildResult:
    """(출처, 글) 들로 색인을 만들어 root/<kind>/ 에 쓴다. 있던 파일은 덮는다. 문서는 한 번만 읽는다.

    shardSentences 는 조각 크기다. 어떤 값이든 결과 바이트는 같다 (시험이 4 로 줄여 본다)."""
    target = root / kind
    target.mkdir(parents=True, exist_ok=True)
    work = target / "build"
    work.mkdir(exist_ok=True)
    seen: dict[int, int] = {}
    lengths = array("I")
    documentCounts = array("I")
    lastDocument = array("I")
    postingIds: dict[str, array] = {}
    postingTfs: dict[str, array] = {}
    shards: list[Path] = []
    documentCount = 0
    tokenTotal = 0
    position = 0
    with (target / "sentences.tsv").open("wb") as sentences, (target / "offsets.bin").open("wb") as offsets:
        for source, text in documents:
            documentCount += 1
            for sentence in sentencesOf(text):
                digest = keyHash(sentenceKey(sentence))
                known = seen.get(digest)
                if known is not None:
                    if lastDocument[known] != documentCount:
                        documentCounts[known] += 1
                        lastDocument[known] = documentCount
                    continue
                tokens = indexTokens(sentence)
                if not tokens:
                    continue
                sentenceId = len(lengths)
                seen[digest] = sentenceId
                line = f"{source}\t{sentence}\n".encode()
                offsets.write(position.to_bytes(8, "little"))
                sentences.write(line)
                position += len(line)
                lengths.append(len(tokens))
                documentCounts.append(1)
                lastDocument.append(documentCount)
                tokenTotal += len(tokens)
                counts: dict[str, int] = {}
                for token in tokens:
                    counts[token] = counts.get(token, 0) + 1
                for token, count in counts.items():
                    ids = postingIds.get(token)
                    if ids is None:
                        ids = postingIds[token] = array("I")
                        postingTfs[token] = array("H")
                    ids.append(sentenceId)
                    postingTfs[token].append(min(count, 65535))
                if len(lengths) % shardSentences == 0:
                    shards.append(writeShard(work, len(shards), postingIds, postingTfs))
                    postingIds, postingTfs = {}, {}
    if postingIds or not shards:
        shards.append(writeShard(work, len(shards), postingIds, postingTfs))
    termCount = mergeShards(work, shards, target)
    for path in work.iterdir():
        path.unlink()
    work.rmdir()
    (target / "lengths.bin").write_bytes(littleEndian(lengths))
    (target / "documents.bin").write_bytes(littleEndian(documentCounts))
    meta = {
        "format": FORMAT,
        "kind": kind,
        "documents": documentCount,
        "sentences": len(lengths),
        "tokens": tokenTotal,
        "terms": termCount,
    }
    (target / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return BuildResult(documentCount, len(lengths), termCount)


@dataclass(frozen=True)
class Hit:
    text: str
    documents: int
    """이 문장이 나온 문서 수."""
    source: str
    """처음 본 문서의 출처 (파일 이름이나 jsonl 의 source)."""
    score: int
    """BM25 값을 SCORE_SCALE 배 해 내린 정수. 낱말 겹침의 크기이지 글의 판정이 아니다."""


@dataclass(frozen=True)
class Collocation:
    term: str
    sampled: int
    """읽은 문장 수 (postings 앞에서부터, COLLOCATION_SAMPLE 까지)."""
    predicates: tuple[tuple[str, int], ...]
    """바로 뒤에 오는 용언의 어간과 문서 수."""
    following: tuple[tuple[str, int], ...]
    """바로 뒤에 오는 명사 어절과 문서 수."""
    preceding: tuple[tuple[str, int], ...]
    """바로 앞에 오는 명사 어절과 문서 수."""


@cache
def collocationStops() -> frozenset[str]:
    return frozenset(loadLines("collocationStops.txt"))


def predicateStem(core: str) -> str | None:
    """용언 어절의 어간. 꼬리 사전의 꼬리 (또는 PREDICATE_TAILS) 를 떼고 남은 활용 조각 (하였, 되었 …) 을 한 번 더 뗀다.
    용언이 아니면 None, 용언인데 어간이 한 글자면 빈 문자열 (`대하여` 의 대, `또한` 의 또. 결합이 아니라 문법이다)."""
    tail = tailOf(core, "verbTails.txt")
    if tail is None:
        tail = next((piece for piece in PREDICATE_TAILS if core.endswith(piece) and len(core) > len(piece)), None)
    if tail is None:
        return None
    stem = core[: -len(tail)]
    stripped = False
    for piece in PREDICATE_STEMS:
        if stem.endswith(piece) and len(stem) > len(piece):
            stem = stem[: -len(piece)]
            stripped = True
            break
    if len(tail) == 1 and not stripped:
        # 한 글자 꼬리 (서, 고, 며, 다) 는 `기업회계기준서` 같은 명사의 끝 글자와 갈리지 않는다. 하/되 가 앞에 있을 때만 용언이다.
        return None
    return stem if len(stem) >= 2 and HANGUL_WORD.match(stem) else ""


def neighbourOf(core: str) -> tuple[str, str] | None:
    """이웃 어절을 (부류, 낱말) 로. 부류는 predicate 나 noun. 연결 어절, 의존명사, 한 글자, 한글 아닌 것은 None."""
    if core in collocationStops() or core in nonNouns():
        return None
    stem = predicateStem(core)
    if stem is not None:
        return ("predicate", stem) if stem else None
    if len(core) >= 2 and HANGUL_WORD.match(core) and isBareNoun(core):
        return ("noun", core)
    return None


def topCounts(found: dict[str, set[str]]) -> tuple[tuple[str, int], ...]:
    ranked = sorted(((len(sources), term) for term, sources in found.items()), key=lambda item: (-item[0], item[1]))
    return tuple((term, count) for count, term in ranked[:COLLOCATION_TOP])


class UsageIndex:
    """폴더 하나의 색인. lengths.bin 과 documents.bin 만 통째로 들고 토큰 표와 문장과 postings 는 자리로 읽는다."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        if self.meta.get("format") != FORMAT:
            raise ValueError(f"{folder} 의 색인 format 이 {self.meta.get('format')} 이다. {FORMAT} 으로 다시 만든다")
        self.lengths = array("I")
        self.lengths.frombytes((folder / "lengths.bin").read_bytes())
        self.documentCounts = array("I")
        self.documentCounts.frombytes((folder / "documents.bin").read_bytes())

    @property
    def kind(self) -> str:
        return self.meta["kind"]

    @property
    def documents(self) -> int:
        return self.meta["documents"]

    @property
    def sentences(self) -> int:
        return self.meta["sentences"]

    def lineAt(self, name: str, offsetsName: str, index: int) -> str:
        """offsetsName 의 index 번째 위치에서 name 의 한 줄."""
        with (self.folder / offsetsName).open("rb") as handle:
            handle.seek(index * 8)
            offset = int.from_bytes(handle.read(8), "little")
        with (self.folder / name).open("rb") as handle:
            handle.seek(offset)
            return handle.readline().decode("utf-8").rstrip("\n")

    def lookup(self, term: str) -> tuple[int, int, int] | None:
        """(문서 빈도, postings 위치, 바이트 수). 토큰 표를 코드 포인트 순으로 이분 탐색한다. 없으면 None."""
        low, high = 0, int(self.meta["terms"])
        while low < high:
            middle = (low + high) // 2
            found, df, offset, size = self.lineAt("terms.tsv", "termOffsets.bin", middle).split("\t")
            if found < term:
                low = middle + 1
            elif found > term:
                high = middle
            else:
                return int(df), int(offset), int(size)
        return None

    def postings(self, term: str) -> list[tuple[int, int]]:
        found = self.lookup(term)
        return self.postingsAt(found[1], found[2]) if found else []

    def postingsAt(self, offset: int, size: int) -> list[tuple[int, int]]:
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
        source, text = self.lineAt("sentences.tsv", "offsets.bin", sentenceId).split("\t", 1)
        return int(self.documentCounts[sentenceId]), source, text

    def search(self, query: str, limit: int) -> list[Hit]:
        tokens = sorted(set(indexTokens(query)))
        if not tokens or not self.sentences:
            return []
        averageLength = self.meta["tokens"] / self.sentences
        scores: dict[int, float] = {}
        for token in tokens:
            found = self.lookup(token)
            if not found or (self.sentences >= MIN_FILTER_SENTENCES and found[0] > self.sentences * MAX_DF_SHARE):
                continue
            df, offset, size = found
            idf = math.log(1 + (self.sentences - df + 0.5) / (df + 0.5))
            for sentenceId, tf in self.postingsAt(offset, size):
                norm = tf + K1 * (1 - B + B * self.lengths[sentenceId] / averageLength)
                scores[sentenceId] = scores.get(sentenceId, 0.0) + idf * (tf * (K1 + 1)) / norm
        scaled = ((math.floor(score * SCORE_SCALE), sentenceId) for sentenceId, score in scores.items())
        ranked = sorted(scaled, key=lambda item: (-item[0], item[1]))
        hits = []
        for score, sentenceId in ranked[:limit]:
            documents, source, text = self.sentence(sentenceId)
            hits.append(Hit(text, documents, source, score))
        return hits

    def collocations(self, term: str) -> Collocation | None:
        """그 낱말 바로 앞뒤에 오는 말. 낱말이 색인에 없으면 None."""
        found = self.lookup(term)
        if not found:
            return None
        postings = self.postingsAt(found[1], found[2])
        stride = max(1, len(postings) // COLLOCATION_SAMPLE)
        sample = postings[::stride][:COLLOCATION_SAMPLE]
        predicates: dict[str, set[str]] = {}
        following: dict[str, set[str]] = {}
        preceding: dict[str, set[str]] = {}
        for sentenceId, _ in sample:
            _, source, text = self.sentence(sentenceId)
            tokens = words(text)
            for index, word in enumerate(tokens):
                if word.particle or stripJosa(word.core) != term:
                    continue
                if index + 1 < len(tokens) and not word.endsClause:
                    after = tokens[index + 1]
                    found = None if after.particle else neighbourOf(after.core)
                    if found is not None:
                        (predicates if found[0] == "predicate" else following).setdefault(found[1], set()).add(source)
                if index > 0:
                    before = tokens[index - 1]
                    found = None if before.endsClause or before.particle else neighbourOf(before.core)
                    if found is not None and found[0] == "noun":
                        preceding.setdefault(found[1], set()).add(source)
        return Collocation(term, len(sample), topCounts(predicates), topCounts(following), topCounts(preceding))


def loadIndex(kind: str, root: Path) -> UsageIndex | None:
    folder = root / kind
    if not all((folder / name).exists() for name in FILES):
        return None
    return UsageIndex(folder)


def listIndexes(root: Path) -> list[dict]:
    """root 아래 색인 폴더의 meta. 종류 이름 순."""
    found = []
    if not root.is_dir():
        return found
    for folder in sorted(root.iterdir(), key=lambda path: path.name):
        if folder.is_dir() and all((folder / name).exists() for name in FILES):
            found.append(json.loads((folder / "meta.json").read_text(encoding="utf-8")))
    return found
