"""문서 층. 마크다운을 블록, 절, 문서 모델로 바꾼다. 순수 파싱이라 분석기를 모른다."""

from __future__ import annotations

from .model import Block, Document, Section
from .parseMarkdown import dropFences, fenceLanguage, parseMarkdown
from .plainText import codeSpans, plainText

__all__ = ["Block", "Document", "Section", "codeSpans", "dropFences", "fenceLanguage", "parseMarkdown", "plainText"]
