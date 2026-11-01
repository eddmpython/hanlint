// @ts-check
/**
 * 용례(usage). 실제 글에서 단어가 어떻게 쓰였는지를 든다. 뜻은 파이썬 usage/가 정한다.
 * counts는 실리는 빈도표, sentences는 사용자 기계의 문장 역인덱스다.
 * fingerprint와 같은 단계다. rules와 cli가 이 부분을 쓰고, 이 부분은 analysis와 config와 data만 쓴다.
 */
export { attested, chainDocuments, conventional, patternDocuments, usageKindOf, usageTable } from "./counts.js";
export { UsageIndex, buildIndex, defaultRoot as defaultUsageRoot, indexTokens, listIndexes, loadIndex, queryCores, readDocuments } from "./sentences.js";
