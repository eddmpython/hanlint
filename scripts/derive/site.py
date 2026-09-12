"""같은 npm 엔진과 정적 편집기를 GitHub Pages 배포 폴더에 조립한다."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def buildSite(output: Path) -> None:
    """명시한 빈 실행 폴더에만 배포물을 만든다. 기존 파일은 덮어쓰지 않는다."""
    output = output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("배포 산출물은 저장소 밖의 공통 실행 공간에 둔다")
    if output.exists() and any(output.iterdir()):
        raise ValueError("배포 폴더는 비어 있어야 한다")
    output.mkdir(parents=True, exist_ok=True)
    for source in (ROOT / "web").iterdir():
        if source.is_file() and source.suffix in {".html", ".css", ".js", ".svg"}:
            shutil.copy2(source, output / source.name)
    shutil.copytree(ROOT / "npm" / "src", output / "npm" / "src")
    dataRoot = output / "npm" / "data"
    dataRoot.mkdir(parents=True)
    files = {path.name: path.read_text(encoding="utf-8") for path in sorted((ROOT / "npm" / "data").iterdir())}
    (dataRoot / "siteData.json").write_text(json.dumps(files, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (output / ".nojekyll").write_text("", encoding="utf-8")
    licenses = [ROOT / "npm" / "LICENSE", ROOT / "npm" / "koglType1.LICENSE.md"]
    sections = "".join(
        f"<h2>{html.escape(path.name)}</h2><pre>{html.escape(path.read_text(encoding='utf-8'))}</pre>" for path in licenses
    )
    page = (
        '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>출처와 라이선스 · 한린트</title><link rel="icon" href="./brand.svg"><link rel="stylesheet" href="./style.css">'
        '<body><main class="documentPage"><a href="./">← 한린트 편집기로</a><h1>출처와 라이선스</h1>'
        "<p>브라우저 검사기는 배포판과 같은 사전, 규칙과 본보기를 사용합니다. 포함한 자료의 고지는 아래와 같습니다.</p>"
        f"{sections}</main></body></html>"
    )
    (output / "license.html").write_text(page, encoding="utf-8")


def main() -> None:
    """출력 경로를 명시해 실행한다."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    buildSite(args.output)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
