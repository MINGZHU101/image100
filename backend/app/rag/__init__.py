"""轻量工作台 RAG：教程入库 + 检索拒答。"""

from app.rag.index import ensure_index, rebuild_index
from app.rag.retrieve import answer_question

__all__ = ["ensure_index", "rebuild_index", "answer_question"]
