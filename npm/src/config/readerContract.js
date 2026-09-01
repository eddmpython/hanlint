// @ts-check
/** 모델과 실행 환경에 독립적인 최소 Reader Contract와 정확 Patch. */
import { createHash } from "node:crypto";

export const CONTRACT_VERSION = 1;
export const LATEST_CONTRACT_VERSION = 2;
export const CONTRACT_VERSIONS = Object.freeze([CONTRACT_VERSION, LATEST_CONTRACT_VERSION]);

/** @param {unknown} value @param {string} where */
function checkedString(value, where) {
  if (typeof value !== "string" || !value || value !== value.trim()) {
    throw new Error(`${where} 는 양끝 공백 없는 문자열이다`);
  }
  if (value !== value.normalize("NFC")) throw new Error(`${where} 는 NFC 문자열이어야 한다`);
  return value;
}

/** @param {unknown} value @param {string} where @param {boolean} [allowEmpty] */
function checkedStrings(value, where, allowEmpty = false) {
  if (!Array.isArray(value) || (!allowEmpty && !value.length)) {
    throw new Error(`${where} 는 ${allowEmpty ? "문자열 배열" : "비지 않은 문자열 배열"}이다`);
  }
  const found = value.map((item, index) => checkedString(item, `${where} ${index + 1}번째`));
  if (new Set(found).size !== found.length) throw new Error(`${where} 에 같은 값이 두 번 있다`);
  return found;
}

/** 파이썬 문자열 순서와 같은 코드 포인트 순서. @param {string} left @param {string} right */
function compareText(left, right) {
  const leftPoints = [...left].map((value) => /** @type {number} */ (value.codePointAt(0)));
  const rightPoints = [...right].map((value) => /** @type {number} */ (value.codePointAt(0)));
  const limit = Math.min(leftPoints.length, rightPoints.length);
  for (let index = 0; index < limit; index += 1) {
    if (leftPoints[index] !== rightPoints[index]) return leftPoints[index] - rightPoints[index];
  }
  return leftPoints.length - rightPoints.length;
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

export class ProtectedSurface {
  /** @param {string[]} [numbers] @param {string[]} [urls] @param {string[]} [code] @param {string[]} [links] */
  constructor(numbers = [], urls = [], code = [], links = []) {
    this.numbers = Object.freeze(checkedStrings(numbers, "surface.numbers", true).sort(compareText));
    this.urls = Object.freeze(checkedStrings(urls, "surface.urls", true).sort(compareText));
    this.code = Object.freeze(checkedStrings(code, "surface.code", true).sort(compareText));
    this.links = Object.freeze(checkedStrings(links, "surface.links", true).sort(compareText));
    Object.freeze(this);
  }

  /** @param {unknown} raw */
  static fromMapping(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("surface 는 JSON 객체다");
    const data = /** @type {Record<string, unknown>} */ (raw);
    const expected = ["numbers", "urls", "code", "links"];
    const unknown = Object.keys(data).filter((key) => !expected.includes(key)).sort();
    const missing = expected.filter((key) => !(key in data)).sort();
    if (unknown.length) throw new Error(`surface 의 모르는 키: ${unknown.join(", ")}`);
    if (missing.length) throw new Error(`surface 의 빠진 키: ${missing.join(", ")}`);
    return new ProtectedSurface(
      /** @type {string[]} */ (data.numbers),
      /** @type {string[]} */ (data.urls),
      /** @type {string[]} */ (data.code),
      /** @type {string[]} */ (data.links),
    );
  }

  get text() {
    return [
      ...this.numbers,
      ...this.urls,
      ...this.code.map((value) => `\`${value}\``),
      ...this.links.map((value) => `[](${value})`),
    ].join("\n");
  }

  asDict() {
    return { numbers: [...this.numbers], urls: [...this.urls], code: [...this.code], links: [...this.links] };
  }
}

export class Outline {
  /** @param {number} level @param {string[]} headings */
  constructor(level, headings) {
    if (!Number.isInteger(level) || level < 1 || level > 6) throw new Error(`outline.level 은 1~6 정수다: ${level}`);
    this.level = level;
    this.headings = Object.freeze(checkedStrings(headings, "outline.headings"));
    Object.freeze(this);
  }

  /** @param {unknown} raw */
  static fromMapping(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("outline 은 JSON 객체다");
    const data = /** @type {Record<string, unknown>} */ (raw);
    const expected = ["level", "headings"];
    const unknown = Object.keys(data).filter((key) => !expected.includes(key)).sort();
    const missing = expected.filter((key) => !(key in data)).sort();
    if (unknown.length) throw new Error(`outline 의 모르는 키: ${unknown.join(", ")}`);
    if (missing.length) throw new Error(`outline 의 빠진 키: ${missing.join(", ")}`);
    return new Outline(/** @type {number} */ (data.level), /** @type {string[]} */ (data.headings));
  }

  asDict() {
    return { level: this.level, headings: [...this.headings] };
  }
}

export class ContractV2 {
  /** @param {string} reader @param {string} goal @param {string[]} facts @param {ProtectedSurface | Record<string, unknown>} surface @param {Outline | Record<string, unknown>} outline @param {number} [version] */
  constructor(reader, goal, facts, surface, outline, version = LATEST_CONTRACT_VERSION) {
    if (!Number.isInteger(version) || version !== LATEST_CONTRACT_VERSION) {
      throw new Error(`reader contract version 은 ${LATEST_CONTRACT_VERSION}다: ${version}`);
    }
    this.reader = checkedString(reader, "reader");
    this.goal = checkedString(goal, "goal");
    this.facts = Object.freeze(checkedStrings(facts, "facts", true));
    this.surface = surface instanceof ProtectedSurface ? surface : ProtectedSurface.fromMapping(surface);
    this.outline = outline instanceof Outline ? outline : Outline.fromMapping(outline);
    this.version = version;
    Object.freeze(this);
  }

  /** @param {unknown} raw */
  static fromMapping(raw) {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("reader contract 는 JSON 객체다");
    const data = /** @type {Record<string, unknown>} */ (raw);
    const expected = ["version", "reader", "goal", "facts", "surface", "outline"];
    const unknown = Object.keys(data).filter((key) => !expected.includes(key)).sort();
    const missing = expected.filter((key) => !(key in data)).sort();
    if (unknown.length) throw new Error(`reader contract 의 모르는 키: ${unknown.join(", ")}`);
    if (missing.length) throw new Error(`reader contract 의 빠진 키: ${missing.join(", ")}`);
    return new ContractV2(
      /** @type {string} */ (data.reader),
      /** @type {string} */ (data.goal),
      /** @type {string[]} */ (data.facts),
      /** @type {Record<string, unknown>} */ (data.surface),
      /** @type {Record<string, unknown>} */ (data.outline),
      /** @type {number} */ (data.version),
    );
  }

  get text() {
    return [this.reader, this.goal, ...this.facts, this.surface.text].filter(Boolean).join("\n");
  }

  get digest() {
    const encoded = {
      facts: this.facts,
      goal: this.goal,
      outline: { headings: this.outline.headings, level: this.outline.level },
      reader: this.reader,
      surface: {
        code: this.surface.code,
        links: this.surface.links,
        numbers: this.surface.numbers,
        urls: this.surface.urls,
      },
      version: this.version,
    };
    return digest(JSON.stringify(encoded));
  }

  asDict() {
    return {
      version: this.version,
      reader: this.reader,
      goal: this.goal,
      facts: [...this.facts],
      surface: this.surface.asDict(),
      outline: this.outline.asDict(),
    };
  }
}

/** @param {unknown} raw */
export function parseContract(raw) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("reader contract 는 JSON 객체다");
  const version = /** @type {Record<string, unknown>} */ (raw).version;
  if (version === CONTRACT_VERSION) return Contract.fromMapping(raw);
  if (version === LATEST_CONTRACT_VERSION) return ContractV2.fromMapping(raw);
  throw new Error(`reader contract version 은 ${CONTRACT_VERSIONS.join(",")} 가운데 하나다: ${version}`);
}
