// @ts-check
/** 개인 저장소의 한 파일만 읽고 쓴다. 토큰과 충돌 기준은 인스턴스 메모리에만 둔다. */
import { parseWorkspace, serializeWorkspace } from "./records.js";
const API = "https://api.github.com";
const FILE_PATH = "hanlint/workspace.json";
const API_VERSION = "2022-11-28";

export function encodeContent(text) {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

/** base64 본문을 글로. BOM 은 남겨 소스 파일을 되돌려 쓸 때 그대로다. */
export function decodeContent(content) {
  const binary = atob(content.replace(/\s/g, ""));
  return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(Uint8Array.from(binary, (char) => char.charCodeAt(0)));
}

export class GitHubStore {
  // 기본값이 `fetch` 그 자체가 아닌 이유: `this.request(...)` 로 부르면 브라우저가 Illegal invocation 을 던진다 (실측 2026-09-18).
  constructor(request = (url, options) => fetch(url, options)) { this.request = request; this.repository = ""; this.token = ""; this.sha = undefined; }

  connect(repository, token) {
    if (!/^[A-Za-z0-9][A-Za-z0-9-]*\/[A-Za-z0-9_.-]+$/.test(repository) || repository.split("/")[1] === "." || repository.split("/")[1] === "..") throw new Error("저장소를 계정/저장소 형식으로 입력해 주세요.");
    if (!token.trim() || /\s/.test(token.trim())) throw new Error("GitHub 토큰을 입력해 주세요.");
    if (this.repository !== repository || this.token !== token) this.sha = undefined;
    this.repository = repository;
    this.token = token;
  }

  disconnect() { this.repository = ""; this.token = ""; this.sha = undefined; }

  async call(path, options = {}) {
    if (!this.token) throw new Error("GitHub 저장소를 연결해 주세요.");
    const controller = new AbortController(), timer = setTimeout(() => controller.abort(), 20000);
    let response;
    try {
      response = await this.request(`${API}/repos/${this.repository}${path}`, { ...options, signal: controller.signal,
        headers: { Accept: "application/vnd.github+json", Authorization: `Bearer ${this.token}`,
          "X-GitHub-Api-Version": API_VERSION, ...(options.body ? { "Content-Type": "application/json" } : {}) } });
    } catch {
      throw new Error("GitHub에 연결하지 못했습니다. 원고는 그대로 있습니다. 네트워크를 확인하고 다시 시도해 주세요.");
    } finally { clearTimeout(timer); }
    if (response.status === 404) return null;
    if ([409, 422].includes(response.status)) throw new Error("GitHub 기록이 달라졌거나 현재 쓸 수 없는 상태입니다. 기록을 내보낸 뒤 GitHub에서 다시 가져와 확인해 주세요.");
    if (!response.ok) {
      if ([401, 403].includes(response.status)) throw new Error("토큰의 만료와 선택한 저장소의 Contents 읽기·쓰기 권한 또는 GitHub 요청 제한을 확인해 주세요.");
      throw new Error(`GitHub가 저장을 처리하지 못했습니다 (${response.status}). 잠시 뒤 다시 시도해 주세요.`);
    }
    return response.json();
  }

  async load() {
    const data = await this.call(`/contents/${FILE_PATH}`);
    if (!data) throw new Error("저장된 기록이 없거나 저장소 접근 권한이 없습니다. 저장소와 토큰을 확인해 주세요.");
    if (data.type !== "file" || data.encoding !== "base64") throw new Error("GitHub의 기록 파일 형식이나 크기를 확인해 주세요.");
    const workspace = parseWorkspace(decodeContent(data.content));
    return { workspace, sha: data.sha };
  }

  accept(sha) { this.sha = sha; }

  async save(workspace) {
    const content = encodeContent(serializeWorkspace(workspace));
    if (this.sha === undefined) {
      const repository = await this.call("");
      if (!repository) throw new Error("저장소를 찾을 수 없습니다. 먼저 개인 저장소를 만들고 토큰 접근을 허용해 주세요.");
      const existing = await this.call(`/contents/${FILE_PATH}`);
      if (existing) throw new Error("GitHub에 기존 기록이 있습니다. 먼저 가져오거나 로컬 기록을 내보내 보관해 주세요.");
      this.sha = null;
    }
    const result = await this.call(`/contents/${FILE_PATH}`, { method: "PUT", body: JSON.stringify({
      message: "글: 한린트 원고와 수정 이력 보관", content, ...(this.sha ? { sha: this.sha } : {}),
    }) });
    if (!result?.content?.sha) throw new Error("저장 완료를 확인하지 못했습니다. GitHub 기록을 확인해 주세요.");
    this.sha = result.content.sha;
    return result.content.html_url;
  }
}
