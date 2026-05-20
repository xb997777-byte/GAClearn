import re
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[4]
DOC_EXTENSIONS = {".md", ".txt"}
DOC_TARGET_SIZE = 450
DOC_OVERLAP = 80
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(?P<title>.+?)\s*$")
EXCLUDED_DIR_NAMES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "anaconda_projects",
    "media",
    "node_modules",
}


@dataclass
class ProjectDocument:
    relative_path: str
    audience: str
    source_kind: str
    title: str
    content: str


@dataclass
class ProjectDocumentSection:
    relative_path: str
    audience: str
    source_kind: str
    section_title: str
    content: str


def _safe_relative_path(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _should_skip_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDED_DIR_NAMES:
        return True
    relative = _safe_relative_path(path)
    if relative.startswith("backend/logs/") or relative.startswith("backend/media/") or relative.startswith("media/"):
        return True
    if relative.startswith("backend/scripts/resources/"):
        return True
    if path.suffix.lower() == ".txt" and not relative.startswith("00-换电脑迁移包/"):
        return True
    return False


def _classify_document(relative_path: str) -> Dict[str, str]:
    if relative_path.startswith("00-换电脑迁移包/"):
        return {"audience": "migration", "source_kind": "migration_doc", "title_prefix": "迁移文档"}
    if relative_path.startswith("3-架构设计/"):
        return {"audience": "dev", "source_kind": "dev_doc", "title_prefix": "架构文档"}
    if relative_path.startswith("1-需求分析/"):
        return {"audience": "product", "source_kind": "product_doc", "title_prefix": "需求文档"}
    return {"audience": "product", "source_kind": "project_doc", "title_prefix": "项目文档"}


def iter_project_doc_paths() -> Iterable[Path]:
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in DOC_EXTENSIONS:
            continue
        if _should_skip_path(path):
            continue
        yield path


def read_project_documents() -> List[ProjectDocument]:
    docs: List[ProjectDocument] = []
    for path in iter_project_doc_paths():
        relative_path = _safe_relative_path(path)
        classification = _classify_document(relative_path)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        docs.append(
            ProjectDocument(
                relative_path=relative_path,
                audience=classification["audience"],
                source_kind=classification["source_kind"],
                title=f"{classification['title_prefix']}：{path.stem}",
                content=text,
            )
        )
    return docs


def _flush_section(
    sections: List[ProjectDocumentSection],
    relative_path: str,
    audience: str,
    source_kind: str,
    section_title: str,
    lines: List[str],
) -> None:
    text = "\n".join(lines).strip()
    if not text:
        return
    normalized = re.sub(r"\n{3,}", "\n\n", text)
    sections.append(
        ProjectDocumentSection(
            relative_path=relative_path,
            audience=audience,
            source_kind=source_kind,
            section_title=section_title.strip() or Path(relative_path).stem,
            content=normalized,
        )
    )


def split_document_sections(document: ProjectDocument) -> List[ProjectDocumentSection]:
    sections: List[ProjectDocumentSection] = []
    current_title = document.title
    current_lines: List[str] = []

    for raw_line in (document.content or "").splitlines():
        line = raw_line.rstrip()
        heading_match = HEADING_PATTERN.match(line.strip())
        if heading_match:
            _flush_section(
                sections,
                document.relative_path,
                document.audience,
                document.source_kind,
                current_title,
                current_lines,
            )
            current_title = heading_match.group("title").strip()
            current_lines = []
            continue
        current_lines.append(line)

    _flush_section(
        sections,
        document.relative_path,
        document.audience,
        document.source_kind,
        current_title,
        current_lines,
    )
    return sections


def chunk_document_text(text: str, target_size: int = DOC_TARGET_SIZE, overlap: int = DOC_OVERLAP) -> List[str]:
    normalized = re.sub(r"\r\n?", "\n", str(text or ""))
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    if not normalized:
        return []

    chunks: List[str] = []
    start = 0
    minimum_backtrack = max(int(target_size * 0.55), 1)
    while start < len(normalized):
        hard_end = min(len(normalized), start + target_size)
        end = hard_end
        if hard_end < len(normalized):
            candidate = -1
            search_start = start + minimum_backtrack
            for separator in ["\n\n", "\n", "。", "！", "？", ". ", "; ", "；"]:
                position = normalized.rfind(separator, search_start, hard_end)
                if position > candidate:
                    candidate = position + len(separator)
            if candidate > start:
                end = candidate
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        next_start = max(end - overlap, start + 1)
        while next_start < len(normalized) and normalized[next_start].isspace():
            next_start += 1
        start = next_start
    return chunks


def build_project_document_catalog() -> List[Dict[str, object]]:
    docs = read_project_documents()
    sections = []
    chunk_count = 0
    audience_breakdown: Dict[str, int] = {}
    for item in docs:
        audience_breakdown[item.audience] = audience_breakdown.get(item.audience, 0) + 1
        doc_sections = split_document_sections(item)
        sections.extend(doc_sections)
        for section in doc_sections:
            chunk_count += len(chunk_document_text(section.content))
    return [
        {
            "key": "project_docs",
            "label": "项目文档知识库",
            "table": "repo_docs",
            "description": "项目内需求、架构、迁移与说明文档，默认按受众标签参与 RAG 召回。",
            "record_count": len(docs),
            "chunk_count": chunk_count,
            "section_count": len(sections),
            "audience_breakdown": audience_breakdown,
        }
    ]


def get_project_document_chunk_count() -> int:
    catalog = build_project_document_catalog()
    if not catalog:
        return 0
    return int(catalog[0].get("chunk_count") or 0)


def get_project_document_identity(relative_path: str) -> int:
    return zlib.crc32(str(relative_path).encode("utf-8")) & 0x7FFFFFFF
