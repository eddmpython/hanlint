// @ts-check
/** 모델과 실행 환경에 독립적인 최소 Reader Contract와 정확 Patch. */
import { createHash } from "node:crypto";

export const CONTRACT_VERSION = 1;

/** @param {unknown} value @param {string} where */
function checkedString(value, where) {
  if (typeof value !== "string" || !value || value !== value.trim()) {
    throw new Error(`${where} 는 양끝 공백 없는 문자열이다`);
  }
  if (value !== value.normalize("NFC")) throw new Error(`${where} 는 NFC 문자열이어야 한다`);
  return value;
}

/** @param {unknown} value @param {string} where */
function checkedStrings(value, where) {
  if (!Array.isArray(value) || !value.length) throw new Error(`${where} 는 비지 않은 문자열 배열이다`);
  const found = value.map((item, index) => checkedString(item, `${where} ${index + 1}번째`));
  if (new Set(found).size !== found.length) throw new Error(`${where} 에 같은 값이 두 번 있다`);
  return found;
}

/** @param {string} text */
function digest(text) {
  return createHash("sha256").update(text, "utf8").digest("hex");
}

export class Contract {
  /** @param {string} reader @param {string} goal @param {string[]} facts @param {number} [version] */
  constructor(reader, goal, facts, version = CONTRACT_VERSION) {
    if (!Number.isInteger(version) || version !== CONTRACT_VERSION) {
      throw new Error(`reader contract version 은 ${CONTRACT_VERSION}이다: ${version}`);
    }
    this.reader = checkedString(reader, "reader");
    this.goal = checkedString(goal, "goal");
    this.facts = Object.freeze(checkedStrings(facts, "facts"));
    this.version = version;
    Object.freeze(this);
  }

  /** @param {unknown} raw */
  static fromMapping(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("reader contract 는 JSON 객체다");
    const data = /** @type {Record<string, unknown>} */ (raw);
    const expected = ["version", "reader", "goal", "facts"];
    const unknown = Object.keys(data).filter((key) => !expected.includes(key)).sort();
    const missing = expected.filter((key) => !(key in data)).sort();
    if (unknown.length) throw new Error(`reader contract 의 모르는 키: ${unknown.join(", ")}`);
    if (missing.length) throw new Error(`reader contract 의 빠진 키: ${missing.join(", ")}`);
    return new Contract(
      /** @type {string} */ (data.reader),
      /** @type {string} */ (data.goal),
      /** @type {string[]} */ (data.facts),
      /** @type {number} */ (data.version),
    );
  }

  get text() {
    return [this.reader, this.goal, ...this.facts].join("\n");
  }

  get digest() {
    return digest(JSON.stringify({ facts: this.facts, goal: this.goal, reader: this.reader, version: this.version }));
  }

  asDict() {
    return { version: this.version, reader: this.reader, goal: this.goal, facts: [...this.facts] };
  }
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
    return digest(JSON.stringify({ after: this.after, before: this.before, reason: this.reason }));
  }

  asDict() {
    return { reason: this.reason, before: this.before, after: this.after };
  }
}
