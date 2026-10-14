/** 后端健康检查响应（与 /api/health 对齐） */
export interface HealthResponse {
  status: string
  postgres: string
  redis: string
}

/**
 * 请求后端健康检查。
 * 开发环境走 Vite 代理 /api → 7302，无需写死后端主机。
 */
export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  if (!response.ok) {
    throw new Error(`健康检查失败：HTTP ${response.status}`)
  }
  return response.json() as Promise<HealthResponse>
}
