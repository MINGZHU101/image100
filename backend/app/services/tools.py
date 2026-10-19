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


async def get_run_compat(session: AsyncSession, run_id: UUID) -> dict:
    """工具运行或文生图 → 原仓 Run 形状。"""
    from app.compat.session_detail import to_frontend_asset
    from app.models.asset import Asset
    from app.models.generation_run import GenerationRun
    from app.services.assets import to_asset_out

    run = await session.get(ToolRun, run_id)
    if run is not None:
        return {
            "id": str(run.id),
            "tool": run.tool_name,
            "status": run.status,
            "progress": run.progress,
            "stage": "",
            "error": run.error,
            "prompt": None,
            "candidates": [],
            "result": {"asset_id": str(run.result_asset_id)} if run.result_asset_id else {},
        }

    generation = await session.get(GenerationRun, run_id)
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="运行不存在")

    candidates = []
    for raw_id in generation.result_asset_ids or []:
        try:
            asset = await session.get(Asset, UUID(str(raw_id)))
        except ValueError:
            continue
        if asset is not None:
            candidates.append(to_frontend_asset(to_asset_out(asset)))

    return {
        "id": str(generation.id),
        "tool": "generate_image",
        "status": generation.status,
        "progress": generation.progress,
        "stage": "",
        "error": generation.error,
        "prompt": generation.prompt,
        "candidates": candidates,
        "result": {},
    }
