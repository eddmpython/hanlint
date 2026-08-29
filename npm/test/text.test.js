// @ts-check
import assert from "node:assert/strict";
import { test } from "node:test";

import { roundHalfEven } from "../src/text.js";

test("roundHalfEven gives the same digits as python round", () => {
  // 기대값은 파이썬 3.13 의 round 로 확인했다. 정확한 이진 값을 십진으로 풀어 반올림하고 정확히 절반이면 짝수로 간다.
  assert.equal(roundHalfEven(0.8125, 3), 0.812);
  assert.equal(roundHalfEven(0.0078125, 6), 0.007812);
  assert.equal(roundHalfEven(62.5, 0), 62);
  assert.equal(roundHalfEven(63.5, 0), 64);
  assert.equal(roundHalfEven(0.5, 0), 0);
  assert.equal(roundHalfEven(1.5, 0), 2);
  // 0.8135 와 2.675 는 이진으로 정확하지 않다. 절반처럼 보여도 실제 값이 위인지 아래인지가 정한다.
  assert.equal(roundHalfEven(0.8135, 3), 0.814);
  assert.equal(roundHalfEven(2.675, 2), 2.67);
  assert.equal(roundHalfEven(0.1234565, 6), 0.123456);
  assert.equal(roundHalfEven(1e-7, 6), 0);
  assert.equal(roundHalfEven(0.9999995, 6), 1);
  assert.equal(roundHalfEven(-0.8125, 3), -0.812);
  assert.equal(roundHalfEven(12, 6), 12);
});
