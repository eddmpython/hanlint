// @ts-check
/** 이유가 붙은 정확 국소 Patch 입력 계약. */
import { createHash } from "node:crypto";

/** @param {unknown} value @param {string} where */
function checkedString(value, where) {
  if (typeof value !== "string" || !value || value !== value.trim()) {
    throw new Error(`${where} 는 양끝 공백 없는 문자열이다`);
  }
  if (value !== value.normalize("NFC")) throw new Error(`${where} 는 NFC 문자열이어야 한다`);
  return value;
}

export class Patch {
  /** @param {string} reason @param {string} before @param {string} after */
  constructor(reason, before, after) {
    this.reason = checkedString(reason, "reason");
    this.before = checkedString(before, "before");
    this.after = checkedString(after, "after");
    if (this.before === this.after) throw new Error("patch before 와 after 는 달라야 한다");
    Object.freeze(this);
  }

  /** @param {unknown} raw */
  static fromMapping(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("patch 는 JSON 객체다");
    const data = /** @type {Record<string, unknown>} */ (raw);
    const expected = ["reason", "before", "after"];
    const unknown = Object.keys(data).filter((key) => !expected.includes(key)).sort();
    const missing = expected.filter((key) => !(key in data)).sort();
    if (unknown.length) throw new Error(`patch 의 모르는 키: ${unknown.join(", ")}`);
    if (missing.length) throw new Error(`patch 의 빠진 키: ${missing.join(", ")}`);
    return new Patch(
      /** @type {string} */ (data.reason),
      /** @type {string} */ (data.before),
      /** @type {string} */ (data.after),
    );
  }

  get digest() {
    const encoded = JSON.stringify({ after: this.after, before: this.before, reason: this.reason });
    return createHash("sha256").update(encoded, "utf8").digest("hex");
  }

  asDict() {
    return { reason: this.reason, before: this.before, after: this.after };
  }
}
