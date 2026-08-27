// @ts-check
/**
 * hanlint 설정에 쓰이는 TOML 부분집합을 읽는다. 의존성 0 을 지키려고 직접 쓴다.
 *
 * 되는 것: 주석, `key = 값`, 점 키, `[table]`, `[[array]]`, 문자열 ("..." 와 '...'), 정수, 실수, 불리언,
 * 여러 줄 배열, 인라인 테이블. 안 되는 것: 여러 줄 문자열, 날짜. 만나면 어디서 막혔는지 말하고 던진다.
 */

const BACKSLASH = String.fromCharCode(92);
/** @type {Record<string, string>} */
const SIMPLE_ESCAPES = { n: "\n", t: "\t", r: "\r", '"': '"', b: "\b", f: "\f", [BACKSLASH]: BACKSLASH };

/** @param {string} text @returns {Record<string, unknown>} */
export function parseToml(text) {
  return new Parser(text).document();
}

class Parser {
  /** @param {string} text */
  constructor(text) {
    this.text = text;
    this.pos = 0;
    /** @type {Record<string, unknown>} */
    this.root = {};
    this.current = this.root;
  }

  /** @param {string} message */
  error(message) {
    const line = this.text.slice(0, this.pos).split("\n").length;
    return new Error(`TOML ${line}번째 줄: ${message}. hanlint 가 읽는 TOML 부분집합이 아니다`);
  }

  document() {
    for (;;) {
      this.skipBlank();
      if (this.pos >= this.text.length) return this.root;
      if (this.text.startsWith("[[", this.pos)) this.arrayTable();
      else if (this.text[this.pos] === "[") this.table();
      else this.keyValue(this.current);
      this.endOfLine();
    }
  }

  skipBlank() {
    while (this.pos < this.text.length) {
      const c = this.text[this.pos];
      if (c === "#") {
        while (this.pos < this.text.length && this.text[this.pos] !== "\n") this.pos++;
      } else if (c === " " || c === "\t" || c === "\n" || c === "\r") {
        this.pos++;
      } else {
        return;
      }
    }
  }

  skipSpaces() {
    while (this.pos < this.text.length && (this.text[this.pos] === " " || this.text[this.pos] === "\t")) this.pos++;
  }

  endOfLine() {
    this.skipSpaces();
    if (this.pos >= this.text.length) return;
    const c = this.text[this.pos];
    if (c === "#") {
      while (this.pos < this.text.length && this.text[this.pos] !== "\n") this.pos++;
      return;
    }
    if (c === "\n" || c === "\r") return;
    throw this.error(`줄 끝에 남은 글자 '${c}'`);
  }

  /** @returns {string[]} */
  keyPath() {
    const parts = [];
    for (;;) {
      this.skipSpaces();
      const c = this.text[this.pos];
      if (c === '"' || c === "'") {
        parts.push(this.string());
      } else {
        const match = /^[A-Za-z0-9_-]+/.exec(this.text.slice(this.pos));
        if (!match) throw this.error("키가 없다");
        parts.push(match[0]);
        this.pos += match[0].length;
      }
      this.skipSpaces();
      if (this.text[this.pos] === ".") {
        this.pos++;
        continue;
      }
      return parts;
    }
  }

  /** @param {Record<string, unknown>} base @param {string[]} parts */
  descend(base, parts) {
    let node = base;
    for (const part of parts) {
      if (!(part in node)) node[part] = {};
      const next = node[part];
      if (Array.isArray(next)) node = /** @type {Record<string, unknown>} */ (next[next.length - 1]);
      else if (typeof next === "object" && next !== null) node = /** @type {Record<string, unknown>} */ (next);
      else throw this.error(`${part} 는 테이블이 아니다`);
    }
    return node;
  }

  table() {
    this.pos++;
    const parts = this.keyPath();
    if (this.text[this.pos] !== "]") throw this.error("] 가 없다");
    this.pos++;
    this.current = this.descend(this.root, parts);
  }

  arrayTable() {
    this.pos += 2;
    const parts = this.keyPath();
    if (!this.text.startsWith("]]", this.pos)) throw this.error("]] 가 없다");
    this.pos += 2;
    const parent = this.descend(this.root, parts.slice(0, -1));
    const name = parts[parts.length - 1];
    if (!(name in parent)) parent[name] = [];
    const list = parent[name];
    if (!Array.isArray(list)) throw this.error(`${name} 은 배열이 아니다`);
    /** @type {Record<string, unknown>} */
    const entry = {};
    list.push(entry);
    this.current = entry;
  }

  /** @param {Record<string, unknown>} target */
  keyValue(target) {
    const parts = this.keyPath();
    if (this.text[this.pos] !== "=") throw this.error("= 가 없다");
    this.pos++;
    this.skipSpaces();
    const node = this.descend(target, parts.slice(0, -1));
    node[parts[parts.length - 1]] = this.value();
  }

  /** @returns {unknown} */
  value() {
    this.skipSpaces();
    const c = this.text[this.pos];
    if (c === '"' || c === "'") return this.string();
    if (c === "[") return this.array();
    if (c === "{") return this.inlineTable();
    const rest = this.text.slice(this.pos);
    const bool = /^(true|false)(?![A-Za-z0-9_])/.exec(rest);
    if (bool) {
      this.pos += bool[0].length;
      return bool[1] === "true";
    }
    const number = /^[+-]?(?:\d[\d_]*)(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?(?![A-Za-z_])/.exec(rest);
    if (number) {
      this.pos += number[0].length;
      return Number(number[0].replace(/_/g, ""));
    }
    throw this.error(`값을 읽을 수 없다: '${rest.slice(0, 12)}'`);
  }

  string() {
    const quote = this.text[this.pos];
    if (this.text.startsWith(quote.repeat(3), this.pos)) throw this.error("여러 줄 문자열은 지원하지 않는다");
    this.pos++;
    let out = "";
    while (this.pos < this.text.length) {
      const c = this.text[this.pos];
      if (c === quote) {
        this.pos++;
        return out;
      }
      if (c === "\n") throw this.error("문자열이 닫히지 않았다");
      if (quote === '"' && c === BACKSLASH) {
        const next = this.text[this.pos + 1];
        if (next in SIMPLE_ESCAPES) {
          out += SIMPLE_ESCAPES[next];
          this.pos += 2;
          continue;
        }
        if (next === "u" || next === "U") {
          const width = next === "u" ? 4 : 8;
          const hex = this.text.slice(this.pos + 2, this.pos + 2 + width);
          out += String.fromCodePoint(parseInt(hex, 16));
          this.pos += 2 + width;
          continue;
        }
        throw this.error(`모르는 이스케이프 ${BACKSLASH}${next}`);
      }
      out += c;
      this.pos++;
    }
    throw this.error("문자열이 닫히지 않았다");
  }

  array() {
    this.pos++;
    /** @type {unknown[]} */
    const items = [];
    for (;;) {
      this.skipBlank();
      if (this.text[this.pos] === "]") {
        this.pos++;
        return items;
      }
      items.push(this.value());
      this.skipBlank();
      if (this.text[this.pos] === ",") this.pos++;
      else if (this.text[this.pos] !== "]") throw this.error("배열에 , 나 ] 가 없다");
    }
  }

  inlineTable() {
    this.pos++;
    /** @type {Record<string, unknown>} */
    const table = {};
    this.skipSpaces();
    if (this.text[this.pos] === "}") {
      this.pos++;
      return table;
    }
    for (;;) {
      this.keyValue(table);
      this.skipSpaces();
      if (this.text[this.pos] === ",") {
        this.pos++;
        continue;
      }
      if (this.text[this.pos] === "}") {
        this.pos++;
        return table;
      }
      throw this.error("인라인 테이블에 , 나 } 가 없다");
    }
  }
}
