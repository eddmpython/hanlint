"""OpenDART 에서 사업보고서 원본을 받아 본문 문단만 글로 떨군다. 용례 엔진 (usage) 의 report 말뭉치 재료다.

무엇을 받나: 공시검색 (list.json, pblntf_detail_ty=A001 사업보고서) 으로 접수번호를 모으고, 공시서류원본파일
(document.xml) 의 zip 에서 본문 XML (14자리 접수번호.xml) 을 읽는다. 표 (`<TABLE>`) 는 통째로 빼고 `<P>` 문단의 글만
남긴다. 표의 칸은 문장이 아니고, 제목과 각주 (※) 는 문장이 아닌 것이 많아 뒤에서 문장 꼴로 거른다.

어디에 두나: `~/.cache/hanlint/corpus/dart/<접수번호>.txt` (문단 하나가 한 줄) 와 `manifest.json` (접수번호, 회사, 접수일,
보고서 이름, 문단 수, sha256). 저장소 안에는 두지 않는다. 키는 환경 변수 DART_API_KEY 로만 받는다.

라이선스 (2026-09-19 확인, https://opendart.fss.or.kr/intro/terms.do): 제16조 ① "금융감독원이 제공하는 오픈API 서비스 및
관련 프로그램의 저작권은 금융감독원에 있습니다", 제23조 ① "서비스에서 제공되는 공시정보는 공시제출인의 책임 하에
작성되었으며", 제16조 ④ "약관에 명시되지 않은 저작권과 관련된 사항은 저작권법 및 공공데이터법에 따릅니다". 재배포를
허용하는 조항도 금지하는 조항도 없다. 그래서 hanlint 는 이 문장을 패키지에 싣지 않고 (사용자 기계 색인만), 통계인
빈도표만 싣는다. 출처는 접수번호와 DART 주소로 남긴다.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Iterator
from pathlib import Path

API = "https://opendart.fss.or.kr/api"
DETAIL_TYPE = "A001"
"""공시 상세 유형. A001 은 사업보고서다."""
PAGE_COUNT = 100
PAUSE_SECONDS = 0.2
"""요청 사이 쉼. 하루 20,000회 한도와 무관하게 서버를 두드리지 않는 예의다."""
MIN_PARAGRAPH = 15
TABLE = re.compile(r"<TABLE\b.*?</TABLE>", re.S | re.I)
PARAGRAPH = re.compile(r"<P\b[^>]*>(.*?)</P>", re.S | re.I)
BREAK = re.compile(r"<BR\s*/?>", re.I)
BOLD = re.compile(r"<SPAN\b[^>]*USERMARK=\"B\"[^>]*>(.*?)</SPAN>", re.S | re.I)
"""굵은 SPAN 은 `다. 최대주주의 변동` 같은 작은 제목이라 본문과 한 문단이 아니다. 줄로 갈라 둔다."""
TAG = re.compile(r"<[^>]+>")
KOREAN = re.compile(r"[가-힣]")
MAIN_XML = re.compile(r"^\d{14}\.xml$")


def defaultRoot() -> Path:
    return Path.home() / ".cache" / "hanlint" / "corpus" / "dart"


def readCorpus(root: Path, limit: int | None = None) -> Iterator[tuple[str, str]]:
    """받아 둔 보고서를 (접수번호, 글) 로 접수번호 순서대로. measure 와 derive 스크립트가 같은 순서로 읽는다."""
    for index, path in enumerate(sorted(root.glob("*.txt"))):
        if limit is not None and index >= limit:
            break
        yield path.stem, path.read_text(encoding="utf-8")


def apiKey() -> str:
    key = os.environ.get("DART_API_KEY", "").strip()
    if not key:
        raise SystemExit("DART_API_KEY 환경 변수가 없다. OpenDART 에서 발급한 키를 환경 변수로만 준다 (파일에 적지 않는다)")
    return key


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def listFilings(key: str, begin: str, end: str, count: int) -> list[dict]:
    """접수번호 목록. 회사마다 하나만 (같은 회사의 정정 보고서는 뒤의 것을 버린다)."""
    found: list[dict] = []
    seen: set[str] = set()
    page = 1
    while len(found) < count:
        query = urllib.parse.urlencode(
            {
                "crtfc_key": key,
                "pblntf_detail_ty": DETAIL_TYPE,
                "bgn_de": begin,
                "end_de": end,
                "page_no": page,
                "page_count": PAGE_COUNT,
            }
        )
        data = json.loads(fetch(f"{API}/list.json?{query}").decode("utf-8"))
        if data.get("status") != "000":
            raise SystemExit(f"OpenDART 목록 실패: {data.get('status')} {data.get('message')}")
        items = data.get("list", [])
        if not items:
            break
        for item in items:
            if item["corp_code"] in seen or "사업보고서" not in item["report_nm"]:
                continue
            seen.add(item["corp_code"])
            found.append(item)
            if len(found) >= count:
                break
        if page >= int(data.get("total_page", 1)):
            break
        page += 1
        time.sleep(PAUSE_SECONDS)
    return found


def decodeXml(raw: bytes) -> str:
    head = raw[:200].decode("ascii", errors="ignore").lower()
    encoding = "cp949" if "euc-kr" in head or "cp949" in head or "ks_c_5601" in head else "utf-8"
    return raw.decode(encoding, errors="replace")


def paragraphsOf(document: str) -> list[str]:
    """표를 뺀 본문의 문단. 태그를 벗기고 엔티티를 풀고 공백을 하나로 모은다."""
    body = TABLE.sub(" ", document)
    paragraphs = []
    for inner in PARAGRAPH.findall(body):
        for piece in BOLD.sub("\n\\1\n", BREAK.sub("\n", inner)).split("\n"):
            text = re.sub(r"\s+", " ", html.unescape(TAG.sub("", piece))).strip()
            if len(text) >= MIN_PARAGRAPH and KOREAN.search(text):
                paragraphs.append(text)
    return paragraphs


def mainDocument(archive: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        names = [info.filename for info in bundle.infolist() if MAIN_XML.match(info.filename)]
        if not names:
            raise ValueError("zip 에 본문 XML (접수번호.xml) 이 없다")
        return decodeXml(bundle.read(names[0]))


def download(key: str, filings: list[dict], root: Path) -> list[dict]:
    root.mkdir(parents=True, exist_ok=True)
    manifestPath = root / "manifest.json"
    manifest: dict[str, dict] = {}
    if manifestPath.exists():
        manifest = {entry["rcept_no"]: entry for entry in json.loads(manifestPath.read_text(encoding="utf-8"))["documents"]}
    for index, filing in enumerate(filings, 1):
        rceptNo = filing["rcept_no"]
        target = root / f"{rceptNo}.txt"
        if rceptNo in manifest and target.exists():
            continue
        query = urllib.parse.urlencode({"crtfc_key": key, "rcept_no": rceptNo})
        try:
            paragraphs = paragraphsOf(mainDocument(fetch(f"{API}/document.xml?{query}")))
        except (ValueError, zipfile.BadZipFile) as error:
            print(f"{rceptNo} {filing['corp_name']}: 건너뜀 ({error})", file=sys.stderr)
            continue
        text = "\n".join(paragraphs) + "\n"
        target.write_text(text, encoding="utf-8", newline="\n")
        manifest[rceptNo] = {
            "rcept_no": rceptNo,
            "corp_name": filing["corp_name"],
            "corp_code": filing["corp_code"],
            "rcept_dt": filing["rcept_dt"],
            "report_nm": filing["report_nm"],
            "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcptNo={rceptNo}",
            "paragraphs": len(paragraphs),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        manifestPath.write_text(
            json.dumps(
                {"source": "OpenDART document.xml", "detailType": DETAIL_TYPE, "documents": list(manifest.values())},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"{index}/{len(filings)} {rceptNo} {filing['corp_name']} 문단 {len(paragraphs)}", file=sys.stderr)
        time.sleep(PAUSE_SECONDS)
    return list(manifest.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--count", type=int, default=300, help="받을 회사 수. 기본 300")
    parser.add_argument("--begin", default="20260301", help="접수일 시작 (YYYYMMDD)")
    parser.add_argument("--end", default="20260430", help="접수일 끝 (YYYYMMDD)")
    parser.add_argument("--output", type=Path, default=defaultRoot(), help="받을 폴더. 기본 ~/.cache/hanlint/corpus/dart")
    args = parser.parse_args()
    key = apiKey()
    filings = listFilings(key, args.begin, args.end, args.count)
    documents = download(key, filings, args.output)
    print(f"{len(documents)}편, 문단 {sum(item['paragraphs'] for item in documents):,}개 → {args.output}")


if __name__ == "__main__":
    main()
