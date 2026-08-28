// @ts-check
/**
 * 폴더에서 검사할 마크다운을 찾는 규칙. 첫 화면과 검사가 **같은 함수**를 쓴다.
 * 무엇을 건너뛰고 왜 그러는지는 파이썬 `cli/commands/shared.py` 의 SKIPPED_FOLDERS 가 소유한다.
 */
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

/** 폴더를 주면 이 확장자만 찾는다. */
export const MARKDOWN = [".md", ".markdown"];
/** 폴더를 훑을 때 안 들어가는 이름. 점으로 시작하는 폴더도 함께 건너뛴다. */
export const SKIPPED_FOLDERS = ["node_modules"];

/** @param {string} name */
export function isSkipped(name) {
  return name.startsWith(".") || SKIPPED_FOLDERS.includes(name);
}

/** 폴더 아래 마크다운. 건너뛸 폴더에는 안 들어간다. 경로 문자열 순이라 두 판이 같은 차례를 낸다. @param {string} folder */
export function markdownUnder(folder) {
  /** @type {string[]} */
  const found = [];
  for (const name of [...readdirSync(folder)].sort()) {
    const path = join(folder, name);
    if (statSync(path).isDirectory()) {
      if (!isSkipped(name)) found.push(...markdownUnder(path));
    } else if (MARKDOWN.includes(name.slice(name.lastIndexOf(".")).toLowerCase())) found.push(path);
  }
  return found.sort();
}
