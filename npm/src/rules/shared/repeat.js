// @ts-check
/**
 * 반복 기제. 같은 모양이 창 안에서 이어지거나 (runsOf) 한 모양이 창을 채우는 (shareOf) 자리를 센다.
 * 파이썬 rules/shared/repeat.py 와 같다. 규칙은 열쇠와 창과 임계만 선언하고 셈은 여기서 한다.
 */

/**
 * 같은 값이 minLength 개 이상 이어지는 구간을 [시작 위치, 길이, 값] 으로 준다.
 * @template T
 * @param {T[]} values
 * @param {number} minLength
 * @returns {[number, number, T][]}
 */
export function runsOf(values, minLength) {
  /** @type {[number, number, T][]} */
  const runs = [];
  let start = 0;
  while (start < values.length) {
    let end = start;
    while (end + 1 < values.length && values[end + 1] === values[start]) end += 1;
    const length = end - start + 1;
    if (length >= minLength) runs.push([start, length, values[start]]);
    start = end + 1;
  }
  return runs;
}

/**
 * 가장 많은 값과 그 수와 전체 수. 같은 수면 먼저 나온 값이 이긴다. 빈 열이면 [null, 0, 0].
 * @template T
 * @param {T[]} values
 * @returns {[T | null, number, number]}
 */
export function shareOf(values) {
  /** @type {Map<T, number>} */
  const counts = new Map();
  for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
  /** @type {T | null} */
  let best = null;
  let count = 0;
  for (const [value, seen] of counts) {
    if (seen > count) {
      best = value;
      count = seen;
    }
  }
  return [best, count, values.length];
}
