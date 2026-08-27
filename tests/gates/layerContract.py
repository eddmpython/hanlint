"""층 순위의 정본. 뜻은 skills/specs/operation/moduleLayers.md 가 설명한다.

숫자가 작을수록 아래층이다. import 는 자기보다 작은 숫자로만 간다. 같은 숫자는 형제이고 서로
import 하지 않는다. 새 층은 그 표면이 실제로 생겼을 때 여기에 한 줄 더한다.
"""

from __future__ import annotations

PACKAGE = "hanlint"

JS_ROOT = "util"
"""npm/src 루트의 도우미 (text.js, regex.js). 파이썬 str 과 re 의 뜻을 드는 층이라 data 보다도 아래다. npm 에만 있다."""

LAYERS: dict[str, int] = {
    JS_ROOT: -1,
    "data": 0,
    "config": 1,
    "document": 2,
    "analysis": 3,
    "fingerprint": 4,
    "rules": 5,
    "audit": 5,
    "profile": 5,
    "report": 6,
    "edit": 6,
    "cli": 7,
}

RULE_LAYER = "rules"
"""이 층 안의 규칙 파일은 서로 import 하지 않는다. 공통은 rules/shared 에 둔다."""

RULE_SHARED = "shared"
"""rules 안에서 규칙 파일이 import 해도 되는 유일한 하위 폴더."""
