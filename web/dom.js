// @ts-check
/** 원고는 항상 텍스트 노드로 그린다. */
export const get = (id) => document.getElementById(id);
export function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}
export function button(text, action, className = "textButton") {
  const node = element("button", className, text);
  node.type = "button";
  node.addEventListener("click", action);
  return node;
}
/** 화면에 보일 오류 글. 우리가 던진 한국어 오류는 그대로, 브라우저가 던진 오류는 한국어 안내 뒤에 괄호로 붙인다.
 * 우리 오류는 이름이 `Error`인 평범한 오류다. JSON.parse(SyntaxError)나 저장 공간(QuotaExceededError)처럼 브라우저가 던진
 * 오류는 이름이 다르고, 사용자 파일의 앞부분을 문장에 담아 한글이 섞일 수 있어 한글로는 가리지 않는다. */
export function errorText(error, lead = "처리하지 못했어요.") {
  const message = String(error?.message ?? error ?? "");
  const ours = (error?.name ?? "Error") === "Error" && /[가-힣]/.test(message);
  if (ours) return message;
  return message ? `${lead} (브라우저 오류: ${message})`.trim() : lead;
}
export function download(name, text, type = "application/json") {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = element("a");
  link.href = url;
  link.download = name.replace(/[<>:"/\\|?*\u0000-\u001f]/g, "_");
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function highlight(text, findings) {
  const root = get("highlights");
  root.replaceChildren();
  const lines = text.split("\n");
  lines.forEach((line, index) => {
    const finding = findings.find((item) => item.line === index + 1);
    const fragment = finding?.fragment || finding?.quote;
    const start = fragment ? line.indexOf(fragment) : -1;
    if (start >= 0) {
      root.append(document.createTextNode(line.slice(0, start)), element("mark", finding.severity === "notice" ? "noticeMark" : "", fragment), document.createTextNode(line.slice(start + fragment.length)));
    } else root.append(document.createTextNode(line));
    root.append(document.createTextNode("\n"));
  });
  root.scrollTop = get("draft").scrollTop;
}
