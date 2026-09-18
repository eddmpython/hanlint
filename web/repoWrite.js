// @ts-check
/**
 * 표의 고침을 GitHub 저장소에 바로 되돌려 쓴다 (저장소 모드 2단계). 파일마다 Contents API 로 읽고, 워커의 `sheetApply`
 * (CLI `sheet apply` 와 같은 applyRows) 로 바꾼 뒤, 같은 브랜치에 파일마다 commit 하나로 쓴다. 토큰은 메모리에만 둔다.
 * 실측: 시트를 내려받고 터미널에서 apply 하는 두 단계가 비개발자에게는 벽이었다 (2026-09-18).
 */
import { GitHubStore, decodeContent, encodeContent } from "./github.js";

function encodedPath(path) {
  return path.split("/").map(encodeURIComponent).join("/");
}

export class RepoWriter {
  /**
   * @param {{ request(payload: object, timeout?: number): Promise<any> }} engine 워커 연결. `sheetApply` 액션을 쓴다
   * @param {GitHubStore} [store] 테스트가 가짜 fetch 를 넣은 store 를 준다
   */
  constructor(engine, store = new GitHubStore()) {
    this.engine = engine;
    this.store = store;
  }

  /** 토큰을 메모리에서 지운다. 창을 떠날 때와 사람이 지우기를 누를 때. */
  forget() {
    this.store.disconnect();
  }

  /**
   * 고침이 적힌 행을 파일마다 모아 쓴다. 한 파일이 실패해도 다른 파일은 계속한다.
   * @param {{ owner: string, repo: string, ref: string }} target
   * @param {{ file: string, line: number, column: number, text: string, fix: string }[]} rows
   * @param {string} token
   * @param {(done: number, total: number, file: string) => void} [onProgress]
   * @returns {Promise<{ files: { file: string, applied: string[], failed: string[], commit: string | null, source: string | null }[], applied: number, failed: number }>}
   */
  async write(target, rows, token, onProgress) {
    this.store.connect(`${target.owner}/${target.repo}`, token);
    /** @type {Map<string, typeof rows>} */
    const byFile = new Map();
    for (const row of rows) {
      if (!row.fix) continue;
      if (!byFile.has(row.file)) byFile.set(row.file, []);
      /** @type {typeof rows} */ (byFile.get(row.file)).push(row);
    }
    const files = [...byFile.keys()].sort();
    const results = [];
    let done = 0;
    for (const file of files) {
      const fileRows = /** @type {typeof rows} */ (byFile.get(file));
      const result = { file, applied: /** @type {string[]} */ ([]), failed: /** @type {string[]} */ ([]), commit: /** @type {string | null} */ (null), source: /** @type {string | null} */ (null) };
      try {
        const data = await this.store.call(`/contents/${encodedPath(file)}?ref=${encodeURIComponent(target.ref)}`);
        if (!data || data.type !== "file" || data.encoding !== "base64") throw new Error("파일이 없다");
        const source = decodeContent(data.content);
        const [rewritten, applied, failed] = await this.engine.request({ action: "sheetApply", preset: "screen", patches: [], source, rows: fileRows });
        result.applied = applied;
        result.failed = failed;
        if (applied.length) {
          const body = { message: `hanlint: 화면 글 고침 ${applied.length}곳 (${file})`, content: encodeContent(rewritten), sha: data.sha, branch: target.ref };
          const written = await this.store.call(`/contents/${encodedPath(file)}`, { method: "PUT", body: JSON.stringify(body) });
          result.commit = written?.commit?.sha ?? null;
          result.source = rewritten;
        }
      } catch (error) {
        result.failed = [...result.failed, `${file}: ${error.message}`];
      }
      results.push(result);
      done += 1;
      onProgress?.(done, files.length, file);
    }
    return {
      files: results,
      applied: results.reduce((sum, item) => sum + item.applied.length, 0),
      failed: results.reduce((sum, item) => sum + item.failed.length, 0),
    };
  }
}
