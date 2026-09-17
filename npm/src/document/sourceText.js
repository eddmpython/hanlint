// @ts-check
/**
 * 소스 파일의 글 마디. 사람이 읽는 한국어 문자열 리터럴과 JSX 글을 줄 번호와 함께 뽑는다.
 * 뜻과 규칙은 파이썬 document/sourceText.py 가 소유한다. 여기는 같은 값을 낸다.
 */

export const SOURCE_SUFFIXES = [".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".rs", ".py"];

const KOREAN = /[가-힣]/;
// 문자열의 경계. 줄을 앞에서부터 훑어 여는 따옴표에서 같은 닫는 따옴표까지를 한 마디로 본다. 파이썬 sourceText.py 와 같다.
const QUOTES = ["'", '"', "`"];
const EXPRESSION = /\{[^{}]*\}/g;
const BLOCK_COMMENT = /\/\*[\s\S]*?\*\//g;
const DEVELOPER_LINE = /new Error\(|console\.|panic!\(|expect\(|assert/;
const RUST_CONTINUATION = /\\\r?\n[ \t]*/g;
const RUST_TEST_MARKER = "#[cfg(test)]";

/**
 * @typedef {object} SourceLiteral
 * @property {number} line 1부터 세는 줄 번호. 여러 줄을 이은 러스트 문자열은 시작 줄이다
 * @property {string} text 따옴표와 태그를 뺀 글. 파일에 있는 그대로라 되돌려 쓸 때 찾을 수 있다
 * @property {string} plain 검사에 쓰는 글. 식 (`${...}`, `{...}`) 을 비우고 공백을 하나로 모았다
 */

/** 템플릿 리터럴의 `${ ... }` 식을 (중첩 괄호를 세어) 같은 길이의 빈칸으로 바꾼다. @param {string} source */
export function withoutTemplateExpressions(source) {
  let output = "";
  let index = 0;
  while (index < source.length) {
    if (source[index] === "$" && source[index + 1] === "{") {
      let depth = 0;
      let cursor = index + 1;
      for (; cursor < source.length; cursor++) {
        if (source[cursor] === "{") depth += 1;
        else if (source[cursor] === "}") {
          depth -= 1;
          if (depth === 0) break;
        }
      }
      output += " ".repeat(cursor + 1 - index);
      index = cursor + 1;
      continue;
    }
    output += source[index];
    index += 1;
  }
  return output;
}

/** 주석과 개발자용 줄을 걷어낸 소스. 줄 번호는 유지한다. @param {string} source @param {string} path */
export function userFacingSource(source, path) {
  const isRust = path.endsWith(".rs");
  let body = source;
  if (isRust && body.includes(RUST_TEST_MARKER)) body = body.slice(0, body.indexOf(RUST_TEST_MARKER));
  if (isRust) body = body.replace(RUST_CONTINUATION, "");
  body = body.replace(BLOCK_COMMENT, (block) => block.replace(/[^\n]/g, " "));
  return body
    .split("\n")
    .map((line) => {
      const trimmed = line.trim();
      if (trimmed.startsWith("//") || trimmed.startsWith("*") || trimmed.startsWith("#")) return "";
      if (DEVELOPER_LINE.test(line)) return "";
      return line.replace(/\/\/.*$/, "");
    })
    .join("\n");
}

/** 검사에 쓰는 글. 식을 비우고 공백을 하나로 모은다. @param {string} text */
export function plainText(text) {
  let copy = withoutTemplateExpressions(text);
  while (EXPRESSION.test(copy)) copy = copy.replace(EXPRESSION, " ");
  return copy.replace(/\s+/g, " ").trim();
}

/** `start` 의 따옴표를 닫는 자리. 역슬래시 뒤 글자는 건너뛴다. 없으면 -1. @param {string} line @param {number} start */
function closingQuote(line, start) {
  const quote = line[start];
  let index = start + 1;
  while (index < line.length) {
    const char = line[index];
    if (char === "\\") {
      index += 2;
      continue;
    }
    if (char === quote) return index;
    index += 1;
  }
  return -1;
}

/** `index` 의 `>` 가 JSX 여는 태그의 끝인가. 뜻은 파이썬 tagCloses 가 소유한다. @param {string} line @param {number} index */
function tagCloses(line, index) {
  if (index === 0 || line[index + 1] === "=") return false;
  const before = line[index - 1];
  return "\"'}".includes(before) || /[A-Za-z0-9]/.test(before);
}

/** 한 줄의 글 마디를 나온 차례로. 뜻은 파이썬 lineLiterals 가 소유한다. @param {string} line @returns {string[]} */
export function lineLiterals(line) {
  /** @type {string[]} */
  const found = [];
  let index = 0;
  while (index < line.length) {
    const char = line[index];
    if (QUOTES.includes(char)) {
      const end = closingQuote(line, index);
      if (end < 0) break;
      found.push(line.slice(index + 1, end));
      index = end + 1;
      continue;
    }
    if (char === ">" && tagCloses(line, index)) {
      const end = line.indexOf("<", index + 1);
      if (end > index) {
        const inner = line.slice(index + 1, end);
        found.push(inner);
        if (!inner.includes("{")) {
          index = end;
          continue;
        }
      }
    }
    index += 1;
  }
  return found;
}

/** 소스에서 글 마디를 줄 번호 순으로. @param {string} source @param {string} [path] @returns {SourceLiteral[]} */
export function sourceLiterals(source, path = "") {
  /** @type {SourceLiteral[]} */
  const found = [];
  userFacingSource(source, path).split("\n").forEach((line, index) => {
    for (const raw of lineLiterals(line)) {
      const text = raw.trim();
      const plain = plainText(text);
      if (text && KOREAN.test(plain)) found.push({ line: index + 1, text, plain });
    }
  });
  return found;
}

/**
 * 한 줄 안에서 글 `old` 를 `new` 로 바꾼다. 몇 번 나왔는지 같이 준다 (한 번일 때만 바꾼 것이 확정이다).
 * @param {string} lineText @param {string} oldText @param {string} newText @returns {[string, number]}
 */
export function replaceLiteral(lineText, oldText, newText) {
  const count = lineText.split(oldText).length - 1;
  if (count !== 1) return [lineText, count];
  return [lineText.replace(oldText, () => newText), 1];
}
