// @ts-check
/** 파이썬 `analysis/grammar/voice.py`의 투영. 확정되는 사동과 피동의 겹만 분해한다. */
import { loadLines } from "../../data/load.js";

export const PASSIVE = "피동";
export const CAUSATIVE = "사동";
const CAUSATIVE_FORM = /^([가-힣]+)게\s+만들([가-힣]*)$/;
const CONTRACTION = new Map([
  ["이", "여"],
  ["히", "혀"],
  ["리", "려"],
  ["기", "겨"],
]);
let passiveCache = null;

function passiveLinks() {
  if (!passiveCache) {
    passiveCache = new Map([["되어지", "되"]]);
    for (const stem of loadLines("passiveStems.txt")) {
      const last = stem.at(-1);
      const linked = CONTRACTION.has(last) ? stem.slice(0, -1) + CONTRACTION.get(last) : stem + "어";
      passiveCache.set(linked + "지", stem);
    }
  }
  return passiveCache;
}

/** @param {string} surface */
export function decomposePassive(surface) {
  const base = passiveLinks().get(surface);
  return base === undefined ? null : { surface, kind: PASSIVE, base, markers: ["접미 피동", "어지"], reduced: base };
}

/** @param {string} surface */
export function decomposeCausative(surface) {
  const match = CAUSATIVE_FORM.exec(surface);
  return match ? { surface, kind: CAUSATIVE, base: match[1], markers: ["게", "만들"], reduced: null } : null;
}

/** @param {string} surface */
export function decomposeVoice(surface) {
  return decomposePassive(surface) ?? decomposeCausative(surface);
}
