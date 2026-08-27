// @ts-check
/** 설정 파일을 찾아 읽는다. `hanlint.toml` 이거나 `pyproject.toml` 의 `[tool.hanlint]` 다. 파이썬과 같은 탐색이다. */
import { existsSync, readFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";

import { configFromMapping, defaultConfig } from "./settings.js";
import { parseToml } from "./toml.js";

export const CONFIG_NAME = "hanlint.toml";
export const PYPROJECT_NAME = "pyproject.toml";

/** @param {string} path */
export function readConfigFile(path) {
  let data = parseToml(readFileSync(path, "utf-8"));
  if (basename(path) === PYPROJECT_NAME) {
    const tool = /** @type {Record<string, unknown>} */ (data.tool ?? {});
    data = /** @type {Record<string, unknown>} */ (tool.hanlint ?? {});
  }
  const config = configFromMapping(data);
  config.source = path;
  return config;
}

/** start 에서 위로 올라가며 hanlint.toml 이나 [tool.hanlint] 를 가진 pyproject.toml 을 찾는다. @param {string} start */
export function findConfigFile(start) {
  let folder = resolve(start);
  while (true) {
    const candidate = join(folder, CONFIG_NAME);
    if (existsSync(candidate)) return candidate;
    const pyproject = join(folder, PYPROJECT_NAME);
    if (existsSync(pyproject)) {
      const data = parseToml(readFileSync(pyproject, "utf-8"));
      const tool = /** @type {Record<string, unknown>} */ (data.tool ?? {});
      if ("hanlint" in tool) return pyproject;
    }
    const parent = dirname(folder);
    if (parent === folder) return null;
    folder = parent;
  }
}

/**
 * `path` 를 주면 그 파일만 읽는다. 안 주면 `start` (기본 현재 폴더) 에서 찾고, 없으면 기본값이다.
 * @param {string | null} [path]
 * @param {string | null} [start]
 */
export function loadConfig(path = null, start = null) {
  if (path) return readConfigFile(path);
  const found = findConfigFile(start ?? process.cwd());
  return found ? readConfigFile(found) : defaultConfig();
}
