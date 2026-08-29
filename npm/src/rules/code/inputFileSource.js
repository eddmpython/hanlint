// @ts-check
import { createdIn, fileName, readsIn, writeTargets } from "../../fingerprint/codeMarkers.js";
import { DOCUMENT, NOTICE, finding } from "../finding.js";

export const name = "inputFileSource";
export const mechanism = "reader";

const EXTENSIONS = new Set(
  "csv xlsx xls parquet json jsonl txt png jpg jpeg svg gif db sqlite md py yaml yml toml html pdf zip ndjson".split(" "),
);
/** 별표, 서식 자리표시자, URL 이 든 경로는 파일 하나를 가리키지 않는다. */
const NOT_A_FILE = ["*", "{", "http", "://", "<", ">"];
/** 폴더를 볼 때는 물음표까지 뺀다. */
const NOT_A_PATH = [...NOT_A_FILE, "?"];

/** @param {string} path */
function isDataFile(path) {
  if (NOT_A_FILE.some((mark) => path.includes(mark))) return false;
  const name2 = fileName(path);
  return name2.includes(".") && EXTENSIONS.has(name2.split(".").pop()?.toLowerCase() ?? "");
}

/** @param {string} path */
function directoryOf(path) {
  const parts = path.replace(/\\/g, "/").split("/");
  return parts.length > 1 && !["", ".", ".."].includes(parts[0]) ? parts[0] : null;
}

/** @param {import("../../fingerprint/build.js").DocumentPrint} doc */
export function run(doc) {
  const findings = [];
  /** 이미 짚은 폴더. 같은 폴더를 두 번 짚지 않는다. @type {Set<string>} */
  const reported = new Set();
  for (const block of doc.codeBlocks) {
    const reader = doc.reader.beforeBlock[block.index];
    const [blockWrites, blockDirs] = createdIn(block.lines.map(([, line]) => line));
    // 이 블록이 만드는 폴더는 같은 블록의 읽기에도 미리 센다. 파일은 블록 안에서 쓴 것 (blockWrites) 만 따로 본다.
    const have = new Set([...reader.files, ...blockDirs, ...reported]);
    for (const [line, code] of block.lines) {
      const reads = readsIn(code);
      for (const path of reads) {
        if (!isDataFile(path)) continue;
        const name2 = fileName(path);
        if (have.has(name2) || blockWrites.has(name2) || doc.reader.mentionedBefore(block.index, name2)) continue;
        findings.push(finding(name, line, code.trim(), `\`${name2}\` 을 읽는데 글 어디에서도 만들지 않았다. 독자는 여기서 파일 없음 오류로 멈춘다`, null, "error", DOCUMENT, block.index));
      }
      for (const path of [...writeTargets(code), ...reads]) {
        if (NOT_A_PATH.some((mark) => path.includes(mark))) continue;
        const directory = directoryOf(path);
        if (!directory || have.has(directory) || doc.reader.mentionedBefore(block.index, directory)) continue;
        have.add(directory);
        reported.add(directory);
        findings.push(finding(name, line, code.trim(), `\`${directory}\` 폴더를 쓰는데 글 어디에서도 만들지 않았다. 없으면 파일을 쓰다 멈춘다`, null, NOTICE, DOCUMENT, block.index));
      }
    }
  }
  return findings;
}
