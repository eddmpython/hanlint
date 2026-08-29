// @ts-check
/**
 * 분석 층. 문장 분리와 어절 판정을 표층 (어절과 꼬리 사전) 으로 한다. 형태소 분석기는 없다. 파이썬 analysis/__init__.py 와 같다.
 * 지문이 필요로 하는 것은 넷이다. splitSentences, euiCount 와 euiAdjacent, longestNounRun, doublePassives.
 */
export { splitSentences } from "./splitSentences.js";
export { doublePassives, euiAdjacent, euiCount, longestNounRun } from "./tokenize.js";
