"""工具列表、调用、运行查询。"""

from uuid import UUID

from fastapi import APIRouter

from app.deps import DbDep
from app.schemas.run import RunOut, ToolInfoOut, ToolInvokeIn, ToolInvokeOut
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
) -> ToolInvokeOut:
    return await tools_service.invoke_tool(db, session_id, tool_name, body.params)


@router.get("/runs/{run_id}", response_model=RunOut)
async def get_run(run_id: UUID, db: DbDep) -> RunOut:
    return await tools_service.get_run(db, run_id)
