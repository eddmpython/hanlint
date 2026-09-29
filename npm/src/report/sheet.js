// @ts-check
/**
 * 글 시트. 소스에서 뽑은 글 마디와 지적을 마크다운 표 하나로 내고, 사람이 고친 표를 다시 읽는다.
 * 뜻과 칸의 정본은 파이썬 report/sheet.py 다. 여기는 같은 글자를 낸다.
 */

import { parseMarkdown } from "../document/parseMarkdown.js";
import { replaceLiteral, sourceLiterals } from "../document/sourceText.js";
import { buildFingerprint } from "../fingerprint/build.js";
import { runAll } from "../rules/registry.js";

export const HEADER = ["번호", "자리", "글", "지적", "고침"];
const ROW_PATTERN = /^\|(.*)\|$/;

/**
 * @typedef {object} SheetRow
 * @property {string} file 작업 폴더 기준 상대 경로. 구분자는 언제나 `/`
 * @property {number} line
 * @property {string} text
 * @property {import("../rules/finding.js").Finding[]} findings
 * @property {string} fix 사람이 표에 적은 고친 글. 뽑을 때는 비어 있다
 * @property {number} column 1부터 세는 칸. 0 이면 모른다
 */

/** @param {string} text */
/**
 * 지적이 하나이고 그 지적에 고침이 있으면 고침 칸에 미리 적는다. 뜻은 파이썬 report/sheet.py 의 prefilledFix 가 소유한다.
 * @param {import("../document/sourceText.js").SourceLiteral} literal
 * @param {import("../rules/finding.js").Finding[]} findings
 */
function prefilledFix(literal, findings) {
  if (literal.plain !== literal.text || findings.length !== 1) return "";
  const only = findings[0];
  return only.fix !== null && only.quote === literal.plain ? only.fix : "";
}

/**
 * (라벨, 소스) 마다 글을 뽑아 규칙을 돌리고 표의 행을 만든다. 지적은 `error` 만 남긴다.
 * 소스를 읽는 쪽 (CLI 는 디스크, 브라우저는 저장소) 이 다르므로 읽기는 밖에 두고 문자열만 받는다.
 * @param {Iterable<{ label: string, source: string }>} sources
 * @param {import("../config/settings.js").Config} config
 * @param {boolean} [everything] 지적이 없는 글도 넣는다
 * @returns {SheetRow[]}
 */
export function sheetRows(sources, config, everything = false) {
  /** @type {SheetRow[]} */
  const rows = [];
  for (const { label, source } of sources) {
    for (const literal of sourceLiterals(source, label)) {
      const findings = runAll(buildFingerprint(parseMarkdown(literal.plain), config), config).filter((finding) => finding.severity === "error");
      if (findings.length || everything) rows.push({ file: label, line: literal.line, text: literal.text, findings, fix: prefilledFix(literal, findings), column: literal.column });
    }
  }
  return rows;
}

export function escapeCell(text) {
  return text.replaceAll("\\", "\\\\").replaceAll("|", "\\|");
}

/** @param {string} text */
export function unescapeCell(text) {
  return text.replaceAll("\\|", "|").replaceAll("\\\\", "\\");
}

/** `| a | b |` 를 칸으로. `\|` 는 칸 경계가 아니다. @param {string} line @returns {string[] | null} */
export function splitRow(line) {
  const match = ROW_PATTERN.exec(line.trim());
  if (!match) return null;
  const cells = [];
  let current = "";
  let escaped = false;
  for (const char of match[1]) {
    if (escaped) {
      current += char;
      escaped = false;
    } else if (char === "\\") {
      current += char;
      escaped = true;
    } else if (char === "|") {
      cells.push(current.trim());
      current = "";
    } else current += char;
  }
  cells.push(current.trim());
  return cells;
}

/** @param {import("../rules/finding.js").Finding[]} findings */
const CUE = /^`[^`]+`/;


/**
 * `column` (1부터) 에 `old` 가 그대로 있으면 그 자리만 `new` 로 바꾼다.
 * @param {string} lineText @param {number} column @param {string} old @param {string} replacement @returns {[string, boolean]}
 */
function replaceAt(lineText, column, old, replacement) {
  const start = column - 1;
  if (start < 0 || lineText.slice(start, start + old.length) !== old) return [lineText, false];
  return [lineText.slice(0, start) + replacement + lineText.slice(start + old.length), true];
}

/**
 * 한 파일의 소스에 표의 행들을 되돌려 쓴다. [새 소스, 적용한 자리, 실패한 자리와 이유]. 뜻은 파이썬 report/sheet.py 의
 * applyRows 가 소유한다. 한 줄에 고침이 여럿이면 뒤 칸부터 바꾼다. 줄은 `\n` 으로만 나누므로 `\r` 은 남아 CRLF 파일이 그대로다.
 * @param {string} source @param {SheetRow[]} rows @returns {[string, string[], string[]]}
 */
export function applyRows(source, rows) {
  const lines = source.split("\n");
  /** @type {string[]} */
  const applied = [];
  /** @type {string[]} */
  const failed = [];
  for (const row of [...rows].sort((a, b) => a.line - b.line || b.column - a.column)) {
    const place = placeOf(row);
    if (row.line < 1 || row.line > lines.length) {
      failed.push(`${place}: 그 줄이 없다`);
      continue;
    }
    let newLine = lines[row.line - 1];
    if (row.column > 0) {
      const [replaced, hit] = replaceAt(newLine, row.column, row.text, row.fix);
      if (!hit) {
        failed.push(`${place}: 그 칸에 그 글이 없다. 표를 다시 뽑는다`);
        continue;
      }
      newLine = replaced;
    } else {
      const [replaced, count] = replaceLiteral(newLine, row.text, row.fix);
      if (count !== 1) {
        failed.push(`${place}: 글이 그 줄에 ${count}번 있다. 한 번이어야 바꾼다`);
        continue;
      }
      newLine = replaced;
    }
    lines[row.line - 1] = newLine;
    applied.push(`${place}: ${row.text} -> ${row.fix}`);
  }
  return [lines.join("\n"), applied, failed];
}

/**
 * 규칙마다 한 번. 첫 지적의 이유는 온전히, 같은 규칙의 나머지는 단서 (이유 앞의 `…`) 만 `(또 …)` 로 잇는다.
 * 뜻은 파이썬 report/sheet.py 의 findingCell 이 소유한다.
 * @param {import("../rules/finding.js").Finding[]} findings
 */
function findingCell(findings) {
  /** @type {Map<string, string[]>} */
  const byRule = new Map();
  for (const finding of findings) {
    if (!byRule.has(finding.rule)) byRule.set(finding.rule, []);
    /** @type {string[]} */ (byRule.get(finding.rule)).push(finding.why);
  }
  const cells = [];
  for (const [rule, whys] of byRule) {
    let cell = `${rule}: ${whys[0]}`;
    if (whys.length > 1) {
      const cues = whys.slice(1).map((why) => CUE.exec(why)?.[0]).filter((cue) => cue !== undefined);
      cell += cues.length === whys.length - 1 ? ` (또 ${cues.join(", ")})` : ` (또 ${whys.length - 1}건)`;
    }
    cells.push(cell);
  }
  return cells.join(" / ");
}

/** @param {SheetRow} row */
function placeOf(row) {
  return row.column > 0 ? `${row.file}:${row.line}:${row.column}` : `${row.file}:${row.line}`;
}

/** `경로:줄:칸` 이나 `경로:줄` 을 [경로, 줄, 칸] 으로. 칸이 없으면 0. 꼴이 아니면 경로가 null. @param {string} place @returns {[string | null, number, number]} */
export function splitPlace(place) {
  const last = place.lastIndexOf(":");
  if (last < 0 || !/^[0-9]+$/.test(place.slice(last + 1))) return [null, 0, 0];
  const head = place.slice(0, last);
  const middle = head.lastIndexOf(":");
  if (middle > 0 && /^[0-9]+$/.test(head.slice(middle + 1))) return [head.slice(0, middle), Number(head.slice(middle + 1)), Number(place.slice(last + 1))];
  return [head, Number(place.slice(last + 1)), 0];
}

/** 사람이 읽고 고치는 마크다운 표. @param {SheetRow[]} rows @param {string} preset @param {number} fileCount */
export function renderSheet(rows, preset, fileCount) {
  const flagged = rows.filter((row) => row.findings.length).length;
  const lines = [
    "# hanlint sheet",
    "",
    `프리셋 ${preset}, 파일 ${fileCount}개, 글 ${rows.length}개, 지적 있는 글 ${flagged}개. ` +
      "고침 칸에 새 글을 적고 `hanlint sheet apply 이파일.md` 로 되돌려 쓴다. 다른 칸은 고치지 않는다.",
    "",
    `| ${HEADER.join(" | ")} |`,
    `| ${HEADER.map(() => "---").join(" | ")} |`,
  ];
  rows.forEach((row, index) => {
    const cells = [String(index + 1), placeOf(row), row.text, findingCell(row.findings), row.fix];
    lines.push(`| ${cells.map(escapeCell).join(" | ")} |`);
  });
  return lines.join("\n");
}

/** 기계가 읽는 형식. @param {SheetRow[]} rows @param {string} preset @param {number} fileCount */
export function renderSheetJson(rows, preset, fileCount) {
  const data = {
    version: 1,
    preset,
    files: fileCount,
    rows: rows.map((row) => ({
      file: row.file,
      line: row.line,
      column: row.column,
      text: row.text,
      findings: row.findings.map((finding) => ({ rule: finding.rule, why: finding.why })),
      fix: row.fix,
    })),
  };
  return JSON.stringify(data, null, 2);
}

/**
 * 사람이 고친 표를 읽는다. 머리글과 구분선은 넘기고 `고침` 이 있는 줄만 남긴다.
 * @param {string} markdown @returns {{ rows: SheetRow[], problems: string[] }}
 */
export function parseSheet(markdown) {
  /** @type {SheetRow[]} */
  const rows = [];
  /** @type {string[]} */
  const problems = [];
  markdown.split("\n").forEach((raw, index) => {
    const lineNumber = index + 1;
    const cells = splitRow(raw);
    if (cells === null) return;
    if (cells.slice(0, HEADER.length).join(" ") === HEADER.join(" ") || cells.every((cell) => cell.replace(/-/g, "") === "")) return;
    if (cells.length !== HEADER.length) {
      problems.push(`${lineNumber}행: 칸이 ${cells.length}개다. ${HEADER.length}개여야 한다`);
      return;
    }
    const place = unescapeCell(cells[1]);
    const [file, line, column] = splitPlace(place);
    if (file === null) {
      problems.push(`${lineNumber}행: 자리 \`${place}\` 가 경로:줄 이나 경로:줄:칸 꼴이 아니다`);
      return;
    }
    const fix = unescapeCell(cells[4]);
    if (!fix) return;
    rows.push({ file, line, text: unescapeCell(cells[2]), findings: [], fix, column });
  });
  return { rows, problems };
}
