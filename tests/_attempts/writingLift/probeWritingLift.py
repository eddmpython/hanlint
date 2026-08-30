"""완성 글에서 writingPacket과 한 차례 수정 반복의 실제 효용을 잰다.

과제와 실행기는 저장소에 남기되 모델 원시 출력과 판정은 프로젝트 밖 실행 공간에 둔다. 같은 사실 brief를
네 조건에 주고, 조건 이름을 숨긴 쌍 비교는 두 seed와 A/B 양쪽 순서가 모두 일치할 때만 승패로 센다.

```powershell
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/writingLift/probeWritingLift.py prepare `
  --output C:/Users/MSI/AppData/Local/dev-workspace/hanlint-writing-lift-20260831/manifest.json
.venv/Scripts/python.exe -X utf8 -B tests/_attempts/writingLift/probeWritingLift.py generate `
  C:/Users/MSI/AppData/Local/dev-workspace/hanlint-writing-lift-20260831/manifest.json `
  --model qwen3:8b `
  --output C:/Users/MSI/AppData/Local/dev-workspace/hanlint-writing-lift-20260831/responses.json
```
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from hanlint import Config, auditText, lintText, writingPacket  # noqa: E402

OLLAMA_ENDPOINT = "http://127.0.0.1:11434"
GENERATION_OPTIONS = {"temperature": 0, "seed": 42, "num_predict": 1200}
JUDGE_SEEDS = (314159, 271828)
JUDGE_OPTIONS = {"temperature": 0, "num_predict": 384}
CONDITIONS = ("plainBrief", "rulePrompt", "writingPacket", "packetLoop")
INITIAL_CONDITIONS = CONDITIONS[:3]
COMPARISON_CONDITIONS = CONDITIONS[1:]
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "factFidelity": {"type": "string", "enum": ["A", "B", "tie"]},
        "taskUtility": {"type": "string", "enum": ["A", "B", "tie"]},
        "naturalKorean": {"type": "string", "enum": ["A", "B", "tie"]},
        "organization": {"type": "string", "enum": ["A", "B", "tie"]},
        "concision": {"type": "string", "enum": ["A", "B", "tie"]},
        "overall": {"type": "string", "enum": ["A", "B", "tie"]},
        "note": {"type": "string"},
    },
    "required": [
        "factFidelity",
        "taskUtility",
        "naturalKorean",
        "organization",
        "concision",
        "overall",
        "note",
    ],
    "additionalProperties": False,
}


BRIEFS = (
    {
        "id": "blog-balcony-basil",
        "preset": "blog",
        "title": "베란다 바질 관찰 결과",
        "reader": "작은 베란다에서 바질 물주기 방식을 고르려는 초보 재배자",
        "task": "세 화분의 관찰 결과를 비교하고 다음 2주의 물주기 방식을 고르게 돕는 완결된 블로그 글",
        "length": [550, 850],
        "facts": [
            "관찰 장소는 하늘뜰 302호의 동향 베란다다.",
            "관찰 기간은 2026년 8월 12일부터 8월 25일까지다.",
            "바질 화분 A, 바질 화분 B, 바질 화분 C에는 같은 흙 800 g을 담았고 햇빛은 하루 4시간이었다.",
            "바질 화분 A에는 매일 200 mL를 주었고 새잎은 8장 늘었다.",
            "바질 화분 B에는 이틀마다 300 mL를 주었고 새잎은 6장 늘었다.",
            "바질 화분 C에는 매일 100 mL를 주었고 새잎은 4장 늘었다.",
            "세 화분 모두 병충해는 관찰되지 않았다.",
            "이 결과는 한 장소의 짧은 관찰이라 물의 양이 차이를 만들었다고 입증하지 않는다.",
        ],
        "mustInclude": [
            "하늘뜰 302호",
            "2026년 8월 12일",
            "8월 25일",
            "바질 화분 A",
            "바질 화분 B",
            "바질 화분 C",
            "800 g",
            "4시간",
            "200 mL",
            "8장",
            "300 mL",
            "6장",
            "100 mL",
            "4장",
        ],
        "forbidden": ["인과관계가 입증", "모든 바질", "가장 좋은 방법으로 확정"],
    },
    {
        "id": "report-library-seat",
        "preset": "report",
        "title": "해솔도서관 좌석 예약 시범 운영 보고",
        "reader": "시범 운영의 연장 여부를 결정할 해솔도서관 운영위원회",
        "task": "관찰값과 한계를 구분하고 다음 조치를 결정하게 하는 짧은 내부 보고서",
        "length": [600, 900],
        "facts": [
            "시범 운영 기간은 2026년 7월 1일부터 7월 14일까지였다.",
            "대상은 해솔도서관 2층의 좌석 48석이었다.",
            "기간 중 예약 이용자는 612명이었다.",
            "현장 대기시간 중앙값은 시행 전 18분에서 시행 중 7분으로 줄었다.",
            "예약 뒤 나타나지 않은 비율은 첫 주 21%에서 둘째 주 9%로 줄었다.",
            "안내판과 문자 발송 비용은 합계 380,000원이었다.",
            "시범 운영에는 예약을 쓰지 않은 비교 층이 없어서 제도만의 효과로 단정할 수 없다.",
            "운영팀의 제안은 8주 연장하고 매주 대기시간과 미방문율을 공개하는 것이다.",
        ],
        "mustInclude": [
            "해솔도서관",
            "2026년 7월 1일",
            "7월 14일",
            "2층",
            "48석",
            "612명",
            "18분",
            "7분",
            "21%",
            "9%",
            "380,000원",
            "8주",
        ],
        "forbidden": ["통계적으로 유의", "예약제가 입증", "전 지점 도입"],
    },
    {
        "id": "docs-mora-check",
        "preset": "docs",
        "title": "mora check 빠른 시작",
        "reader": "mora 1.4를 처음 실행하는 문서 작성자",
        "task": "설정 파일을 만든 뒤 한 문서를 검사하고 종료 코드를 해석할 수 있는 완결된 기술 문서",
        "length": [700, 1050],
        "facts": [
            "이 문서는 mora 1.4만 다룬다.",
            "프로젝트 루트에서 mora init을 실행하면 .mora/config.toml이 생긴다.",
            "검사는 mora check draft.md로 실행한다.",
            "종료 코드 0은 지적 없음, 1은 지적 있음, 2는 설정 또는 입력 오류를 뜻한다.",
            "mora check draft.md --format json은 표준 출력에 JSON을 쓴다.",
            "mora는 검사할 문서를 네트워크로 전송하지 않는다.",
            "알려지지 않은 설정 키가 있으면 종료 코드 2로 끝나고 키 이름을 표준 오류에 쓴다.",
            "세부 명세 링크는 https://example.invalid/mora/check 다.",
        ],
        "mustInclude": [
            "mora 1.4",
            "mora init",
            ".mora/config.toml",
            "mora check draft.md",
            "종료 코드 0",
            "종료 코드 1",
            "종료 코드 2",
            "--format json",
            "https://example.invalid/mora/check",
        ],
        "forbidden": ["클라우드", "자동으로 고친", "Windows 전용"],
    },
    {
        "id": "guide-label-printer",
        "preset": "guide",
        "title": "라온표식기 R2 첫 라벨 출력",
        "reader": "상자를 정리하려고 라온표식기 R2를 처음 켠 사용자",
        "task": "포장을 연 상태에서 시험 라벨 한 장을 출력하고 E04 오류까지 해결할 수 있는 단계별 안내",
        "length": [600, 900],
        "facts": [
            "라온표식기 R2에는 폭 25 mm 라벨 롤만 사용한다.",
            "전원 버튼을 2초 누르면 표시등이 파란색으로 켜진다.",
            "Raon Mark 앱에서 기기 이름 R2-LOFT를 고른다.",
            "첫 연결의 짝짓기 코드는 482731이다.",
            "연결되면 표시등이 초록색으로 3초 켜진다.",
            "시험 라벨의 문구는 창고 A-17이고 인쇄 매수는 1장이다.",
            "E04는 라벨 롤이 안내선 밖에 있을 때 나타난다.",
            "E04가 뜨면 덮개를 열어 롤 가장자리를 회색 안내선 안쪽에 맞춘 뒤 다시 출력한다.",
        ],
        "mustInclude": [
            "라온표식기 R2",
            "25 mm",
            "2초",
            "Raon Mark",
            "R2-LOFT",
            "482731",
            "3초",
            "창고 A-17",
            "1장",
            "E04",
        ],
        "forbidden": ["블루투스 5.0", "방수", "공장 초기화"],
    },
    {
        "id": "essay-last-bus-stop",
        "preset": "essay",
        "title": "마지막 버스 뒤의 정류장",
        "reader": "작은 관찰에서 감정의 변화를 따라가려는 문예지 독자",
        "task": "주어진 사건과 감각만으로 망설임에서 안도로 움직이는 완결된 짧은 수필",
        "length": [550, 850],
        "facts": [
            "화자는 2026년 8월 3일 밤 11시 20분에 솔내정류장에 도착했다.",
            "마지막 17번 버스는 4분 전에 떠났다.",
            "정류장 의자 아래에는 젖은 노란 장갑 한 짝이 있었다.",
            "맞은편 세탁소 간판의 글자 가운데 탁만 켜져 있었다.",
            "화자의 휴대전화 배터리는 6%였다.",
            "화자는 택시를 부르지 않고 1.8 km를 걸어 집에 갔다.",
            "걷는 동안 비는 그쳤고 장갑은 정류장 의자 위로 옮겨 두었다.",
            "화자는 집에 도착한 뒤 현관 불이 켜진 것을 보고 안도했다.",
        ],
        "mustInclude": [
            "2026년 8월 3일",
            "밤 11시 20분",
            "솔내정류장",
            "17번 버스",
            "4분",
            "노란 장갑",
            "탁",
            "6%",
            "1.8 km",
        ],
        "forbidden": ["교통사고", "어머니의 전화", "기적"],
    },
    {
        "id": "fiction-locker-note",
        "preset": "fiction",
        "title": "27번 보관함",
        "reader": "설명보다 행동과 대화로 긴장을 느끼려는 단편소설 독자",
        "task": "두 인물과 주어진 물건만 써서 오해가 풀리는 완결된 한 장면",
        "length": [650, 950],
        "facts": [
            "장면은 밤 11시 40분, 문을 닫기 직전의 새봄역에서 시작한다.",
            "인물은 서윤과 민호 두 명뿐이다.",
            "서윤은 빨간 우산을 들고 있고 민호는 젖은 종이봉투를 들고 있다.",
            "27번 보관함 안에는 파란 목도리와 메모 한 장이 있다.",
            "메모에는 빌린 건 목도리뿐이야. 말하지 못해 미안해라고 적혀 있다.",
            "서윤은 민호가 돈을 가져갔다고 오해했지만 돈은 처음부터 봉투의 이중 바닥에 있었다.",
            "민호가 봉투의 이중 바닥을 펼쳐 돈을 보여 준다.",
            "장면은 서윤이 빨간 우산을 민호 쪽으로 기울이며 끝난다.",
        ],
        "mustInclude": [
            "밤 11시 40분",
            "새봄역",
            "서윤",
            "민호",
            "빨간 우산",
            "젖은 종이봉투",
            "27번 보관함",
            "파란 목도리",
            "이중 바닥",
        ],
        "forbidden": ["경찰", "어린 시절", "열차 사고"],
    },
    {
        "id": "encyclopedia-nuriseom-bird",
        "preset": "encyclopedia",
        "title": "누리섬솔새",
        "reader": "가상의 누리섬솔새를 처음 찾는 일반 독자",
        "task": "제공된 사실의 범위 안에서 분포, 생김새, 먹이, 번식을 구분한 짧은 백과 항목",
        "length": [600, 900],
        "facts": [
            "누리섬솔새의 학명은 Aves nuriensis다.",
            "누리섬솔새는 가상의 누리섬 북서쪽 해발 300 m에서 700 m 사이 숲에만 산다.",
            "성체의 몸길이는 14 cm에서 16 cm이고 몸무게는 22 g에서 27 g이다.",
            "등은 짙은 녹색이고 눈 위에는 흰 줄이 한 줄 있다.",
            "먹이는 작은 딱정벌레와 누리나무 열매다.",
            "번식기는 4월부터 6월까지이고 한 번에 알 3개를 낳는다.",
            "둥지는 누리나무의 지상 2 m에서 5 m 높이에 짓는다.",
            "개체 수와 보전 등급은 조사되지 않았다.",
        ],
        "mustInclude": [
            "누리섬솔새",
            "Aves nuriensis",
            "300 m",
            "700 m",
            "14 cm",
            "16 cm",
            "22 g",
            "27 g",
            "4월",
            "6월",
            "알 3개",
            "2 m",
            "5 m",
        ],
        "forbidden": ["멸종위기", "천연기념물", "대한민국"],
    },
)


def stableJson(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256Text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha256File(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def readJson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def writeJson(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def briefMarkdown(brief: dict) -> str:
    facts = "\n".join(f"- {fact}" for fact in brief["facts"])
    forbidden = ", ".join(brief["forbidden"])
    minimum, maximum = brief["length"]
    return (
        f"# {brief['title']} 작성 요구\n\n"
        f"- 글 종류: {brief['preset']}\n"
        f"- 독자: {brief['reader']}\n"
        f"- 독자가 할 일: {brief['task']}\n"
        f"- 본문 길이: 공백 포함 {minimum}자 이상 {maximum}자 이하\n"
        "- 숫자로 된 순서 표시는 쓰지 않는다.\n"
        "- 아래 사실 밖의 원인, 배경, 수치, 인물, 기능을 만들지 않는다.\n\n"
        f"## 반드시 담을 사실\n\n{facts}\n\n"
        f"## 쓰지 않을 주장\n\n{forbidden}\n"
    )


def plainPrompt(brief: dict) -> str:
    return (
        "아래 요구를 충족하는 완결된 한국어 글을 써라. 사실을 빠뜨리거나 보태지 말고 독자가 할 일을 실제로 "
        "마칠 수 있게 하라. 풀이, 자기평가, 작성 과정, 바깥 코드 펜스 없이 완성된 마크다운만 출력하라.\n\n" + briefMarkdown(brief)
    )


def rulePrompt(brief: dict) -> str:
    rules = (
        "다음 편집 원칙도 지켜라.\n"
        "- 첫 부분에서 독자의 질문과 글이 줄 결과를 바로 밝힌다.\n"
        "- 한 문단과 한 절에는 한 가지 일만 둔다.\n"
        "- 추상적인 예고, 상투적인 맺음, 같은 종결과 접속어의 기계적 반복을 피한다.\n"
        "- 문장 길이를 억지로 같게 맞추지 말고 쉼표로 절을 줄줄이 잇지 않는다.\n"
        "- 사실과 해석, 관찰과 권고를 구분하며 요구에 없는 인과를 만들지 않는다.\n"
        "- 마지막은 독자가 확인하거나 실행할 구체적인 결과로 닫는다.\n\n"
    )
    return plainPrompt(brief) + "\n\n" + rules


def packetPrompt(brief: dict, packet: dict) -> str:
    return (
        "다음 hanlint writingPacket을 실행하라. contract를 최우선으로 지키고 input.text의 요구와 사실만 써서 "
        "독자의 과업을 끝내는 글을 작성하라. referenceProfile은 품질 점수가 아니며 문장을 복사하지 않는다. "
        "풀이, 자기평가, 작성 과정, 바깥 코드 펜스 없이 완성된 한국어 마크다운만 출력하라.\n\n"
        + json.dumps(packet, ensure_ascii=False, indent=2)
    )


def revisionPrompt(brief: dict, draft: str) -> str:
    config = Config(preset=brief["preset"])
    packet = writingPacket(draft, config, path=f"{brief['id']}.md", purpose="revise")
    return (
        "아래 원래 요구와 hanlint 수정 packet을 대조해 초안을 한 번만 고쳐라. 원래 사실, 수치, 이름, 링크, "
        "코드와 조건을 모두 보존하고 새 사실을 만들지 않는다. findings는 정확한 자리부터 고치되 error 0을 "
        "좋은 글의 증명으로 여기지 말라. 글 전체를 완결된 상태로 내고 풀이, 자기평가, 작성 과정, 바깥 코드 "
        "펜스는 출력하지 말라.\n\n"
        "<원래 요구>\n"
        + briefMarkdown(brief)
        + "\n</원래 요구>\n\n<수정 packet>\n"
        + json.dumps(packet, ensure_ascii=False, indent=2)
        + "\n</수정 packet>"
    )


def buildManifest() -> dict:
    tasks = []
    for brief in BRIEFS:
        config = Config(preset=brief["preset"])
        source = briefMarkdown(brief)
        packet = writingPacket(source, config, path=f"{brief['id']}.md", purpose="draft")
        task = dict(brief)
        task["briefMarkdown"] = source
        task["prompts"] = {
            "plainBrief": plainPrompt(brief),
            "rulePrompt": rulePrompt(brief),
            "writingPacket": packetPrompt(brief, packet),
        }
        tasks.append(task)
    payload = {"version": 1, "conditions": list(CONDITIONS), "generationOptions": GENERATION_OPTIONS, "tasks": tasks}
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def ollamaJson(endpoint: str, route: str, timeout: int, data: dict | None = None) -> dict:
    body = json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    request = urllib.request.Request(
        endpoint.rstrip("/") + route,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ollamaInfo(endpoint: str, model: str, timeout: int) -> dict:
    tags = ollamaJson(endpoint, "/api/tags", timeout)
    found = next((item for item in tags.get("models", []) if item.get("name") == model), None)
    if found is None:
        raise RuntimeError(f"Ollama에 {model} 모델이 없다")
    return {key: found[key] for key in ("name", "digest", "size", "modified_at") if key in found}


def ollamaGenerate(
    prompt: str,
    model: str,
    endpoint: str,
    timeout: int,
    options: dict,
    outputFormat: dict | None = None,
) -> tuple[str, dict]:
    request = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "keep_alive": "10m",
        "options": options,
    }
    if outputFormat:
        request["format"] = outputFormat
    result = ollamaJson(endpoint, "/api/generate", timeout, request)
    output = result.get("response", "").strip()
    metrics = {
        key: result[key]
        for key in ("done_reason", "total_duration", "load_duration", "prompt_eval_count", "eval_count")
        if key in result
    }
    return output, metrics


def responseKey(response: dict) -> tuple[str, str]:
    return response["taskId"], response["condition"]


def checkpointBase(manifest: dict, modelInfo: dict) -> dict:
    return {
        "version": 1,
        "complete": False,
        "manifestSha256": manifest["contentSha256"],
        "runner": {
            "kind": "ollama",
            "model": modelInfo,
            "think": False,
            "options": GENERATION_OPTIONS,
        },
        "responses": [],
    }


def loadGenerationCheckpoint(output: Path, manifest: dict, modelInfo: dict) -> dict:
    if not output.exists():
        return checkpointBase(manifest, modelInfo)
    checkpoint = readJson(output)
    if checkpoint.get("manifestSha256") != manifest["contentSha256"]:
        raise ValueError("기존 응답의 manifest가 현재 manifest와 다르다")
    if checkpoint.get("runner", {}).get("model", {}).get("digest") != modelInfo.get("digest"):
        raise ValueError("기존 응답의 모델 digest가 현재 모델과 다르다")
    return checkpoint


def runGeneration(manifest: dict, model: str, endpoint: str, timeout: int, output: Path) -> dict:
    modelInfo = ollamaInfo(endpoint, model, timeout)
    checkpoint = loadGenerationCheckpoint(output, manifest, modelInfo)
    seen = {responseKey(item) for item in checkpoint["responses"]}
    tasks = manifest["tasks"]
    schedule = []
    for index, task in enumerate(tasks):
        rotated = INITIAL_CONDITIONS[index % 3 :] + INITIAL_CONDITIONS[: index % 3]
        schedule.extend((task, condition) for condition in rotated)
    schedule.extend((task, "packetLoop") for task in tasks)
    total = len(schedule)
    for task, condition in schedule:
        key = (task["id"], condition)
        if key in seen:
            continue
        if condition == "packetLoop":
            drafts = {responseKey(item): item["output"] for item in checkpoint["responses"]}
            draft = drafts.get((task["id"], "writingPacket"))
            if draft is None:
                raise ValueError(f"{task['id']}의 writingPacket 초안이 없다")
            prompt = revisionPrompt(task, draft)
        else:
            prompt = task["prompts"][condition]
        generated, metrics = ollamaGenerate(prompt, model, endpoint, timeout, GENERATION_OPTIONS)
        checkpoint["responses"].append(
            {
                "taskId": task["id"],
                "condition": condition,
                "promptSha256": sha256Text(prompt),
                "output": generated,
                "outputSha256": sha256Text(generated),
                "metrics": metrics,
            }
        )
        seen.add(key)
        writeJson(output, checkpoint)
        print(f"생성 {len(seen)}/{total}: {task['id']} {condition}", flush=True)
    expected = {(task["id"], condition) for task in tasks for condition in CONDITIONS}
    if seen != expected:
        raise ValueError(f"생성 키가 맞지 않는다: 빠짐 {len(expected - seen)}, 모름 {len(seen - expected)}")
    checkpoint["complete"] = True
    checkpoint["rawResponseSha256"] = sha256Text(stableJson(checkpoint["responses"]))
    writeJson(output, checkpoint)
    return checkpoint


def numberAtoms(text: str) -> set[str]:
    return {match.group(0).replace(",", "") for match in NUMBER.finditer(text)}


def automaticResult(task: dict, response: dict) -> dict:
    output = response["output"]
    config = Config(preset=task["preset"])
    findings = lintText(output, config, path=f"{task['id']}.md")
    audit = auditText(output, config, path=f"{task['id']}.md")
    errors = [finding for finding in findings if finding.severity == "error"]
    notices = [finding for finding in findings if finding.severity != "error"]
    expectedNumbers = numberAtoms("\n".join(task["facts"]))
    actualNumbers = numberAtoms(output)
    missingLiterals = [literal for literal in task["mustInclude"] if literal not in output]
    forbiddenHits = [literal for literal in task["forbidden"] if literal in output]
    minimum, maximum = task["length"]
    characterCount = len(output)
    missingNumbers = sorted(expectedNumbers - actualNumbers)
    extraNumbers = sorted(actualNumbers - expectedNumbers)
    factSurfacePass = not missingLiterals and not forbiddenHits and not missingNumbers and not extraNumbers
    return {
        "taskId": task["id"],
        "condition": response["condition"],
        "outputSha256": response["outputSha256"],
        "characterCount": characterCount,
        "lengthPass": minimum <= characterCount <= maximum,
        "factSurfacePass": factSurfacePass,
        "missingLiterals": missingLiterals,
        "forbiddenHits": forbiddenHits,
        "missingNumbers": missingNumbers,
        "extraNumbers": extraNumbers,
        "errorCount": len(errors),
        "noticeCount": len(notices),
        "errorRules": dict(sorted(Counter(finding.rule for finding in errors).items())),
        "noticeRules": dict(sorted(Counter(finding.rule for finding in notices).items())),
        "audit": {
            "sentenceCount": audit.sentenceCount,
            "paragraphCount": audit.paragraphCount,
            "sectionCount": audit.sectionCount,
            "wordCount": audit.wordCount,
            "typeTokenRatio": audit.lexicon.typeTokenRatio,
            "burstiness": audit.rhythm.burstiness,
            "commaRatio": audit.commaRatio,
            "shortParagraphRatio": audit.shortParagraphRatio,
            "endingMix": [list(item) for item in audit.endingMix],
        },
    }


def scoreAutomatic(manifest: dict, responses: dict) -> dict:
    tasks = {task["id"]: task for task in manifest["tasks"]}
    results = [automaticResult(tasks[item["taskId"]], item) for item in responses["responses"]]
    return {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "responsesSha256": responses["rawResponseSha256"],
        "results": results,
        "contentSha256": sha256Text(stableJson(results)),
    }


def judgePrompt(task: dict, outputA: str, outputB: str) -> str:
    facts = "\n".join(f"- {fact}" for fact in task["facts"])
    return f"""두 한국어 글을 조건 이름과 작성법을 모른 채 비교하라. 길이나 화려함 하나로 고르지 말고 각 항목을 따로 판정한다.

사실 보존: 제공 사실을 빠뜨리거나 관계를 바꾸거나 새 사실을 더하지 않았는가.
과업 효용: 독자 {task["reader"]}가 {task["task"]}라는 일을 실제로 마칠 수 있는가.
자연스러운 한국어: 번역투, 상투구, 과도한 접속어와 쉼표, 같은 문장 틀의 반복 없이 사람이 다듬은 글처럼 읽히는가.
조직: 도입, 전개, 마무리가 글 종류 {task["preset"]}와 독자의 읽는 순서에 맞는가.
간결성: 필요한 사실과 행동은 남기되 중복, 메타 설명, 빈 예고가 없는가.
종합: 사실을 잃은 글은 문체가 좋아도 우선하지 않는다. 차이가 확실하지 않으면 tie를 고른다.

허용된 사실:
{facts}

금지된 주장:
{", ".join(task["forbidden"])}

<글 A>
{outputA}
</글 A>

<글 B>
{outputB}
</글 B>

지정된 JSON 필드만 출력하라. note에는 가장 결정적인 근거를 한국어 한 문장으로 쓴다."""


def judgmentKey(item: dict) -> tuple[str, str, int, bool]:
    return item["taskId"], item["candidate"], item["seed"], item["swapped"]


def loadJudgmentCheckpoint(output: Path, manifest: dict, responses: dict, modelInfo: dict) -> dict:
    if not output.exists():
        return {
            "version": 1,
            "complete": False,
            "manifestSha256": manifest["contentSha256"],
            "responsesSha256": responses["rawResponseSha256"],
            "judge": {
                "kind": "ollama",
                "model": modelInfo,
                "think": False,
                "seeds": list(JUDGE_SEEDS),
                "options": JUDGE_OPTIONS,
                "orderSwap": True,
                "blindConditionLabels": True,
                "sameModelAsGenerator": modelInfo.get("digest") == responses["runner"]["model"].get("digest"),
            },
            "judgments": [],
        }
    checkpoint = readJson(output)
    if checkpoint.get("responsesSha256") != responses["rawResponseSha256"]:
        raise ValueError("기존 판정의 원시 응답 hash가 현재 응답과 다르다")
    if checkpoint.get("judge", {}).get("model", {}).get("digest") != modelInfo.get("digest"):
        raise ValueError("기존 판정의 모델 digest가 현재 판정 모델과 다르다")
    return checkpoint


def runJudgments(
    manifest: dict,
    responses: dict,
    model: str,
    endpoint: str,
    timeout: int,
    output: Path,
) -> dict:
    modelInfo = ollamaInfo(endpoint, model, timeout)
    checkpoint = loadJudgmentCheckpoint(output, manifest, responses, modelInfo)
    seen = {judgmentKey(item) for item in checkpoint["judgments"]}
    tasks = {task["id"]: task for task in manifest["tasks"]}
    responseMap = {responseKey(item): item["output"] for item in responses["responses"]}
    schedule = [
        (taskId, candidate, seed, swapped)
        for taskId in tasks
        for candidate in COMPARISON_CONDITIONS
        for seed in JUDGE_SEEDS
        for swapped in (False, True)
    ]
    for taskId, candidate, seed, swapped in schedule:
        key = (taskId, candidate, seed, swapped)
        if key in seen:
            continue
        baselineOutput = responseMap[(taskId, "plainBrief")]
        candidateOutput = responseMap[(taskId, candidate)]
        outputA, outputB = (candidateOutput, baselineOutput) if swapped else (baselineOutput, candidateOutput)
        prompt = judgePrompt(tasks[taskId], outputA, outputB)
        options = {**JUDGE_OPTIONS, "seed": seed}
        raw, metrics = ollamaGenerate(prompt, model, endpoint, timeout, options, JUDGE_SCHEMA)
        try:
            decision = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"{taskId} {candidate}의 판정 JSON을 읽지 못했다: {raw}") from error
        checkpoint["judgments"].append(
            {
                "taskId": taskId,
                "candidate": candidate,
                "seed": seed,
                "swapped": swapped,
                "aIs": candidate if swapped else "plainBrief",
                "bIs": "plainBrief" if swapped else candidate,
                "promptSha256": sha256Text(prompt),
                "decision": decision,
                "rawSha256": sha256Text(raw),
                "metrics": metrics,
            }
        )
        seen.add(key)
        writeJson(output, checkpoint)
        print(f"판정 {len(seen)}/{len(schedule)}: {taskId} {candidate} seed={seed} swap={swapped}", flush=True)
    if seen != set(schedule):
        raise ValueError("판정 키가 완전하지 않다")
    checkpoint["complete"] = True
    checkpoint["judgmentSha256"] = sha256Text(stableJson(checkpoint["judgments"]))
    writeJson(output, checkpoint)
    return checkpoint


def mappedPreference(judgment: dict, dimension: str) -> str:
    selected = judgment["decision"][dimension]
    if selected == "tie":
        return "tie"
    return judgment["aIs"] if selected == "A" else judgment["bIs"]


def consensusPreference(items: list[dict], dimension: str, candidate: str) -> str:
    mapped = [mappedPreference(item, dimension) for item in items]
    if all(value == candidate for value in mapped):
        return "candidate"
    if all(value == "plainBrief" for value in mapped):
        return "baseline"
    return "unstableOrTie"


def pairOutcome(pair: dict, baselineAuto: dict, candidateAuto: dict) -> str:
    if pair["consensus"]["overall"] == "candidate":
        if candidateAuto["factSurfacePass"] and candidateAuto["errorCount"] <= baselineAuto["errorCount"]:
            return "candidate"
        return "unsafeCandidate"
    if pair["consensus"]["overall"] == "baseline":
        if baselineAuto["factSurfacePass"] and baselineAuto["errorCount"] <= candidateAuto["errorCount"]:
            return "baseline"
        return "unsafeBaseline"
    return "unstableOrTie"


def scoreAll(manifest: dict, responses: dict, automatic: dict, judgments: dict) -> dict:
    autoMap = {(item["taskId"], item["condition"]): item for item in automatic["results"]}
    grouped: dict[tuple[str, str], list[dict]] = {}
    for item in judgments["judgments"]:
        grouped.setdefault((item["taskId"], item["candidate"]), []).append(item)
    dimensions = ("factFidelity", "taskUtility", "naturalKorean", "organization", "concision", "overall")
    pairs = []
    for (taskId, candidate), items in sorted(grouped.items()):
        if len(items) != len(JUDGE_SEEDS) * 2:
            raise ValueError(f"{taskId} {candidate} 판정이 네 개가 아니다")
        pair = {
            "taskId": taskId,
            "candidate": candidate,
            "consensus": {dimension: consensusPreference(items, dimension, candidate) for dimension in dimensions},
        }
        pair["safeOutcome"] = pairOutcome(
            pair,
            autoMap[(taskId, "plainBrief")],
            autoMap[(taskId, candidate)],
        )
        pairs.append(pair)
    conditionSummary = {}
    for condition in CONDITIONS:
        selected = [item for item in automatic["results"] if item["condition"] == condition]
        paired = [item for item in pairs if item["candidate"] == condition]
        conditionSummary[condition] = {
            "outputs": len(selected),
            "factSurfacePass": sum(item["factSurfacePass"] for item in selected),
            "lengthPass": sum(item["lengthPass"] for item in selected),
            "errorFree": sum(item["errorCount"] == 0 for item in selected),
            "errors": sum(item["errorCount"] for item in selected),
            "meanCharacters": round(sum(item["characterCount"] for item in selected) / len(selected), 1),
            "meanCommaRatio": round(sum(item["audit"]["commaRatio"] for item in selected) / len(selected), 4),
            "meanBurstiness": round(sum(item["audit"]["burstiness"] for item in selected) / len(selected), 4),
            "safeWins": sum(item["safeOutcome"] == "candidate" for item in paired),
            "safeLosses": sum(item["safeOutcome"] == "baseline" for item in paired),
            "unsafePreferences": sum(item["safeOutcome"].startswith("unsafe") for item in paired),
            "unstableOrTies": sum(item["safeOutcome"] == "unstableOrTie" for item in paired),
            "naturalKoreanConsensusWins": sum(item["consensus"]["naturalKorean"] == "candidate" for item in paired),
            "taskUtilityConsensusWins": sum(item["consensus"]["taskUtility"] == "candidate" for item in paired),
        }
    payload = {
        "version": 1,
        "manifestSha256": manifest["contentSha256"],
        "responsesSha256": responses["rawResponseSha256"],
        "automaticSha256": automatic["contentSha256"],
        "judgmentSha256": judgments["judgmentSha256"],
        "judgeLimitation": "생성기와 판정기가 같은 qwen3:8b digest라 교차 모델 또는 사람 평가가 아니다",
        "conditionSummary": conditionSummary,
        "pairs": pairs,
    }
    payload["contentSha256"] = sha256Text(stableJson(payload))
    return payload


def renderScore(score: dict) -> str:
    lines = ["완성 글 조건별 집계", ""]
    for condition in CONDITIONS:
        item = score["conditionSummary"][condition]
        pairText = ""
        if condition != "plainBrief":
            pairText = (
                f", 안전 승/패 {item['safeWins']}/{item['safeLosses']}, 불안정·무승부 {item['unstableOrTies']}, "
                f"안전 가드 탈락 선호 {item['unsafePreferences']}"
            )
        lines.append(
            f"{condition}: 사실 표면 {item['factSurfacePass']}/{item['outputs']}, 길이 {item['lengthPass']}/"
            f"{item['outputs']}, error 0 {item['errorFree']}/{item['outputs']}, error {item['errors']}건, "
            f"평균 {item['meanCharacters']}자, 쉼표 문장 {item['meanCommaRatio']}, burstiness {item['meanBurstiness']}"
            f"{pairText}"
        )
    lines.extend(
        [
            "",
            "안전 승패는 plainBrief와 견준 네 블라인드 판정이 모두 같은 쪽이고, 후보가 사실 표면 가드를 통과하며,",
            "hanlint error가 baseline보다 늘지 않은 경우만 센다.",
            f"판정 한계: {score['judgeLimitation']}",
            f"score SHA256: {score['contentSha256']}",
        ]
    )
    return "\n".join(lines)


def selfTest() -> None:
    manifest = buildManifest()
    assert len(manifest["tasks"]) == 7
    assert manifest["conditions"] == list(CONDITIONS)
    for task in manifest["tasks"]:
        assert set(task["prompts"]) == set(INITIAL_CONDITIONS)
        assert task["preset"] in {"blog", "report", "docs", "guide", "essay", "fiction", "encyclopedia"}
        assert task["mustInclude"] and task["facts"]
    sample = {
        "taskId": manifest["tasks"][0]["id"],
        "condition": "plainBrief",
        "output": "숫자는 200 mL와 8장이다.",
        "outputSha256": sha256Text("숫자는 200 mL와 8장이다."),
    }
    result = automaticResult(manifest["tasks"][0], sample)
    assert not result["factSurfacePass"] and result["missingLiterals"]
    candidate = "rulePrompt"
    decisions = []
    for seed in JUDGE_SEEDS:
        for swapped in (False, True):
            decisions.append(
                {
                    "taskId": "test",
                    "candidate": candidate,
                    "seed": seed,
                    "swapped": swapped,
                    "aIs": candidate if swapped else "plainBrief",
                    "bIs": "plainBrief" if swapped else candidate,
                    "decision": {dimension: "A" if swapped else "B" for dimension in JUDGE_SCHEMA["required"][:-1]}
                    | {"note": "후보가 낫다."},
                }
            )
    assert consensusPreference(decisions, "overall", candidate) == "candidate"


def parseArgs(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="완성 글에서 hanlint 작문 계약의 실제 향상을 잰다")
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--output", type=Path, required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("manifest", type=Path)
    generate.add_argument("--model", required=True)
    generate.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    generate.add_argument("--timeout", type=int, default=300)
    generate.add_argument("--output", type=Path, required=True)
    auto = subparsers.add_parser("score-auto")
    auto.add_argument("manifest", type=Path)
    auto.add_argument("responses", type=Path)
    auto.add_argument("--output", type=Path, required=True)
    judge = subparsers.add_parser("judge")
    judge.add_argument("manifest", type=Path)
    judge.add_argument("responses", type=Path)
    judge.add_argument("--model", required=True)
    judge.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    judge.add_argument("--timeout", type=int, default=300)
    judge.add_argument("--output", type=Path, required=True)
    score = subparsers.add_parser("score")
    score.add_argument("manifest", type=Path)
    score.add_argument("responses", type=Path)
    score.add_argument("automatic", type=Path)
    score.add_argument("judgments", type=Path)
    score.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        selfTest()
        print("writingLift self-test 통과")
        return 0
    args = parseArgs(argv)
    if args.command == "prepare":
        manifest = buildManifest()
        writeJson(args.output, manifest)
        print(f"{args.output}에 사실 고정 과제 {len(manifest['tasks'])}개를 썼다")
    elif args.command == "generate":
        runGeneration(readJson(args.manifest), args.model, args.endpoint, args.timeout, args.output)
        print(f"원시 응답 SHA256: {sha256File(args.output)}")
    elif args.command == "score-auto":
        automatic = scoreAutomatic(readJson(args.manifest), readJson(args.responses))
        writeJson(args.output, automatic)
        print(f"자동 측정 SHA256: {sha256File(args.output)}")
    elif args.command == "judge":
        runJudgments(
            readJson(args.manifest),
            readJson(args.responses),
            args.model,
            args.endpoint,
            args.timeout,
            args.output,
        )
        print(f"판정 SHA256: {sha256File(args.output)}")
    else:
        score = scoreAll(
            readJson(args.manifest),
            readJson(args.responses),
            readJson(args.automatic),
            readJson(args.judgments),
        )
        writeJson(args.output, score)
        print(renderScore(score))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
