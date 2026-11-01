// @ts-check
/**
 * 분석 부분. 문장 분리와 어절 판정을 글자 모양(어절과 꼬리 사전)만으로 한다. 형태소 분석기는 없다. 파이썬 analysis/__init__.py와 같다.
 * 글 분석에 필요한 것은 넷이다. splitSentences, euiCount와 euiAdjacent, longestNounRun, doublePassives.
 */
export { splitSentences } from "./splitSentences.js";
export { doublePassives, doublePassiveSpans, euiAdjacent, euiCount, longestNounRun, nounRuns } from "./tokenize.js";
