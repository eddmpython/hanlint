// @ts-check
/**
 * GitHub 저장소의 소스를 브라우저로 가져온다. 트리는 api.github.com 한 번, 내용은 raw.githubusercontent.com 에서 파일마다.
 * 실측 (2026-09-18): tarball 은 CORS 가 render.githubusercontent.com 전용이라 브라우저가 못 받고, raw 는 `*` 이며
 * API 한도 (비인증 60회/시간) 밖이다. 제3자 CDN 은 끼우지 않는다. 글은 이 브라우저 안에서 검사한다.
 * 파일 고르기는 CLI 의 npm/src/cli/walk.js 와 같다 (`.` 접두 폴더와 node_modules 만 건너뛴다). 같은 파일이면
 * 같은 표가 나와야 하기 때문이다. 비공개 저장소와 되돌려 쓰기는 다루지 않는다.
 */

/** 한 번에 받는 파일 수. 넘으면 경로를 좁히라고 한다. 비인증 API 한도와 무관하게 raw 요청 수를 묶는 값이다. */
export const MAX_FILES = 300;
/** 한 번에 받는 소스 합계 바이트. 표 하나로 읽을 수 있는 크기의 상한이다. */
export const MAX_BYTES = 8_000_000;
/** 파일 하나의 상한 바이트. 이보다 큰 소스는 번들이나 생성물이라 표에서 빼고, 워커 요청 하나가 30초 안에 끝나게 한다. */
export const MAX_FILE_BYTES = 1_000_000;
/** 동시에 여는 raw 요청 수. 브라우저가 호스트 하나에 여는 연결 수와 같다. */
export const CONCURRENCY = 6;
/** 브랜치 이름에 `/` 가 있을 때 (release/8.0) 경로 조각을 브랜치로 옮겨 다시 묻는 최대 횟수. API 요청이 그만큼 는다. */
export const REF_RETRIES = 2;
const API = "https://api.github.com";
const RAW = "https://raw.githubusercontent.com";
const API_VERSION = "2022-11-28";
const SKIPPED_FOLDERS = ["node_modules"];
const TIMEOUT_MS = 20000;
const HOST = /^(?:https?:\/\/)?(?:www\.)?github\.com\//i;
const NAME = /^[A-Za-z0-9][A-Za-z0-9-]*$/;
const REPO = /^[A-Za-z0-9_.-]+$/;
const NOT_FOUND = "저장소나 브랜치를 찾지 못했습니다. 공개 저장소의 주소인지 확인해 주세요.";

/**
 * @typedef {object} RepoRef
 * @property {string} owner
 * @property {string} repo
 * @property {string | null} ref 브랜치나 태그. 없으면 기본 브랜치를 API 로 묻는다
 * @property {string} path 저장소 안의 폴더나 파일. 비면 전체
 */

function decoded(segment) {
  try { return decodeURIComponent(segment); } catch { return segment; }
}

/** 붙여 넣은 글이 GitHub 주소인가. 원문 칸에 주소만 붙여 넣으면 저장소 모드로 들어가는 판단에 쓴다. */
export function isRepoUrl(text) {
  return HOST.test(text.trim()) && parseRepoUrl(text) !== null;
}

/**
 * `github.com/계정/저장소`, `.../tree/브랜치/경로`, `.../blob/브랜치/파일`, `계정/저장소` 를 읽는다.
 * 주소창의 퍼센트 인코딩 (한글, 공백) 은 푼다. 브랜치 이름에 `/` 가 있으면 첫 조각만 브랜치로 보고,
 * 그 브랜치가 없을 때 RepoSource.resolveTree 가 경로 조각을 브랜치로 옮겨 다시 묻는다.
 * @returns {RepoRef | null}
 */
export function parseRepoUrl(text) {
  let rest = text.trim().replace(HOST, "");
  rest = rest.split(/[?#]/)[0].replace(/\/+$/, "");
  const parts = rest.split("/").filter(Boolean).map(decoded);
  if (parts.length < 2) return null;
  const owner = parts[0];
  const repo = parts[1].replace(/\.git$/, "");
  if (!NAME.test(owner) || !REPO.test(repo) || repo === "." || repo === "..") return null;
  if (parts.length === 2) return { owner, repo, ref: null, path: "" };
  if (parts.length >= 4 && (parts[2] === "tree" || parts[2] === "blob")) {
    return { owner, repo, ref: parts[3], path: parts.slice(4).join("/") };
  }
  return null;
}

function isSkipped(name) {
  return name.startsWith(".") || SKIPPED_FOLDERS.includes(name);
}

/**
 * 트리 항목 가운데 검사할 소스 파일만 고른다. 경로가 파일이면 그 하나, 폴더면 그 아래 전부.
 * 건너뛰기 (`.` 접두 폴더, node_modules) 는 CLI 처럼 고른 경로 아래에서만 본다. 고른 경로가 `.github` 여도 그 안은 읽는다.
 * 심볼릭 링크 (mode 120000) 는 raw 가 링크 대상 경로를 주므로 뺀다. MAX_FILE_BYTES 를 넘는 파일은 세어서 뺀다.
 * @param {{ path: string, type: string, mode?: string, size?: number }[]} entries
 * @param {{ suffixes: string[], path?: string }} options
 * @returns {{ files: { path: string, size: number }[], bytes: number, oversized: number }}
 */
export function selectFiles(entries, { suffixes, path = "" }) {
  const lowered = suffixes.map((suffix) => suffix.toLowerCase());
  const depth = path ? path.split("/").length : 0;
  const files = [];
  let bytes = 0;
  let oversized = 0;
  for (const entry of entries) {
    if (entry.type !== "blob" || entry.mode === "120000") continue;
    if (path && entry.path !== path && !entry.path.startsWith(`${path}/`)) continue;
    const segments = entry.path.split("/");
    if (segments.slice(depth, -1).some(isSkipped)) continue;
    const name = segments[segments.length - 1];
    const dot = name.lastIndexOf(".");
    if (dot < 0 || !lowered.includes(name.slice(dot).toLowerCase())) continue;
    if ((entry.size ?? 0) > MAX_FILE_BYTES) { oversized += 1; continue; }
    files.push({ path: entry.path, size: entry.size ?? 0 });
    bytes += entry.size ?? 0;
  }
  files.sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
  return { files, bytes, oversized };
}

/** 예산을 넘으면 사람이 할 수 있는 일 (경로 좁히기) 을 말하는 오류를 던진다. */
export function checkBudget(files, bytes) {
  if (files.length > MAX_FILES) {
    throw new Error(`소스 파일이 ${files.length}개라 한 번에 받기엔 많습니다. /tree/main/src 처럼 경로를 좁혀 주세요 (한 번에 ${MAX_FILES}개까지).`);
  }
  if (bytes > MAX_BYTES) {
    throw new Error(`소스가 ${(bytes / 1_000_000).toFixed(1)}MB 라 한 번에 받기엔 큽니다. 경로를 좁혀 주세요 (한 번에 ${MAX_BYTES / 1_000_000}MB 까지).`);
  }
}

function encodedPath(path) {
  return path.split("/").map(encodeURIComponent).join("/");
}

/** 표의 자리에서 GitHub 의 그 줄로 가는 주소. */
export function blobUrl({ owner, repo, ref }, path, line) {
  return `https://github.com/${owner}/${repo}/blob/${encodedPath(ref)}/${encodedPath(path)}#L${line}`;
}

export class RepoSource {
  /**
   * @param {(url: string, options: RequestInit) => Promise<Response>} request 테스트가 가짜 fetch 를 넣는다.
   * 기본값이 `fetch` 그 자체가 아닌 이유: `this.request(...)` 로 부르면 브라우저가 Illegal invocation 을 던진다 (실측 2026-09-18).
   */
  constructor(request = (url, options) => fetch(url, options)) {
    this.request = request;
  }

  /**
   * 요청 하나. 머리와 본문 읽기를 합쳐 TIMEOUT_MS 안에 끝낸다. 바깥 signal 이 끊기면 (새 요청이나 모드 나가기) 함께 끊는다.
   * @param {string} url @param {"json" | "text"} kind @param {AbortSignal} [signal]
   */
  async call(url, kind, signal) {
    const controller = new AbortController();
    const abort = () => controller.abort();
    signal?.addEventListener("abort", abort, { once: true });
    const timer = setTimeout(abort, TIMEOUT_MS);
    try {
      let response;
      try {
        const headers = kind === "json" ? { Accept: "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION } : {};
        response = await this.request(url, { headers, signal: controller.signal });
      } catch {
        if (signal?.aborted) throw new Error("불러오기를 멈췄습니다.");
        throw new Error("GitHub 에 연결하지 못했습니다. 네트워크를 확인하고 다시 시도해 주세요.");
      }
      if (response.status === 404) throw new Error(NOT_FOUND);
      if (response.status === 403 || response.status === 429) {
        throw new Error("GitHub 요청 한도에 닿았습니다. 한 시간쯤 뒤에 다시 시도해 주세요.");
      }
      if (!response.ok) throw new Error(`GitHub 가 응답하지 않았습니다 (${response.status}). 잠시 뒤 다시 시도해 주세요.`);
      try {
        if (kind === "json") return await response.json();
        // text() 는 앞의 BOM 을 지우지만 CLI 의 readFileSync 는 남긴다. 첫 줄의 칸이 같아야 apply 가 맞으므로 BOM 을 그대로 둔다.
        return new TextDecoder("utf-8", { ignoreBOM: true }).decode(await response.arrayBuffer());
      } catch {
        throw new Error("GitHub 의 응답을 끝까지 읽지 못했습니다. 다시 시도해 주세요.");
      }
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort);
    }
  }

  /** 기본 브랜치 이름. API 1회. */
  async defaultBranch(owner, repo, signal) {
    const data = await this.call(`${API}/repos/${owner}/${repo}`, "json", signal);
    if (typeof data.default_branch !== "string" || !data.default_branch) throw new Error("저장소의 기본 브랜치를 읽지 못했습니다.");
    return data.default_branch;
  }

  /**
   * 브랜치의 전체 트리. API 1회. 잘린 트리는 파일이 빠진 표를 만들므로 받지 않는다.
   * @returns {Promise<{ path: string, type: string, size?: number }[]>}
   */
  async tree(owner, repo, ref, signal) {
    const data = await this.call(`${API}/repos/${owner}/${repo}/git/trees/${encodedPath(ref)}?recursive=1`, "json", signal);
    if (!Array.isArray(data.tree)) throw new Error("저장소의 파일 목록을 읽지 못했습니다.");
    if (data.truncated) throw new Error("저장소가 커서 파일 목록이 잘렸습니다. /tree/main/src 처럼 경로를 좁혀 주세요.");
    return data.tree;
  }

  /**
   * 주소의 브랜치와 경로를 확정하며 트리를 받는다. `release/8.0` 처럼 브랜치에 `/` 가 있으면 첫 조각이 브랜치로 잡혀
   * 404 가 나므로, 경로 조각을 하나씩 브랜치로 옮겨 REF_RETRIES 번까지 다시 묻는다.
   * @param {RepoRef & { ref: string }} target
   * @returns {Promise<{ target: RepoRef & { ref: string }, tree: { path: string, type: string, size?: number }[] }>}
   */
  async resolveTree(target, signal) {
    let { ref, path } = target;
    for (let attempt = 0; ; attempt++) {
      try {
        return { target: { ...target, ref, path }, tree: await this.tree(target.owner, target.repo, ref, signal) };
      } catch (error) {
        const segments = path.split("/").filter(Boolean);
        if (error.message !== NOT_FOUND || attempt >= REF_RETRIES || !segments.length) throw error;
        ref = `${ref}/${segments[0]}`;
        path = segments.slice(1).join("/");
      }
    }
  }

  /**
   * raw 에서 파일 내용을 받는다. 동시에 CONCURRENCY 개, 결과는 files 순서 그대로. 하나가 실패하면 나머지를 멈춘다.
   * @param {RepoRef & { ref: string }} target
   * @param {{ path: string }[]} files
   * @param {(done: number, total: number) => void} [onProgress]
   * @param {AbortSignal} [signal]
   * @returns {Promise<{ label: string, source: string }[]>}
   */
  async fetchSources(target, files, onProgress, signal) {
    const results = new Array(files.length);
    let next = 0;
    let done = 0;
    let failure = null;
    const lane = async () => {
      while (next < files.length && failure === null && !signal?.aborted) {
        const index = next++;
        const path = files[index].path;
        try {
          const url = `${RAW}/${target.owner}/${target.repo}/${encodedPath(target.ref)}/${encodedPath(path)}`;
          results[index] = { label: path, source: await this.call(url, "text", signal) };
        } catch (error) {
          failure = failure ?? error;
          return;
        }
        done += 1;
        onProgress?.(done, files.length);
      }
    };
    await Promise.all(Array.from({ length: Math.min(CONCURRENCY, files.length) }, lane));
    if (failure) throw failure;
    if (signal?.aborted) throw new Error("불러오기를 멈췄습니다.");
    return results;
  }
}
