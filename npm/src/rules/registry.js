// @ts-check
/**
 * 규칙 목록. 규칙 하나는 파일 하나이고 `name`과 `run(doc, config)`을 내보낸다. 파이썬은 폴더를 걸어 찾고
 * 여기는 목록으로 든다. test/rules.test.js가 목록과 폴더와 ruleDocs.json이 같은지 본다.
 * 규칙 설명(왜, 어디서, 고치기, 안 잡는 것)은 파이썬 docstring을 옮긴 data/ruleDocs.json에서 읽는다.
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
import * as calqueFrame from "./sentence/calqueFrame.js";
import * as cliche from "./sentence/cliche.js";
import * as hardWord from "./sentence/hardWord.js";
import * as connectorRepeat from "./sentence/connectorRepeat.js";
import * as phraseRepeat from "./sentence/phraseRepeat.js";
import * as danglingDeixis from "./sentence/danglingDeixis.js";
import * as draftHistory from "./sentence/draftHistory.js";
import * as numberOrphan from "./sentence/numberOrphan.js";
import * as dash from "./sentence/dash.js";
import * as deixis from "./sentence/deixis.js";
import * as doubleNegative from "./sentence/doubleNegative.js";
import * as doublePassive from "./sentence/doublePassive.js";
import * as endingRepeat from "./sentence/endingRepeat.js";
import * as euiChain from "./sentence/euiChain.js";
import * as fillerOpener from "./sentence/fillerOpener.js";
import * as imperativePeriod from "./sentence/imperativePeriod.js";
import * as japaneseLoan from "./sentence/japaneseLoan.js";
import * as longSentence from "./sentence/longSentence.js";
import * as negationRedefine from "./sentence/negationRedefine.js";
import * as nounPile from "./sentence/nounPile.js";
import * as outsideProfile from "./sentence/outsideProfile.js";
import * as redundantPair from "./sentence/redundantPair.js";
import * as translationese from "./sentence/translationese.js";
import * as blockUnread from "./structure/blockUnread.js";
import * as bridgeRepeat from "./structure/bridgeRepeat.js";
import * as emojiBullet from "./structure/emojiBullet.js";
import * as introImage from "./structure/introImage.js";
import * as loneSubheading from "./structure/loneSubheading.js";
import * as moreLater from "./structure/moreLater.js";
import * as headingSentence from "./structure/headingSentence.js";
import * as headingSkip from "./structure/headingSkip.js";
import * as headingUniform from "./structure/headingUniform.js";
import * as introLong from "./structure/introLong.js";
import * as sectionNoProse from "./structure/sectionNoProse.js";
import * as screenNarration from "./screen/screenNarration.js";
import * as screenSentence from "./screen/screenSentence.js";
import * as screenTone from "./screen/screenTone.js";
import * as screenWord from "./screen/screenWord.js";

/**
 * @typedef {object} Rule
 * @property {string} name
 * @property {string} mechanism 세는 방법. MECHANISMS의 키 하나
 * @property {(doc: import("../fingerprint/build.js").DocumentPrint, config: import("../config/settings.js").Config) => import("./finding.js").Finding[]} run
 */

/** @type {Rule[]} */
export const RULES = [
  calqueFrame,
  cliche,
  connectorRepeat,
  phraseRepeat,
  danglingDeixis,
  dash,
  draftHistory,
  numberOrphan,
  deixis,
  doubleNegative,
  doublePassive,
  endingRepeat,
  euiChain,
  fillerOpener,
  hardWord,
  imperativePeriod,
  japaneseLoan,
  longSentence,
  negationRedefine,
  nounPile,
  outsideProfile,
  redundantPair,
  translationese,
  factListParagraph,
  paraFragment,
  blockUnread,
  bridgeRepeat,
  emojiBullet,
  introImage,
  loneSubheading,
  moreLater,
  headingSentence,
  headingSkip,
  headingUniform,
  introLong,
  sectionNoProse,
  countMismatch,
  enoughOnce,
  fieldEcho,
  tableOddCell,
  keywordHeading,
  keywordMissing,
  noQuestion,
  promiseRecall,
  spelling,
  spacing,
  confusable,
  inputFileSource,
  installImport,
  duplicateBlock,
  firstResultDistance,
  platformApi,
  screenNarration,
  screenSentence,
  screenTone,
  screenWord,
];

/**
 * 규칙이 찾는 방법의 닫힌 목록. 파이썬 rules/registry.py의 MECHANISMS와 같은 값과 같은 순서다.
 * @type {Record<string, string>}
 */
export const MECHANISMS = {
  dictionary: "사전. 단어 목록과 정규식이 맞는 곳",
  repeat: "반복. 같은 모양이 가까이에서 여러 번 나오는 곳",
  threshold: "수치. 글에서 잰 값이 기준값을 넘거나 정해 둔 형식과 다른 곳",
  contrast: "비교. 두 곳을 비교해 어긋난 곳",
  reader: "독자. 앞에서 읽은 내용만으로 그 문장을 이해할 수 있는지 문장 순서대로 본다",
};
for (const rule of RULES) {
  if (!(rule.mechanism in MECHANISMS)) {
    throw new Error(`규칙 ${rule.name}의 찾는 방법이 닫힌 집합 밖이다: ${rule.mechanism} (있는 것: ${Object.keys(MECHANISMS).join(", ")}). 새 방법은 규칙 하나 때문에 더하지 않는다. 멈추고 묻는다`);
  }
}

const BY_NAME = new Map(RULES.map((rule) => [rule.name, rule]));

/** 이름 순. */
export function ruleNames() {
  return [...BY_NAME.keys()].sort();
}

/** @param {string} name */
export function ruleDoc(name) {
  const docs = loadRuleDocs();
  if (!(name in docs) || !BY_NAME.has(name)) throw new Error(`모르는 규칙: ${name}. hanlint rules로 목록을 본다`);
  return docs[name];
}

/** @param {string} name */
export function ruleSummary(name) {
  return ruleDoc(name).split("\n")[0];
}

/** 기술서의 네 절 표. 파이썬 rules/registry.py의 REQUIRED_SECTIONS와 같다. */
export const REQUIRED_SECTIONS = ["왜:", "어디서:", "고치기:", "안 잡는 것:"];

/** 기술서에서 절 하나의 본문을 한 줄로. 파이썬 docSection과 같다. @param {string} doc @param {string} label */
export function docSection(doc, label) {
  const collected = [];
  let inside = false;
  for (const raw of doc.split("\n")) {
    const line = raw.trim();
    if (!inside) {
      if (line.startsWith(label)) {
        inside = true;
        collected.push(line.slice(label.length).trim());
      }
      continue;
    }
    if (!line || REQUIRED_SECTIONS.some((other) => line.startsWith(other))) break;
    collected.push(line);
  }
  return collected.filter(Boolean).join(" ");
}

/** 규칙의 고치기 절 한 줄. primer가 쓰기 전에 읽히는 그 문장이다. @param {string} name */
export function ruleFix(name) {
  return docSection(ruleDoc(name), "고치기:");
}

/**
 * 묶음의 사람 이름. 파이썬 rules/registry.py의 CATEGORY_TITLES와 같은 값과 같은 순서다.
 * @type {Record<string, string>}
 */
export const CATEGORY_TITLES = {
  sentence: "문장",
  paragraph: "문단",
  structure: "글의 짜임",
  document: "앞뒤 맞추기",
  orthography: "표기와 띄어쓰기",
  code: "코드 블록",
  screen: "화면의 글",
};

/** 규칙이 세는 방법. @param {string} name */
export function ruleMechanism(name) {
  const rule = BY_NAME.get(name);
  if (!rule) throw new Error(`모르는 규칙: ${name}. hanlint rules로 목록을 본다`);
  return rule.mechanism;
}

/** 규칙이 사는 묶음. 정본은 파이썬 쪽 폴더이고 여기는 그 투영을 읽는다. @param {string} name */
export function ruleCategory(name) {
  const categories = loadRuleCategories();
  if (!(name in categories)) throw new Error(`모르는 규칙: ${name}. hanlint rules로 목록을 본다`);
  return categories[name];
}

/**
 * 인라인 제어가 그 줄에서 그 규칙을 껐는가. `*`는 전부다.
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
