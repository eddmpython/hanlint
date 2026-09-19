// @ts-check
/**
 * 문장 역인덱스. 뜻과 파일 꼴은 파이썬 usage/sentences.py 가 소유한다. 같은 글에서 같은 바이트를 만들고 같은 순서로 답한다.
 * 토큰은 조사를 뗀 어절과 한글 어절의 글자 두 개짜리 조각, 순서는 BM25 (k1 1.5, b 0.75) 값, 값은 SCORE_SCALE 배의
 * 정수로 내려 견준다 (두 판의 log 가 마지막 자리에서 다를 수 있다). 만들기는 문장 표를 바로 쓰고 postings 를 조각으로
 * 내렸다가 병합한다 (파이썬과 같은 조각 크기, 같은 병합 결과). 함께 쓰는 말은 조회 때 postings 앞 문장을 읽어 센다.
 */
import { createHash } from "node:crypto";
import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readdirSync,
  readFileSync,
  readSync,
  rmdirSync,
  statSync,
  unlinkSync,
  writeFileSync,
  writeSync,
} from "node:fs";
import { homedir } from "node:os";
import { basename, extname, join, relative, sep } from "node:path";

import { splitSentences } from "../analysis/splitSentences.js";
import { COPULA, EDGE_PUNCTUATION, isBareNoun, josaSet, nonNouns, stripJosa, tailOf, words } from "../analysis/tokenize.js";
import { loadLines } from "../data/load.js";
import { splitLines, splitWords, stripChars } from "../text.js";

export const FORMAT = 3;
const K1 = 1.5;
const B = 0.75;
export const SCORE_SCALE = 1_000_000;
const MAX_DF_SHARE = 0.5;
const MIN_FILTER_SENTENCES = 1000;
const SHARD_SENTENCES = 250_000;
const COLLOCATION_SAMPLE = 4000;
const COLLOCATION_TOP = 8;
const PREDICATE_STEMS = ["하였", "되었", "시켰", "했", "됐", "하", "되"];
const PREDICATE_TAILS = ["하지", "되지", "하거나", "되거나", "하기", "되기"];
const HANGUL_WORD = /^[가-힣]+$/;
const HANGUL = /[가-힣]/;
const ASCII_WORD = /[A-Za-z0-9]+/g;
const DIGITS = /[0-9]+/g;
const SPACE = /\s+/g;
const STRAY = /[\u001c-\u001f\u0085]/g;
const BOM = /\ufeff/g;
const BULLET = /^(?:(?:[-*·•※]|\([0-9a-z]{1,2}\)|[0-9]{1,2}[.)])\s+|(?:\([가-힣]\)|[가-힣][.)])\s*)/;
const TERMINAL = /(?<![0-9])[.!?]["'”’)\]]*$/;
const FENCE = "```";
const TEXT_SUFFIXES = new Set([".txt", ".md"]);
const JSONL_SUFFIX = ".jsonl";
export const FILES = [
  "meta.json",
  "sentences.tsv",
  "offsets.bin",
  "lengths.bin",
  "documents.bin",
  "terms.tsv",
  "termOffsets.bin",
  "postings.bin",
];

export function defaultRoot() {
  return join(homedir(), ".cache", "hanlint", "usage");
}

/** 파이썬 sorted() 와 같은 코드 포인트 순. @param {string} a @param {string} b */
export function compareCodePoints(a, b) {
  const left = [...a];
  const right = [...b];
  const count = Math.min(left.length, right.length);
  for (let i = 0; i < count; i++) {
    const delta = /** @type {number} */ (left[i].codePointAt(0)) - /** @type {number} */ (right[i].codePointAt(0));
    if (delta) return delta;
  }
  return left.length - right.length;
}

/** 두 판이 같은 글자를 보게 한다. 뜻은 파이썬 normalized 가 소유한다. @param {string} text */
export function normalized(text) {
  return text.replace(BOM, "").replace(STRAY, " ");
}

/** BM25 토큰. 조사를 뗀 어절과 한글 어절의 글자 두 개짜리 조각. 영문과 숫자는 부호에서 갈라 소문자로. @param {string} text @returns {string[]} */
export function indexTokens(text) {
  /** @type {string[]} */
  const found = [];
  for (const raw of splitWords(normalized(text))) {
    let core = stripChars(raw, EDGE_PUNCTUATION);
    if (!core || josaSet().has(core) || COPULA.test(core)) continue;
    core = stripJosa(core);
    if (HANGUL.test(core)) {
      found.push(core);
      const chars = [...core];
      if (chars.length >= 3) {
        for (let i = 0; i < chars.length - 1; i++) found.push(chars[i] + chars[i + 1]);
      }
    } else {
      for (const piece of core.match(ASCII_WORD) ?? []) found.push(piece.toLowerCase());
    }
  }
  return found;
}

/** 함께 쓰는 말을 물을 낱말. 뜻은 파이썬 queryCores 가 소유한다. @param {string} text @returns {string[]} */
export function queryCores(text) {
  /** @type {string[]} */
  const found = [];
  for (const raw of splitWords(normalized(text))) {
    const core = stripJosa(stripChars(raw, EDGE_PUNCTUATION));
    if ([...core].length >= 2 && HANGUL.test(core) && !found.includes(core)) found.push(core);
  }
  return found;
}

/** 같은 문장으로 접는 꼴. @param {string} text */
export function sentenceKey(text) {
  return text.replace(SPACE, " ").trim().replace(DIGITS, "0");
}

/** 접는 꼴의 64비트 해시 (SHA-256 앞 8바이트, little endian). 파이썬 keyHash 와 같은 값이다. @param {string} key */
export function keyHash(key) {
  return createHash("sha256").update(key, "utf-8").digest().readBigUInt64LE(0);
}

/** 글의 산문 줄. 코드 펜스 안, 제목, 표 줄은 넘기고 목록 표시는 뗀다. @param {string} text @returns {string[]} */
export function paragraphsOf(text) {
  /** @type {string[]} */
  const found = [];
  let inFence = false;
  for (const line of splitLines(normalized(text))) {
    const stripped = line.trim();
    if (stripped.startsWith(FENCE)) {
      inFence = !inFence;
      continue;
    }
    if (inFence || !stripped || stripped.startsWith("#") || stripped.startsWith("|")) continue;
    found.push(stripped.replace(BULLET, ""));
  }
  return found;
}

/** @param {string} text @returns {string[]} */
export function sentencesOf(text) {
  /** @type {string[]} */
  const found = [];
  for (const paragraph of paragraphsOf(text)) {
    for (const sentence of splitSentences(paragraph)) {
      if (HANGUL.test(sentence.text) && TERMINAL.test(sentence.text)) found.push(sentence.text.replace(SPACE, " ").trim());
    }
  }
  return found;
}

/** @param {number} value @param {number[]} out */
function pushVarint(value, out) {
  while (true) {
    const byte = value & 0x7f;
    value = Math.floor(value / 128);
    if (value) out.push(byte | 0x80);
    else {
      out.push(byte);
      return;
    }
  }
}

/** @param {Uint8Array} data @returns {number[]} */
export function decodeVarints(data) {
  /** @type {number[]} */
  const values = [];
  let value = 0;
  let scale = 1;
  for (const byte of data) {
    value += (byte & 0x7f) * scale;
    if (byte & 0x80) scale *= 128;
    else {
      values.push(value);
      value = 0;
      scale = 1;
    }
  }
  return values;
}

/**
 * 폴더 (하위 포함) 의 txt 와 md 는 파일 하나가 문서 하나, jsonl 은 줄 하나가 문서 하나. 폴더 기준 posix 경로의 코드 포인트
 * 순이라 파이썬 readDocuments 와 같은 차례다. 큰 jsonl 을 통째로 들지 않게 generator 다.
 * @param {string} folder @returns {Generator<[string, string]>}
 */
export function* readDocuments(folder) {
  /** @type {string[]} */
  const paths = [];
  const walk = (/** @type {string} */ dir) => {
    for (const name of readdirSync(dir)) {
      const path = join(dir, name);
      const suffix = extname(name).toLowerCase();
      if (statSync(path).isDirectory()) walk(path);
      else if (TEXT_SUFFIXES.has(suffix) || suffix === JSONL_SUFFIX) paths.push(path);
    }
  };
  walk(folder);
  const posix = (/** @type {string} */ path) => relative(folder, path).split(sep).join("/");
  paths.sort((a, b) => compareCodePoints(posix(a), posix(b)));
  for (const path of paths) {
    if (extname(path).toLowerCase() === JSONL_SUFFIX) {
      yield* readJsonl(path);
    } else {
      yield [basename(path, extname(path)), readFileSync(path, "utf-8")];
    }
  }
}

/** jsonl 을 줄 단위로 읽는다. 위키백과처럼 1 GB 가 넘는 파일을 한 번에 들지 않는다. @param {string} path @returns {Generator<[string, string]>} */
function* readJsonl(path) {
  const fd = openSync(path, "r");
  const chunk = Buffer.alloc(1 << 20);
  let rest = Buffer.alloc(0);
  try {
    while (true) {
      const read = readSync(fd, chunk, 0, chunk.length, null);
      if (!read) break;
      let data = Buffer.concat([rest, chunk.subarray(0, read)]);
      let start = 0;
      while (true) {
        const end = data.indexOf(0x0a, start);
        if (end < 0) break;
        const line = data.subarray(start, end).toString("utf-8");
        start = end + 1;
        if (line.trim()) {
          const record = JSON.parse(line);
          yield [String(record.source), String(record.text)];
        }
      }
      rest = Buffer.from(data.subarray(start));
    }
    const line = rest.toString("utf-8");
    if (line.trim()) {
      const record = JSON.parse(line);
      yield [String(record.source), String(record.text)];
    }
  } finally {
    closeSync(fd);
  }
}

/** @param {number[]} values */
function littleEndian(values) {
  const bytes = Buffer.alloc(values.length * 4);
  values.forEach((value, index) => bytes.writeUInt32LE(value, index * 4));
  return bytes;
}

/**
 * 조각 하나. 토큰 순 terms 줄과 (절대 문장 번호, 빈도) varint 덩어리. 뜻은 파이썬 writeShard 가 소유한다.
 * @param {string} work @param {number} index @param {Map<string, number[]>} postingIds @param {Map<string, number[]>} postingTfs
 */
function writeShard(work, index, postingIds, postingTfs) {
  const terms = [...postingIds.keys()].sort(compareCodePoints);
  /** @type {string[]} */
  const lines = [];
  /** @type {Buffer[]} */
  const chunks = [];
  let offset = 0;
  for (const term of terms) {
    const ids = /** @type {number[]} */ (postingIds.get(term));
    const tfs = /** @type {number[]} */ (postingTfs.get(term));
    /** @type {number[]} */
    const bytes = [];
    ids.forEach((sentenceId, at) => {
      pushVarint(sentenceId, bytes);
      pushVarint(tfs[at], bytes);
    });
    chunks.push(Buffer.from(bytes));
    lines.push(`${term}\t${ids.length}\t${offset}\t${bytes.length}\n`);
    offset += bytes.length;
  }
  writeFileSync(join(work, `shard${index}.bin`), Buffer.concat(chunks));
  const path = join(work, `shard${index}.tsv`);
  writeFileSync(path, lines.join(""), "utf-8");
  return path;
}

/** 조각의 terms 줄을 차례로 주는 읽개. @param {string} path */
function shardLines(path) {
  const lines = splitLines(readFileSync(path, "utf-8"));
  let at = 0;
  return () => {
    if (at >= lines.length) return null;
    const [term, df, offset, size] = lines[at++].split("\t");
    return { term, df: Number(df), offset: Number(offset), size: Number(size) };
  };
}

/**
 * 조각들을 토큰 순으로 병합해 postings.bin, terms.tsv, termOffsets.bin 을 쓴다. 뜻은 파이썬 mergeShards 가 소유한다.
 * @param {string} work @param {string[]} shards @param {string} target @returns {number}
 */
function mergeShards(work, shards, target) {
  const readers = shards.map((path) => shardLines(path));
  const dataFds = shards.map((path) => openSync(join(work, basename(path).replace(".tsv", ".bin")), "r"));
  /** @type {({ term: string, df: number, offset: number, size: number, shard: number } | null)[]} */
  const heads = readers.map((next, shard) => {
    const line = next();
    return line ? { ...line, shard } : null;
  });
  const postingsFd = openSync(join(target, "postings.bin"), "w");
  const termsFd = openSync(join(target, "terms.tsv"), "w");
  /** @type {Buffer[]} */
  const termOffsets = [];
  let termPosition = 0;
  let postingPosition = 0;
  let termCount = 0;
  try {
    while (true) {
      let term = null;
      for (const head of heads) {
        if (head && (term === null || compareCodePoints(head.term, term) < 0)) term = head.term;
      }
      if (term === null) break;
      /** @type {number[]} */
      const bytes = [];
      let previous = 0;
      let total = 0;
      for (let shard = 0; shard < heads.length; shard++) {
        const head = heads[shard];
        if (!head || head.term !== term) continue;
        const buffer = Buffer.alloc(head.size);
        readSync(dataFds[shard], buffer, 0, head.size, head.offset);
        const values = decodeVarints(buffer);
        for (let index = 0; index < values.length; index += 2) {
          pushVarint(values[index] - previous, bytes);
          pushVarint(values[index + 1], bytes);
          previous = values[index];
        }
        total += head.df;
        const line = readers[shard]();
        heads[shard] = line ? { ...line, shard } : null;
      }
      const chunk = Buffer.from(bytes);
      writeSync(postingsFd, chunk);
      const line = Buffer.from(`${term}\t${total}\t${postingPosition}\t${chunk.length}\n`, "utf-8");
      postingPosition += chunk.length;
      const offsetBytes = Buffer.alloc(8);
      offsetBytes.writeBigUInt64LE(BigInt(termPosition), 0);
      termOffsets.push(offsetBytes);
      writeSync(termsFd, line);
      termPosition += line.length;
      termCount += 1;
    }
  } finally {
    closeSync(postingsFd);
    closeSync(termsFd);
    for (const fd of dataFds) closeSync(fd);
  }
  writeFileSync(join(target, "termOffsets.bin"), Buffer.concat(termOffsets));
  return termCount;
}

/**
 * [출처, 글] 들로 색인을 만들어 root/<kind>/ 에 쓴다. 문서는 한 번만 읽는다.
 * @param {string} kind @param {Iterable<[string, string]>} documents @param {string} root
 * @param {number} [shardSentences] 조각 크기. 어떤 값이든 결과 바이트는 같다
 * @returns {{ documents: number, sentences: number, terms: number }}
 */
export function buildIndex(kind, documents, root, shardSentences = SHARD_SENTENCES) {
  const target = join(root, kind);
  mkdirSync(target, { recursive: true });
  const work = join(target, "build");
  mkdirSync(work, { recursive: true });
  /** @type {Map<bigint, number>} */
  const seen = new Map();
  /** @type {number[]} */
  const lengths = [];
  /** @type {number[]} */
  const documentCounts = [];
  /** @type {number[]} */
  const lastDocument = [];
  /** @type {Map<string, number[]>} */
  let postingIds = new Map();
  /** @type {Map<string, number[]>} */
  let postingTfs = new Map();
  /** @type {string[]} */
  const shards = [];
  let documentCount = 0;
  let tokenTotal = 0;
  let position = 0;
  const sentencesFd = openSync(join(target, "sentences.tsv"), "w");
  const offsetsFd = openSync(join(target, "offsets.bin"), "w");
  try {
    for (const [source, text] of documents) {
      documentCount += 1;
      for (const sentence of sentencesOf(text)) {
        const digest = keyHash(sentenceKey(sentence));
        const known = seen.get(digest);
        if (known !== undefined) {
          if (lastDocument[known] !== documentCount) {
            documentCounts[known] += 1;
            lastDocument[known] = documentCount;
          }
          continue;
        }
        const tokens = indexTokens(sentence);
        if (!tokens.length) continue;
        const sentenceId = lengths.length;
        seen.set(digest, sentenceId);
        const line = Buffer.from(`${source}\t${sentence}\n`, "utf-8");
        const offsetBytes = Buffer.alloc(8);
        offsetBytes.writeBigUInt64LE(BigInt(position), 0);
        writeSync(offsetsFd, offsetBytes);
        writeSync(sentencesFd, line);
        position += line.length;
        lengths.push(tokens.length);
        documentCounts.push(1);
        lastDocument.push(documentCount);
        tokenTotal += tokens.length;
        /** @type {Map<string, number>} */
        const counts = new Map();
        for (const token of tokens) counts.set(token, (counts.get(token) ?? 0) + 1);
        for (const [token, count] of counts) {
          let ids = postingIds.get(token);
          if (!ids) {
            ids = [];
            postingIds.set(token, ids);
            postingTfs.set(token, []);
          }
          ids.push(sentenceId);
          /** @type {number[]} */ (postingTfs.get(token)).push(Math.min(count, 65535));
        }
        if (lengths.length % shardSentences === 0) {
          shards.push(writeShard(work, shards.length, postingIds, postingTfs));
          postingIds = new Map();
          postingTfs = new Map();
        }
      }
    }
  } finally {
    closeSync(sentencesFd);
    closeSync(offsetsFd);
  }
  if (postingIds.size || !shards.length) shards.push(writeShard(work, shards.length, postingIds, postingTfs));
  const termCount = mergeShards(work, shards, target);
  for (const name of readdirSync(work)) unlinkSync(join(work, name));
  rmdirSync(work);
  writeFileSync(join(target, "lengths.bin"), littleEndian(lengths));
  writeFileSync(join(target, "documents.bin"), littleEndian(documentCounts));
  const meta = { format: FORMAT, kind, documents: documentCount, sentences: lengths.length, tokens: tokenTotal, terms: termCount };
  writeFileSync(join(target, "meta.json"), `${JSON.stringify(meta, null, 2)}\n`, "utf-8");
  return { documents: documentCount, sentences: lengths.length, terms: termCount };
}

/** @typedef {{ text: string, documents: number, source: string, score: number }} Hit */
/** @typedef {{ term: string, sampled: number, predicates: [string, number][], following: [string, number][], preceding: [string, number][] }} Collocation */

/** @type {Set<string> | null} */
let stopCache = null;
function collocationStops() {
  if (!stopCache) stopCache = new Set(loadLines("collocationStops.txt"));
  return stopCache;
}

/**
 * 용언 어절의 어간. 뜻은 파이썬 predicateStem 이 소유한다. 용언이 아니면 null, 어간이 한 글자면 "".
 * @param {string} core @returns {string | null}
 */
export function predicateStem(core) {
  let tail = tailOf(core, "verbTails.txt");
  if (tail === null) tail = PREDICATE_TAILS.find((piece) => core.endsWith(piece) && core.length > piece.length) ?? null;
  if (tail === null) return null;
  let stem = core.slice(0, -tail.length);
  let stripped = false;
  for (const piece of PREDICATE_STEMS) {
    if (stem.endsWith(piece) && stem.length > piece.length) {
      stem = stem.slice(0, -piece.length);
      stripped = true;
      break;
    }
  }
  // 한 글자 꼬리는 명사의 끝 글자와 갈리지 않는다 (기업회계기준서). 하/되 가 앞에 있을 때만 용언이다.
  if ([...tail].length === 1 && !stripped) return null;
  return [...stem].length >= 2 && HANGUL_WORD.test(stem) ? stem : "";
}

/** 이웃 어절을 [부류, 낱말] 로. 뜻은 파이썬 neighbourOf 가 소유한다. @param {string} core @returns {["predicate" | "noun", string] | null} */
export function neighbourOf(core) {
  if (collocationStops().has(core) || nonNouns().has(core)) return null;
  const stem = predicateStem(core);
  if (stem !== null) return stem ? ["predicate", stem] : null;
  if ([...core].length >= 2 && HANGUL_WORD.test(core) && isBareNoun(core)) return ["noun", core];
  return null;
}

/** @param {Map<string, Set<string>>} found @returns {[string, number][]} */
function topCounts(found) {
  const ranked = [...found].map(([term, sources]) => /** @type {[string, number]} */ ([term, sources.size]));
  ranked.sort((a, b) => b[1] - a[1] || compareCodePoints(a[0], b[0]));
  return ranked.slice(0, COLLOCATION_TOP);
}

export class UsageIndex {
  /** @param {string} folder */
  constructor(folder) {
    this.folder = folder;
    this.meta = JSON.parse(readFileSync(join(folder, "meta.json"), "utf-8"));
    if (this.meta.format !== FORMAT) throw new Error(`${folder} 의 색인 format 이 ${this.meta.format} 이다. ${FORMAT} 으로 다시 만든다`);
    const lengthBytes = readFileSync(join(folder, "lengths.bin"));
    this.lengths = new Uint32Array(lengthBytes.buffer, lengthBytes.byteOffset, lengthBytes.length / 4);
    const documentBytes = readFileSync(join(folder, "documents.bin"));
    this.documentCounts = new Uint32Array(documentBytes.buffer, documentBytes.byteOffset, documentBytes.length / 4);
  }

  get kind() {
    return /** @type {string} */ (this.meta.kind);
  }

  get documents() {
    return /** @type {number} */ (this.meta.documents);
  }

  get sentences() {
    return /** @type {number} */ (this.meta.sentences);
  }

  /** @param {string} name @param {number} offset @param {number} size */
  readAt(name, offset, size) {
    const fd = openSync(join(this.folder, name), "r");
    try {
      const buffer = Buffer.alloc(size);
      const read = readSync(fd, buffer, 0, size, offset);
      return buffer.subarray(0, read);
    } finally {
      closeSync(fd);
    }
  }

  /** offsetsName 의 index 번째 위치에서 name 의 한 줄. @param {string} name @param {string} offsetsName @param {number} index */
  lineAt(name, offsetsName, index) {
    const offset = Number(this.readAt(offsetsName, index * 8, 8).readBigUInt64LE(0));
    const size = statSync(join(this.folder, name)).size;
    let span = 4096;
    let chunk = this.readAt(name, offset, Math.min(size - offset, span));
    while (chunk.indexOf(0x0a) < 0 && offset + span < size) {
      span *= 4;
      chunk = this.readAt(name, offset, Math.min(size - offset, span));
    }
    const end = chunk.indexOf(0x0a);
    return chunk.subarray(0, end < 0 ? chunk.length : end).toString("utf-8");
  }

  /**
   * [문서 빈도, postings 위치, 바이트 수]. 토큰 표를 코드 포인트 순으로 이분 탐색한다. 뜻은 파이썬 lookup 이 소유한다.
   * @param {string} term @returns {[number, number, number] | null}
   */
  lookup(term) {
    let low = 0;
    let high = Number(this.meta.terms);
    while (low < high) {
      const middle = Math.floor((low + high) / 2);
      const [found, df, offset, size] = this.lineAt("terms.tsv", "termOffsets.bin", middle).split("\t");
      const order = compareCodePoints(found, term);
      if (order < 0) low = middle + 1;
      else if (order > 0) high = middle;
      else return [Number(df), Number(offset), Number(size)];
    }
    return null;
  }

  /** @param {string} term @returns {[number, number][]} */
  postings(term) {
    const found = this.lookup(term);
    return found ? this.postingsAt(found[1], found[2]) : [];
  }

  /** @param {number} offset @param {number} size @returns {[number, number][]} */
  postingsAt(offset, size) {
    const values = decodeVarints(this.readAt("postings.bin", offset, size));
    /** @type {[number, number][]} */
    const result = [];
    let sentenceId = 0;
    for (let index = 0; index < values.length; index += 2) {
      sentenceId += values[index];
      result.push([sentenceId, values[index + 1]]);
    }
    return result;
  }

  /** (문서 수, 출처, 글). @param {number} sentenceId @returns {[number, string, string]} */
  sentence(sentenceId) {
    const line = this.lineAt("sentences.tsv", "offsets.bin", sentenceId);
    const first = line.indexOf("\t");
    return [this.documentCounts[sentenceId], line.slice(0, first), line.slice(first + 1)];
  }

  /** @param {string} query @param {number} limit @returns {Hit[]} */
  search(query, limit) {
    const tokens = [...new Set(indexTokens(query))].sort(compareCodePoints);
    if (!tokens.length || !this.sentences) return [];
    const averageLength = this.meta.tokens / this.sentences;
    /** @type {Map<number, number>} */
    const scores = new Map();
    for (const token of tokens) {
      const found = this.lookup(token);
      if (!found || (this.sentences >= MIN_FILTER_SENTENCES && found[0] > this.sentences * MAX_DF_SHARE)) continue;
      const [df, offset, size] = found;
      const idf = Math.log(1 + (this.sentences - df + 0.5) / (df + 0.5));
      for (const [sentenceId, tf] of this.postingsAt(offset, size)) {
        const norm = tf + K1 * (1 - B + (B * this.lengths[sentenceId]) / averageLength);
        scores.set(sentenceId, (scores.get(sentenceId) ?? 0) + (idf * (tf * (K1 + 1))) / norm);
      }
    }
    const ranked = [...scores].map(([sentenceId, score]) => [Math.floor(score * SCORE_SCALE), sentenceId]);
    ranked.sort((a, b) => b[0] - a[0] || a[1] - b[1]);
    return ranked.slice(0, limit).map(([score, sentenceId]) => {
      const [documents, source, text] = this.sentence(sentenceId);
      return { text, documents, source, score };
    });
  }

  /** 그 낱말 바로 앞뒤에 오는 말. 뜻은 파이썬 collocations 가 소유한다. @param {string} term @returns {Collocation | null} */
  collocations(term) {
    const found = this.lookup(term);
    if (!found) return null;
    const postings = this.postingsAt(found[1], found[2]);
    const stride = Math.max(1, Math.floor(postings.length / COLLOCATION_SAMPLE));
    const sample = postings.filter((_, index) => index % stride === 0).slice(0, COLLOCATION_SAMPLE);
    /** @type {Map<string, Set<string>>} */
    const predicates = new Map();
    /** @type {Map<string, Set<string>>} */
    const following = new Map();
    /** @type {Map<string, Set<string>>} */
    const preceding = new Map();
    const add = (/** @type {Map<string, Set<string>>} */ bucket, /** @type {string} */ key, /** @type {string} */ source) => {
      let sources = bucket.get(key);
      if (!sources) {
        sources = new Set();
        bucket.set(key, sources);
      }
      sources.add(source);
    };
    for (const [sentenceId] of sample) {
      const [, source, text] = this.sentence(sentenceId);
      const tokens = words(text);
      tokens.forEach((word, index) => {
        if (word.particle || stripJosa(word.core) !== term) return;
        if (index + 1 < tokens.length && !word.endsClause) {
          const after = tokens[index + 1];
          const found = after.particle ? null : neighbourOf(after.core);
          if (found !== null) add(found[0] === "predicate" ? predicates : following, found[1], source);
        }
        if (index > 0) {
          const before = tokens[index - 1];
          const found = before.endsClause || before.particle ? null : neighbourOf(before.core);
          if (found !== null && found[0] === "noun") add(preceding, found[1], source);
        }
      });
    }
    return { term, sampled: sample.length, predicates: topCounts(predicates), following: topCounts(following), preceding: topCounts(preceding) };
  }
}

/** @param {string} kind @param {string} root @returns {UsageIndex | null} */
export function loadIndex(kind, root) {
  const folder = join(root, kind);
  if (!FILES.every((name) => existsSync(join(folder, name)))) return null;
  return new UsageIndex(folder);
}

/** root 아래 색인 폴더의 meta. 종류 이름 순. @param {string} root @returns {Record<string, unknown>[]} */
export function listIndexes(root) {
  if (!existsSync(root) || !statSync(root).isDirectory()) return [];
  const found = [];
  for (const name of readdirSync(root).sort(compareCodePoints)) {
    const folder = join(root, name);
    if (statSync(folder).isDirectory() && FILES.every((file) => existsSync(join(folder, file)))) {
      found.push(JSON.parse(readFileSync(join(folder, "meta.json"), "utf-8")));
    }
  }
  return found;
}
