"""`python -m hanlint` 진입점. 콘솔 스크립트 `hanlint` 와 같다."""

from __future__ import annotations

import sys

from .cli import main

sys.exit(main())
