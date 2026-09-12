// @ts-check
/** 같은 자료를 Node 파일 또는 브라우저 배포 묶음에서 읽는다. */
const isNode = typeof process === "object" && Boolean(process.versions?.node);
const fileSystem = isNode ? await import("node:fs") : null;
const files = isNode ? null : await fetch(new URL("../../data/siteData.json", import.meta.url)).then((response) => {
  if (!response.ok) throw new Error("검사 자료를 불러오지 못했습니다. 새로고침해 주세요.");
  return response.json();
});

/** @param {string} name @returns {string} */
export function readData(name) {
  if (fileSystem) return fileSystem.readFileSync(new URL(`../../data/${name}`, import.meta.url), "utf8");
  if (typeof files[name] !== "string") throw new Error(`검사 자료가 없습니다: ${name}`);
  return files[name];
}

/** @param {string} path @returns {string} */
export function readExternal(path) {
  if (!fileSystem) throw new Error("파일 경로 읽기는 Node에서 지원합니다. 브라우저에는 텍스트를 전달해 주세요.");
  return fileSystem.readFileSync(path, "utf8");
}
