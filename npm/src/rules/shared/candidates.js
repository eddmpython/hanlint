// @ts-check
/** 파이썬 rules/shared/candidates.py의 투영. 후보에는 점수와 순위가 없다. */
import { HAEYO, HANDA, HAPNIDA, REGISTERS, conjugate, fitJosa } from "../../analysis/grammar/index.js";
import * as hangul from "../../analysis/grammar/hangul.js";
import { decomposePassive } from "../../analysis/grammar/voice.js";
import { stripJosa, words } from "../../analysis/tokenize.js";
import { loadLines } from "../../data/load.js";

const ENDING_CANDIDATES = {
  [HAPNIDA]: [["-습니까?", "같은 문체의 의문형"], ["-기 때문입니다", "같은 문체의 인과형"]],
  [HANDA]: [["-는가?", "같은 문체의 의문형"], ["-기 때문이다", "같은 문체의 인과형"]],
  [HAEYO]: [["-나요?", "같은 문체의 의문형"], ["-기 때문이에요", "같은 문체의 인과형"]],
};

/** @param {string} text @returns {import("../finding.js").Candidate[]} */
export function longSentenceCandidates(text) {
  const endings = [...loadLines("candidateSplitEndings.txt")].sort((a, b) => b.length - a.length);
  const pattern = new RegExp(`([가-힣]+(${endings.join("|")}))[,;]?\\s+`, "g");
  const candidates = [];
  for (const match of text.matchAll(pattern)) {
    const word = match[1];
    const ending = match[2];
    if (word === "그리고" || word.length <= ending.length) continue;
    const end = /** @type {number} */ (match.index) + match[0].length;
    const marked = text.slice(0, end).trimEnd() + " | " + text.slice(end).trimStart();
    candidates.push({ text: marked, why: `연결 어미 \`${ending}\` 뒤를 문장 경계로 검토한다` });
  }
  return candidates;
}

/** @param {string} topic @param {string} deixis */
function replacementForDeixis(topic, deixis) {
  if (deixis.startsWith("이것")) {
    const suffix = deixis.slice("이것".length);
    return topic + fitJosa(topic, suffix);
  }
  if (deixis.startsWith("해당 ")) {
    const last = deixis.trim().split(/\s+/).at(-1) ?? "";
    const base = stripJosa(last);
    return topic + fitJosa(topic, last.slice(base.length));
  }
  if (deixis.startsWith("이러한 ")) return topic + "의 " + deixis.slice("이러한 ".length);
  if (deixis === "이처럼") return topic + "처럼";
  return topic;
}

/** @param {import("../../fingerprint/build.js").SentencePrint} current @param {import("../../fingerprint/build.js").SentencePrint | null} previous */
export function danglingDeixisCandidates(current, previous) {
  if (previous === null || !current.deixis.length) return [];
  const deixis = current.deixis[0];
  const topics = [...previous.topics].sort((a, b) => previous.text.toLowerCase().indexOf(a) - previous.text.toLowerCase().indexOf(b) || a.localeCompare(b));
  return topics.map((topic) => ({
    text: current.text.replace(deixis, replacementForDeixis(topic, deixis)),
    why: `바로 앞 문장에 나온 명사 \`${topic}\``,
  }));
}

/** @param {string} text */
export function nounPileCandidates(text) {
  const actionNouns = new Set(loadLines("candidateActionNouns.txt"));
  const found = [];
  for (const word of words(text)) {
    const core = stripJosa(word.core);
    if (actionNouns.has(core) && !found.includes(core)) found.push(core);
  }
  return found.map((noun) => ({ text: noun + "하다", why: `명사 \`${noun}\`${fitJosa(noun, "을")} 동사 어근으로 되돌린다` }));
}

/** @param {string} register */
export function endingRepeatCandidates(register) {
  const target = REGISTERS.includes(register) ? register : HAPNIDA;
  return ENDING_CANDIDATES[target].map(([text, why]) => ({ text, why }));
}

/** @param {string} text @param {string} surface @param {string} reduced */
function reducedPassiveText(text, surface, reduced) {
  const prefix = surface.slice(0, -1);
  let start = 0;
  while ((start = text.indexOf(prefix, start)) >= 0) {
    const tailAt = start + prefix.length;
    const tail = text[tailAt];
    if (!tail || !hangul.isSyllable(tail)) {
      start += 1;
      continue;
    }
    const [initial, vowel, final] = hangul.split(tail);
    if (initial !== 12 || ![hangul.IH, hangul.YEO].includes(vowel)) {
      start += 1;
      continue;
    }
    let replacement;
    if (vowel === hangul.YEO) {
      const base = conjugate(reduced);
      replacement = final ? base.slice(0, -1) + hangul.withFinal(base.at(-1), final) : base;
    } else if (final === hangul.BIEUP) {
      const polite = renderPolite(reduced);
      replacement = polite.slice(0, -2);
    } else {
      replacement = final ? reduced.slice(0, -1) + hangul.withFinal(reduced.at(-1), final) : reduced;
    }
    return text.slice(0, start) + replacement + text.slice(tailAt + 1);
  }
  return null;
}

/** polite는 공개 함수가 아니므로 합니다체 활용에서 니다만 뗀다. @param {string} reduced */
function renderPolite(reduced) {
  const last = hangul.finalOf(reduced.at(-1));
  if (last === hangul.NONE || last === hangul.RIEUL) {
    const stem = last === hangul.RIEUL ? reduced.slice(0, -1) + hangul.withFinal(reduced.at(-1), hangul.NONE) : reduced;
    return stem.slice(0, -1) + hangul.withFinal(stem.at(-1), hangul.BIEUP) + "니다";
  }
  return reduced + "습니다";
}

/** @param {string} text @param {string[]} passives */
export function doublePassiveCandidates(text, passives) {
  const candidates = [];
  const seen = new Set();
  for (const surface of passives) {
    const voice = decomposePassive(surface);
    if (!voice || voice.reduced === null) continue;
    const candidateText = reducedPassiveText(text, surface, voice.reduced);
    if (candidateText === null || seen.has(candidateText)) continue;
    seen.add(candidateText);
    candidates.push({ text: candidateText, why: `\`${surface}\`의 피동 겹을 하나로 줄인다` });
  }
  return candidates;
}
