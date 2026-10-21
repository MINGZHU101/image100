"""将《使用教程》切块写入 Chroma。"""

from __future__ import annotations

from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import ROOT_DIR, get_settings

_GUIDE_REL = Path("docs") / "电商商品视觉工作台使用教程.md"


def guide_path() -> Path:
    return ROOT_DIR / _GUIDE_REL


def _embeddings() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.dashscope_api_key or "mock-key",
        base_url=settings.dashscope_base_url,
        check_embedding_ctx_length=False,
    )


def get_vector_store(*, create: bool = False) -> Chroma:
    settings = get_settings()
    settings.rag_root.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.rag_collection,
        embedding_function=_embeddings(),
        persist_directory=str(settings.rag_root),
    )


def rebuild_index() -> dict:
    """清空并重建索引；无 DashScope Key 时写入空标记，检索走关键词降级。"""
    settings = get_settings()
    path = guide_path()
    if not path.exists():
        raise FileNotFoundError(f"教程不存在: {path}")

    text = path.read_text(encoding="utf-8")
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    docs = splitter.create_documents([text], metadatas=[{"source": str(_GUIDE_REL)}])

    # 先删旧集合
    persist = settings.rag_root
    persist.mkdir(parents=True, exist_ok=True)
    marker = persist / ".built"
    if not settings.dashscope_api_key:
        # 无 Key：仅落纯文本块供降级检索
        fallback = persist / "fallback_chunks.txt"
        fallback.write_text(
            "\n\n-----\n\n".join(doc.page_content for doc in docs),
            encoding="utf-8",
        )
        marker.write_text("fallback", encoding="utf-8")
        return {"mode": "fallback", "chunks": len(docs)}

    store = get_vector_store(create=True)
    try:
        store.delete_collection()
    except Exception:
        pass
    store = Chroma(
        collection_name=settings.rag_collection,
        embedding_function=_embeddings(),
        persist_directory=str(persist),
    )
    store.add_documents(docs)
    marker.write_text("chroma", encoding="utf-8")
    return {"mode": "chroma", "chunks": len(docs)}


def ensure_index() -> None:
    """启动或首次问答时：无标记则建索引。"""
    settings = get_settings()
    marker = settings.rag_root / ".built"
    if marker.exists() and guide_path().exists():
        return
    if guide_path().exists():
        rebuild_index()
