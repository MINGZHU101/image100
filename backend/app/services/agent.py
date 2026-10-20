"""Agent 用例：规划落库、确认串行入队、取消。"""

import asyncio
import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.agent.graph import run_planner
from app.config import get_settings
from app.models.agent_run import AgentRun
from app.models.edit_session import EditSession
from app.models.tool_run import ToolRun
from app.providers.dashscope import PlannerUnavailable
from app.queue import enqueue_agent_plan
from app.schemas.agent import (
    AgentConfirmOut,
    AgentRunOut,
    PlannerOptionsOut,
)
from app.services import tools as tools_service

logger = logging.getLogger(__name__)


async def _cancel_stale_planned(session: AsyncSession, session_id: UUID) -> None:
    """新对话到来时，作废同会话里尚未确认的旧计划，避免 UI 堆积。"""
    await session.execute(
        update(AgentRun)
        .where(
            AgentRun.session_id == session_id,
            AgentRun.status == "planned",
        )
        .values(status="cancelled", error="已被新对话取代")
    )


def planner_options() -> PlannerOptionsOut:
    settings = get_settings()
    default = settings.planner_provider.strip().lower()
    if default not in ("mock", "dashscope"):
        default = "dashscope"
    has_key = bool(settings.dashscope_api_key)
    return PlannerOptionsOut(
        default_provider=default if default == "mock" or has_key else "mock",
        dashscope_available=has_key,
        providers=["mock", "dashscope"],
    )


def _resolve_provider(requested: str | None) -> str:
    settings = get_settings()
    name = (requested or settings.planner_provider or "dashscope").strip().lower()
    if name not in ("mock", "dashscope"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="planner_provider 仅支持 mock 或 dashscope",
        )
    if name == "dashscope" and not settings.dashscope_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置 DASHSCOPE_API_KEY，请切换到 Mock 规划器",
        )
    return name


def _canvas_context(document: dict | None) -> str:
    doc = document or {}
    canvas = doc.get("canvas") or {}
    layers = doc.get("layers") or []
    layer_bits = []
    for layer in layers:
        visible = "显" if layer.get("visible", True) else "隐"
        layer_bits.append(f"{layer.get('name')}({layer.get('id')},{visible})")
    layers_text = "、".join(layer_bits) if layer_bits else "无"
    active = doc.get("active_layer_id") or "无"
    selection = doc.get("selection")
    if selection and isinstance(selection, dict):
        sel_type = selection.get("type") or "unknown"
        selection_text = f"选区：有（{sel_type}）"
    else:
        selection_text = "选区：无"
    return (
        f"画布 {canvas.get('width')}×{canvas.get('height')}；"
        f"图层：{layers_text}；"
        f"当前层={active}；"
        f"{selection_text}"
    )


def _to_out(row: AgentRun) -> AgentRunOut:
    ids = row.tool_run_ids or []
    return AgentRunOut(
        id=row.id,
        session_id=row.session_id,
        goal=row.goal,
        reply=row.reply,
        plan=row.plan or {},
        status=row.status,
        planner_provider=row.planner_provider,
        error=row.error,
        tool_run_ids=[str(item) for item in ids],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def create_agent_run(
    session: AsyncSession,
    session_id: UUID,
    goal: str,
    planner_provider: str | None,
) -> AgentRunOut:
    edit_session = await session.get(EditSession, session_id)
    if edit_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    await _cancel_stale_planned(session, session_id)

    provider = _resolve_provider(planner_provider)
    context = _canvas_context(edit_session.document)

    try:
        reply, steps, error = await run_planner(
            goal.strip(),
            context,
            planner_provider=provider,
        )
    except PlannerUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("规划失败")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"规划失败：{exc}",
        ) from exc

    if error or not steps:
        row = AgentRun(
            session_id=session_id,
            goal=goal.strip(),
            reply=reply or error,
            plan={"steps": []},
            status="failed",
            planner_provider=provider,
            error=error or reply or "规划失败",
            tool_run_ids=[],
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return _to_out(row)

    row = AgentRun(
        session_id=session_id,
        goal=goal.strip(),
        reply=reply,
        plan={"steps": steps},
        status="planned",
        planner_provider=provider,
        error=None,
        tool_run_ids=[],
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_out(row)


async def get_agent_run(session: AsyncSession, agent_run_id: UUID) -> AgentRunOut:
    row = await session.get(AgentRun, agent_run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规划不存在")
    return _to_out(row)


async def confirm_agent_run(
    session: AsyncSession,
    session_id: UUID,
    agent_run_id: UUID,
) -> AgentConfirmOut:
    row = await session.get(AgentRun, agent_run_id)
    if row is None or row.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规划不存在")
    if row.status != "planned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前状态不可确认：{row.status}",
        )
    steps = (row.plan or {}).get("steps") or []
    if not steps:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="计划为空")

    row.status = "confirmed"
    await session.commit()

    try:
        await enqueue_agent_plan(row.id)
    except Exception as exc:  # noqa: BLE001
        row.status = "failed"
        row.error = f"入队失败: {exc}"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"计划入队失败: {exc}",
        ) from exc

    row.status = "running"
    await session.commit()
    return AgentConfirmOut(
        agent_run_id=row.id,
        status=row.status,
        tool_run_ids=[],
        message="已确认，正在按序执行",
    )


async def cancel_agent_run(
    session: AsyncSession,
    session_id: UUID,
    agent_run_id: UUID,
) -> AgentRunOut:
    row = await session.get(AgentRun, agent_run_id)
    if row is None or row.session_id != session_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规划不存在")
    if row.status not in ("planned", "confirmed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"当前状态不可取消：{row.status}",
        )
    row.status = "cancelled"
    await session.commit()
    await session.refresh(row)
    return _to_out(row)


async def execute_plan_serial(session: AsyncSession, agent_run_id: UUID) -> dict:
    """
    Worker 入口：严格串行——每步 invoke_tool，等 succeeded 再下一步。
    """
    row = await session.get(AgentRun, agent_run_id)
    if row is None:
        return {"ok": False, "error": "agent_run_not_found"}
    if row.status == "cancelled":
        return {"ok": False, "error": "cancelled"}

    row.status = "running"
    await session.commit()

    steps = (row.plan or {}).get("steps") or []
    tool_run_ids: list[str] = list(row.tool_run_ids or [])

    try:
        for step in steps:
            # 每步前检查是否被取消
            await session.refresh(row)
            if row.status == "cancelled":
                return {"ok": False, "error": "cancelled"}

            invoke = await tools_service.invoke_tool(
                session,
                row.session_id,
                step["tool_name"],
                step.get("params") or {},
                source="agent",
            )
            tool_run_ids.append(str(invoke.run_id))
            row.tool_run_ids = tool_run_ids
            flag_modified(row, "tool_run_ids")
            await session.commit()

            ok = await _wait_tool_succeeded(session, invoke.run_id)
            if not ok:
                tool = await session.get(ToolRun, invoke.run_id)
                row.status = "failed"
                row.error = (tool.error if tool else None) or "工具执行失败"
                await session.commit()
                return {"ok": False, "error": row.error}

        row.status = "done"
        row.error = None
        await session.commit()
        return {"ok": True, "tool_run_ids": tool_run_ids}
    except Exception as exc:  # noqa: BLE001
        logger.exception("计划串行执行失败 agent_run_id=%s", agent_run_id)
        row.status = "failed"
        row.error = str(exc)
        await session.commit()
        return {"ok": False, "error": str(exc)}


async def _wait_tool_succeeded(
    session: AsyncSession,
    run_id: UUID,
    *,
    timeout_sec: float = 300.0,
) -> bool:
    """轮询 tool_runs 直到终态。"""
    elapsed = 0.0
    interval = 0.4
    while elapsed < timeout_sec:
        run = await session.get(ToolRun, run_id)
        if run is None:
            return False
        if run.status == "succeeded":
            return True
        if run.status == "failed":
            return False
        await asyncio.sleep(interval)
        elapsed += interval
        await session.refresh(run)
    return False
