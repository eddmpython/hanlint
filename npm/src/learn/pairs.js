// @ts-check
/** Python SequenceMatcher(autojunk=False)의 문장 대응. 가장 긴 연속 일치의 앞쪽을 먼저 택한다. */
function longest(left, right, start, end, otherStart, otherEnd) {
  let best = [start, otherStart, 0], previous = new Map();
  const positions = new Map();
  for (let index = otherStart; index < otherEnd; index++) {
    const list = positions.get(right[index]) ?? [];
    list.push(index);
    positions.set(right[index], list);
  }
  for (let index = start; index < end; index++) {
    const current = new Map();
    for (const other of positions.get(left[index]) ?? []) {
      const size = (previous.get(other - 1) ?? 0) + 1;
      current.set(other, size);
      if (size > best[2]) best = [index - size + 1, other - size + 1, size];
    }
    previous = current;
  }
  return best;
}

/** @param {string[]} left @param {string[]} right */
export function changedRanges(left, right) {
  const pending = [[0, left.length, 0, right.length]], blocks = [];
  while (pending.length) {
    const [start, end, otherStart, otherEnd] = pending.pop();
    const [at, other, size] = longest(left, right, start, end, otherStart, otherEnd);
    if (!size) continue;
    blocks.push([at, other, size]);
    if (start < at && otherStart < other) pending.push([start, at, otherStart, other]);
    if (at + size < end && other + size < otherEnd) pending.push([at + size, end, other + size, otherEnd]);
  }
  blocks.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  blocks.push([left.length, right.length, 0]);
  const ranges = [];
  let start = 0, otherStart = 0;
  for (const [at, other, size] of blocks) {
    if (start < at || otherStart < other) ranges.push([start, at, otherStart, other]);
    start = at + size;
    otherStart = other + size;
  }
  return ranges;
}

/** 기존 Python learn의 일대일 및 한 문장 분할 대응을 그대로 따른다. */
export function changedSentencePairs(before, after) {
  const pairs = new Map();
  for (const [start, end, otherStart, otherEnd] of changedRanges(before.map((item) => item.text), after.map((item) => item.text))) {
    const count = end - start, otherCount = otherEnd - otherStart;
    if (!count || !otherCount) continue;
    if (count === otherCount) {
      for (let offset = 0; offset < count; offset++) pairs.set(before[start + offset].index, [after[otherStart + offset]]);
    } else if (count === 1) pairs.set(before[start].index, after.slice(otherStart, otherEnd));
  }
  return pairs;
}
