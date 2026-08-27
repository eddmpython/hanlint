"""정밀 분석기. kiwipiepy 가 있을 때만 쓴다. 모듈을 import 해도 kiwipiepy 를 올리지 않는다."""

from __future__ import annotations

from .kiwiAnalyzer import KiwiAnalyzer

__all__ = ["KiwiAnalyzer"]
