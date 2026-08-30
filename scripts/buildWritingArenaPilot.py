"""자체 작성한 일곱 장르 writingArena v1 프로토콜 fixture를 결정적으로 만든다.

이 자료에는 사람 선호 정답도 외부 참조 원문도 없다. 패널 배정, import, 자동 심사기 순서 일관성
계약을 실행하기 위한 작은 고정 입력이다.
"""

from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "hanlint" / "data" / "writingArenaPilotV1.json"
MODEL_ID = "hanlint.protocolFixture"
MODEL_SHA = sha256(b"hanlint.protocolFixture.v1").hexdigest()


CASES = (
    {
        "id": "blog-basil-01",
        "preset": "blog",
        "reader": "베란다에서 바질을 처음 기르는 사람",
        "task": "바질에 물을 줄 시점과 확인할 흙 깊이를 이해한다",
        "facts": ("바질은 오전 7시에 물을 준다.", "흙 윗부분 2cm가 마르면 물을 준다."),
        "mustInclude": ("바질", "오전 7시", "2cm"),
        "baseline": (
            "# 바질 물주기\n\n바질은 오전 7시에 물을 준다. 흙 윗부분 2cm가 마른 상태인지 확인한 후 물을 준다. "
            "처음 기르는 사람은 이 두 조건을 확인한다.\n"
        ),
        "candidate": (
            "# 바질은 언제 물을 마실까\n\n오전 7시, 먼저 손가락으로 흙 윗부분 2cm를 살핀다. "
            "그곳이 말랐다면 바질에 물을 줄 때다. 시각보다 흙의 상태를 함께 보면 판단이 한결 쉽다.\n"
        ),
    },
    {
        "id": "report-haesol-01",
        "preset": "report",
        "reader": "해솔 계획의 다음 확인 순서를 정할 운영자",
        "task": "해솔 계획의 시작일과 예산을 확인한다",
        "facts": ("해솔 계획은 2026년 8월 31일 시작한다.", "해솔 계획의 예산은 380,000원이다."),
        "mustInclude": ("해솔 계획", "2026년 8월 31일", "380,000원"),
        "baseline": (
            "# 해솔 계획\n\n해솔 계획은 2026년 8월 31일 시작하며 예산은 380,000원이다. "
            "운영자는 시작일과 예산을 확인하고 다음 순서를 정한다.\n"
        ),
        "candidate": (
            "# 해솔 계획 확인 사항\n\n해솔 계획의 시작일은 2026년 8월 31일이고 예산은 380,000원이다. "
            "운영자는 두 값을 확인한 뒤 다음 점검 순서를 정한다.\n"
        ),
    },
    {
        "id": "docs-retry-01",
        "preset": "docs",
        "reader": "호출 제한 오류를 처리하는 API 개발자",
        "task": "HTTP 429 응답에서 재시도 횟수를 설정한다",
        "facts": ("HTTP 429 응답은 호출 제한을 뜻한다.", "재시도는 최대 3회 수행한다."),
        "mustInclude": ("HTTP 429", "최대 3회"),
        "baseline": (
            "# 재시도 설정\n\nHTTP 429 응답은 호출 제한을 뜻한다. 이 응답을 받으면 재시도를 최대 3회 수행한다. "
            "개발자는 이 횟수를 넘기지 않도록 처리한다.\n"
        ),
        "candidate": (
            "# 호출 제한 재시도\n\n서버가 HTTP 429를 반환하면 호출 제한에 걸린 것이다. 재시도는 최대 3회로 제한한다. "
            "그 뒤에도 같은 응답이 오면 호출을 멈추고 오류를 기록한다.\n"
        ),
    },
    {
        "id": "guide-drill-01",
        "preset": "guide",
        "reader": "새로 입사해 대피 훈련에 참여하는 직원",
        "task": "오후 2시에 동쪽 계단으로 대피한다",
        "facts": ("대피 훈련은 오후 2시에 시작한다.", "참가자는 동쪽 계단을 이용한다."),
        "mustInclude": ("오후 2시", "동쪽 계단"),
        "baseline": (
            "# 대피 훈련 안내\n\n대피 훈련은 오후 2시에 시작한다. 참가자는 동쪽 계단을 이용한다. "
            "시작 시각과 이동 경로를 미리 확인한다.\n"
        ),
        "candidate": (
            "# 대피 훈련 순서\n\n오후 2시에 안내가 나오면 업무를 멈춘다. 가까운 통로를 따라 동쪽 계단으로 이동한다. "
            "출발하기 전에 시각과 계단 위치를 한 번 확인한다.\n"
        ),
    },
    {
        "id": "essay-library-01",
        "preset": "essay",
        "reader": "동네 변화에 관한 짧은 수필을 읽는 주민",
        "task": "도서관 이전이 만든 등굣길의 변화를 떠올린다",
        "facts": ("동네 도서관은 2024년에 이전했다.", "새 도서관은 학교에서 600m 떨어져 있다."),
        "mustInclude": ("동네 도서관", "2024년", "600m"),
        "baseline": (
            "# 옮겨 간 도서관\n\n동네 도서관은 2024년에 이전했다. 새 도서관은 학교에서 600m 떨어져 있다. "
            "나는 달라진 등굣길을 걸으며 이전의 의미를 생각했다.\n"
        ),
        "candidate": (
            "# 길 끝의 도서관\n\n2024년, 동네 도서관이 자리를 옮겼다. 학교에서 600m 떨어진 새 건물까지 걷자 "
            "익숙했던 등굣길이 조금 길어졌다. 늘 지나치던 길도 목적지가 바뀌면 새롭게 보였다.\n"
        ),
    },
    {
        "id": "fiction-umbrella-01",
        "preset": "fiction",
        "reader": "짧은 장면 소설을 읽는 독자",
        "task": "민아가 밤 9시에 역 앞에서 파란 우산을 펴는 장면을 본다",
        "facts": ("민아는 밤 9시에 역 앞에 도착한다.", "민아는 파란 우산을 편다."),
        "mustInclude": ("민아", "밤 9시", "역 앞", "파란 우산"),
        "baseline": (
            "# 역 앞\n\n민아는 밤 9시에 역 앞에 도착했다. 비가 내리고 있었다. 민아는 파란 우산을 폈다. "
            "그는 우산 아래에서 길 건너편을 바라보았다.\n"
        ),
        "candidate": (
            "# 파란 우산\n\n밤 9시, 민아가 역 앞에 닿자 빗방울이 간판 불빛을 잘게 흔들었다. "
            "민아는 파란 우산을 펴고 길 건너편을 바라보았다. 기다리던 사람은 아직 보이지 않았다.\n"
        ),
    },
    {
        "id": "encyclopedia-wetland-01",
        "preset": "encyclopedia",
        "reader": "지역 습지의 기본 정보를 찾는 학생",
        "task": "해오름 습지의 지정 연도와 면적을 확인한다",
        "facts": ("해오름 습지는 1998년에 보호 구역으로 지정됐다.", "해오름 습지의 면적은 42ha다."),
        "mustInclude": ("해오름 습지", "1998년", "42ha"),
        "baseline": (
            "# 해오름 습지\n\n해오름 습지는 1998년에 보호 구역으로 지정됐다. 면적은 42ha다. "
            "이 두 수치는 습지의 기본 현황을 나타낸다.\n"
        ),
        "candidate": (
            "# 해오름 습지\n\n해오름 습지는 면적 42ha의 보호 구역이다. 1998년에 보호 구역으로 지정됐으며, "
            "지역 습지의 지정 현황을 설명할 때 이 연도와 면적을 함께 쓴다.\n"
        ),
    },
)


def digest(text: str) -> str:
    return sha256(text.encode()).hexdigest()


def generation(strategyId: str, caseId: str, text: str) -> dict:
    return {
        "strategyId": strategyId,
        "modelId": MODEL_ID,
        "modelSha256": MODEL_SHA,
        "promptSha256": digest(f"{strategyId}:{caseId}:hanlint.writingArena.fixture.v1"),
        "outputSha256": digest(text),
        "text": text,
    }


def trial(case: dict) -> dict:
    facts = [{"id": f"F{index}", "statement": value} for index, value in enumerate(case["facts"], start=1)]
    contractText = "\n".join((case["reader"], case["task"], *case["facts"]))
    from hanlint.config import numberValues

    return {
        "version": 1,
        "id": case["id"],
        "brief": {
            "version": 1,
            "preset": case["preset"],
            "reader": case["reader"],
            "task": case["task"],
            "facts": facts,
            "mustInclude": list(case["mustInclude"]),
            "allowedNumbers": list(numberValues(contractText)),
            "forbidden": ["효과가 입증됐다"],
            "length": {"min": 65, "max": 420},
        },
        "baseline": generation("plainBrief", case["id"], case["baseline"]),
        "candidate": generation("contextFirstV1", case["id"], case["candidate"]),
    }


def render() -> str:
    sys.path.insert(0, str(ROOT / "src"))
    from hanlint import preparePanelTrialSet

    data = preparePanelTrialSet(
        "hanlint-writing-arena-pilot-v1",
        [trial(case) for case in CASES],
        {
            "origin": "syntheticProtocolFixture",
            "license": "MIT",
            "containsExternalReferenceText": False,
            "qualityLabels": False,
        },
    )
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str]) -> int:
    content = render()
    if "--check" in argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != content:
            print("writingArenaPilotV1.json이 builder 결과와 다르다")
            return 1
        print("writingArenaPilotV1.json이 builder 결과와 같다")
        return 0
    TARGET.write_text(content, encoding="utf-8", newline="\n")
    print(f"writingArenaPilotV1.json에 {len(CASES)}개 장르 사례를 썼다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
