import json
import os
import re
import subprocess
from collections import deque
from pathlib import Path
from typing import Any, Dict, List

from .chroma_runtime import get_chroma_runtime
from .knowledge_base import get_knowledge_source_catalog


BACKEND_DIR = Path(__file__).resolve().parents[3]
LOG_DIR = Path(os.getenv("AI_RAG_LOG_DIR", str(BACKEND_DIR / "logs")))
RAG_REBUILD_OUT_LOG = Path(os.getenv("AI_RAG_REBUILD_OUT_LOG", str(LOG_DIR / "rag_rebuild_full.out.log")))
RAG_REBUILD_ERR_LOG = Path(os.getenv("AI_RAG_REBUILD_ERR_LOG", str(LOG_DIR / "rag_rebuild_full.err.log")))
RAG_REBUILD_STATUS_FILE = Path(
    os.getenv("AI_RAG_REBUILD_STATUS_FILE", str(LOG_DIR / "rag_rebuild_status.json"))
)

PROGRESS_PATTERN = re.compile(r"Inserted batch\s+(?P<start>\d+)-(?P<end>\d+)\s*/\s*(?P<total>\d+)", re.IGNORECASE)
SUCCESS_PATTERN = re.compile(r"Rebuilt Chroma RAG index with\s+(?P<total>\d+)\s+chunks", re.IGNORECASE)
ERROR_KEYWORDS = ("traceback", "error", "exception", "failed", "commanderror")


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _read_tail_lines(path: Path, limit: int = 20) -> List[str]:
    if not path.exists():
        return []
    rows: deque[str] = deque(maxlen=max(int(limit or 20), 1))
    with path.open("r", encoding="utf-8", errors="ignore") as file_obj:
        for line in file_obj:
            text = line.rstrip("\r\n")
            if text:
                rows.append(text)
    return list(rows)


def _extract_progress(lines: List[str]) -> Dict[str, Any]:
    latest_line = ""
    for line in reversed(lines):
        text = (line or "").strip()
        if not text:
            continue
        if not latest_line:
            latest_line = text
        success_match = SUCCESS_PATTERN.search(text)
        if success_match:
            total = int(success_match.group("total"))
            return {
                "inserted_count": total,
                "total_count": total,
                "last_progress_line": text,
                "latest_line": latest_line or text,
                "completed": True,
            }
        progress_match = PROGRESS_PATTERN.search(text)
        if progress_match:
            return {
                "inserted_count": int(progress_match.group("end")),
                "total_count": int(progress_match.group("total")),
                "last_progress_line": text,
                "latest_line": latest_line or text,
                "completed": False,
            }
    return {
        "inserted_count": 0,
        "total_count": 0,
        "last_progress_line": "",
        "latest_line": latest_line,
        "completed": False,
    }


def _read_status_file() -> Dict[str, Any]:
    if not RAG_REBUILD_STATUS_FILE.exists():
        return {}
    try:
        with RAG_REBUILD_STATUS_FILE.open("r", encoding="utf-8") as file_obj:
            return json.load(file_obj) or {}
    except Exception:
        return {}


def write_rag_rebuild_status(payload: Dict[str, Any]) -> None:
    _ensure_log_dir()
    temp_path = RAG_REBUILD_STATUS_FILE.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, ensure_ascii=False, indent=2)
    temp_path.replace(RAG_REBUILD_STATUS_FILE)


def _list_windows_rebuild_processes() -> List[Dict[str, Any]]:
    command = """
$ErrorActionPreference = 'Stop'
$rows = Get-CimInstance Win32_Process |
  Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'rebuild_rag_index' } |
  Select-Object `
    @{Name='pid';Expression={$_.ProcessId}},
    @{Name='command_line';Expression={$_.CommandLine}}
if ($rows) {
  $rows | ConvertTo-Json -Compress
} else {
  '[]'
}
""".strip()
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        return []
    raw = (completed.stdout or "").strip() or "[]"
    try:
        parsed = json.loads(raw)
    except Exception:
        return []
    if isinstance(parsed, dict):
        parsed = [parsed]
    rows: List[Dict[str, Any]] = []
    for item in parsed or []:
        rows.append(
            {
                "pid": int(item.get("pid") or 0),
                "command_line": item.get("command_line", "") or "",
            }
        )
    return [item for item in rows if item["pid"] > 0]


def _list_posix_rebuild_processes() -> List[Dict[str, Any]]:
    completed = subprocess.run(
        ["ps", "-eo", "pid,args"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        return []
    rows: List[Dict[str, Any]] = []
    for line in (completed.stdout or "").splitlines()[1:]:
        text = (line or "").strip()
        if "rebuild_rag_index" not in text or "python" not in text:
            continue
        parts = text.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        rows.append({"pid": pid, "command_line": parts[1]})
    return rows


def list_rag_rebuild_processes() -> List[Dict[str, Any]]:
    try:
        if os.name == "nt":
            return _list_windows_rebuild_processes()
        return _list_posix_rebuild_processes()
    except Exception:
        return []


def build_rag_index_status() -> Dict[str, Any]:
    runtime = get_chroma_runtime()
    catalog = runtime.get("knowledge_source_catalog") or get_knowledge_source_catalog()
    expected_chunk_count = int(runtime.get("expected_chunk_count") or 0)
    if not expected_chunk_count:
        expected_chunk_count = sum(int(item.get("chunk_count") or item.get("record_count") or 0) for item in catalog)
    processes = list_rag_rebuild_processes()
    status_file = _read_status_file()
    out_tail = _read_tail_lines(RAG_REBUILD_OUT_LOG, limit=16)
    out_progress = _extract_progress(_read_tail_lines(RAG_REBUILD_OUT_LOG, limit=240))
    err_tail_all = _read_tail_lines(RAG_REBUILD_ERR_LOG, limit=40)
    err_tail = [line for line in err_tail_all if any(keyword in line.lower() for keyword in ERROR_KEYWORDS)][-8:]

    inserted_count = int(status_file.get("inserted_count") or 0)
    total_count = int(status_file.get("total_count") or 0)
    last_progress_line = status_file.get("last_progress_line", "") or ""
    latest_line = status_file.get("latest_line", "") or ""
    rebuild_state = status_file.get("state", "") or ""

    if out_progress.get("inserted_count", 0) >= inserted_count:
        inserted_count = int(out_progress.get("inserted_count") or inserted_count)
        total_count = int(out_progress.get("total_count") or total_count)
        last_progress_line = out_progress.get("last_progress_line", "") or last_progress_line
        latest_line = out_progress.get("latest_line", "") or latest_line
        if out_progress.get("completed"):
            rebuild_state = "completed"

    if expected_chunk_count and not total_count:
        total_count = expected_chunk_count
    if runtime.get("chunk_count") and (not inserted_count or not processes):
        inserted_count = min(max(inserted_count, int(runtime.get("chunk_count") or 0)), total_count or int(runtime.get("chunk_count") or 0))
    if total_count and inserted_count > total_count:
        inserted_count = total_count

    running = bool(processes)
    if running:
        rebuild_state = "running"
    elif runtime.get("indexed") and total_count and inserted_count >= total_count:
        rebuild_state = "completed"
        inserted_count = total_count
    elif runtime.get("indexed") and expected_chunk_count and int(runtime.get("chunk_count") or 0) >= expected_chunk_count:
        rebuild_state = "completed"
        inserted_count = int(runtime.get("chunk_count") or 0)
        total_count = expected_chunk_count
    elif status_file.get("state") == "failed":
        rebuild_state = "failed"
    elif not rebuild_state:
        rebuild_state = "idle"

    runtime_available = bool(runtime.get("available"))
    runtime_indexed = bool(runtime.get("indexed"))
    runtime_degraded_reason = str(runtime.get("runtime_degraded_reason") or "").strip()
    active_retrieval_backend = str(
        runtime.get("backend") if runtime_available and runtime_indexed else (runtime.get("fallback_runtime") or runtime.get("backend") or "")
    ).strip()
    runtime_state = "ready"
    if running:
        runtime_state = "building"
    elif not runtime_available:
        runtime_state = "runtime_unavailable"
    elif not runtime_indexed:
        runtime_state = "not_indexed"
    elif str(runtime.get("collection_health") or "") == "partial":
        runtime_state = "partial"
    runtime_degraded = bool(runtime.get("runtime_degraded")) or runtime_state in {"runtime_unavailable", "not_indexed", "partial", "degraded"}
    if runtime_degraded and runtime_state == "ready":
        runtime_state = "degraded"

    state = rebuild_state
    if rebuild_state == "completed" and runtime_state != "ready":
        state = runtime_state
    elif rebuild_state in {"idle", "failed", "running"}:
        state = rebuild_state

    progress_percent = 0.0
    if total_count > 0:
        progress_percent = round(min(100.0, max(0.0, inserted_count * 100.0 / total_count)), 2)
    if rebuild_state == "completed" and total_count > 0:
        progress_percent = 100.0

    expose_error_tail = rebuild_state == "failed"

    return {
        "state": state,
        "rebuild_state": rebuild_state,
        "runtime_state": runtime_state,
        "running": running,
        "processes": processes,
        "pid_list": [item["pid"] for item in processes],
        "inserted_count": inserted_count,
        "total_count": total_count,
        "expected_chunk_count": expected_chunk_count,
        "progress_percent": progress_percent,
        "last_progress_line": last_progress_line,
        "latest_line": latest_line or (out_tail[-1] if out_tail else ""),
        "last_error_line": err_tail[-1] if expose_error_tail and err_tail else "",
        "log_tail": out_tail,
        "error_log_tail": err_tail if expose_error_tail else [],
        "runtime_chunk_count": int(runtime.get("chunk_count") or 0),
        "runtime_indexed": runtime_indexed,
        "runtime_available": runtime_available,
        "runtime_degraded": runtime_degraded,
        "runtime_degraded_reason": runtime_degraded_reason,
        "active_retrieval_backend": active_retrieval_backend,
        "source_breakdown": runtime.get("source_breakdown") or [],
        "collection_name": runtime.get("collection_name", "") or "",
        "collection_fingerprint": runtime.get("collection_fingerprint", "") or "",
        "embedding_dimension": int(runtime.get("embedding_dimension") or 0),
        "collection_health": runtime.get("collection_health", "unknown") or "unknown",
        "stale_collections": runtime.get("stale_collections") or [],
        "status_file_path": str(RAG_REBUILD_STATUS_FILE),
        "out_log_path": str(RAG_REBUILD_OUT_LOG),
        "err_log_path": str(RAG_REBUILD_ERR_LOG),
        "status_updated_at": status_file.get("updated_at", "") or "",
        "status_started_at": status_file.get("started_at", "") or "",
        "embedding_backend": runtime.get("embedding_backend", "") or "",
        "embedding_provider": runtime.get("embedding_provider", "") or "",
        "embedding_model": runtime.get("embedding_model", "") or "",
    }
