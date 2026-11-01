// @ts-check
/**
 * 쓰기 전에 읽는 글쓰기 지침. 파이썬 data/prose.py를 옮긴 것이고 내용은 koreanProse.txt 하나에 있다.
 * primer는 절마다 한 줄로 펴서 첫머리에 싣고, hook --prime은 본문을 그대로 에이전트 문맥에 넣는다.
 */
import { readText } from "./load.js";

export const PROSE = "koreanProse.txt";

/** 글쓰기 지침 본문. 끝의 줄바꿈 하나까지 파일 그대로다. @returns {string} */
export function proseGuide() {
  return readText(PROSE);
}

/**
 * (제목, 본문) 짝. 첫 짝은 문서 제목과 첫머리이고 나머지는 일곱 줄이다. 제목의 `#`은 뗀다.
 * 파이썬 proseSections와 같다. @returns {[string, string][]}
 */
export function proseSections() {
  /** @type {[string, string[]][]} */
  const sections = [];
  for (const line of proseGuide().split(/\r?\n/)) {
    if (line.startsWith("#")) sections.push([line.replace(/^#+/, "").trim(), []]);
    else if (sections.length) sections[sections.length - 1][1].push(line);
  }
  return sections.map(([title, body]) => [title, body.join("\n").trim()]);
}
