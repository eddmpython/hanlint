// @ts-check
/** 브라우저의 저장소 읽기. 주소 해석, 파일 고르기와 예산, raw 받기의 동시성과 오류를 가짜 fetch 로 본다. 네트워크는 없다. */
import assert from "node:assert/strict";
import test from "node:test";

import { GitHubStore } from "../../web/github.js";
import { CONCURRENCY, MAX_BYTES, MAX_FILES, MAX_FILE_BYTES, REF_RETRIES, RepoSource, blobUrl, checkBudget, isRepoUrl, parseRepoUrl, selectFiles } from "../../web/repoSource.js";

const SUFFIXES = [".js", ".jsx", ".ts", ".py"];

test("parseRepoUrl reads the address forms people paste", () => {
  assert.deepEqual(parseRepoUrl("https://github.com/eddmpython/hanlint"), { owner: "eddmpython", repo: "hanlint", ref: null, path: "" });
  assert.deepEqual(parseRepoUrl("  github.com/eddmpython/hanlint.git/ "), { owner: "eddmpython", repo: "hanlint", ref: null, path: "" });
  assert.deepEqual(parseRepoUrl("https://www.github.com/eddmpython/hanlint/tree/main/web?tab=x#top"), { owner: "eddmpython", repo: "hanlint", ref: "main", path: "web" });
  assert.deepEqual(parseRepoUrl("https://github.com/o/r/blob/v1.2/src/app.js"), { owner: "o", repo: "r", ref: "v1.2", path: "src/app.js" });
  assert.deepEqual(parseRepoUrl("o/r"), { owner: "o", repo: "r", ref: null, path: "" });
  assert.deepEqual(parseRepoUrl("https://github.com/o/r/tree/feature/x/src"), { owner: "o", repo: "r", ref: "feature", path: "x/src" });
  assert.deepEqual(parseRepoUrl("https://github.com/o/r/tree/main/%ED%95%9C%EA%B8%80%20%ED%8F%B4%EB%8D%94/src"), { owner: "o", repo: "r", ref: "main", path: "한글 폴더/src" });
  for (const bad of ["", "https://github.com/o", "https://github.com/o/r/pull/3", "https://gitlab.com/o/r", "o/..", "-o/r", "글 한 줄"]) {
    assert.equal(parseRepoUrl(bad), null, bad);
  }
});

test("isRepoUrl needs the github.com host so pasted prose never switches mode", () => {
  assert.equal(isRepoUrl("https://github.com/o/r\n"), true);
  assert.equal(isRepoUrl("github.com/o/r/tree/main/src"), true);
  assert.equal(isRepoUrl("o/r"), false);
  assert.equal(isRepoUrl("https://github.com/o/r 를 봐 주세요"), false);
});

test("selectFiles follows the CLI walk: suffix, dot folders, node_modules, and the chosen path", () => {
  const entries = [
    { path: "src/app.js", type: "blob", size: 10, sha: "aa" },
    { path: "src/view.tsx", type: "blob", size: 5 },
    { path: "src/readme.md", type: "blob", size: 5 },
    { path: "node_modules/x/index.js", type: "blob", size: 99 },
    { path: ".github/scripts/a.js", type: "blob", size: 7, sha: "gh" },
    { path: "src/.hidden/b.js", type: "blob", size: 7 },
    { path: "docs/App.PY", type: "blob", size: 3, sha: "py" },
    { path: "src/link.js", type: "blob", mode: "120000", size: 20 },
    { path: "dist/bundle.js", type: "blob", size: MAX_FILE_BYTES + 1 },
    { path: "src", type: "tree" },
  ];
  assert.deepEqual(selectFiles(entries, { suffixes: SUFFIXES }), { files: [{ path: "docs/App.PY", size: 3, sha: "py" }, { path: "src/app.js", size: 10, sha: "aa" }], bytes: 13, oversized: 1 });
  assert.deepEqual(selectFiles(entries, { suffixes: SUFFIXES, path: ".github" }).files, [{ path: ".github/scripts/a.js", size: 7, sha: "gh" }]);
  assert.deepEqual(selectFiles(entries, { suffixes: SUFFIXES, path: ".github/scripts/a.js" }).files, [{ path: ".github/scripts/a.js", size: 7, sha: "gh" }]);
  assert.deepEqual(selectFiles(entries, { suffixes: SUFFIXES, path: "src" }).files, [{ path: "src/app.js", size: 10, sha: "aa" }]);
  assert.deepEqual(selectFiles(entries, { suffixes: SUFFIXES, path: "src/app.js" }).files, [{ path: "src/app.js", size: 10, sha: "aa" }]);
  assert.deepEqual(selectFiles(entries, { suffixes: SUFFIXES, path: "sr" }).files, []);
});

test("checkBudget names the limit and the way out", () => {
  checkBudget(Array.from({ length: MAX_FILES }, (_, i) => ({ path: `${i}.js` })), MAX_BYTES);
  assert.throws(() => checkBudget(Array.from({ length: MAX_FILES + 1 }, (_, i) => ({ path: `${i}.js` })), 1), /경로를 좁혀 주세요/);
  assert.throws(() => checkBudget([{ path: "a.js" }], MAX_BYTES + 1), /MB/);
});

test("blobUrl points at the line on GitHub", () => {
  assert.equal(blobUrl({ owner: "o", repo: "r", ref: "main", path: "" }, "src/한글 폴더/a.js", 12), "https://github.com/o/r/blob/main/src/%ED%95%9C%EA%B8%80%20%ED%8F%B4%EB%8D%94/a.js#L12");
});

function reply(status, body) {
  const bytes = () => new TextEncoder().encode(typeof body === "string" ? body : "").buffer;
  return { status, ok: status >= 200 && status < 300, json: async () => body, text: async () => body, arrayBuffer: async () => bytes() };
}

test("tree and defaultBranch use the API once each and map failures to plain words", async () => {
  const calls = [];
  const source = new RepoSource(async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith("/repos/o/r")) return reply(200, { default_branch: "main" });
    if (url.includes("/git/trees/main?recursive=1")) return reply(200, { tree: [{ path: "a.js", type: "blob", size: 1 }], truncated: false });
    if (url.includes("/git/trees/huge")) return reply(200, { tree: [], truncated: true });
    if (url.includes("/git/trees/gone")) return reply(404, {});
    return reply(403, {});
  });
  assert.equal(await source.defaultBranch("o", "r"), "main");
  assert.deepEqual(await source.tree("o", "r", "main"), [{ path: "a.js", type: "blob", size: 1 }]);
  assert.equal(calls[0].options.headers["X-GitHub-Api-Version"], "2022-11-28");
  await assert.rejects(source.tree("o", "r", "huge"), /잘렸습니다/);
  await assert.rejects(source.tree("o", "r", "gone"), /찾지 못했습니다/);
  await assert.rejects(source.tree("o", "r", "limited"), /요청 한도/);
  await assert.rejects(new RepoSource(async () => { throw new Error("offline"); }).tree("o", "r", "main"), /연결하지 못했습니다/);
});

test("fetchSources keeps file order, caps concurrency, reports progress and stops on the first failure", async () => {
  let open = 0;
  let peak = 0;
  const source = new RepoSource(async (url) => {
    open += 1;
    peak = Math.max(peak, open);
    await new Promise((resolve) => setTimeout(resolve, 5));
    open -= 1;
    const name = decodeURIComponent(url.split("/").pop());
    return url.includes("/o/r/main/") ? reply(200, `내용 ${name}`) : reply(500, "");
  });
  const files = Array.from({ length: 20 }, (_, i) => ({ path: `src/f${String(i).padStart(2, "0")}.js` }));
  const progress = [];
  const got = await source.fetchSources({ owner: "o", repo: "r", ref: "main", path: "" }, files, (done, total) => progress.push([done, total]));
  assert.deepEqual(got.map((item) => item.label), files.map((file) => file.path));
  assert.equal(got[3].source, "내용 f03.js");
  assert.ok(peak <= CONCURRENCY && peak > 1, String(peak));
  assert.deepEqual(progress[progress.length - 1], [20, 20]);
  await assert.rejects(source.fetchSources({ owner: "o", repo: "r", ref: "dev", path: "" }, files.slice(0, 3)), /응답하지 않았습니다 \(500\)/);
});

test("the default request never calls fetch with a foreign this (browsers throw Illegal invocation)", async () => {
  const native = globalThis.fetch;
  const seen = [];
  globalThis.fetch = function (url) {
    if (this !== undefined && this !== globalThis) throw new TypeError("Failed to execute 'fetch' on 'Window': Illegal invocation");
    seen.push(url);
    return Promise.resolve(reply(200, { default_branch: "main", type: "file", encoding: "base64", content: "", sha: "s" }));
  };
  try {
    assert.equal(await new RepoSource().defaultBranch("o", "r"), "main");
    const store = new GitHubStore();
    store.connect("o/r", "token");
    assert.equal((await store.call("")).default_branch, "main");
    assert.equal(seen.length, 2);
  } finally {
    globalThis.fetch = native;
  }
});

test("resolveTree moves path segments into a slashed branch name after a 404, bounded by REF_RETRIES", async () => {
  const asked = [];
  const source = new RepoSource(async (url) => {
    asked.push(decodeURIComponent(url.split("/git/trees/")[1]?.split("?")[0] ?? url));
    return url.includes("/git/trees/release/8.0?") ? reply(200, { tree: [{ path: "src/a.js", type: "blob", size: 1 }] }) : reply(404, {});
  });
  const { target, tree } = await source.resolveTree({ owner: "o", repo: "r", ref: "release", path: "8.0/src" });
  assert.deepEqual(asked, ["release", "release/8.0"]);
  assert.deepEqual(target, { owner: "o", repo: "r", ref: "release/8.0", path: "src" });
  assert.equal(tree.length, 1);
  const never = new RepoSource(async () => reply(404, {}));
  await assert.rejects(never.resolveTree({ owner: "o", repo: "r", ref: "a", path: "b/c/d/e" }), /찾지 못했습니다/);
  assert.ok(REF_RETRIES >= 1);
});

test("an aborted signal stops the lanes and the call reports the stop, not a network failure", async () => {
  const controller = new AbortController();
  let calls = 0;
  const source = new RepoSource(async (url, options) => {
    calls += 1;
    if (calls === 2) controller.abort();
    if (options.signal.aborted) throw new DOMException("aborted", "AbortError");
    await new Promise((resolve) => setTimeout(resolve, 2));
    return reply(200, "글");
  });
  const files = Array.from({ length: 12 }, (_, i) => ({ path: `f${i}.js` }));
  await assert.rejects(source.fetchSources({ owner: "o", repo: "r", ref: "main", path: "" }, files, undefined, controller.signal), /멈췄습니다/);
  assert.ok(calls < files.length, String(calls));
});

test("raw text keeps a leading BOM like the CLI's readFileSync, so line-1 columns agree", async () => {
  const source = new RepoSource(async () => ({ status: 200, ok: true, arrayBuffer: async () => new Uint8Array([0xef, 0xbb, 0xbf, 0x61]).buffer }));
  const [{ source: text }] = await source.fetchSources({ owner: "o", repo: "r", ref: "main", path: "" }, [{ path: "a.js" }]);
  assert.equal(text, "﻿a");
});

test("unchanged blobs and the default branch are not fetched twice while the page lives", async () => {
  let calls = 0;
  const source = new RepoSource(async (url) => {
    calls += 1;
    if (url.endsWith("/repos/o/r")) return reply(200, { default_branch: "main" });
    return reply(200, `내용 ${decodeURIComponent(url.split("/").pop())}`);
  });
  const target = { owner: "o", repo: "r", ref: "main", path: "" };
  const first = await source.fetchSources(target, [{ path: "a.js", sha: "1" }, { path: "b.js", sha: "2" }]);
  assert.deepEqual(first.map((item) => item.source), ["내용 a.js", "내용 b.js"]);
  assert.equal(calls, 2);
  const second = await source.fetchSources(target, [{ path: "a.js", sha: "1" }, { path: "b.js", sha: "3" }, { path: "c.js" }]);
  assert.deepEqual(second.map((item) => item.source), ["내용 a.js", "내용 b.js", "내용 c.js"]);
  assert.equal(calls, 4, "sha 가 바뀐 b 와 sha 없는 c 만 다시 받는다");
  assert.equal(await source.defaultBranch("o", "r"), "main");
  assert.equal(await source.defaultBranch("o", "r"), "main");
  assert.equal(calls, 5);
});
