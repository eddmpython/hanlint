"""종류별 프로파일. 기준 말뭉치 (corpus/catalogue.toml) 의 글을 종류마다 지문으로 만들어 `data/profiles.json` 에 쓴다.

계산은 `hanlint.profile.buildProfile` 하나다. 사용자의 `hanlint profile build` 와 같은 함수라 같은 글에 같은 표가
나온다. 제품은 이 파일만 싣는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from hanlint import Config, fingerprint  # noqa: E402
from hanlint.data.profiles import renderProfiles  # noqa: E402
from hanlint.profile import buildProfile  # noqa: E402

CORPUS_ROOT = (REPO / "../hanlint.out/corpus").resolve()
TARGET = REPO / "src" / "hanlint" / "data" / "profiles.json"


def render() -> str:
    metadata = json.loads((CORPUS_ROOT / "metadata.json").read_text(encoding="utf-8"))["documents"]
    byKind: dict[str, list] = {}
    for entry in metadata:
        text = (CORPUS_ROOT / entry["path"]).read_text(encoding="utf-8")
        byKind.setdefault(entry["type"], []).append(fingerprint(text, Config(preset=entry["preset"]), path=entry["path"]))
    return renderProfiles({kind: buildProfile(docs, kind) for kind, docs in byKind.items()})


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="종류별 프로파일을 만든다")
    parser.add_argument("--check", action="store_true", help="말뭉치에서 다시 세어 기록과 글자 단위로 견준다")
    return parser.parse_args()


def main() -> int:
    args = parseArgs()
    text = render()
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != text:
            print("다시 만들어야 한다: data/profiles.json")
            return 1
        print("프로파일이 말뭉치와 같다")
        return 0
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    data = json.loads(text)
    sizes = ", ".join(f"{kind} {len(json.dumps(value, ensure_ascii=False)) // 1024}KB" for kind, value in data["types"].items())
    print(f"{TARGET} 에 종류 {len(data['types'])}개의 프로파일을 썼다 ({len(text) // 1024}KB. {sizes})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
