// @ts-check
/** 비동기 모듈 준비 전에 보낸 첫 요청도 보존하는 검사 작업 연결. */
export class EngineClient {
  constructor(worker, onError, timeout = 30000) {
    this.worker = worker; this.onError = onError; this.timeout = timeout;
    this.ready = false; this.failure = null; this.nextId = 0; this.pending = new Map();
    worker.onmessage = ({ data }) => {
      if (data.ready) {
        if (this.ready) return;
        this.ready = true;
        for (const item of this.pending.values()) worker.postMessage(item.message);
        return;
      }
      const item = this.pending.get(data.id);
      if (!item) return;
      this.pending.delete(data.id); clearTimeout(item.timer);
      if (data.error) item.reject(new Error(data.error)); else item.resolve(data.result);
    };
    worker.onerror = () => this.fail(new Error("검사기를 불러오지 못했습니다. 원고를 내려받아 보관한 뒤 새로고침해 주세요."));
  }

  fail(error) {
    this.failure = error;
    for (const item of this.pending.values()) { clearTimeout(item.timer); item.reject(error); }
    this.pending.clear();
    this.worker.terminate();
    this.onError(error);
  }

  request(payload) {
    if (this.failure) return Promise.reject(this.failure);
    const id = ++this.nextId, message = { ...payload, id };
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => this.fail(new Error("검사 응답이 늦어 중단했습니다. 원고를 내려받아 보관한 뒤 새로고침해 주세요.")), this.timeout);
      this.pending.set(id, { message, resolve, reject, timer });
      if (this.ready) this.worker.postMessage(message);
    });
  }
}
