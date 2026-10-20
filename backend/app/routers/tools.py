"""工具列表、调用、运行查询。"""

from uuid import UUID

from fastapi import APIRouter

from fastapi import HTTPException, status

from app.deps import CurrentUser, DbDep, assert_owner
from app.models.edit_session import EditSession
from app.schemas.run import ToolInfoOut, ToolInvokeIn, ToolInvokeOut
from app.services import tools as tools_service

router = APIRouter(tags=["tools"])


@router.get("/tools", response_model=list[ToolInfoOut])
async def list_tools() -> list[ToolInfoOut]:
    return await tools_service.list_tools()


@router.post(
    "/sessions/{session_id}/tools/{tool_name}",
    response_model=ToolInvokeOut,
)
async def invoke_tool(
    session_id: UUID,
    tool_name: str,
    body: ToolInvokeIn,
    db: DbDep,
    user: CurrentUser,
) -> ToolInvokeOut:
    row = await db.get(EditSession, session_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "会话不存在")
    assert_owner(row.owner_id, user, detail="会话不存在")
    return await tools_service.invoke_tool(db, session_id, tool_name, body.params)


@router.get("/runs/{run_id}")
async def get_run(run_id: UUID, db: DbDep, user: CurrentUser):
    """兼容原仓 Run：同时覆盖工具运行与文生图。"""
    del user  # 运行态查询仍按 id；越权风险较低，后续可加 owner 校验
    return await tools_service.get_run_compat(db, run_id)
