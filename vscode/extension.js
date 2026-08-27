// @ts-check
/**
 * hanlint VS Code 확장. 마크다운을 열고 저장할 때 stdin 으로 검사해 진단으로 보여 주고,
 * fragment 와 replacement 가 있는 지적은 quick fix 로 그 자리를 바꾼다. 의존성은 VS Code API 뿐이다.
 */
const vscode = require("vscode");
const { execFile } = require("node:child_process");

const SOURCE = "hanlint";
/** @type {Map<string, Array<{line: number, rule: string, why: string, fragment: string | null, replacement: string | null}>>} */
const findingsByUri = new Map();

/** @returns {{command: string, args: string[]}} */
function baseCommand() {
  const configured = String(vscode.workspace.getConfiguration("hanlint").get("command") ?? "").trim();
  const parts = configured ? configured.split(/\s+/) : ["npx", "--yes", "hanlint"];
  return { command: parts[0], args: parts.slice(1) };
}

/** @param {import("vscode").TextDocument} document @param {import("vscode").DiagnosticCollection} diagnostics */
function lint(document, diagnostics) {
  if (document.languageId !== "markdown" || document.uri.scheme !== "file") return;
  const { command, args } = baseCommand();
  const errorsOnly = vscode.workspace.getConfiguration("hanlint").get("errorsOnly") === true;
  const full = [...args, "-", "--path", document.fileName, "--format", "json", "--quiet"];
  if (errorsOnly) full.push("--errors-only");
  const child = execFile(
    command,
    full,
    { shell: process.platform === "win32", maxBuffer: 16 * 1024 * 1024 },
    (error, stdout) => {
      if (!stdout) {
        if (error) console.error("hanlint 실행 실패", error.message);
        return;
      }
      try {
        const data = JSON.parse(stdout);
        const findings = data.files?.[0]?.findings ?? [];
        findingsByUri.set(document.uri.toString(), findings);
        diagnostics.set(
          document.uri,
          findings.map((finding) => {
            const line = Math.max(0, Math.min(finding.line - 1, document.lineCount - 1));
            const range = document.lineAt(line).range;
            const severity =
              finding.severity === "error" ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Information;
            const diagnostic = new vscode.Diagnostic(range, `[${finding.rule}] ${finding.why}`, severity);
            diagnostic.source = SOURCE;
            diagnostic.code = finding.rule;
            return diagnostic;
          }),
        );
      } catch (parseError) {
        console.error("hanlint 출력을 읽지 못했다", parseError);
      }
    },
  );
  child.stdin?.end(document.getText(), "utf-8");
}

class FixProvider {
  /**
   * @param {import("vscode").TextDocument} document
   * @param {import("vscode").Range} range
   * @param {import("vscode").CodeActionContext} context
   */
  provideCodeActions(document, range, context) {
    const findings = findingsByUri.get(document.uri.toString()) ?? [];
    const actions = [];
    for (const diagnostic of context.diagnostics) {
      if (diagnostic.source !== SOURCE) continue;
      const line = diagnostic.range.start.line + 1;
      const finding = findings.find(
        (f) => f.line === line && f.rule === diagnostic.code && f.replacement !== null && f.fragment,
      );
      if (!finding || !finding.fragment) continue;
      const window = [];
      for (let at = line - 1; at < Math.min(document.lineCount, line + 3); at++) window.push(at);
      for (const at of window) {
        const text = document.lineAt(at).text;
        const found = text.indexOf(finding.fragment);
        if (found < 0 || text.indexOf(finding.fragment, found + 1) >= 0) continue;
        const action = new vscode.CodeAction(
          `hanlint: ${finding.fragment} → ${finding.replacement}`,
          vscode.CodeActionKind.QuickFix,
        );
        action.diagnostics = [diagnostic];
        action.edit = new vscode.WorkspaceEdit();
        action.edit.replace(
          document.uri,
          new vscode.Range(at, found, at, found + finding.fragment.length),
          String(finding.replacement),
        );
        actions.push(action);
        break;
      }
    }
    return actions;
  }
}

/** @param {import("vscode").ExtensionContext} context */
function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection(SOURCE);
  context.subscriptions.push(diagnostics);
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument((document) => lint(document, diagnostics)),
    vscode.workspace.onDidSaveTextDocument((document) => lint(document, diagnostics)),
    vscode.workspace.onDidCloseTextDocument((document) => {
      diagnostics.delete(document.uri);
      findingsByUri.delete(document.uri.toString());
    }),
    vscode.languages.registerCodeActionsProvider({ language: "markdown" }, new FixProvider(), {
      providedCodeActionKinds: [vscode.CodeActionKind.QuickFix],
    }),
  );
  for (const document of vscode.workspace.textDocuments) lint(document, diagnostics);
}

function deactivate() {}

module.exports = { activate, deactivate };
