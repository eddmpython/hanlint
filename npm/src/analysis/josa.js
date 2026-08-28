// @ts-check
/**
 * 받침에 따라 꼴이 갈리는 조사를 맞춘다. 파이썬 `hanlint/analysis/josa.py` 의 투영이다.
 * 왜 있는지와 `으로` 의 ㄹ 예외는 그 파일의 docstring 이 정본이다.
 */

/** (받침 뒤 꼴, 받침 없는 뒤 꼴). 긴 것부터 대조해야 `으로` 가 `은` 보다 먼저 걸린다. */
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

/** 숫자 하나를 한자어로 읽었을 때의 종성. 영 일 이 삼 사 오 육 칠 팔 구 차례다. */
const DIGIT_FINALS = [21, 8, 0, 16, 0, 0, 1, 8, 8, 0];
/** 뒤에 붙은 0 의 개수가 정하는 자리값의 종성. 십 ㅂ, 백 ㄱ, 천 ㄴ. */
const PLACE_FINALS = { 1: 17, 2: 1, 3: 4 };
/** 네 자리 묶음의 이름. 만 ㄴ, 억 ㄱ, 조 (받침 없음), 경 ㅇ. */
const GROUP_FINALS = [4, 1, 0, 21];

const HANGUL_BASE = 0xac00;
const HANGUL_LAST = 0xd7a3;
const JONGSEONG_COUNT = 28;
/** 종성 표에서 ㄹ 의 자리. `으로` 만 이 받침을 없는 것처럼 다룬다. */
const RIEUL = 8;
const ALNUM = /[\p{L}\p{N}]/u;

/** 숫자를 한자어로 읽었을 때 마지막 소리의 종성. 뜻은 파이썬 analysis/josa.py 가 소유한다. @param {string} digits */
export function digitFinal(digits) {
  const body = digits.replace(/0+$/, "");
  if (!body) return DIGIT_FINALS[0];
  const zeros = digits.length - body.length;
  if (zeros === 0) return DIGIT_FINALS[Number(digits[digits.length - 1])];
  if (zeros >= 4) return GROUP_FINALS[Math.min(Math.floor(zeros / 4), GROUP_FINALS.length) - 1];
  return PLACE_FINALS[zeros];
}

/** 마지막 소리의 종성 번호. 셀 수 없으면 (로마자, 기호) null. @param {string} word */
export function finalOf(word) {
  if (!word) return null;
  const last = word[word.length - 1];
  if (last >= "0" && last <= "9") return digitFinal(word.match(/[0-9]+$/)[0]);
  const code = word.charCodeAt(word.length - 1);
  if (code < HANGUL_BASE || code > HANGUL_LAST) return null;
  return (code - HANGUL_BASE) % JONGSEONG_COUNT;
}

/** 뒤 첫 조사가 바뀌어야 하면 [지금 꼴, 바꿀 꼴]. 아니면 null. @param {string} word @param {string} following */
export function josaSwap(word, following) {
  const final = finalOf(word);
  if (final === null || !following) return null;
  for (const [withFinal, withoutFinal] of PAIRS) {
    for (const form of [withFinal, withoutFinal]) {
      if (!following.startsWith(form)) continue;
      const rest = following.slice(form.length);
      // 조사가 아니라 더 긴 낱말의 앞머리다 (`이유`, `과정`, `로그`)
      if (rest && ALNUM.test(rest[0])) break;
      const wanted = withFinal === "으로" ? (final === 0 || final === RIEUL ? withoutFinal : withFinal) : final ? withFinal : withoutFinal;
      return wanted === form ? null : [form, wanted];
    }
  }
  return null;
}

/** 뒤에 오는 글의 첫 조사 꼴을 받침에 맞춘 글. @param {string} word @param {string} following */
export function fitJosa(word, following) {
  const swap = josaSwap(word, following);
  if (!swap) return following;
  return swap[1] + following.slice(swap[0].length);
}
