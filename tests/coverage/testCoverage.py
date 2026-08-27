"""겹침 층. 평가자 인용을 본문에서 찾고 hanlint 지적과 자리를 견준다."""

from __future__ import annotations

import json

from hanlint import lintText
from hanlint.coverage import coverageOf, loadReview, renderCoverage

TEXT = "## 절\n\n핵심은 속도입니다. 파일을 엽니다.\n\n표가 보입니다. 이것으로 됩니다.\n\n마지막 문단입니다.\n"
REVIEW = {
    "rounds": [
        {
            "reviewers": [
                {
                    "role": "첫 독자",
                    "findings": [
                        {"quote": "핵심은 속도입니다.", "why": "포장하는 말이다", "fix": "지운다"},
                        {"quote": "마지막 문단입니다.", "why": "결말이 앞 절을 다시 읊는다", "fix": "확인으로 닫는다"},
                        {"quote": "본문에서 사라진 문장입니다.", "why": "파일이 없다", "fix": ""},
                    ],
                }
            ]
        }
    ]
}


def testCoverageCountsLocatedAndCovered(tmp_path):
    review = tmp_path / "review.json"
    review.write_text(json.dumps(REVIEW, ensure_ascii=False), encoding="utf-8")
    reviews = loadReview(review)
    assert len(reviews) == 3 and reviews[0].round == 1 and reviews[0].role == "첫 독자"
    coverage = coverageOf(TEXT, lintText(TEXT), reviews)
    assert (coverage.total, coverage.located, coverage.covered, coverage.coveredByError) == (3, 2, 1, 1)
    assert coverage.byRule[0][0] == "cliche"
    assert len(coverage.uncaught) == 1 and coverage.uncaught[0].line == 7
    assert coverage.uncaught[0].kind == "순서와 구조"
    text = renderCoverage(coverage)
    assert "평가자 지적 3건. 본문에서 찾은 인용 2건 (본문이 바뀐 1건은 잴 수 없다)" in text
    assert "hanlint 가 같은 자리를 집은 것 1건 (50%). error 로 1건, notice 로만 0건" in text and "7행" in text


def testFlatListIsAccepted(tmp_path):
    review = tmp_path / "flat.json"
    review.write_text(json.dumps([{"quote": "표가 보입니다.", "why": "짧다"}], ensure_ascii=False), encoding="utf-8")
    coverage = coverageOf(TEXT, lintText(TEXT), loadReview(review))
    assert coverage.total == 1 and coverage.located == 1
