export type PlannerProvider = 'mock' | 'dashscope'

export interface PlannerOptions {
  default_provider: PlannerProvider
  dashscope_available: boolean
  providers: PlannerProvider[]
}

export interface PlanStep {
  id: string
  tool_name: string
  params: Record<string, unknown>
  depends_on: string[]
}

export interface AgentRunOut {
  id: string
  session_id: string
  goal: string
  reply: string | null
  plan: { steps?: PlanStep[] }
  status: string
  planner_provider: string
  error: string | null
  tool_run_ids: string[]
  created_at: string
  updated_at: string
}

export interface AgentConfirmOut {
  agent_run_id: string
  status: string
  tool_run_ids: string[]
  message: string
}

export async function getPlannerOptions(): Promise<PlannerOptions> {
  const response = await fetch('/api/agent/planner-options')
  if (!response.ok) {
    throw new Error(`获取规划器选项失败：HTTP ${response.status}`)
  }
  return response.json() as Promise<PlannerOptions>
}

export async function createAgentRun(
  sessionId: string,
  goal: string,
  plannerProvider: PlannerProvider,
): Promise<AgentRunOut> {
  const response = await fetch(`/api/sessions/${sessionId}/agent/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal, planner_provider: plannerProvider }),
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`规划失败：${response.status} ${text}`)
  }
  return response.json() as Promise<AgentRunOut>
}

export async function getAgentRun(
  sessionId: string,
  agentRunId: string,
): Promise<AgentRunOut> {
  const response = await fetch(`/api/sessions/${sessionId}/agent/runs/${agentRunId}`)
  if (!response.ok) {
    throw new Error(`查询规划失败：HTTP ${response.status}`)
  }
  return response.json() as Promise<AgentRunOut>
}

export async function confirmAgentRun(
  sessionId: string,
  agentRunId: string,
): Promise<AgentConfirmOut> {
  const response = await fetch(
    `/api/sessions/${sessionId}/agent/runs/${agentRunId}/confirm`,
    { method: 'POST' },
  )
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`确认失败：${response.status} ${text}`)
  }
  return response.json() as Promise<AgentConfirmOut>
}

export async function cancelAgentRun(
  sessionId: string,
  agentRunId: string,
): Promise<AgentRunOut> {
  const response = await fetch(
    `/api/sessions/${sessionId}/agent/runs/${agentRunId}/cancel`,
    { method: 'POST' },
  )
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`取消失败：${response.status} ${text}`)
  }
  return response.json() as Promise<AgentRunOut>
}
