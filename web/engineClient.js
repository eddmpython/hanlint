// @ts-check
/**
 * 비동기 모듈 준비 전에 보낸 첫 요청도 보존하는 검사 작업 연결.
 * 시간 초과나 워커 오류는 기다리던 요청만 끝내고 워커를 새로 띄운다. 실측: 30초 타임아웃 하나가 워커를 죽여 새로고침
 * 전까지 편집기 전체가 멎었다 (2026-09-18). 다시 띄우기가 RESTARTS 번 연달아 실패하면 그때 멈춘다.
 */
const RESTARTS = 3;

export class EngineClient {
  /**
   * @param {(() => Worker) | Worker} createWorker 워커를 만드는 함수. 다시 띄울 때 또 부른다. 워커 하나를 주면 다시 띄우지 않는다.
   * @param {(error: Error) => void} onError
   * @param {number} [timeout] 요청 하나의 기본 제한 (ms)
   */
  constructor(createWorker, onError, timeout = 30000) {
    this.createWorker = typeof createWorker === "function" ? createWorker : () => createWorker;
    this.canRestart = typeof createWorker === "function";
    this.onError = onError; this.timeout = timeout;
    this.failure = null; this.nextId = 0; this.pending = new Map(); this.restarts = 0;
    this.worker = null; this.ready = false;
    this.start();
  }

  start() {
    const worker = this.createWorker();
    this.worker = worker; this.ready = false;
    worker.onmessage = ({ data }) => {
      if (worker !== this.worker) return;
      if (data.ready) {
        if (this.ready) return;
        this.ready = true; this.restarts = 0;
        for (const item of this.pending.values()) worker.postMessage(item.message);
        return;
      }
      const item = this.pending.get(data.id);
      if (!item) return;
      this.pending.delete(data.id); clearTimeout(item.timer);
      if (data.error) item.reject(new Error(data.error)); else item.resolve(data.result);
    };
    worker.onerror = () => { if (worker === this.worker) this.fail(new Error("검사기를 불러오지 못했습니다. 원고를 내려받아 보관한 뒤 새로고침해 주세요.")); };
  }

  /** 기다리던 요청을 모두 끝내고 워커를 새로 띄운다. 연달아 RESTARTS 번 넘게 실패하면 멈춘다. */
  fail(error) {
    for (const item of this.pending.values()) { clearTimeout(item.timer); item.reject(error); }
    this.pending.clear();
    this.worker?.terminate();
    this.restarts += 1;
    if (this.canRestart && this.restarts <= RESTARTS) this.start();
    else { this.failure = error; this.worker = null; }
    this.onError(error);
  }

  /**
   * @param {object} payload
   * @param {number} [timeout] 이 요청만의 제한 (ms). 파일 묶음처럼 오래 걸리는 요청이 준다.
   */
  request(payload, timeout = this.timeout) {
    if (this.failure) return Promise.reject(this.failure);
    const id = ++this.nextId, message = { ...payload, id };
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        if (!this.pending.has(id)) return;
        this.pending.delete(id);
        reject(new Error("검사 응답이 늦어 이 요청을 중단했습니다. 검사기를 다시 띄웠으니 한 번 더 시도해 주세요."));
        this.fail(new Error("검사 응답이 늦어 중단했습니다. 검사기를 다시 띄웠습니다."));
      }, timeout);
      this.pending.set(id, { message, resolve, reject, timer });
      if (this.ready && this.worker) this.worker.postMessage(message);
    });
  }
}
