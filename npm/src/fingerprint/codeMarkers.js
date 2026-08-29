// @ts-check
/**
 * 코드 줄에서 파일의 공급과 수요를 읽는다. 어떤 줄이 파일을 만들고 (쓰기, 폴더 만들기) 어떤 줄이 파일을 읽는가.
 * 파이썬 fingerprint/codeMarkers.py 와 같다. 줄마다 대조하므로 여러 줄에 걸친 호출은 보지 않는다.
 */

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
/** open 의 모드에 이 글자가 있으면 쓰기다. 없으면 (기본 r) 읽기다. */
const WRITE_MODES = [..."wax"];

/** @param {string} path */
export function fileName(path) {
  const parts = path.replace(/\\/g, "/").replace(/\/+$/, "").split("/");
  return parts[parts.length - 1];
}

/** @param {string | undefined} mode */
function isWriteMode(mode) {
  return WRITE_MODES.some((flag) => (mode ?? "r").includes(flag));
}

/** @param {RegExp} pattern @param {string} text @param {number} group */
function all(pattern, text, group) {
  const found = [];
  for (const match of text.matchAll(pattern)) if (match[group] !== undefined) found.push(match[group]);
  return found;
}

/**
 * 코드 줄들이 만드는 [파일 이름, 폴더 이름]. 쓰기 함수, 셸 리다이렉션, 쓰기 모드의 open, mkdir 을 본다.
 * @param {string[]} lines
 * @returns {[Set<string>, Set<string>]}
 */
export function createdIn(lines) {
  /** @type {Set<string>} */
  const files = new Set();
  /** @type {Set<string>} */
  const dirs = new Set();
  for (const code of lines) {
    for (const path of all(WRITES, code, 1)) files.add(fileName(path));
    for (const path of all(SHELL_WRITES, code, 1)) files.add(fileName(path));
    for (const match of code.matchAll(OPENS)) if (isWriteMode(match[2])) files.add(fileName(match[1]));
    for (const match of code.matchAll(MAKES_DIR)) dirs.add((match[1] ?? match[2]).replace(/\\/g, "/").split("/")[0]);
  }
  return [files, dirs];
}

/** 한 줄이 읽는 경로. 읽기 함수, 읽기 모드의 open, SQL 의 FROM 차례다. @param {string} code */
export function readsIn(code) {
  const reads = all(READS, code, 1);
  for (const match of code.matchAll(OPENS)) if (!isWriteMode(match[2])) reads.push(match[1]);
  reads.push(...all(SQL_PATHS, code, 1));
  return reads;
}

/** 한 줄이 쓰기 함수로 쓰는 경로 그대로. 그 경로의 폴더가 있는지 볼 때 쓴다. @param {string} code */
export function writeTargets(code) {
  return all(WRITES, code, 1);
}
