// @ts-check
/**
 * 분석기. 지문 생성이 필요로 하는 넷만 드러낸다. sentences, euiCount, longestNounRun, doublePassives.
 * npm 에는 의존성 0 의 surface 만 있다. kiwi 정밀 모드는 파이썬 패키지 (`pip install hanlint[kiwi]`) 에 있다.
 */
import { splitSentences } from "./surface/splitSentences.js";
import * as tokenize from "./surface/tokenize.js";

/**
 * @typedef {object} Analyzer
 * @property {string} name
 * @property {(text: string) => import("./surface/splitSentences.js").Sentence[]} sentences
 * @property {(sentence: string) => number} euiCount
 * @property {(sentence: string) => number} longestNounRun
 * @property {(sentence: string) => string[]} doublePassives
 */

/** @type {Analyzer} */
export const surfaceAnalyzer = {
  name: "surface",
  sentences: splitSentences,
  euiCount: tokenize.euiCount,
  longestNounRun: tokenize.longestNounRun,
  doublePassives: tokenize.doublePassives,
};

/** @param {string} name @returns {Analyzer} */
export function makeAnalyzer(name) {
  if (name === "surface") return surfaceAnalyzer;
  if (name === "kiwi") {
    throw new Error("kiwi 분석기는 파이썬 패키지에 있다 (pip install hanlint[kiwi]). npm 에서는 --analyzer surface 를 쓴다");
  }
  throw new Error(`모르는 분석기: ${name}. surface 를 쓴다`);
}
