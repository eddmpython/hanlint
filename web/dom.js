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
