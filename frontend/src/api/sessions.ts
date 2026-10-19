/** 编辑会话 API */

import type { CanvasSelection } from '../types/selection'

export interface SessionOut {
  id: string
  title: string | null
  document: {
    version: number
    canvas: { width: number; height: number }
    layers: Array<{
      id: string
      name: string
      asset_id: string
      asset_key: string
      visible: boolean
    }>
    selection: CanvasSelection | null
  }
  created_at: string
  updated_at: string
}

export async function createSession(assetId: string): Promise<SessionOut> {
  const response = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ asset_id: assetId }),
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`创建会话失败：${response.status} ${text}`)
  }
  return response.json() as Promise<SessionOut>
}

export async function getSession(sessionId: string): Promise<SessionOut> {
  const response = await fetch(`/api/sessions/${sessionId}`)
  if (!response.ok) {
    throw new Error(`获取会话失败：HTTP ${response.status}`)
  }
  return response.json() as Promise<SessionOut>
}

/** 同步选区；传 null 清除 */
export async function patchSelection(
  sessionId: string,
  selection: CanvasSelection | null,
): Promise<SessionOut> {
  const response = await fetch(`/api/sessions/${sessionId}/selection`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ selection }),
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`同步选区失败：${response.status} ${text}`)
  }
  return response.json() as Promise<SessionOut>
}

