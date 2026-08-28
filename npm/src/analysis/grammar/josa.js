// @ts-check
/** 파이썬 `analysis/grammar/josa.py`의 투영. 받침에 따라 조사 꼴을 맞춘다. */
import * as hangul from "./hangul.js";

const PAIRS = [
  ["으로부터", "로부터"],
  ["으로서", "로서"],
  ["으로써", "로써"],
  ["이라고", "라고"],
  ["이라서", "라서"],
  ["이라는", "라는"],
  ["이라면", "라면"],
  ["이나마", "나마"],
  ["으로", "로"],
  ["이란", "란"],
  ["이라", "라"],
  ["이며", "며"],
  ["이랑", "랑"],
  ["이든", "든"],
  ["이나", "나"],
  ["이여", "여"],
  ["이야", "야"],
  ["은", "는"],
  ["이", "가"],
  ["을", "를"],
  ["과", "와"],
  ["아", "야"],
];
const DIGIT_FINALS = [hangul.IEUNG, hangul.RIEUL, hangul.NONE, hangul.MIEUM, hangul.NONE, hangul.NONE, hangul.GIYEOK, hangul.RIEUL, hangul.RIEUL, hangul.NONE];
const PLACE_FINALS = { 1: hangul.BIEUP, 2: hangul.GIYEOK, 3: hangul.NIEUN };
const GROUP_FINALS = [hangul.NIEUN, hangul.GIYEOK, hangul.NONE, hangul.IEUNG];
const ALNUM = /[\p{L}\p{N}]/u;

/** @param {string} digits */
export function digitFinal(digits) {
  const body = digits.replace(/0+$/, "");
  if (!body) return DIGIT_FINALS[0];
  const zeros = digits.length - body.length;
  if (zeros === 0) return DIGIT_FINALS[Number(digits.at(-1))];
  if (zeros >= 4) return GROUP_FINALS[Math.min(Math.floor(zeros / 4), GROUP_FINALS.length) - 1];
  return PLACE_FINALS[zeros];
}

/** @param {string} word */
export function finalOf(word) {
  if (!word) return null;
  if (/[0-9]$/.test(word)) return digitFinal(/[0-9]+$/.exec(word)[0]);
  return hangul.finalOf(word.at(-1));
}

/** @param {string} word @param {string} following */
export function josaSwap(word, following) {
  const final = finalOf(word);
  if (final === null || !following) return null;
  for (const [withFinal, withoutFinal] of PAIRS) {
    for (const form of [withFinal, withoutFinal]) {
      if (!following.startsWith(form)) continue;
      const rest = following.slice(form.length);
      if (rest && ALNUM.test(rest[0])) break;
      const wanted = withFinal === "으로"
        ? (final === hangul.NONE || final === hangul.RIEUL ? withoutFinal : withFinal)
        : (final ? withFinal : withoutFinal);
      return wanted === form ? null : [form, wanted];
    }
  }
  return null;
}

/** @param {string} word @param {string} following */
export function fitJosa(word, following) {
  const swap = josaSwap(word, following);
  return swap ? swap[1] + following.slice(swap[0].length) : following;
}
