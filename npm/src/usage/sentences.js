// @ts-check
/**
 * 문장 역인덱스. 뜻과 파일 꼴은 파이썬 usage/sentences.py 가 소유한다. 같은 글에서 같은 바이트를 만들고 같은 순서로 답한다.
 * 토큰은 조사를 뗀 어절과 한글 어절의 글자 두 개짜리 조각, 순서는 BM25 (k1 1.5, b 0.75) 값, 값은 SCORE_SCALE 배의
 * 정수로 내려 견준다 (두 판의 log 가 마지막 자리에서 다를 수 있다).
 */
import { closeSync, existsSync, mkdirSync, openSync, readdirSync, readFileSync, readSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { basename, extname, join, relative, sep } from "node:path";

import { splitSentences } from "../analysis/splitSentences.js";
import { COPULA, EDGE_PUNCTUATION, josaSet, stripJosa } from "../analysis/tokenize.js";
import { splitLines, splitWords, stripChars } from "../text.js";

export const FORMAT = 1;
const K1 = 1.5;
const B = 0.75;
export const SCORE_SCALE = 1_000_000;
const MAX_DF_SHARE = 0.5;
const MIN_FILTER_SENTENCES = 1000;
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
export const FILES = ["meta.json", "sentences.tsv", "offsets.bin", "lengths.bin", "terms.tsv", "postings.bin"];

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

/** 같은 문장으로 접는 꼴. @param {string} text */
export function sentenceKey(text) {
  return text.replace(SPACE, " ").trim().replace(DIGITS, "0");
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

/** 폴더 (하위 포함) 의 txt 와 md. [출처, 글] 을 경로 순으로. @param {string} folder @returns {[string, string][]} */
export function readDocuments(folder) {
  /** @type {string[]} */
  const paths = [];
  const walk = (/** @type {string} */ dir) => {
    for (const name of readdirSync(dir)) {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) walk(path);
      else if (TEXT_SUFFIXES.has(extname(name).toLowerCase())) paths.push(path);
    }
  };
  walk(folder);
  // 폴더 기준 posix 경로의 코드 포인트 순. 파이썬 readDocuments 와 같은 차례다.
  const posix = (/** @type {string} */ path) => relative(folder, path).split(sep).join("/");
  paths.sort((a, b) => compareCodePoints(posix(a), posix(b)));
  return paths.map((path) => [basename(path, extname(path)), readFileSync(path, "utf-8")]);
}

/**
 * [출처, 글] 들로 색인을 만들어 root/<kind>/ 에 쓴다.
 * @param {string} kind @param {Iterable<[string, string]>} documents @param {string} root
 * @returns {{ documents: number, sentences: number, terms: number }}
 */
export function buildIndex(kind, documents, root) {
  const target = join(root, kind);
  mkdirSync(target, { recursive: true });
  /** @type {Map<string, number>} */
  const sentenceIds = new Map();
  /** @type {string[]} */
  const texts = [];
  /** @type {string[]} */
  const sources = [];
  /** @type {number[]} */
  const lengths = [];
  /** @type {Set<string>[]} */
  const documentSets = [];
  /** @type {Map<string, number[]>} */
  const postingIds = new Map();
  /** @type {Map<string, number[]>} */
  const postingTfs = new Map();
  let documentCount = 0;
  let tokenTotal = 0;
  for (const [source, text] of documents) {
    documentCount += 1;
    for (const sentence of sentencesOf(text)) {
      const key = sentenceKey(sentence);
      const known = sentenceIds.get(key);
      if (known !== undefined) {
        documentSets[known].add(source);
        continue;
      }
      const tokens = indexTokens(sentence);
      if (!tokens.length) continue;
      const sentenceId = texts.length;
      sentenceIds.set(key, sentenceId);
      texts.push(sentence);
      sources.push(source);
      lengths.push(tokens.length);
      documentSets.push(new Set([source]));
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
    }
  }
  /** @type {Buffer[]} */
  const sentenceChunks = [];
  const offsets = Buffer.alloc(texts.length * 8);
  let position = 0;
  for (let sentenceId = 0; sentenceId < texts.length; sentenceId++) {
    offsets.writeBigUInt64LE(BigInt(position), sentenceId * 8);
    const chunk = Buffer.from(`${documentSets[sentenceId].size}\t${sources[sentenceId]}\t${texts[sentenceId]}\n`, "utf-8");
    sentenceChunks.push(chunk);
    position += chunk.length;
  }
  writeFileSync(join(target, "sentences.tsv"), Buffer.concat(sentenceChunks));
  writeFileSync(join(target, "offsets.bin"), offsets);
  const lengthBytes = Buffer.alloc(lengths.length * 4);
  lengths.forEach((length, index) => lengthBytes.writeUInt32LE(length, index * 4));
  writeFileSync(join(target, "lengths.bin"), lengthBytes);
  const terms = [...postingIds.keys()].sort(compareCodePoints);
  /** @type {string[]} */
  const termLines = [];
  /** @type {Buffer[]} */
  const postingChunks = [];
  let offset = 0;
  for (const term of terms) {
    const ids = /** @type {number[]} */ (postingIds.get(term));
    const tfs = /** @type {number[]} */ (postingTfs.get(term));
    /** @type {number[]} */
    const bytes = [];
    let previous = 0;
    ids.forEach((sentenceId, index) => {
      pushVarint(sentenceId - previous, bytes);
      pushVarint(tfs[index], bytes);
      previous = sentenceId;
    });
    postingChunks.push(Buffer.from(bytes));
    termLines.push(`${term}\t${ids.length}\t${offset}\t${bytes.length}\n`);
    offset += bytes.length;
  }
  writeFileSync(join(target, "postings.bin"), Buffer.concat(postingChunks));
  writeFileSync(join(target, "terms.tsv"), termLines.join(""), "utf-8");
  const meta = { format: FORMAT, kind, documents: documentCount, sentences: texts.length, tokens: tokenTotal, terms: terms.length };
  writeFileSync(join(target, "meta.json"), `${JSON.stringify(meta, null, 2)}\n`, "utf-8");
  return { documents: documentCount, sentences: texts.length, terms: terms.length };
}

/** @typedef {{ text: string, documents: number, source: string, score: number }} Hit */

export class UsageIndex {
  /** @param {string} folder */
  constructor(folder) {
    this.folder = folder;
    this.meta = JSON.parse(readFileSync(join(folder, "meta.json"), "utf-8"));
    if (this.meta.format !== FORMAT) throw new Error(`${folder} 의 색인 format 이 ${this.meta.format} 이다. ${FORMAT} 으로 다시 만든다`);
    /** @type {Map<string, [number, number, number]>} */
    this.terms = new Map();
    for (const line of splitLines(readFileSync(join(folder, "terms.tsv"), "utf-8"))) {
      const [term, df, offset, size] = line.split("\t");
      this.terms.set(term, [Number(df), Number(offset), Number(size)]);
    }
    const lengthBytes = readFileSync(join(folder, "lengths.bin"));
    this.lengths = new Uint32Array(lengthBytes.buffer, lengthBytes.byteOffset, lengthBytes.length / 4);
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

  /** @param {string} term @returns {[number, number][]} */
  postings(term) {
    const found = this.terms.get(term);
    if (!found) return [];
    const [, offset, size] = found;
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
    const offset = Number(this.readAt("offsets.bin", sentenceId * 8, 8).readBigUInt64LE(0));
    const size = statSync(join(this.folder, "sentences.tsv")).size;
    let span = 4096;
    let chunk = this.readAt("sentences.tsv", offset, Math.min(size - offset, span));
    while (chunk.indexOf(0x0a) < 0 && offset + span < size) {
      span *= 4;
      chunk = this.readAt("sentences.tsv", offset, Math.min(size - offset, span));
    }
    const end = chunk.indexOf(0x0a);
    const line = chunk.subarray(0, end < 0 ? chunk.length : end).toString("utf-8");
    const first = line.indexOf("\t");
    const second = line.indexOf("\t", first + 1);
    return [Number(line.slice(0, first)), line.slice(first + 1, second), line.slice(second + 1)];
  }

  /** @param {string} query @param {number} limit @returns {Hit[]} */
  search(query, limit) {
    const tokens = [...new Set(indexTokens(query))].sort(compareCodePoints);
    if (!tokens.length || !this.sentences) return [];
    const averageLength = this.meta.tokens / this.sentences;
    /** @type {Map<number, number>} */
    const scores = new Map();
    for (const token of tokens) {
      const found = this.terms.get(token);
      if (!found || (this.sentences >= MIN_FILTER_SENTENCES && found[0] > this.sentences * MAX_DF_SHARE)) continue;
      const df = found[0];
      const idf = Math.log(1 + (this.sentences - df + 0.5) / (df + 0.5));
      for (const [sentenceId, tf] of this.postings(token)) {
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
}

/** @param {string} kind @param {string} root @returns {UsageIndex | null} */
export function loadIndex(kind, root) {
  const folder = join(root, kind);
  if (!FILES.every((name) => existsSync(join(folder, name)))) return null;
  return new UsageIndex(folder);
}
