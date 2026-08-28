// @ts-check
import { fitJosa } from "../../analysis/grammar/josa.js";
import { PROSE } from "../../document/model.js";
import { matchedTexts } from "../../fingerprint/markers.js";
import { NOTICE, SENTENCE, finding } from "../finding.js";

export const name = "numberOrphan";
const NUMBER = /\d[\d,]*(?:\.\d+)?/g;
const RANGE = /(\d[\d,]*(?:\.\d+)?)[^\s.!?]{0,4}\s?에서\s?(\d[\d,]*(?:\.\d+)?)[^\s.!?]{0,4}\s?(?:로|으로)/g;
/** 한 자리 수는 재는 값이 아니라 세는 말이라 뺀다. */
const MIN_DIGITS = 2;
/** 기준값 앞 몇 글자에서 출처를 밝히는 말을 찾는가. */
const ANCHOR_WINDOW = 12;

/** @param {string} text @returns {Set<string>} */
function numeralsIn(text) {
  const found = new Set();
  for (const match of text.matchAll(NUMBER)) found.add(match[0].replaceAll(",", ""));
  return found;
}

/** @param {string} numeral */
function isMeasured(numeral) {
  return numeral.includes(".") || numeral.replaceAll(".", "").length >= MIN_DIGITS;
}

/** 값 바로 앞이 그 값이 어디서 온 것인지 말하고 있는가. @param {string} text @param {number} start */
function isAnchored(text, start) {
  return matchedTexts(text.slice(Math.max(0, start - ANCHOR_WINDOW), start), "baselineAnchors.txt").length > 0;
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  void config;
  const findings = [];
  /** @type {Set<string>} */
  const seen = new Set();
  const pending = doc.blocks.filter((block) => block.kind !== PROSE).sort((a, b) => a.startLine - b.startLine || a.index - b.index);
  let position = 0;
  for (const sentence of doc.sentences) {
    while (position < pending.length && pending[position].startLine < sentence.line) {
      for (const numeral of numeralsIn(pending[position].text)) seen.add(numeral);
      position += 1;
    }
    for (const match of sentence.text.matchAll(RANGE)) {
      const base = match[1].replaceAll(",", "");
      if (!isMeasured(base) || base === match[2].replaceAll(",", "")) continue;
      const start = /** @type {number} */ (match.index);
      if (seen.has(base) || numeralsIn(sentence.text.slice(0, start)).has(base)) continue;
      if (isAnchored(sentence.text, start)) continue;
      findings.push(
        finding(name, sentence.line, sentence.text, `\`${base}\` ${fitJosa(base, "가")} 여기서 처음 나오는 값이다. 무엇에서 올라간 것인지 알 수 없다. 그 값이 어디서 나왔는지 밝힌다`, null, NOTICE, SENTENCE, sentence.index),
      );
    }
    for (const numeral of numeralsIn(sentence.text)) seen.add(numeral);
  }
  return findings;
}
