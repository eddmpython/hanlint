// @ts-check
/**
 * 설정과 임계 기본값. 정본은 파이썬 config/settings.py 이고 여기는 같은 값을 든다. 필드 이름이 곧 설정 파일의 키다.
 * 기본값을 바꾸면 양쪽을 같은 작업에서 바꾼다. tests/parity 가 두 구현의 결과를 견준다.
 */

export const ANALYZERS = ["surface", "kiwi"];

/**
 * @typedef {object} Config
 * @property {Set<string>} disable 끌 규칙 이름
 * @property {string} analyzer
 * @property {string | null} keywordField
 * @property {string | null} profile
 * @property {Record<string, unknown[]>} dictionary
 * @property {string | null} source 설정을 읽은 파일. 기본값이면 null. loadConfig 가 채운다
 * @property {number} fragmentRun
 * @property {number} introMaxParagraphs
 * @property {number} headingUniformRatio
 * @property {number} nounPileMin
 * @property {number} endingRun
 * @property {number} factListMinSentences
 * @property {number} factListMaxMeanLength
 * @property {number} topicBreakMinSentences
 * @property {number} longSentenceMax
 */

/** @returns {Config} */
export function defaultConfig() {
  return {
    disable: new Set(),
    analyzer: "surface",
    keywordField: null,
    profile: null,
    dictionary: {},
    source: null,
    fragmentRun: 3,
    introMaxParagraphs: 4,
    headingUniformRatio: 0.75,
    nounPileMin: 5,
    endingRun: 4,
    factListMinSentences: 3,
    factListMaxMeanLength: 8.0,
    topicBreakMinSentences: 2,
    longSentenceMax: 30,
  };
}

/** @param {Config} config @param {string} ruleName */
export function enabled(config, ruleName) {
  return !config.disable.has(ruleName);
}

/** @param {Record<string, unknown>} data @returns {Config} */
export function configFromMapping(data) {
  const config = defaultConfig();
  for (const [key, value] of Object.entries(data)) {
    if (key === "disable") {
      config.disable = new Set(/** @type {string[]} */ (value));
    } else if (key === "analyzer") {
      if (!ANALYZERS.includes(/** @type {string} */ (value))) {
        throw new Error(`analyzer 는 ${ANALYZERS.join(" 또는 ")} 다: ${value}`);
      }
      config.analyzer = /** @type {string} */ (value);
    } else if (key === "dictionary") {
      config.dictionary = { .../** @type {Record<string, unknown[]>} */ (value) };
    } else if (key !== "source" && key in config) {
      config[key] = value;
    } else {
      throw new Error(`모르는 설정 키: ${key}. hanlint init 이 만드는 파일의 키만 쓴다`);
    }
  }
  return config;
}
