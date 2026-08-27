// @ts-check
import { TABLE } from "../../document/model.js";
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "tableOddCell";
const SEPARATOR = /^:?-{2,}:?$/;
const MEASURE = /^([+-]?\d[\d,]*(?:\.\d+)?)\s*([^\s\d]{0,6})$/;
const EMPTY = ["", "-", "--"];

/** (블록 안 줄 오프셋, 칸 목록). 구분 줄은 뺀다. @param {string} text @returns {[number, string[]][]} */
function cellsOf(text) {
  /** @type {[number, string[]][]} */
  const rows = [];
  text.split("\n").forEach((line, offset) => {
    const stripped = line.trim();
    if (!stripped.startsWith("|")) return;
    const cells = stripped.replace(/^\|+/, "").replace(/\|+$/, "").split("|").map((cell) => cell.trim());
    if (cells.length && cells.filter((cell) => cell).every((cell) => SEPARATOR.test(cell))) return;
    rows.push([offset, cells]);
  });
  return rows;
}

/** `3.72초` 는 초, `533MB` 는 MB, `직접 부르지 않음` 은 null. @param {string} cell */
function unitOf(cell) {
  const match = MEASURE.exec(cell);
  return match ? match[2] : null;
}

/**
 * @param {import("../../fingerprint/build.js").DocumentPrint} doc
 * @param {import("../../config/settings.js").Config} config
 */
export function run(doc, config) {
  const findings = [];
  for (const block of doc.blocks) {
    if (block.kind !== TABLE) continue;
    const rows = cellsOf(block.text);
    if (rows.length < 2) continue;
    const body = rows.slice(1);
    const width = Math.min(...body.map(([, cells]) => cells.length));
    for (let column = 1; column < width; column += 1) {
      /** @type {[number, string][]} */
      const values = [];
      for (const [offset, cells] of body) if (!EMPTY.includes(cells[column])) values.push([offset, cells[column]]);
      if (values.length < config.tableOddCellMinRows) continue;
      const units = values.map(([offset, cell]) => /** @type {[number, string, string | null]} */ ([offset, cell, unitOf(cell)]));
      const odd = units.filter(([, , unit]) => unit === null);
      const kinds = new Set(units.filter(([, , unit]) => unit !== null).map(([, , unit]) => unit));
      if (odd.length !== 1 || kinds.size !== 1) continue;
      const unit = [...kinds][0];
      const [offset, cell] = odd[0];
      findings.push(
        finding(name, block.startLine + offset, cell, `이 열의 나머지 ${values.length - 1}칸은 \`${unit}\` 으로 잰 값 하나인데 이 칸만 다르다. 같은 잣대로 다시 재거나 그 줄을 본문 문장으로 옮긴다`, null, NOTICE, DOCUMENT, block.index),
      );
    }
  }
  return findings;
}
