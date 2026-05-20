from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.ai.rag.chroma_runtime import (
    chroma_available,
    embed_texts,
    get_chroma_runtime,
    reset_chroma_collection,
)
from apps.ai.rag.index_status import write_rag_rebuild_status
from apps.ai.rag.knowledge_base import build_all_knowledge_chunks, chunk_stats, split_chroma_payload


class Command(BaseCommand):
    help = "Rebuild the Chroma RAG knowledge index from project learning content."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Optional limit for quick local rebuild.")
        parser.add_argument("--batch-size", type=int, default=64, help="Batch size for embedding and Chroma insert.")

    def handle(self, *args, **options):
        if not chroma_available():
            raise CommandError("Chroma dependencies are not installed. Run pip install -r requirements.txt first.")

        limit = int(options.get("limit") or 0) or None
        batch_size = max(int(options.get("batch_size") or 64), 1)
        started_at = datetime.now().isoformat()
        runtime = {}
        try:
            chunks = build_all_knowledge_chunks(limit=limit)
            if not chunks:
                raise CommandError("No knowledge chunks were built. Check your content tables first.")

            ids, documents, metadatas = split_chroma_payload(chunks)
            total = len(ids)
            runtime = get_chroma_runtime()
            write_rag_rebuild_status(
                {
                    "state": "running",
                    "started_at": started_at,
                    "updated_at": started_at,
                    "inserted_count": 0,
                    "total_count": total,
                    "last_progress_line": "",
                    "latest_line": "RAG rebuild started",
                    "embedding_backend": runtime.get("embedding_backend", ""),
                    "embedding_provider": runtime.get("embedding_provider", ""),
                    "embedding_model": runtime.get("embedding_model", ""),
                    "batch_size": batch_size,
                    "limit": limit or 0,
                }
            )

            self.stdout.write(
                self.style.NOTICE(
                    f"Building RAG index with backend={runtime['embedding_backend']} model={runtime['embedding_model']}"
                )
            )
            self.stdout.write(self.style.NOTICE(f"Knowledge sources: {', '.join(runtime['knowledge_sources'])}"))
            for source in runtime.get("knowledge_source_catalog", []):
                self.stdout.write(
                    f"  - {source['key']} ({source['table']}): {source['record_count']} records"
                )

            collection = reset_chroma_collection()
            for start in range(0, total, batch_size):
                end = min(start + batch_size, total)
                batch_ids = ids[start:end]
                batch_documents = documents[start:end]
                batch_metadatas = metadatas[start:end]
                embeddings = embed_texts(batch_documents)
                collection.add(
                    ids=batch_ids,
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                    embeddings=embeddings,
                )
                progress_line = f"Inserted batch {start + 1}-{end} / {total}"
                self.stdout.write(progress_line)
                write_rag_rebuild_status(
                    {
                        "state": "running",
                        "started_at": started_at,
                        "updated_at": datetime.now().isoformat(),
                        "inserted_count": end,
                        "total_count": total,
                        "last_progress_line": progress_line,
                        "latest_line": progress_line,
                        "embedding_backend": runtime.get("embedding_backend", ""),
                        "embedding_provider": runtime.get("embedding_provider", ""),
                        "embedding_model": runtime.get("embedding_model", ""),
                        "batch_size": batch_size,
                        "limit": limit or 0,
                    }
                )

            stats = chunk_stats(chunks)
            success_line = f"Rebuilt Chroma RAG index with {len(ids)} chunks."
            self.stdout.write(self.style.SUCCESS(success_line))
            for source_type, count in sorted(stats.items()):
                self.stdout.write(f"- {source_type}: {count}")
            write_rag_rebuild_status(
                {
                    "state": "completed",
                    "started_at": started_at,
                    "updated_at": datetime.now().isoformat(),
                    "inserted_count": len(ids),
                    "total_count": len(ids),
                    "last_progress_line": success_line,
                    "latest_line": success_line,
                    "embedding_backend": runtime.get("embedding_backend", ""),
                    "embedding_provider": runtime.get("embedding_provider", ""),
                    "embedding_model": runtime.get("embedding_model", ""),
                    "batch_size": batch_size,
                    "limit": limit or 0,
                    "stats": stats,
                }
            )
        except Exception as exc:
            write_rag_rebuild_status(
                {
                    "state": "failed",
                    "started_at": started_at,
                    "updated_at": datetime.now().isoformat(),
                    "inserted_count": 0,
                    "total_count": 0,
                    "last_progress_line": "",
                    "latest_line": str(exc),
                    "embedding_backend": runtime.get("embedding_backend", ""),
                    "embedding_provider": runtime.get("embedding_provider", ""),
                    "embedding_model": runtime.get("embedding_model", ""),
                    "batch_size": batch_size,
                    "limit": limit or 0,
                }
            )
            raise
