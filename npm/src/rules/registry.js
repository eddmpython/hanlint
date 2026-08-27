// @ts-check
/**
 * 규칙 등록부. 규칙 하나는 파일 하나이고 `name` 과 `run(doc, config)` 을 내보낸다. 파이썬은 폴더를 걸어 찾고
 * 여기는 목록으로 든다. test/rules.test.js 가 목록과 폴더와 ruleDocs.json 이 같은지 본다.
 * 기술서 (왜, 어디서, 고치기, 안 잡는 것) 는 파이썬 docstring 의 투영 data/ruleDocs.json 에서 읽는다.
 */
import { enabled } from "../config/settings.js";
import { loadRuleCategories, loadRuleDocs } from "../data/load.js";
import * as countMismatch from "./document/countMismatch.js";
import * as enoughOnce from "./document/enoughOnce.js";
import * as fieldEcho from "./document/fieldEcho.js";
import * as keywordHeading from "./document/keywordHeading.js";
import * as keywordMissing from "./document/keywordMissing.js";
import * as noQuestion from "./document/noQuestion.js";
import * as promiseRecall from "./document/promiseRecall.js";
import * as readerAbsent from "./document/readerAbsent.js";
import * as tableOddCell from "./document/tableOddCell.js";
import * as duplicateBlock from "./code/duplicateBlock.js";
import * as firstResultDistance from "./code/firstResultDistance.js";
import * as inputFileSource from "./code/inputFileSource.js";
import * as installImport from "./code/installImport.js";
import * as platformApi from "./code/platformApi.js";
import * as confusable from "./orthography/confusable.js";
import * as spacing from "./orthography/spacing.js";
import * as spelling from "./orthography/spelling.js";
import * as factListParagraph from "./paragraph/factListParagraph.js";
import * as paraFragment from "./paragraph/paraFragment.js";
import * as topicBreak from "./paragraph/topicBreak.js";
import * as cliche from "./sentence/cliche.js";
import * as hardWord from "./sentence/hardWord.js";
import * as connectorRepeat from "./sentence/connectorRepeat.js";
import * as danglingDeixis from "./sentence/danglingDeixis.js";
import * as draftHistory from "./sentence/draftHistory.js";
import * as numberOrphan from "./sentence/numberOrphan.js";
import * as dash from "./sentence/dash.js";
import * as deixis from "./sentence/deixis.js";
import * as doubleNegative from "./sentence/doubleNegative.js";
import * as doublePassive from "./sentence/doublePassive.js";
import * as ellipsis from "./sentence/ellipsis.js";
import * as endingRepeat from "./sentence/endingRepeat.js";
import * as euiChain from "./sentence/euiChain.js";
import * as fillerOpener from "./sentence/fillerOpener.js";
import * as imperativePeriod from "./sentence/imperativePeriod.js";
import * as japaneseLoan from "./sentence/japaneseLoan.js";
import * as longSentence from "./sentence/longSentence.js";
import * as negationRedefine from "./sentence/negationRedefine.js";
import * as nounPile from "./sentence/nounPile.js";
import * as redundantPair from "./sentence/redundantPair.js";
import * as translationese from "./sentence/translationese.js";
import * as blockUnread from "./structure/blockUnread.js";
import * as emojiBullet from "./structure/emojiBullet.js";
import * as headingQuestion from "./structure/headingQuestion.js";
import * as introImage from "./structure/introImage.js";
import * as loneSubheading from "./structure/loneSubheading.js";
import * as moreLater from "./structure/moreLater.js";
import * as headingSentence from "./structure/headingSentence.js";
import * as headingSkip from "./structure/headingSkip.js";
import * as headingUniform from "./structure/headingUniform.js";
import * as introLong from "./structure/introLong.js";
import * as sectionNoProse from "./structure/sectionNoProse.js";
import * as sectionResult from "./structure/sectionResult.js";

/**
 * @typedef {object} Rule
 * @property {string} name
 * @property {(doc: import("../fingerprint/build.js").DocumentPrint, config: import("../config/settings.js").Config) => import("./finding.js").Finding[]} run
 */

/** @type {Rule[]} */
export const RULES = [
  cliche,
  connectorRepeat,
  danglingDeixis,
  dash,
  draftHistory,
  numberOrphan,
  deixis,
  doubleNegative,
  doublePassive,
  ellipsis,
  endingRepeat,
  euiChain,
  fillerOpener,
  hardWord,
  imperativePeriod,
  japaneseLoan,
  longSentence,
  negationRedefine,
  nounPile,
  redundantPair,
  translationese,
  factListParagraph,
  paraFragment,
  topicBreak,
  blockUnread,
  emojiBullet,
  headingQuestion,
  introImage,
  loneSubheading,
  moreLater,
  headingSentence,
  headingSkip,
  headingUniform,
  introLong,
  sectionNoProse,
  sectionResult,
  countMismatch,
  enoughOnce,
  fieldEcho,
  tableOddCell,
  keywordHeading,
  keywordMissing,
  noQuestion,
  promiseRecall,
  readerAbsent,
  spelling,
  spacing,
  confusable,
  inputFileSource,
  installImport,
  duplicateBlock,
  firstResultDistance,
  platformApi,
];

const BY_NAME = new Map(RULES.map((rule) => [rule.name, rule]));

/** 이름 순. */
export function ruleNames() {
  return [...BY_NAME.keys()].sort();
}

/** @param {string} name */
export function ruleDoc(name) {
  const docs = loadRuleDocs();
  if (!(name in docs) || !BY_NAME.has(name)) throw new Error(`모르는 규칙: ${name}. hanlint rules 로 목록을 본다`);
  return docs[name];
}

/** @param {string} name */
export function ruleSummary(name) {
  return ruleDoc(name).split("\n")[0];
}

/**
 * 부류의 사람 이름. 파이썬 rules/registry.py 의 CATEGORY_TITLES 와 같은 값과 같은 순서다.
 * @type {Record<string, string>}
 */
export const CATEGORY_TITLES = {
  sentence: "문장 안에서 세는 것",
  paragraph: "문단 사이에서 세는 것",
  structure: "글의 짜임에서 세는 것",
  document: "두 자리를 대조해 세는 것",
  orthography: "표기와 띄어쓰기",
  code: "코드 블록 사이를 대조하는 것",
};

/** 규칙이 사는 부류. 정본은 파이썬 쪽 폴더이고 여기는 그 투영을 읽는다. @param {string} name */
export function ruleCategory(name) {
  const categories = loadRuleCategories();
  if (!(name in categories)) throw new Error(`모르는 규칙: ${name}. hanlint rules 로 목록을 본다`);
  return categories[name];
}

/**
 * 인라인 제어가 그 줄에서 그 규칙을 껐는가. `*` 는 전부다.
 * @param {import("./finding.js").Finding} f
 * @param {[string, number, number][]} disabled
 */
export function isDisabledAt(f, disabled) {
  return disabled.some(([name, start, end]) => (name === "*" || name === f.rule) && start <= f.line && f.line <= end);
}

/**
 * @param {import("../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../config/settings.js").Config} config
 * @returns {import("./finding.js").Finding[]}
 */
export function runAll(doc, config) {
  /** @type {import("./finding.js").Finding[]} */
  const findings = [];
  for (const name of ruleNames()) {
    if (!enabled(config, name)) continue;
    const rule = /** @type {Rule} */ (BY_NAME.get(name));
    for (const f of rule.run(doc, config)) if (!isDisabledAt(f, doc.disabled)) findings.push(f);
  }
  findings.sort((a, b) => a.line - b.line || (a.rule < b.rule ? -1 : a.rule > b.rule ? 1 : 0));
  return findings;
}
