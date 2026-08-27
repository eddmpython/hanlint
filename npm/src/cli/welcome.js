// @ts-check
/**
 * `hanlint` 를 인자 없이 쳤을 때의 첫 화면. 파이썬 cli/welcome.py 와 같은 글자다.
 * 같은 폴더에서 두 판을 돌리면 결과가 같다.
 */
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const MARKDOWN = [".md", ".markdown"];
/** 현재 폴더에서 예시로 보일 파일 수. 넷을 넘으면 목록이 안내를 밀어낸다. */
const SAMPLE_LIMIT = 3;

/** 현재 폴더 바로 아래의 마크다운. 이름 순이라 같은 폴더면 두 판이 같은 것을 고른다. @param {string} folder */
export function nearbyMarkdown(folder) {
  /** @type {string[]} */
  let names = [];
  try {
    names = readdirSync(folder);
  } catch {
    return [];
  }
  const found = names.filter((name) => {
    if (!MARKDOWN.some((suffix) => name.toLowerCase().endsWith(suffix))) return false;
    try {
      return statSync(join(folder, name)).isFile();
    } catch {
      return false;
    }
  });
  return found.sort().slice(0, SAMPLE_LIMIT);
}

/** @param {string} version @param {string} [folder] */
export function welcome(version, folder) {
  const where = folder ?? process.cwd();
  const nearby = nearbyMarkdown(where);
  const example = nearby.length ? nearby[0] : "글.md";
  const shown = [
    [`hanlint ${example}`, "검사한다. 자리와 이유와 고칠 말이 나온다"],
    [`hanlint fix ${example}`, "기계가 확실히 고칠 수 있는 자리를 원문에 적용한다"],
    [`hanlint audit ${example}`, "글의 모양을 지도와 분포로 본다"],
  ];
  const width = Math.max(...shown.map(([command]) => command.length));
  const lines = [
    `hanlint ${version}  한국어 글에서 세면 확정되는 결함을 집는다. 좋은 글인지는 판정하지 않는다`,
    "",
    ...shown.map(([command, why]) => `  ${command.padEnd(width)}  ${why}`),
  ];
  if (nearby.length) {
    lines.push("", `이 폴더의 마크다운: ${nearby.join(", ")}. 폴더를 통째로 줘도 된다 (hanlint .)`);
  } else {
    lines.push("", "이 폴더에는 마크다운이 없다. 파일 하나나 폴더 하나를 인자로 준다");
  }
  lines.push(
    "",
    "처음이면 hanlint init 으로 설정을 만든다. 글의 종류가 블로그가 아니면 --preset report 나 --preset docs",
    "규칙 목록은 hanlint rules, 규칙 하나가 왜 있는지는 hanlint explain <규칙>, 지금 상태는 hanlint doctor",
    "전체 사용법은 hanlint --help",
  );
  return lines.join("\n");
}
