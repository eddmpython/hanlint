"""기준 말뭉치를 카탈로그대로 고정하고 저장소 밖에 받는다.

자료원과 선택 조건은 corpus/catalogue.toml, 선택된 문서의 판본과 해시는
corpus/documents.json 이 소유한다. 임시 다운로드는 공통 실행 공간만 쓴다.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[1]
CATALOGUE_PATH = REPO / "corpus" / "catalogue.toml"
USER_AGENT = "hanlint-corpus/0.0.7 corpus research contact github.com/eddmpython/hanlint"
KOREAN = re.compile(r"[가-힣]")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
REF = re.compile(r"<ref\b[^>]*>.*?</ref\s*>|<ref\b[^>]*/\s*>", re.DOTALL | re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
LINK = re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]|\[\[([^\]]+)\]\]")
EXTERNAL_LINK = re.compile(r"\[https?://\S+\s+([^\]]+)\]")
HEADING = re.compile(r"^(=+)\s*(.*?)\s*\1\s*$")
WIKI_LIST = re.compile(r"^(#+)\s*(.*)$")
HUGO_HEADING = re.compile(r'^[ \t]*\{\{[%<][ \t]*heading[ \t]+"([^"]+)"[ \t]*[%>]\}\}[ \t]*$', re.MULTILINE)
HUGO_TOOLTIP = re.compile(r"\{\{<\s*glossary_tooltip\s+([^>]+)>\}\}")
HUGO_TEXT = re.compile(r'\btext="([^"]+)"')
HUGO_SHORTCODE = re.compile(r"\{\{[%<].*?[%>]\}\}")
# 도표 본문은 산문이 아니다. 실측: `flowchart LR subgraph ...` 가 문장으로 세어졌다 (2026-08-29).
HUGO_MERMAID = re.compile(r"\{\{<\s*mermaid\s*>\}\}.*?\{\{<\s*/mermaid\s*>\}\}", re.DOTALL)
HUGO_ANCHOR = re.compile(r"[ \t]+\{#[^}\r\n]+\}[ \t]*$", re.MULTILINE)
FRONTMATTER = re.compile(r"\A---\n.*?\n---\s*\n", re.DOTALL)
HUGO_HEADINGS = {
    "cleanup": "정리",
    "objectives": "목표",
    "prerequisites": "시작하기 전에",
    "whatsnext": "다음 내용",
}
STRUCTURAL_LINE = re.compile(r"(?:#{1,6}\s|[-*+>|\[]|\d+[.)]\s)")
METADATA_HEADINGS = {"라이선스", "주석 및 라이선스"}


@dataclass(frozen=True)
class RawDocument:
    sourceId: str
    type: str
    preset: str
    title: str
    sourcePath: str
    revision: str
    url: str
    license: str
    licenseUrl: str
    owner: str
    raw: str


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def readCatalogue() -> dict:
    with CATALOGUE_PATH.open("rb") as file:
        return tomllib.load(file)


def manifestPath(catalogue: dict) -> Path:
    return REPO / catalogue["corpus"]["manifest"]


def corpusRoot(catalogue: dict) -> Path:
    return (REPO / catalogue["corpus"]["root"]).resolve()


def request(url: str) -> bytes:
    asked = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(asked, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 503) or attempt == 5:
                raise
            retryAfter = int(error.headers.get("Retry-After", "0") or "0")
            time.sleep(min(max(retryAfter, 2**attempt), 20))
    raise RuntimeError("자료원 요청 재시도에서 빠져나왔다")


def requestJson(url: str, params: dict[str, str]) -> dict:
    return json.loads(request(url + "?" + urllib.parse.urlencode(params)).decode("utf-8"))


def koreanChars(text: str) -> int:
    return len(KOREAN.findall(text))


def evenly(items: list[RawDocument], limit: int) -> list[RawDocument]:
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[0]]
    return [items[round(index * (len(items) - 1) / (limit - 1))] for index in range(limit)]


def matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or PurePosixPath(path).match(pattern)


def archiveDocuments(source: dict) -> list[RawDocument]:
    archive = BytesIO(request(source["archive"]))
    found: list[RawDocument] = []
    with zipfile.ZipFile(archive) as zipped:
        names = sorted(name for name in zipped.namelist() if not name.endswith("/"))
        prefix = names[0].split("/", 1)[0] + "/"
        for collection in source["collection"]:
            patterns = [collection["include"], *collection.get("alsoInclude", [])]
            excludes = collection.get("exclude", [])
            candidates: list[RawDocument] = []
            for name in names:
                path = name.removeprefix(prefix)
                if not any(matches(path, pattern) for pattern in patterns):
                    continue
                if any(matches(path, pattern) for pattern in excludes):
                    continue
                raw = zipped.read(name).decode("utf-8")
                if koreanChars(raw) < collection["minimumKoreanChars"]:
                    continue
                publicPath = path.removeprefix("content/ko/").removesuffix(".md").removesuffix("/_index")
                candidates.append(
                    RawDocument(
                        sourceId=source["id"],
                        type=collection["type"],
                        preset=collection["preset"],
                        title=frontmatterTitle(raw) or Path(path).stem,
                        sourcePath=path,
                        revision=source["revision"],
                        url=f"{source['home'].rstrip('/')}/{publicPath.strip('/')}/",
                        license=source["license"],
                        licenseUrl=source["licenseUrl"],
                        owner=source["owner"],
                        raw=raw,
                    )
                )
            found.extend(evenly(candidates, collection["limit"]))
    return found


def frontmatterTitle(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    for line in text[4:end].splitlines():
        if line.startswith("title:"):
            return line.partition(":")[2].strip().strip("'\"")
    return None


def categoryMembers(source: dict) -> list[dict]:
    """분류 하나 또는 여럿 (categories) 의 문서. 여러 분류에 든 문서는 한 번만 센다."""
    byId: dict[int, dict] = {}
    for category in source.get("categories") or [source["category"]]:
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": category,
            "cmnamespace": "0",
            "cmlimit": "500",
        }
        while True:
            data = requestJson(source["api"], params)
            for item in data["query"]["categorymembers"]:
                byId.setdefault(item["pageid"], item)
            if "continue" not in data:
                break
            params["cmcontinue"] = data["continue"]["cmcontinue"]
    return sorted(byId.values(), key=lambda item: item["title"])


def batches(items: list[int], size: int = 40) -> Iterable[list[int]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def mediaWikiDocuments(source: dict) -> list[RawDocument]:
    members = categoryMembers(source)
    byId = {item["pageid"]: item for item in members}
    candidates: list[RawDocument] = []
    for batch in batches(list(byId)):
        time.sleep(0.25)
        data = requestJson(
            source["api"],
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "revisions",
                "pageids": "|".join(str(pageId) for pageId in batch),
                "rvprop": "ids|timestamp|content",
                "rvslots": "main",
            },
        )
        for page in data["query"]["pages"]:
            revision = page["revisions"][0]
            raw = revision["slots"]["main"]["content"]
            normalized = normalizeWikitext(raw)
            if raw.lstrip().lower().startswith(("#redirect", "#넘겨주기")):
                continue
            if koreanChars(normalized) < source["minimumKoreanChars"]:
                continue
            title = page["title"]
            oldId = str(revision["revid"])
            candidates.append(
                RawDocument(
                    sourceId=source["id"],
                    type=source["type"],
                    preset=source["preset"],
                    title=title,
                    sourcePath=str(page["pageid"]),
                    revision=oldId,
                    url=f"{source['home'].rstrip('/')}/w/index.php?title={urllib.parse.quote(title)}&oldid={oldId}",
                    license=source["license"],
                    licenseUrl=source["licenseUrl"],
                    owner=source["owner"],
                    raw=raw,
                )
            )
    if source.get("preferUnwrapped"):
        candidates.sort(key=lambda doc: (wrappedLineRatio(doc.raw), doc.title))
        candidates = candidates[: source["limit"]]
        return sorted(candidates, key=lambda doc: doc.title)
    return evenly(sorted(candidates, key=lambda doc: doc.title), source["limit"])


def gitHubTree(source: dict) -> list[dict]:
    """자료원의 treePath 아래 파일 목록 (path, size). 목록 두 번이면 되므로 인증 없는 API 한도 (시간당 60) 안이다."""
    parent, _, name = source["treePath"].rpartition("/")
    listing = requestJson(f"https://api.github.com/repos/{source['repo']}/contents/{parent}", {"ref": source["revision"]})
    treeSha = next(item["sha"] for item in listing if item["name"] == name)
    tree = requestJson(f"https://api.github.com/repos/{source['repo']}/git/trees/{treeSha}", {"recursive": "1"})
    if tree.get("truncated"):
        raise ValueError(f"{source['id']} 의 파일 나무가 잘렸다. treePath 를 좁힌다")
    return sorted((item for item in tree["tree"] if item["type"] == "blob"), key=lambda item: item["path"])


def gitHubRaw(source: dict, path: str) -> str:
    time.sleep(0.1)
    return request(source["raw"].rstrip("/") + "/" + urllib.parse.quote(path)).decode("utf-8")


def gitHubTreeDocuments(source: dict) -> list[RawDocument]:
    """수집 조건마다 경로를 고르게 뽑아 원문을 받고 한글 글자 수로 거른다. 한도의 1.3배를 받아 거른 뒤 한도로 줄인다."""
    files = [item["path"] for item in gitHubTree(source)]
    found: list[RawDocument] = []
    for collection in source["collection"]:
        patterns = [collection["include"], *collection.get("alsoInclude", [])]
        excludes = collection.get("exclude", [])
        paths = [p for p in files if any(matches(p, x) for x in patterns) and not any(matches(p, x) for x in excludes)]
        wanted = [p for p in evenly(paths, int(collection["limit"] * 1.3) + 1)]
        candidates: list[RawDocument] = []
        for path in wanted:
            raw = gitHubRaw(source, path)
            if koreanChars(normalizeMdn(raw) if source.get("normalizer") == "mdn" else raw) < collection["minimumKoreanChars"]:
                continue
            candidates.append(
                RawDocument(
                    sourceId=source["id"],
                    type=collection["type"],
                    preset=collection["preset"],
                    title=frontmatterTitle(raw) or Path(path).parent.name,
                    sourcePath=path,
                    revision=source["revision"],
                    url=f"{source['home'].rstrip('/')}/{path.removesuffix('/index.md').removesuffix('.md')}",
                    license=source["license"],
                    licenseUrl=source["licenseUrl"],
                    owner=source["owner"],
                    raw=raw,
                )
            )
        found.extend(evenly(candidates, collection["limit"]))
    return found


def gitHubTreeRaw(source: dict, entries: list[dict]) -> dict[str, str]:
    return {entry["sourcePath"]: gitHubRaw(source, entry["sourcePath"]) for entry in entries}


def wrappedLineRatio(text: str) -> float:
    """문장 부호 없이 이어지는 일반 본문 줄의 비율을 센다."""
    normalized = normalizeWikitext(text)
    lines = [line.strip() for line in normalized.splitlines()]
    pairs = 0
    wrapped = 0
    for before, after in zip(lines, lines[1:], strict=False):
        if not before or not after or STRUCTURAL_LINE.match(before) or STRUCTURAL_LINE.match(after):
            continue
        pairs += 1
        if before[-1] not in ".!?。！？:;)]}'\"":
            wrapped += 1
    return wrapped / pairs if pairs else 0.0


FILE_LINK_HEADS = ("[[파일:", "[[File:", "[[그림:", "[[Image:", "[[미디어:", "[[Media:")
EMPTY_BULLETS = frozenset({"*", "**", "***", "#", "##", "-"})


def stripFileLinks(text: str) -> str:
    """그림과 파일 링크를 통째로 뺀다. 설명에 링크가 겹쳐 들어 있어 (`[[파일:X|섬네일|[[원각사]]의 사진]]`) 괄호 깊이를 센다.

    실측: 말뭉치에 `섬네일|upright=1.2|left|alt=...` 와 `250px|섬네일|...` 가 문장으로 새어 들었다 (2026-08-29).
    """
    out: list[str] = []
    position = 0
    while True:
        starts = [text.find(head, position) for head in FILE_LINK_HEADS]
        starts = [at for at in starts if at >= 0]
        if not starts:
            out.append(text[position:])
            return "".join(out)
        start = min(starts)
        out.append(text[position:start])
        depth = 0
        cursor = start
        while cursor < len(text):
            if text.startswith("[[", cursor):
                depth += 1
                cursor += 2
            elif text.startswith("]]", cursor):
                depth -= 1
                cursor += 2
                if depth == 0:
                    break
            else:
                cursor += 1
        position = cursor


def normalizeWikitext(text: str) -> str:
    text = COMMENT.sub("", text)
    text = REF.sub("", text)
    text = stripFileLinks(text)
    previous = None
    while previous != text:
        previous = text
        text = TEMPLATE.sub("", text)

    def linkText(match: re.Match[str]) -> str:
        return match.group(2) or match.group(3) or ""

    lines: list[str] = []
    text = LINK.sub(linkText, text)
    text = EXTERNAL_LINK.sub(r"\1", text)
    text = TAG.sub("", text)
    text = text.replace("'''", "").replace("''", "")
    inTable = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("{|"):
            inTable = True
            continue
        if stripped.startswith("|}"):
            inTable = False
            continue
        # 링크 치환 뒤라 [[분류:X]] 는 분류:X 로 남아 있다. 어느 꼴이든 본문이 아니다 (실측: 마지막 문단에 분류 줄이 새어 들었다).
        if inTable or stripped.startswith(("[[분류:", "[[Category:", "분류:", "Category:")):
            continue
        if stripped in EMPTY_BULLETS:
            # 각주 틀만 있던 목록 항목은 틀을 빼면 빈 불릿이다. 본문이 아니다.
            continue
        heading = HEADING.match(stripped)
        if heading:
            if heading.group(2) in METADATA_HEADINGS:
                break
            level = min(len(heading.group(1)), 6)
            lines.append("#" * level + " " + heading.group(2))
            continue
        wikiList = WIKI_LIST.match(stripped)
        if wikiList:
            lines.append("  " * (len(wikiList.group(1)) - 1) + "1. " + wikiList.group(2))
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def normalizeNewlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalizeKubernetes(text: str) -> str:
    text = normalizeNewlines(text)
    text = FRONTMATTER.sub("", text)
    text = HUGO_HEADING.sub(lambda match: "## " + HUGO_HEADINGS.get(match.group(1), match.group(1)), text)

    def tooltipText(match: re.Match[str]) -> str:
        textAttribute = HUGO_TEXT.search(match.group(1))
        return textAttribute.group(1) if textAttribute else ""

    text = HUGO_TOOLTIP.sub(tooltipText, text)
    text = HUGO_MERMAID.sub("", text)
    text = HUGO_SHORTCODE.sub("", text)
    text = HUGO_ANCHOR.sub("", text)
    return text.strip() + "\n"


def normalizeMdn(text: str) -> str:
    """MDN 마크다운. frontmatter 와 매크로 ({{domxref("X")}}, {{Compat}}) 를 뺀다. 매크로는 본문 글자가 아니다."""
    text = normalizeNewlines(text)
    text = FRONTMATTER.sub("", text)
    previous = None
    while previous != text:
        previous = text
        text = TEMPLATE.sub("", text)
    return text.strip() + "\n"


NORMALIZERS = {
    "wikitext": normalizeWikitext,
    "kubernetes": normalizeKubernetes,
    "mdn": normalizeMdn,
    "plain": normalizeNewlines,
}


def normalizerFor(source: dict):
    """카탈로그의 normalizer 가 정본이다. 없으면 자료원 종류로 정한다 (mediaWiki 는 wikitext, 나머지는 plain)."""
    name = source.get("normalizer") or ("wikitext" if source["kind"] == "mediaWiki" else "plain")
    return NORMALIZERS[name]


def normalized(doc: RawDocument, source: dict) -> str:
    return normalizerFor(source)(doc.raw)


def documentId(doc: RawDocument) -> str:
    key = f"{doc.sourceId}\0{doc.sourcePath}\0{doc.revision}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def trackableTitle(title: str) -> str:
    """추적되는 목록에 적는 제목. 원문의 긴 줄표는 저장소 표기 계약 (대시 없음) 에 맞춰 하이픈과 물결표로 적는다."""
    return title.replace(chr(0x2014), "-").replace(chr(0x2013), "~")


def manifestEntry(doc: RawDocument, source: dict) -> dict:
    text = normalized(doc, source)
    return {
        "id": documentId(doc),
        "source": doc.sourceId,
        "type": doc.type,
        "preset": doc.preset,
        "title": trackableTitle(doc.title),
        "sourcePath": doc.sourcePath,
        "revision": doc.revision,
        "url": doc.url,
        "license": doc.license,
        "licenseUrl": doc.licenseUrl,
        "owner": doc.owner,
        "rawSha256": sha256(doc.raw),
        "textSha256": sha256(text),
        "koreanChars": koreanChars(text),
    }


def refreshManifest(catalogue: dict) -> dict:
    entries: list[dict] = []
    for source in catalogue["source"]:
        if source["kind"] == "zipArchive":
            documents = archiveDocuments(source)
        elif source["kind"] == "mediaWiki":
            documents = mediaWikiDocuments(source)
        elif source["kind"] == "gitHubTree":
            documents = gitHubTreeDocuments(source)
        else:
            raise ValueError(f"모르는 자료원 종류: {source['kind']}")
        entries.extend(manifestEntry(doc, source) for doc in documents)
    entries.sort(key=lambda item: (item["type"], item["source"], item["sourcePath"]))
    result = {"version": 1, "documents": entries}
    path = manifestPath(catalogue)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def loadManifest(catalogue: dict) -> dict:
    return json.loads(manifestPath(catalogue).read_text(encoding="utf-8"))


def archiveRaw(source: dict, entries: list[dict]) -> dict[str, str]:
    wanted = {entry["sourcePath"] for entry in entries}
    found: dict[str, str] = {}
    with zipfile.ZipFile(BytesIO(request(source["archive"]))) as zipped:
        names = [name for name in zipped.namelist() if not name.endswith("/")]
        prefix = names[0].split("/", 1)[0] + "/"
        for name in names:
            path = name.removeprefix(prefix)
            if path in wanted:
                found[path] = zipped.read(name).decode("utf-8")
    return found


def mediaWikiRaw(source: dict, entries: list[dict]) -> dict[str, str]:
    found: dict[str, str] = {}
    byRevision = {int(entry["revision"]): entry["sourcePath"] for entry in entries}
    for batch in batches(list(byRevision)):
        time.sleep(0.25)
        data = requestJson(
            source["api"],
            {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "revisions",
                "revids": "|".join(str(revision) for revision in batch),
                "rvprop": "ids|content",
                "rvslots": "main",
            },
        )
        for page in data["query"]["pages"]:
            revision = page["revisions"][0]
            found[byRevision[revision["revid"]]] = revision["slots"]["main"]["content"]
    return found


def fetch(catalogue: dict, manifest: dict) -> None:
    root = corpusRoot(catalogue)
    root.mkdir(parents=True, exist_ok=True)
    sources = {source["id"]: source for source in catalogue["source"]}
    entriesBySource: dict[str, list[dict]] = {}
    for entry in manifest["documents"]:
        entriesBySource.setdefault(entry["source"], []).append(entry)
    expected = {f"{entry['type']}/{entry['id']}.md" for entry in manifest["documents"]}
    for path in root.glob("*/*.md"):
        relative = path.relative_to(root).as_posix()
        if relative not in expected:
            path.unlink()
    metadata: list[dict] = []
    for sourceId, entries in entriesBySource.items():
        source = sources[sourceId]
        if source["kind"] == "zipArchive":
            rawByPath = archiveRaw(source, entries)
        elif source["kind"] == "mediaWiki":
            rawByPath = mediaWikiRaw(source, entries)
        else:
            rawByPath = gitHubTreeRaw(source, entries)
        normalize = normalizerFor(source)
        for entry in entries:
            raw = rawByPath[entry["sourcePath"]]
            if sha256(raw) != entry["rawSha256"]:
                raise ValueError(f"원문 해시가 달라졌다: {sourceId}/{entry['sourcePath']}")
            text = normalize(raw)
            if sha256(text) != entry["textSha256"]:
                raise ValueError(f"정규화 해시가 달라졌다: {sourceId}/{entry['sourcePath']}")
            target = root / entry["type"] / f"{entry['id']}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            metadata.append({**entry, "path": target.relative_to(root).as_posix()})
    (root / "metadata.json").write_text(
        json.dumps({"version": 1, "documents": metadata}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def check(catalogue: dict, manifest: dict) -> list[str]:
    root = corpusRoot(catalogue)
    errors: list[str] = []
    expected = set()
    for entry in manifest["documents"]:
        relative = f"{entry['type']}/{entry['id']}.md"
        expected.add(relative)
        path = root / relative
        if not path.exists():
            errors.append(f"없음: {relative}")
        elif sha256(path.read_text(encoding="utf-8")) != entry["textSha256"]:
            errors.append(f"해시 불일치: {relative}")
    metadataPath = root / "metadata.json"
    if not metadataPath.exists():
        errors.append("없음: metadata.json")
    actual = {path.relative_to(root).as_posix() for path in root.glob("*/*.md")} if root.exists() else set()
    for extra in sorted(actual - expected):
        errors.append(f"목록 밖 파일: {extra}")
    return errors


def validate(catalogue: dict, manifest: dict) -> None:
    entries = manifest["documents"]
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("문서 id 가 겹친다")
    minimum = catalogue["corpus"]["minimumDocuments"]
    if len(entries) < minimum:
        raise ValueError(f"문서가 {len(entries)}편뿐이다. 최소 {minimum}편이 필요하다")
    wantedTypes = set(catalogue["corpus"]["types"])
    actualTypes = {entry["type"] for entry in entries}
    if actualTypes != wantedTypes:
        raise ValueError(f"글 종류가 다르다: {sorted(actualTypes)}")


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="기준 말뭉치를 카탈로그대로 받는다")
    parser.add_argument("--refresh-manifest", action="store_true", help="자료원을 다시 읽어 문서 판본과 해시를 고정한다")
    parser.add_argument("--check", action="store_true", help="저장소 밖 원문이 고정된 해시와 같은지만 본다")
    return parser.parse_args()


def main() -> int:
    args = parseArgs()
    catalogue = readCatalogue()
    if args.refresh_manifest:
        manifest = refreshManifest(catalogue)
    else:
        manifest = loadManifest(catalogue)
    validate(catalogue, manifest)
    if args.check:
        errors = check(catalogue, manifest)
        if errors:
            print("\n".join(errors))
            return 1
        print(f"기준 말뭉치 {len(manifest['documents'])}편의 해시가 같다")
        return 0
    fetch(catalogue, manifest)
    print(f"기준 말뭉치 {len(manifest['documents'])}편을 {corpusRoot(catalogue)} 에 받았다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
