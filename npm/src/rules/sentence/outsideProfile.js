// @ts-check
import { PROFILE_OF } from "../../config/settings.js";
import { profileOf, shareAtOrAbove, userProfile } from "../../data/profiles.js";
import { NOTICE, SENTENCE, finding } from "../finding.js";

export const name = "outsideProfile";
export const mechanism = "threshold";
/** 대조하는 문장 지표와 지적문의 이름과 단위. 파이썬 outsideProfile.py 와 같다. */
const FEATURES = [
  ["length", "문장 길이", "어절"],
  ["commas", "쉼표", "개"],
  ["newTopics", "처음 나온 화제어", "개"],
  ["hedges", "헤지 표현", "개"],
];

/** @param {import("../../config/settings.js").Config} config */
function profileFor(config) {
  if (config.profile) return userProfile(config.profile);
  const kind = PROFILE_OF[config.preset];
  return kind ? profileOf(kind) : null;
}

/** @param {number} permille */
function shareText(permille) {
  return permille === 0 ? "0.1% 아래" : `${Math.floor(permille / 10)}.${permille % 10}%`;
}

/** @param {Set<string>} topics @param {Set<string>} known */
function freshCount(topics, known) {
  let fresh = 0;
  for (const topic of topics) if (!known.has(topic)) fresh += 1;
  return fresh;
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const profile = profileFor(config);
  if (!profile) return [];
  const p = config.profilePercentile;
  const findings = [];
  for (const sentence of doc.sentences) {
    const known = doc.reader.beforeSentence[sentence.index].known;
    const values = { length: sentence.length, commas: sentence.commas, newTopics: freshCount(sentence.topics, known), hedges: sentence.hedges };
    for (const [key, label, unit] of FEATURES) {
      const hist = profile.sentence.get(key);
      if (!hist || !hist.percentiles.has(p)) continue;
      const limit = /** @type {number} */ (hist.percentiles.get(p));
      const value = values[/** @type {"length" | "commas" | "newTopics" | "hedges"} */ (key)];
      if (limit === 0 || value <= limit) continue;
      findings.push(
        finding(
          name,
          sentence.line,
          sentence.text,
          `${label} ${value}${unit}. ${profile.label} ${profile.sentences}문장 가운데 상위 ${shareText(shareAtOrAbove(hist, value))}다. ${p}%는 ${limit}${unit} 이하다`,
          null,
          NOTICE,
          SENTENCE,
          sentence.index,
        ),
      );
    }
  }
  return findings;
}
