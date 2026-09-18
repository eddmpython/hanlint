// @ts-check
/**
 * 소스 파일의 글 마디. 사람이 읽는 한국어 문자열 리터럴과 JSX 글을 줄 번호와 함께 뽑는다.
 * 뜻과 규칙은 파이썬 document/sourceText.py 가 소유한다. 여기는 같은 값을 낸다.
 */

export const SOURCE_SUFFIXES = [".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".rs", ".py", ".html", ".htm", ".vue", ".svelte"];
/** 태그 사이 글과 속성값을 JSX 와 같은 길로 읽는 파일. HTML 주석 `<!-- -->` 을 걷어낸다. */
const MARKUP_SUFFIXES = [".html", ".htm", ".vue", ".svelte"];

const KOREAN = /[가-힣]/;
// 문자열의 경계. 줄을 앞에서부터 훑어 여는 따옴표에서 같은 닫는 따옴표까지를 한 마디로 본다. 파이썬 sourceText.py 와 같다.
const QUOTES = ["'", '"', "`"];
const BLOCK_COMMENT = /\/\*[\s\S]*?\*\//g;
const HTML_COMMENT = /<!--[\s\S]*?-->/g;
const DEVELOPER_LINE = /new Error\(|console\.|panic!\(|expect\(|assert/;
const RUST_CONTINUATION = /\\\r?\n[ \t]*/g;
const RUST_TEST_MARKER = "#[cfg(test)]";
/** 문장을 끊지 않는 HTML 인라인 태그. 같은 줄에서 이 태그만 사이에 둔 글 조각은 한 마디로 잇는다. 파이썬 INLINE_TAGS 와 같다. */
const INLINE_TAGS = new Set("a abbr b bdi bdo cite code data del dfn em i ins kbd mark q s samp small span strong sub sup time u var wbr br".split(" "));
const INLINE_TAG = /<\/?([a-zA-Z][a-zA-Z0-9]*)[^<>]*>/g;
const INLINE_GAP = /^(?:\s*<\/?[a-zA-Z][a-zA-Z0-9]*[^<>]*>)+\s*$/;
const SIBLING_GAP = /<\/[a-zA-Z][a-zA-Z0-9]*\s*>\s*<[a-zA-Z]/;
const CODE_OPEN = /<(?:script|style)\b/i;
const CODE_TAG = /<\/?(?:script|style)\b[^<>]*>/gi;
const CODE_CLOSE = /<\/(?:script|style)\s*>/i;
/** 마크업 파일에서 태그도 코드 기호도 없는 줄. 여러 줄 문단의 이어지는 줄이다. */
const PROSE_LINE = /^(?![\s]*$)[^<>=;{}]*$/;
const HEAD_TEXT = /^\s*[^<\s][^<]*(?=<\/)/;

/**
 * @typedef {object} SourceLiteral
 * @property {number} line 1부터 세는 줄 번호. 여러 줄을 이은 러스트 문자열은 시작 줄이다
 * @property {string} text 따옴표와 태그를 뺀 글. 파일에 있는 그대로라 되돌려 쓸 때 찾을 수 있다
 * @property {string} plain 검사에 쓰는 글. 식 (`${...}`, `{...}`) 을 비우고 공백을 하나로 모았다
 * @property {number} column 1부터 세는 칸. 그 줄에서 text 가 시작하는 자리
 */

/** `start` 의 `{` 를 닫는 `}` 의 자리. 뜻은 파이썬 balancedEnd 가 소유한다. @param {string} line @param {number} start */
function balancedEnd(line, start) {
  let depth = 0;
  let index = start;
  while (index < line.length) {
    const char = line[index];
    if (QUOTES.includes(char)) {
      const end = closingQuote(line, index);
      if (end < 0) return -1;
      index = end + 1;
      continue;
    }
    if (char === "{") depth += 1;
    else if (char === "}") {
      depth -= 1;
      if (depth === 0) return index;
    }
    index += 1;
  }
  return -1;
}

/** 글에 낀 식 `{...}` 와 `${...}` 의 [시작, 끝 다음]. 뜻은 파이썬 expressionSpans 가 소유한다. @param {string} text @returns {[number, number][]} */
export function expressionSpans(text) {
  /** @type {[number, number][]} */
  const spans = [];
  let index = 0;
  while (index < text.length) {
    if (text[index] === "{") {
      const end = balancedEnd(text, index);
      if (end < 0) break;
      const start = index > 0 && text[index - 1] === "$" ? index - 1 : index;
      spans.push([start, end + 1]);
      index = end + 1;
      continue;
    }
    index += 1;
  }
  return spans;
}

/** 템플릿 리터럴의 `${ ... }` 식을 같은 길이의 빈칸으로 바꾼다. 뜻은 파이썬 withoutTemplateExpressions 가 소유한다. @param {string} source */
export function withoutTemplateExpressions(source) {
  let output = source;
  for (const [start, end] of expressionSpans(source)) {
    if (source[start] === "$") output = output.slice(0, start) + " ".repeat(end - start) + output.slice(end);
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
  if (MARKUP_SUFFIXES.some((suffix) => path.endsWith(suffix))) body = body.replace(HTML_COMMENT, (block) => block.replace(/[^\n]/g, " "));
  return body
    .split("\n")
    .map((line) => {
      const trimmed = line.trim();
      if (trimmed.startsWith("//") || trimmed.startsWith("*") || trimmed.startsWith("#")) return "";
      if (DEVELOPER_LINE.test(line)) return "";
      return withoutLineComment(line);
    })
    .join("\n");
}


/**
 * 따옴표 밖의 `//` 부터 자른다. `https://` 처럼 `:` 뒤의 `//` 는 주소라 두고, 문자열 안의 `//` 도 둔다.
 * 뜻은 파이썬 document/sourceText.py 의 withoutLineComment 가 소유한다.
 */
export function withoutLineComment(line) {
  let quote = null;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (quote) {
      if (char === "\\") { i++; continue; }
      if (char === quote) quote = null;
    } else if (char === "'" || char === '"' || char === "`") quote = char;
    else if (char === "/" && line[i + 1] === "/" && (i === 0 || line[i - 1] !== ":")) return line.slice(0, i);
  }
  return line;
}

/** 검사에 쓰는 글. 식을 비우고 공백을 하나로 모은다. @param {string} text */
export function plainText(text) {
  let plain = "";
  let cursor = 0;
  for (const [start, end] of expressionSpans(text)) {
    plain += text.slice(cursor, start) + " ";
    cursor = end;
  }
  plain += text.slice(cursor);
  // 인라인 태그를 비운다. 이름이 영문자로 시작하는 것만이라 `<대상> 필요` 의 꺾쇠는 남는다.
  plain = plain.replace(INLINE_TAG, (tag, name) => (INLINE_TAGS.has(name.toLowerCase()) ? "" : tag));
  return plain.replace(/\s+/g, " ").trim();
}

/** `start` 의 따옴표를 닫는 자리. 백틱 안의 `${...}` 은 통째로 건너뛴다. 뜻은 파이썬 closingQuote 가 소유한다. @param {string} line @param {number} start */
function closingQuote(line, start) {
  const quote = line[start];
  let index = start + 1;
  while (index < line.length) {
    const char = line[index];
    if (char === "\\") {
      index += 2;
      continue;
    }
    if (quote === "`" && char === "$" && line[index + 1] === "{") {
      const end = balancedEnd(line, index + 1);
      if (end < 0) return -1;
      index = end + 1;
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

/** `start` 부터의 JSX 글이 끝나는 `<` 의 자리. 식 안의 `<` 는 글의 끝이 아니다. 뜻은 파이썬 jsxTextEnd 가 소유한다. @param {string} line @param {number} start */
function jsxTextEnd(line, start) {
  let index = start;
  while (index < line.length) {
    const char = line[index];
    if (char === "<") return index;
    if (char === "{") {
      const end = balancedEnd(line, index);
      if (end < 0) return -1;
      index = end + 1;
      continue;
    }
    index += 1;
  }
  return -1;
}

/** 글에 낀 식 안의 글 마디. 뜻은 파이썬 innerLiterals 가 소유한다. @param {string} text @param {number} offset @returns {[number, string][]} */
function innerLiterals(text, offset) {
  /** @type {[number, string][]} */
  const found = [];
  for (const [start, end] of expressionSpans(text)) {
    const brace = text[start] === "$" ? start + 1 : start;
    found.push(...lineLiterals(text.slice(brace + 1, end - 1), offset + brace + 1));
  }
  return found;
}

/** 한 줄의 글 마디를 [시작 자리, 글] 로 나온 차례로. 뜻은 파이썬 lineLiterals 가 소유한다. @param {string} line @param {number} [offset] @returns {[number, string][]} */
/**
 * openEnded (마크업 파일) 이면 여는 태그 뒤 줄 끝까지의 글과 줄 처음부터 닫는 태그 앞까지의 글도 마디다.
 * 뜻은 파이썬 lineLiterals 가 소유한다.
 * @param {string} line @param {number} [offset] @param {boolean} [openEnded]
 */
export function lineLiterals(line, offset = 0, openEnded = false) {
  /** @type {[number, string][]} */
  const found = [];
  let index = 0;
  while (index < line.length) {
    const char = line[index];
    if (QUOTES.includes(char)) {
      const end = closingQuote(line, index);
      if (end < 0) break;
      const raw = line.slice(index + 1, end);
      found.push([offset + index + 1, raw]);
      if (char === "`") found.push(...innerLiterals(raw, offset + index + 1));
      index = end + 1;
      continue;
    }
    if (char === ">" && tagCloses(line, index)) {
      let end = jsxTextEnd(line, index + 1);
      if (end < 0 && openEnded && index + 1 < line.length) end = line.length;
      if (end > index) {
        const raw = line.slice(index + 1, end);
        found.push([offset + index + 1, raw]);
        found.push(...innerLiterals(raw, offset + index + 1));
        index = end;
        continue;
      }
    }
    index += 1;
  }
  if (openEnded) {
    const head = HEAD_TEXT.exec(line);
    if (head && !found.some(([start]) => start < head[0].length)) found.push([offset, head[0]]);
    else if (!found.length && PROSE_LINE.test(line)) found.push([offset, line]);
  }
  found.sort((a, b) => a[0] - b[0]);
  return joinInline(line, found, offset);
}

/**
 * 사이가 인라인 태그뿐인 태그 사이 글 조각을 한 마디로 잇는다. 태그 안의 속성 문자열은 잇기에 끼지 않고 제 마디로 남는다.
 * 뜻은 파이썬 joinInline 이 소유한다.
 * @param {string} line @param {[number, string][]} found @param {number} offset @returns {[number, string][]}
 */
function joinInline(line, found, offset) {
  const pieces = found.filter(([, raw]) => raw.trim());
  const attributes = pieces.filter(([start]) => insideTag(line, start - offset));
  /** @type {[number, string][]} */
  const joined = [];
  for (const piece of pieces) {
    if (attributes.includes(piece)) continue;
    const [start, raw] = piece;
    if (joined.length) {
      const [previousStart, previousRaw] = joined[joined.length - 1];
      const tail = previousStart - offset + previousRaw.length;
      if (start - offset >= tail && inlineOnly(line.slice(tail, start - offset))) {
        joined[joined.length - 1] = [previousStart, line.slice(previousStart - offset, start - offset + raw.length)];
        continue;
      }
    }
    joined.push([start, raw]);
  }
  return [...joined, ...attributes].sort((a, b) => a[0] - b[0]);
}

/** position 이 태그 안 (`<` 뒤, `>` 앞) 인가. @param {string} line @param {number} position */
function insideTag(line, position) {
  const opened = line.lastIndexOf("<", position - 1);
  return opened >= 0 && line.lastIndexOf(">", position - 1) < opened;
}

/** 사이가 인라인 태그뿐이고 형제 (`</a><a>`) 가 아니다. @param {string} gap */
function inlineOnly(gap) {
  if (!INLINE_GAP.test(gap) || SIBLING_GAP.test(gap)) return false;
  return [...gap.matchAll(INLINE_TAG)].every((match) => INLINE_TAGS.has(match[1].toLowerCase()));
}

/** 소스에서 글 마디를 줄 번호 순으로. @param {string} source @param {string} [path] @returns {SourceLiteral[]} */
export function sourceLiterals(source, path = "") {
  /** @type {SourceLiteral[]} */
  const found = [];
  const markup = MARKUP_SUFFIXES.some((suffix) => path.endsWith(suffix));
  // 마크업은 주석 지우기가 줄 수를 지키므로 원문 줄과 나란히 간다. script 블록 판정은 원문 줄로 한다 (`// 주석</script>` 가 지워져도).
  const rawLines = markup ? source.split("\n") : [];
  let inCode = false;
  userFacingSource(source, path).split("\n").forEach((line, index) => {
    // <script> 와 <style> 안은 코드다. 열린 조각 규칙을 끄고 따옴표 문자열만 잡는다. 태그 자체는 빈칸으로 바꿔 자리를 지킨다.
    const rawLine = markup && index < rawLines.length ? rawLines[index] : line;
    const opensCode = markup && CODE_OPEN.test(rawLine);
    const closesCode = markup && CODE_CLOSE.test(rawLine);
    const openEnded = markup && !inCode && !opensCode;
    if (markup) {
      if (opensCode && !closesCode) inCode = true;
      else if (inCode && closesCode) inCode = false;
    }
    const scanned = opensCode || closesCode ? line.replace(CODE_TAG, (tag) => " ".repeat(tag.length)) : line;
    for (const [start, raw] of lineLiterals(scanned, 0, openEnded)) {
      const text = raw.trim();
      const plain = plainText(text);
      if (text && KOREAN.test(plain)) found.push({ line: index + 1, text, plain, column: start + (raw.length - raw.trimStart().length) + 1 });
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
