// @ts-check
/**
 * 마크다운 텍스트를 문서 모델로 바꾼다. 파이썬 document/parseMarkdown.py 와 같은 판정이다.
 * 빈 줄로 블록을 나누고 첫 줄로 종류를 정한다. 코드 펜스 안은 통째로 code 다. H2 가 절을 열고 첫 H2 앞은 도입 절이다.
 */
import { splitLines } from "../text.js";
import { CODE, EMBED, HEADING, HTML, IMAGE, LIST, PROSE, TABLE } from "./model.js";

const FRONTMATTER = /^---\r?\n([\s\S]*?)\r?\n---\r?\n/;
const FENCE = /^\s*(```|~~~)/;
const HEADING_LINE = /^(#{1,6})\s+(.*?)\s*#*\s*$/;
const IMAGE_LINE = /^!\[/;
const LIST_LINE = /^\s*(?:[-*+]|\d+[.)])\s+/;
const TABLE_LINE = /^\s*\|/;
const URL_LINE = /^\s*https?:\/\/\S+\s*$/;
const HTML_LINE = /^\s*</;
const META_KEY = /^[A-Za-z][A-Za-z0-9_]*$/;
const CONTROL = /^\s*<!--\s*hanlint-(disable-next-line|disable-next|disable|enable)\b([^>]*?)-->\s*$/;
const ALL_RULES = "*";

/** frontmatter 를 읽고 본문이 시작하는 줄 번호 (1 부터) 를 함께 준다. @param {string} text */
export function parseFrontmatter(text) {
  const match = FRONTMATTER.exec(text);
  if (!match) return { meta: {}, firstLine: 1 };
  /** @type {Record<string, string>} */
  const meta = {};
  for (const line of splitLines(match[1])) {
    const at = line.indexOf(":");
    if (at < 0) continue;
    const key = line.slice(0, at).trim();
    if (META_KEY.test(key)) meta[key] = line.slice(at + 1).trim();
  }
  return { meta, firstLine: (match[0].match(/\n/g) ?? []).length + 1 };
}

/** @param {string} firstLine */
export function classify(firstLine) {
  if (HEADING_LINE.test(firstLine)) return HEADING;
  if (IMAGE_LINE.test(firstLine)) return IMAGE;
  if (TABLE_LINE.test(firstLine)) return TABLE;
  if (LIST_LINE.test(firstLine)) return LIST;
  if (URL_LINE.test(firstLine)) return EMBED;
  if (HTML_LINE.test(firstLine)) return HTML;
  return PROSE;
}

/**
 * @param {string} text
 * @param {number} firstLine
 * @returns {import("./model.js").Block[]}
 */
export function splitBlocks(text, firstLine) {
  /** @type {import("./model.js").Block[]} */
  const blocks = [];
  /** @type {string[]} */
  let buffer = [];
  let bufferStart = 0;
  let lineNo = firstLine - 1;
  /** @type {string | null} */
  let fence = null;
  let fenceStart = 0;
  /** @type {string[]} */
  let fenceLines = [];

  const flush = () => {
    if (!buffer.length) return;
    const kind = classify(buffer[0]);
    let joined = buffer.join("\n");
    let level = 0;
    if (kind === HEADING) {
      const match = /** @type {RegExpExecArray} */ (HEADING_LINE.exec(buffer[0]));
      level = match[1].length;
      joined = match[2];
    }
    blocks.push({ kind, startLine: bufferStart, endLine: bufferStart + buffer.length - 1, text: joined, level, index: blocks.length });
    buffer = [];
  };

  for (const raw of splitLines(text)) {
    lineNo += 1;
    const line = raw.replace(/\r+$/, "");
    if (fence) {
      fenceLines.push(line);
      if (FENCE.test(line) && line.trim().startsWith(fence)) {
        blocks.push({ kind: CODE, startLine: fenceStart, endLine: lineNo, text: fenceLines.join("\n"), level: 0, index: blocks.length });
        fence = null;
        fenceLines = [];
      }
      continue;
    }
    const opening = FENCE.exec(line);
    if (opening) {
      flush();
      fence = opening[1];
      fenceStart = lineNo;
      fenceLines = [line];
      continue;
    }
    if (!line.trim()) {
      flush();
      continue;
    }
    if (CONTROL.test(line)) {
      flush();
      blocks.push({ kind: HTML, startLine: lineNo, endLine: lineNo, text: line, level: 0, index: blocks.length });
      continue;
    }
    if (HEADING_LINE.test(line) && buffer.length) flush();
    if (!buffer.length) bufferStart = lineNo;
    buffer.push(line);
    if (HEADING_LINE.test(line)) flush();
  }
  flush();
  if (fence) {
    blocks.push({ kind: CODE, startLine: fenceStart, endLine: lineNo, text: fenceLines.join("\n"), level: 0, index: blocks.length });
  }
  return blocks;
}

/** @param {import("./model.js").Block[]} blocks @returns {import("./model.js").Section[]} */
export function groupSections(blocks) {
  /** @type {import("./model.js").Section[]} */
  const sections = [{ heading: null, blocks: [] }];
  for (const block of blocks) {
    if (block.kind === HEADING && block.level === 2) {
      sections.push({ heading: block, blocks: [] });
      continue;
    }
    sections[sections.length - 1].blocks.push(block);
  }
  return sections;
}

/** @param {string} raw */
function controlNames(raw) {
  const names = raw.trim().split(/[\s,]+/).filter(Boolean);
  return names.length ? names : [ALL_RULES];
}

/** @param {import("./model.js").Block[]} blocks @returns {[string, number, number][]} */
export function disabledRanges(blocks) {
  /** @type {[string, number, number][]} */
  const ranges = [];
  /** @type {Map<string, number>} */
  const opened = new Map();
  const lastLine = blocks.length ? blocks[blocks.length - 1].endLine : 1;
  blocks.forEach((block, index) => {
    const match = block.kind === HTML ? CONTROL.exec(block.text) : null;
    if (!match) return;
    const action = match[1];
    const names = controlNames(match[2]);
    if (action === "disable-next" || action === "disable-next-line") {
      if (index + 1 < blocks.length) {
        const target = blocks[index + 1];
        for (const name of names) ranges.push([name, target.startLine, target.endLine]);
      }
    } else if (action === "disable") {
      for (const name of names) if (!opened.has(name)) opened.set(name, block.startLine);
    } else {
      const closing = names.length === 1 && names[0] === ALL_RULES ? [...opened.keys()] : names;
      for (const name of closing) {
        if (opened.has(name)) {
          ranges.push([name, /** @type {number} */ (opened.get(name)), block.endLine]);
          opened.delete(name);
        }
      }
    }
  });
  for (const [name, start] of opened) ranges.push([name, start, lastLine]);
  return ranges;
}

/**
 * @param {string} text
 * @param {string | null} [path]
 * @returns {import("./model.js").Document}
 */
export function parseMarkdown(text, path = null) {
  const { meta, firstLine } = parseFrontmatter(text);
  const body = firstLine === 1 ? text : splitLines(text).slice(firstLine - 1).join("\n");
  const blocks = splitBlocks(body, firstLine);
  return { path, frontmatter: meta, blocks, sections: groupSections(blocks), disabled: disabledRanges(blocks) };
}
