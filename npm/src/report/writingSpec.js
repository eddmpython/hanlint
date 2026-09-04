// @ts-check
/** 쓰기 전 숫자 사양. 파이썬 config/writingSpec.py와 같은 셈과 글자를 낸다. */

import { HAPNIDA, REGISTERS } from "../analysis/grammar/index.js";
import { PROFILE_OF, defaultConfig, enabled } from "../config/settings.js";
import { profileOf, userProfile } from "../data/profiles.js";

export const SPEC_VERSION = 1;
const CHARS_PER_WORD = 6;

/** 양수 반올림. 파이썬의 nearest와 같다. @param {number} value */
function nearest(value) {
  return Math.floor(value + 0.5);
}

/** @param {import("../data/profiles.js").Histogram} histogram @param {number} level */
function percentile(histogram, level) {
  return histogram.percentiles.get(level) ?? 0;
}

/** @param {number} value */
function percent(value) {
  return nearest(value * 100);
}

/** @param {import("./settings.js").Config} config */
function selectedProfile(config) {
  if (config.profile) return userProfile(config.profile);
  const kind = PROFILE_OF[config.preset];
  if (kind === null) throw new Error(`${config.preset} 은 종류 프로파일이 없어 사양을 낼 수 없다`);
  const profile = profileOf(kind);
  if (profile === null) throw new Error(`${kind} 프로파일을 찾지 못했다`);
  return profile;
}

/**
 * 현재 규칙판을 쓰기 전 숫자 사양으로 편다. 품질 점수나 새 임계는 만들지 않는다.
 * @param {import("./settings.js").Config} [config]
 * @param {string} [register]
 * @param {number | null} [targetChars]
 */
export function writingSpec(config = defaultConfig(), register = HAPNIDA, targetChars = null) {
  if (!REGISTERS.includes(register)) throw new Error(`register 는 ${REGISTERS.join(", ")} 가운데 하나다: ${register}`);
  if (targetChars !== null && targetChars <= 0) throw new Error(`chars 는 1 이상이어야 한다: ${targetChars}`);
  const profile = selectedProfile(config);
  const sentence = profile.sentence;
  const paragraph = profile.paragraph.get("sentenceCount");
  if (!paragraph) throw new Error("프로파일에 paragraph.sentenceCount가 없다");
  const perParagraph = percentile(paragraph, 50);
  if (perParagraph <= 0) throw new Error("프로파일의 문단당 문장 중앙값이 1 이상이어야 한다");
  const lengthHistogram = sentence.get("length");
  if (!lengthHistogram) throw new Error("프로파일에 sentence.length가 없다");
  const lengthP50 = percentile(lengthHistogram, 50);
  if (lengthP50 <= 0) throw new Error("프로파일의 문장 길이 중앙값이 1 이상이어야 한다");

  const rows = [];
  let amount = `문단마다 문장 ${perParagraph}~${percentile(paragraph, 90)}개`;
  if (targetChars !== null) {
    const sentences = Math.max(1, nearest(targetChars / CHARS_PER_WORD / lengthP50));
    const paragraphs = Math.max(1, nearest(sentences / perParagraph));
    amount = `문단 ${paragraphs}개, ${amount}, 문장 ${sentences}개 안팎`;
  }
  rows.push({ id: "amount", label: "분량", guidance: amount, basis: [`profile.${profile.kind}.paragraph.sentenceCount`] });

  let length = `중앙 ${lengthP50}어절, 문장 90%가 ${percentile(lengthHistogram, 90)}어절 이하`;
  const lengthBasis = [`profile.${profile.kind}.sentence.length`];
  if (enabled(config, "longSentence")) {
    length += `. ${config.longSentenceMax}어절을 넘으면 longSentence가 지적`;
    lengthBasis.push("rule.longSentence");
  }
  rows.push({ id: "sentenceLength", label: "문장 길이", guidance: length, basis: lengthBasis });

  if (profile.endingRuns !== null) {
    let endingText = `같은 끝맺음 연속 중앙 ${percentile(profile.endingRuns, 50)}개, 90%가 ${percentile(profile.endingRuns, 90)}개 이하`;
    const endingBasis = [`profile.${profile.kind}.endingRuns`];
    if (enabled(config, "endingRepeat")) {
      endingText += `. 인과나 독자 호출 없이 ${config.endingRun}개부터 endingRepeat가 지적`;
      endingBasis.push("rule.endingRepeat");
    }
    rows.push({ id: "endingRun", label: "끝맺음", guidance: endingText, basis: endingBasis });
  }

  const commas = sentence.get("commas");
  if (!commas) throw new Error("프로파일에 sentence.commas가 없다");
  rows.push({
    id: "commas",
    label: "쉼표",
    guidance: `문장 중앙 ${percentile(commas, 50)}개, 90%가 ${percentile(commas, 90)}개 이하, 99%가 ${percentile(commas, 99)}개 이하`,
    basis: [`profile.${profile.kind}.sentence.commas`],
  });

  const eui = sentence.get("euiCount");
  if (!eui) throw new Error("프로파일에 sentence.euiCount가 없다");
  let euiText = `문장 중앙 ${percentile(eui, 50)}개, 90%가 ${percentile(eui, 90)}개 이하`;
  const euiBasis = [`profile.${profile.kind}.sentence.euiCount`];
  if (enabled(config, "euiChain")) {
    euiText += ". 3개부터, 붙은 2개부터 euiChain이 지적";
    euiBasis.push("rule.euiChain");
  }
  rows.push({ id: "euiCount", label: "의", guidance: euiText, basis: euiBasis });

  const nounRun = sentence.get("nounRun");
  if (!nounRun) throw new Error("프로파일에 sentence.nounRun이 없다");
  let nounText = `문장 90%에서 조사 없는 명사 연쇄가 ${percentile(nounRun, 90)}개 이하`;
  const nounBasis = [`profile.${profile.kind}.sentence.nounRun`];
  if (enabled(config, "nounPile")) {
    nounText += `. ${config.nounPileMin}개부터 nounPile이 지적`;
    nounBasis.push("rule.nounPile");
  }
  rows.push({ id: "nounRun", label: "명사 연쇄", guidance: nounText, basis: nounBasis });

  const newTopics = sentence.get("newTopics");
  if (!newTopics) throw new Error("프로파일에 sentence.newTopics가 없다");
  rows.push({
    id: "newTopics",
    label: "새 화제",
    guidance: `문장 중앙 ${percentile(newTopics, 50)}개, 90%가 ${percentile(newTopics, 90)}개 이하`,
    basis: [`profile.${profile.kind}.sentence.newTopics`],
  });

  const connector = profile.rates.connector;
  rows.push({
    id: "connector",
    label: "문두 접속",
    guidance: `문서 중앙은 문장의 ${percent(connector.p50)}%, 문서 90%가 ${percent(connector.p90)}% 이하`,
    basis: [`profile.${profile.kind}.rates.connector`],
  });

  const numbers = sentence.get("numbers");
  if (!numbers) throw new Error("프로파일에 sentence.numbers가 없다");
  const numberP50 = percentile(numbers, 50);
  const numberP90 = percentile(numbers, 90);
  const numberText =
    numberP50 === 0 && numberP90 === 0
      ? "문장 중앙과 90%에서 숫자 없음"
      : `문장 중앙 ${numberP50}개, 90%가 ${numberP90}개 이하`;
  rows.push({ id: "numbers", label: "숫자", guidance: numberText, basis: [`profile.${profile.kind}.sentence.numbers`] });

  const question = profile.rates.question;
  let questionText;
  let questionBasis;
  if (enabled(config, "noQuestion")) {
    questionText = "절이 2개 이상이면 글 전체에 물음표 최소 1개";
    if (question.p50 === 0) questionText += ". 말뭉치 중앙은 0%라 규칙과 어긋나며 켜진 규칙을 따른다";
    questionBasis = [`profile.${profile.kind}.rates.question`, "rule.noQuestion"];
  } else {
    questionText = `규칙 요구 없음. 문서 중앙은 문장의 ${percent(question.p50)}%, 문서 90%가 ${percent(question.p90)}% 이하`;
    questionBasis = [`profile.${profile.kind}.rates.question`];
  }
  rows.push({ id: "question", label: "물음표", guidance: questionText, basis: questionBasis });

  return {
    version: SPEC_VERSION,
    kind: "hanlint.writingSpec",
    preset: config.preset,
    register,
    targetChars,
    profile: profile.kind,
    rows,
  };
}

/** 사람이 읽는 꼴. basis는 JSON에서 확인한다. @param {ReturnType<typeof writingSpec>} spec */
export function renderWritingSpec(spec) {
  const target = spec.targetChars !== null ? `, ${spec.targetChars}자` : "";
  const lines = [
    `hanlint spec  ${spec.preset} 종류, ${spec.register}체${target}. 같은 규칙판의 임계와 ${spec.profile} 프로파일을 쓰기 전 숫자로 편다`,
  ];
  const width = Math.max(...spec.rows.map((row) => row.label.length));
  for (const row of spec.rows) lines.push(`  ${row.label.padEnd(width)}  ${row.guidance}`);
  lines.push("", "이 사양은 품질 점수가 아니다. 쓴 뒤 같은 설정으로 hanlint <글.md>를 실행해 Finding을 확인한다");
  return lines.join("\n");
}
