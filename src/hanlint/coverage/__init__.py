"""겹침 부분. 사람 평가자의 지적과 hanlint의 지적이 같은 곳을 짚는지 잰다. 규칙을 더하는 근거가 이 숫자다."""

from __future__ import annotations

from .match import Coverage, ReviewFinding, Uncaught, coverageDict, coverageOf, loadReview, renderCoverage

__all__ = ["Coverage", "ReviewFinding", "Uncaught", "coverageDict", "coverageOf", "loadReview", "renderCoverage"]
