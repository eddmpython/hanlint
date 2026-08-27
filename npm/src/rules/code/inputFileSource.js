// @ts-check
import { DOCUMENT, NOTICE, finding } from "../finding.js";
import { codeBlocksOf } from "../shared/codeBlocks.js";

export const name = "inputFileSource";

const QUOTED = "\\(\\s*[\"']([^\"'\\n]+)[\"']";
const READS = new RegExp(
  "\\b(?:read_csv|read_excel|read_parquet|read_json|read_sql|read_table|read_ndjson|scan_csv|scan_parquet|scan_ndjson|" +
    "read_text|read_bytes|loadtxt|imread|load_workbook)" + QUOTED,
  "g",
);
const OPENS = new RegExp("\\bopen" + QUOTED + "\\s*(?:,\\s*(?:mode\\s*=\\s*)?[\"']([^\"']*)[\"'])?", "g");
const WRITES = new RegExp(
  "\\b(?:to_csv|to_excel|to_parquet|to_json|to_sql|write_csv|write_parquet|write_json|write_ndjson|sink_parquet|sink_csv|" +
    "write_text|write_bytes|savefig|save|imwrite|savetxt|dump)" + QUOTED,
  "g",
);
const SHELL_WRITES = /(?:>>?|-o|-O|--output|Out-File)\s*["']?([\w./\\-]+\.[A-Za-z0-9]+)/g;
const SQL_PATHS = /FROM\s+'([^']+\.(?:csv|parquet|json|xlsx))'/gi;
const MAKES_DIR = /(?:mkdir(?:\s+-p)?|makedirs|md)\s*\(?\s*["']?([\w./\\-]+)|Path\(\s*["']([^"']+)["']\s*\)\.mkdir/g;
const EXTENSIONS = new Set(
  "csv xlsx xls parquet json jsonl txt png jpg jpeg svg gif db sqlite md py yaml yml toml html pdf zip ndjson".split(" "),
);

/** @param {string} path */
function fileName(path) {
  const parts = path.replace(/\\/g, "/").replace(/\/+$/, "").split("/");
  return parts[parts.length - 1];
}

/** @param {string} path */
function isDataFile(path) {
  if (["*", "{", "http", "://", "<", ">"].some((mark) => path.includes(mark))) return false;
  const name = fileName(path);
  return name.includes(".") && EXTENSIONS.has(name.split(".").pop()?.toLowerCase() ?? "");
}

/** @param {string} path */
function directoryOf(path) {
  const parts = path.replace(/\\/g, "/").split("/");
  return parts.length > 1 && !["", ".", ".."].includes(parts[0]) ? parts[0] : null;
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc @param {string} needle @param {number} line */
function mentionedBefore(doc, needle, line) {
  return doc.sentences.some((s) => s.line < line && s.text.includes(needle));
}

/** @param {RegExp} pattern @param {string} text @param {number} group */
function all(pattern, text, group) {
  pattern.lastIndex = 0;
  const found = [];
  for (const match of text.matchAll(pattern)) if (match[group] !== undefined) found.push(match[group]);
  return found;
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  /** @type {Set<string>} */
  const created = new Set();
  for (const block of codeBlocksOf(doc)) {
    /** @type {Set<string>} */
    const blockWrites = new Set();
    /** @type {Set<string>} */
    const blockDirs = new Set();
    for (const [, code] of block.lines) {
      for (const name2 of all(WRITES, code, 1)) blockWrites.add(fileName(name2));
      for (const name2 of all(SHELL_WRITES, code, 1)) blockWrites.add(fileName(name2));
      OPENS.lastIndex = 0;
      for (const match of code.matchAll(OPENS)) {
        const mode = match[2] ?? "r";
        if ([..."wax"].some((flag) => mode.includes(flag))) blockWrites.add(fileName(match[1]));
      }
      MAKES_DIR.lastIndex = 0;
      for (const match of code.matchAll(MAKES_DIR)) blockDirs.add((match[1] ?? match[2]).replace(/\\/g, "/").split("/")[0]);
    }
    for (const dir of blockDirs) created.add(dir);
    for (const [line, code] of block.lines) {
      OPENS.lastIndex = 0;
      const reads = [...all(READS, code, 1), ...all(SQL_PATHS, code, 1)];
      for (const match of code.matchAll(OPENS)) {
        if (![..."wax"].some((flag) => (match[2] ?? "r").includes(flag))) reads.push(match[1]);
      }
      for (const path of reads) {
        if (!isDataFile(path)) continue;
        const name2 = fileName(path);
        if (created.has(name2) || blockWrites.has(name2) || mentionedBefore(doc, name2, block.startLine)) continue;
        findings.push(finding(name, line, code.trim(), `\`${name2}\` 을 읽는데 글 어디에서도 만들지 않았다. 독자는 여기서 파일 없음 오류로 멈춘다`, null, "error", DOCUMENT, block.index));
      }
      for (const path of [...all(WRITES, code, 1), ...reads]) {
        if (["http", "://", "{", "<", ">", "*", "?"].some((mark) => path.includes(mark))) continue;
        const directory = directoryOf(path);
        if (!directory || created.has(directory) || mentionedBefore(doc, directory, block.startLine)) continue;
        created.add(directory);
        findings.push(finding(name, line, code.trim(), `\`${directory}\` 폴더를 쓰는데 글 어디에서도 만들지 않았다. 없으면 파일을 쓰다 멈춘다`, null, NOTICE, DOCUMENT, block.index));
      }
    }
    for (const write of blockWrites) created.add(write);
  }
  return findings;
}
