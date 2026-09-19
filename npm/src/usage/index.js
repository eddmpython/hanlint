// @ts-check
/**
 * 용례 (usage). 실제 글에서 낱말이 어떻게 쓰였는지를 든다. 뜻은 파이썬 usage/ 가 소유한다.
 * counts 는 실리는 빈도표, sentences 는 사용자 기계의 문장 역인덱스다.
 * fingerprint 와 같은 층이다. rules 와 cli 가 쓰고, analysis 와 config 와 data 만 쓴다.
 */
export { attested, chainDocuments, conventional, patternDocuments, usageKindOf, usageTable } from "./counts.js";
export { UsageIndex, buildIndex, defaultRoot as defaultUsageRoot, indexTokens, loadIndex, readDocuments } from "./sentences.js";
