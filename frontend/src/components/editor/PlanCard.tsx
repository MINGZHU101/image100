import type { AgentRunOut } from '../../api/agent'

const TOOL_LABELS: Record<string, string> = {
  adjust_image: '提亮',
  adjust_region: '局部提亮',
  remove_background: '去背景',
  flip_layer: '水平翻转',
  split_layers: '拆层',
}

interface PlanCardProps {
  run: AgentRunOut
  disabled?: boolean
  onConfirm: () => void
  onCancel: () => void
}

/** 计划卡片：展示步骤 + 确认/取消 */
export function PlanCard({ run, disabled, onConfirm, onCancel }: PlanCardProps) {
  const steps = run.plan.steps ?? []
  if (run.status !== 'planned' || steps.length === 0) {
    return null
  }

  return (
    <div className="plan-card">
      <p className="plan-card-title">计划卡片</p>
      <p className="plan-card-reply">{run.reply}</p>
      <ol className="plan-steps">
        {steps.map((step, index) => (
          <li key={step.id}>
            <span className="plan-step-index">{index + 1}.</span>
            <span>{TOOL_LABELS[step.tool_name] ?? step.tool_name}</span>
            {(step.tool_name === 'adjust_image' || step.tool_name === 'adjust_region') && (
              <span className="muted plan-step-params">
                {' '}
                brightness={String(step.params.brightness ?? 0.2)}
              </span>
            )}
          </li>
        ))}
      </ol>
      <div className="plan-actions">
        <button type="button" className="tool-btn tool-btn-export" disabled={disabled} onClick={onConfirm}>
          确认执行
        </button>
        <button type="button" className="tool-btn" disabled={disabled} onClick={onCancel}>
          取消
        </button>
      </div>
    </div>
  )
}
