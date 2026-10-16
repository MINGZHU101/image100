import { useState } from 'react'
import type { AgentRunOut, PlannerProvider } from '../../api/agent'
import { PlanCard } from './PlanCard'

interface AgentConversationProps {
  provider: PlannerProvider
  dashscopeAvailable: boolean
  busy: boolean
  error: string
  current: AgentRunOut | null
  onProviderChange: (provider: PlannerProvider) => void
  onSubmit: (goal: string) => void
  onConfirm: () => void
  onCancel: () => void
}

/** 右侧 Agent 对话区：Mock/LLM 切换 + 输入 + 计划卡片 */
export function AgentConversation({
  provider,
  dashscopeAvailable,
  busy,
  error,
  current,
  onProviderChange,
  onSubmit,
  onConfirm,
  onCancel,
}: AgentConversationProps) {
  const [goal, setGoal] = useState('')

  return (
    <aside className="agent-panel">
      <div className="agent-panel-header">
        <h2>自然语言修图</h2>
        <div className="planner-toggle" role="group" aria-label="规划器切换">
          <button
            type="button"
            className={`planner-btn${provider === 'mock' ? ' is-active' : ''}`}
            disabled={busy}
            onClick={() => onProviderChange('mock')}
          >
            Mock
          </button>
          <button
            type="button"
            className={`planner-btn${provider === 'dashscope' ? ' is-active' : ''}`}
            disabled={busy || !dashscopeAvailable}
            title={dashscopeAvailable ? '通义千问规划' : '未检测到 DASHSCOPE_API_KEY'}
            onClick={() => onProviderChange('dashscope')}
          >
            LLM
          </button>
        </div>
      </div>

      <p className="muted agent-hint">
        当前：{provider === 'mock' ? 'Mock 规则规划' : 'DashScope LLM'}
        。试试「去掉背景，再提亮一点」
      </p>

      <div className="agent-messages">
        {current && (
          <div className="agent-bubble">
            <p className="agent-goal">你：{current.goal}</p>
            {current.reply && <p className="agent-reply">助手：{current.reply}</p>}
            {current.status !== 'planned' && (
              <p className="muted">状态：{current.status}</p>
            )}
          </div>
        )}
        {current && (
          <PlanCard
            run={current}
            disabled={busy}
            onConfirm={onConfirm}
            onCancel={onCancel}
          />
        )}
      </div>

      {error && <p className="status-error">{error}</p>}

      <form
        className="agent-composer"
        onSubmit={(event) => {
          event.preventDefault()
          if (!goal.trim()) {
            return
          }
          onSubmit(goal)
          setGoal('')
        }}
      >
        <textarea
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          placeholder="用一句话描述修图意图…"
          rows={3}
          disabled={busy}
        />
        <button type="submit" className="tool-btn tool-btn-export" disabled={busy || !goal.trim()}>
          {busy ? '处理中…' : '发送'}
        </button>
      </form>
    </aside>
  )
}
