import { useRef, useState } from 'react'

import { streamAssistantChat, type ChatTurn } from '@/api/assistant'
import { errorMessage } from '@/hooks/useAuth'

/** 工作台右下角 AI 客服悬浮球 + 聊天窗。 */
export default function AssistantFab() {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatTurn[]>([])
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  const send = async () => {
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    const history = [...messages]
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setBusy(true)
    setStatus('检索中…')
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    let reply = ''
    setMessages((prev) => [...prev, { role: 'assistant', content: '' }])
    try {
      await streamAssistantChat(
        { message: text, history },
        (event) => {
          if (event.title) setStatus(event.title)
          if (event.error) {
            reply = event.error
            setMessages((prev) => {
              const next = [...prev]
              next[next.length - 1] = { role: 'assistant', content: reply }
              return next
            })
            return
          }
          if (event.content) {
            reply += event.content
            setMessages((prev) => {
              const next = [...prev]
              next[next.length - 1] = { role: 'assistant', content: reply }
              return next
            })
          }
        },
        controller.signal,
      )
    } catch (err) {
      setMessages((prev) => {
        const next = [...prev]
        next[next.length - 1] = { role: 'assistant', content: errorMessage(err) }
        return next
      })
    } finally {
      setBusy(false)
      setStatus('')
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="bg-ink hover:bg-dark fixed bottom-6 right-6 z-40 flex size-14 items-center justify-center rounded-full text-sm font-medium text-white shadow-lg transition"
        title="AI 智能客服"
        aria-label="打开 AI 智能客服"
      >
        客服
      </button>

      {open && (
        <div className="border-line bg-paper shadow-panel fixed bottom-24 right-6 z-40 flex h-[420px] w-[360px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-panel border">
          <div className="border-line flex items-center justify-between border-b px-4 py-3">
            <div>
              <p className="text-ink text-sm font-semibold">工作台智能客服</p>
              <p className="text-muted text-xs">本站使用助手 · 生图 / 充值 / 积分 / 批量等</p>
            </div>
            <button type="button" className="text-muted text-sm" onClick={() => setOpen(false)}>
              关闭
            </button>
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {messages.length === 0 && (
              <div className="text-muted space-y-1.5 text-sm">
                <p>可以问我例如：</p>
                <p>· 生成的图片在哪里找？</p>
                <p>· 怎么充值兑换积分？</p>
                <p>· 文案生成扣多少分？</p>
                <p>· 批量结果如何打包下载？</p>
                <p>· 怎么升级到钻石会员？</p>
              </div>
            )}
            {messages.map((msg, index) => (
              <div
                key={`${msg.role}-${index}`}
                className={`rounded-lg px-3 py-2 text-sm ${
                  msg.role === 'user' ? 'bg-brand-soft text-ink ml-8' : 'bg-soft text-ink mr-4'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content || (busy ? '…' : '')}</p>
              </div>
            ))}
            {status && <p className="text-faint text-xs">{status}</p>}
          </div>
          <div className="border-line flex gap-2 border-t p-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void send()
                }
              }}
              placeholder="输入问题…"
              className="border-line rounded-control flex-1 border px-3 py-2 text-sm outline-none"
            />
            <button
              type="button"
              disabled={busy || !input.trim()}
              onClick={() => void send()}
              className="bg-ink rounded-control px-3 py-2 text-sm text-white disabled:opacity-40"
            >
              发送
            </button>
          </div>
        </div>
      )}
    </>
  )
}
