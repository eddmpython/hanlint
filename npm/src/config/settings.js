// @ts-check
/**
 * 설정과 임계 기본값. 정본은 파이썬 config/settings.py 이고 여기는 같은 값을 든다. 필드 이름이 곧 설정 파일의 키다.
 * 기본값을 바꾸면 양쪽을 같은 작업에서 바꾼다. tests/parity 가 두 구현의 결과를 견준다.
 */

/**
 * 글의 종류마다 처음부터 끄고 시작할 규칙. 정본은 파이썬 config/settings.py 의 PRESETS 다.
 * @type {Record<string, string[]>}
 */
export const PRESETS = {
  blog: [],
  report: ["noQuestion", "sectionResult", "firstResultDistance", "introImage", "moreLater"],
  docs: [
    "noQuestion",
    "sectionResult",
    "firstResultDistance",
    "introImage",
    "moreLater",
    "draftHistory",
    "blockUnread",
  ],
};

export const PRESET_NAMES = Object.keys(PRESETS);
/** 설정도 옵션도 없을 때의 종류. 이 이름일 때는 출력에 프리셋을 적지 않는다. */
export const DEFAULT_PRESET = PRESET_NAMES[0];

/**
 * @typedef {object} Config
 * @property {string} preset 글의 종류. PRESETS 가 정한 규칙을 처음부터 끈다
 * @property {Set<string>} disable 끌 규칙 이름
 * @property {string | null} keywordField
 * @property {string[]} introFields
 * @property {string[]} endingFields
 * @property {string | null} profile
 * @property {string | null} baseline
 * @property {Record<string, unknown[]>} dictionary
 * @property {string[]} ignoreFences 지문에서 뺄 펜스의 언어 표기. 장면 계약과 도표 원문은 코드 블록이 아니다
 * @property {string | null} source 설정을 읽은 파일. 기본값이면 null. loadConfig 가 채운다
 * @property {number} fragmentRun
 * @property {number} introMaxParagraphs
 * @property {number} headingUniformRatio
 * @property {number} headingSentenceMaxLevel
 * @property {number} bridgeRepeatMin
 * @property {number} nounPileMin
 * @property {number} endingRun
 * @property {number} factListMinSentences
 * @property {number} factListMaxMeanLength
 * @property {number} topicBreakMinSentences
 * @property {number} longSentenceMax
 * @property {number} duplicateBlockRatio
 * @property {number} firstResultMaxParagraphs
 * @property {number} sectionResultMinParagraphs
 * @property {number} introMaxImages
 * @property {number} headingQuestionRatio
 * @property {number} moreLaterMaxChars
 * @property {number} tableOddCellMinRows
 * @property {number} registerMinShare
 */

/** @returns {Config} */
export function defaultConfig() {
  return {
    preset: DEFAULT_PRESET,
    disable: new Set(),
    keywordField: null,
    introFields: [],
    endingFields: [],
    profile: null,
    baseline: null,
    dictionary: {},
    ignoreFences: [],
    source: null,
    fragmentRun: 3,
    introMaxParagraphs: 4,
    headingUniformRatio: 0.75,
    headingSentenceMaxLevel: 6,
    bridgeRepeatMin: 3,
    nounPileMin: 5,
    endingRun: 4,
    factListMinSentences: 3,
    factListMaxMeanLength: 8.0,
    topicBreakMinSentences: 2,
    longSentenceMax: 30,
    duplicateBlockRatio: 0.9,
    firstResultMaxParagraphs: 4,
    sectionResultMinParagraphs: 3,
    introMaxImages: 1,
    headingQuestionRatio: 0.5,
    moreLaterMaxChars: 150,
    tableOddCellMinRows: 4,
    // 기준 말뭉치에서 일관된 에세이 하위 5%는 0.7576, 실제 혼합 기사는 0.625였다.
    registerMinShare: 0.7,
  };
}

/** @param {Config} config @param {string} ruleName */
export function enabled(config, ruleName) {
  return !config.disable.has(ruleName) && !PRESETS[config.preset].includes(ruleName);
}

/** 지금 꺼져 있는 규칙 이름. 프리셋이 끈 것과 disable 이 끈 것을 합친다. @param {Config} config */
export function offRules(config) {
  return [...new Set([...PRESETS[config.preset], ...config.disable])].sort();
}

/** @param {Record<string, unknown>} data @returns {Config} */
export function configFromMapping(data) {
  const config = defaultConfig();
  for (const [key, value] of Object.entries(data)) {
    if (key === "disable") {
      config.disable = new Set(/** @type {string[]} */ (value));
    } else if (key === "analyzer") {
      // 0.0.7 까지의 키. hanlint init 이 surface 를 써 넣었으므로 그 값은 조용히 넘기고 다른 값은 빠졌다고 알린다.
      if (value !== "surface") throw new Error(`analyzer 설정은 빠졌다. 분석기는 표층 하나라 키를 지운다: ${value}`);
    } else if (key === "preset") {
      if (!(/** @type {string} */ (value) in PRESETS)) {
        throw new Error(`preset 은 ${PRESET_NAMES.join(", ")} 가운데 하나다: ${value}`);
      }
      config.preset = /** @type {string} */ (value);
    } else if (key === "dictionary") {
      config.dictionary = { .../** @type {Record<string, unknown[]>} */ (value) };
    } else if (key === "ignoreFences" || key === "introFields" || key === "endingFields") {
      if (!Array.isArray(value) || !value.every((item) => typeof item === "string")) {
        throw new Error(`${key} 는 문자열 배열이다: ${JSON.stringify(value)}`);
      }
      const names = value.map((item) => item.trim());
      config[key] = key === "ignoreFences" ? names.map((name) => name.toLowerCase()) : names;
    } else if (key !== "source" && key in config) {
      config[key] = value;
    } else {
      throw new Error(`모르는 설정 키: ${key}. hanlint init 이 만드는 파일의 키만 쓴다`);
    }
  }
  return config;
}
