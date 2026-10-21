"""命令行：重建工作台教程向量索引。

用法（在 backend 目录）：
  python -m app.rag.build_index
"""

from app.rag.index import rebuild_index


def main() -> None:
    result = rebuild_index()
    print(f"索引完成: {result}")


if __name__ == "__main__":
    main()
