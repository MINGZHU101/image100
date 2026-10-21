import { apiError } from '@/api/client'

export type AssistantEvent = {
  stage?: string
  title?: string
  content?: string
  done?: boolean
  error?: string
}

export type ChatTurn = { role: 'user' | 'assistant'; content: string }

export async function streamAssistantChat(
  body: { message: string; history: ChatTurn[] },
  onEvent: (event: AssistantEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch('/api/assistant/chat/stream', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok) throw await apiError(response, '客服请求失败')
  if (!response.body) throw new Error('浏览器不支持流式响应')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const part of parts) {
      const line = part
        .split('\n')
        .map((l) => l.trim())
        .find((l) => l.startsWith('data:'))
      if (!line) continue
      const data = line.slice(5).trim()
      if (data === '[DONE]') return
      try {
        onEvent(JSON.parse(data) as AssistantEvent)
      } catch {
        /* ignore */
      }
    }
  }
}
