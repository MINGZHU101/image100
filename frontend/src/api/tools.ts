export interface ToolInfo {
  name: string
  label: string
  description: string
}

export interface ToolInvokeOut {
  run_id: string
  status: string
}

export interface RunOut {
  id: string
  session_id: string
  tool_name: string
  status: string
  progress: number
  params: Record<string, unknown>
  result_asset_id: string | null
  error: string | null
}

/** 列出工具栏可用工具 */
export async function listTools(): Promise<ToolInfo[]> {
  const response = await fetch('/api/tools')
  if (!response.ok) {
    throw new Error(`获取工具列表失败：HTTP ${response.status}`)
  }
  return response.json() as Promise<ToolInfo[]>
}

/** 调用会话工具，立即返回 run_id */
export async function invokeTool(
  sessionId: string,
  toolName: string,
  params: Record<string, unknown> = {},
): Promise<ToolInvokeOut> {
  const response = await fetch(`/api/sessions/${sessionId}/tools/${toolName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ params }),
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`调用工具失败：${response.status} ${text}`)
  }
  return response.json() as Promise<ToolInvokeOut>
}

/** 轮询兜底查运行状态 */
export async function getRun(runId: string): Promise<RunOut> {
  const response = await fetch(`/api/runs/${runId}`)
  if (!response.ok) {
    throw new Error(`获取运行状态失败：HTTP ${response.status}`)
  }
  return response.json() as Promise<RunOut>
}

/** 导出下载地址 */
export function exportUrl(sessionId: string): string {
  return `/api/sessions/${sessionId}/export`
}
