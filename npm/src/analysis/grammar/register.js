// @ts-check
/** 파이썬 `analysis/grammar/register.py`의 투영. 글의 문체를 판별하고 문장 끝 서술어를 맞춘다. */
import * as hangul from "./hangul.js";
import { HAEYO, HANDA, HAPNIDA, REGISTERS, parsePredicate, render } from "./ending.js";

export const MIXED = "섞임";
export const NONE = "없음";
const SENTENCE_END = /([가-힣]+)([.?!]+)(["”’\)\]]*)(?=\s|$)/g;
const WORD_BEFORE = /(\S+)\s+$/;
const SKIP_LINE = /^\s*(#|\||```|---)/;
const TEMPLATE_WORD = /\{([가-힣]+)\}/g;
const BARE_LINE_END = /([가-힣]+)$/gm;

/** @param {string} word */
export function registerOfWord(word) {
  if (word.endsWith("습니다") || (word.endsWith("니다") && word.length >= 3 && hangul.finalOf(word.at(-3)) === hangul.BIEUP)) {
    return HAPNIDA;
  }
  if (word.endsWith("요")) return HAEYO;
  if (word.endsWith("다")) return HANDA;
  return null;
}

/** @param {string} text */
export function lastWord(text) {
  const body = text.trimEnd().replace(/[.?!"”’\)\]」』]+$/, "");
  return /([가-힣]+)$/.exec(body)?.[1] ?? "";
}

/** @param {string[]} words @param {number} minShare @returns {[string, number]} */
export function documentRegister(words, minShare) {
  const counted = new Map();
  for (const word of words) {
    const found = registerOfWord(word);
    if (found) counted.set(found, (counted.get(found) ?? 0) + 1);
  }
  const total = [...counted.values()].reduce((sum, count) => sum + count, 0);
  if (!total) return [NONE, 0];
  const [register, count] = [...counted.entries()].sort((a, b) => b[1] - a[1] || REGISTERS.indexOf(b[0]) - REGISTERS.indexOf(a[0]))[0];
  const share = count / total;
  return [share >= minShare ? register : MIXED, share];
}

/** @param {string} line @param {string} target @returns {[string, number, number]} */
export function convertLine(line, target) {
  let converted = 0;
  let skipped = 0;
  const text = line.replace(SENTENCE_END, (whole, word, punct, close, offset) => {
    if (registerOfWord(word) === null) return whole;
    const before = WORD_BEFORE.exec(line.slice(0, offset));
    const value = parsePredicate(word, before ? before[1] : null);
    if (!value) {
      skipped += 1;
      return whole;
    }
    converted += 1;
    return render(value, target) + punct + close;
  });
  return [text, converted, skipped];
}

/** @param {string} text @param {string} target @returns {{text: string, converted: number, skipped: number}} */
export function convertRegister(text, target) {
  if (!REGISTERS.includes(target)) throw new Error(`모르는 문체: ${target}. ${REGISTERS.join(", ")} 가운데 하나다`);
  const out = [];
  let converted = 0;
  let skipped = 0;
  let inFence = false;
  for (const line of text.split("\n")) {
    if (line.trimStart().startsWith("```")) {
      inFence = !inFence;
      out.push(line);
      continue;
    }
    if (inFence || SKIP_LINE.test(line)) {
      out.push(line);
      continue;
    }
    const [changed, found, missed] = convertLine(line, target);
    out.push(changed);
    converted += found;
    skipped += missed;
  }
  return { text: out.join("\n"), converted, skipped };
}

/** 문형의 중괄호 속 활용 자리까지 문체를 바꾼다. @param {string} text @param {string} target */
export function convertTemplate(text, target) {
  const result = convertRegister(text, target);
  let converted = result.converted;
  let skipped = result.skipped;
  const bare = result.text.replace(BARE_LINE_END, (whole, word, offset) => {
    if (registerOfWord(word) === null) return whole;
    const lineStart = result.text.lastIndexOf("\n", offset) + 1;
    const before = WORD_BEFORE.exec(result.text.slice(lineStart, offset));
    const value = parsePredicate(word, before ? before[1] : null);
    if (!value) {
      skipped += 1;
      return whole;
    }
    converted += 1;
    return render(value, target);
  });
  const changed = bare.replace(TEMPLATE_WORD, (whole, word) => {
    if (registerOfWord(word) === null) return whole;
    const value = parsePredicate(word);
    if (!value) {
      skipped += 1;
      return whole;
    }
    converted += 1;
    return `{${render(value, target)}}`;
  });
  return { text: changed, converted, skipped };
}
