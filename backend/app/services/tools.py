"""手动工具用例：校验 → 落库 → 入队。"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edit_session import EditSession
from app.models.tool_run import ToolRun
from app.queue import enqueue_tool_run
from app.schemas.run import RunOut, ToolInfoOut, ToolInvokeOut
from app.tools.registry import get_tool, list_ui_tools


async def list_tools() -> list[ToolInfoOut]:
    return [
        ToolInfoOut(name=item.name, label=item.label, description=item.description)
        for item in list_ui_tools()
    ]


async def invoke_tool(
    session: AsyncSession,
    session_id: UUID,
    tool_name: str,
    params: dict,
    *,
    source: str = "ui",
) -> ToolInvokeOut:
    """创建 ToolRun 并入队，立即返回 run_id。source=ui|agent。"""
    edit_session = await session.get(EditSession, session_id)
    if edit_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    tool = get_tool(tool_name)
    if tool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工具不存在")
    if source == "agent":
        if not tool.agent_exposed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工具不可用于 Agent")
    elif not tool.ui_exposed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工具不存在")

    # 局部工具：入队前校验选区，便于前端立刻看到错误
    if tool_name == "adjust_region":
        selection = (edit_session.document or {}).get("selection")
        if not selection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请先框选或涂抹选区",
            )

    # 用 params_model 校验并规范化参数

    try:
        validated = tool.params_model.model_validate(params or {})
        clean_params = validated.model_dump()
    except Exception as exc:  # noqa: BLE001 — 转成 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"参数无效: {exc}",
        ) from exc

    run = ToolRun(
        session_id=session_id,
        tool_name=tool.name,
        status="queued",
        progress=0,
        params=clean_params,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    try:
        await enqueue_tool_run(run.id)
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.error = f"入队失败: {exc}"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"任务入队失败: {exc}",
        ) from exc

    return ToolInvokeOut(run_id=run.id, status=run.status)


async def get_run(session: AsyncSession, run_id: UUID) -> RunOut:
    run = await session.get(ToolRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运行不存在")
    return RunOut.model_validate(run)
