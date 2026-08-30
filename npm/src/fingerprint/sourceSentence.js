// @ts-check
/** 평문 지문의 문장을 마크다운 표식을 보존한 원문 문장에 다시 맞춘다. */
import { splitSentences } from "../analysis/splitSentences.js";
import { plainText } from "../document/plainText.js";

/**
 * @param {import("./build.js").DocumentPrint} document
 * @returns {Map<number, string>}
 */
export function sourceSentenceTexts(document) {
  /** @type {Map<number, import("./build.js").SentencePrint[]>} */
  const byBlock = new Map();
  for (const sentence of document.sentences) {
    const found = byBlock.get(sentence.blockIndex) ?? [];
    found.push(sentence);
    byBlock.set(sentence.blockIndex, found);
  }
  const blocks = new Map(document.blocks.map((block) => [block.index, block]));
  const result = new Map();
  for (const [blockIndex, plainSentences] of byBlock) {
    const block = blocks.get(blockIndex);
    if (!block) continue;
    const rawSentences = splitSentences(block.text);
    if (rawSentences.length !== plainSentences.length) continue;
    if (plainSentences.some((plain, index) => plainText(rawSentences[index].text) !== plain.text)) continue;
    plainSentences.forEach((plain, index) => result.set(plain.index, rawSentences[index].text));
  }
  return result;
}

/**
 * @param {import("./build.js").DocumentPrint} document
 * @param {import("./build.js").SentencePrint} sentence
 */
export function sourceSentenceText(document, sentence) {
  return sourceSentenceTexts(document).get(sentence.index);
}
