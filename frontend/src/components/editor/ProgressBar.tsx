interface ProgressBarProps {
  progress: number
  message: string
  visible: boolean
}

/** 工具运行进度条 */
export function ProgressBar({ progress, message, visible }: ProgressBarProps) {
  if (!visible) {
    return null
  }
  const clamped = Math.max(0, Math.min(100, progress))
  return (
    <div className="progress-panel" role="status" aria-live="polite">
      <div className="progress-meta">
        <span>{message || '处理中…'}</span>
        <span>{clamped}%</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${clamped}%` }} />
      </div>
    </div>
  )
}
