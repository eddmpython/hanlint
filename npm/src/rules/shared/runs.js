// @ts-check
/** 연속 구간 찾기. 같은 값이 이어지는 자리를 [시작 위치, 길이, 값] 으로 준다. */

/**
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
