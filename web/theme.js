// @ts-check
/** 사이트 경로별 테마 선택. 저장하지 않은 첫 방문은 시스템 설정을 따른다. */
const themeKey = `hanlint.theme:${new URL(".", import.meta.url).pathname}`;
const systemTheme = matchMedia("(prefers-color-scheme: dark)");
let chosenTheme = null;
try { chosenTheme = localStorage.getItem(themeKey); }
catch (error) { console.warn("테마를 읽지 못해 시스템 설정을 사용합니다.", error); }

function renderTheme() {
  const theme = chosenTheme === "dark" || chosenTheme === "light" ? chosenTheme : systemTheme.matches ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  for (const meta of document.querySelectorAll('meta[name="theme-color"]')) meta.setAttribute("content", getComputedStyle(document.body).backgroundColor);
  const toggle = document.getElementById("themeToggle");
  if (toggle) {
    const label = theme === "dark" ? "라이트 모드로 전환" : "다크 모드로 전환";
    toggle.setAttribute("aria-pressed", String(theme === "dark"));
    toggle.setAttribute("aria-label", label);
    toggle.title = label;
  }
}

renderTheme();
systemTheme.addEventListener("change", renderTheme);
document.getElementById("themeToggle")?.addEventListener("click", () => {
  chosenTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  renderTheme();
  try { localStorage.setItem(themeKey, chosenTheme); }
  catch (error) { console.warn("테마는 이 화면에만 적용합니다.", error); }
});
window.addEventListener("storage", (event) => {
  if (event.key !== themeKey) return;
  chosenTheme = event.newValue;
  renderTheme();
});
