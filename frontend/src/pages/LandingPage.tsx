import { useEffect, useState } from 'react'
import { getHealth, type HealthResponse } from '../api/client'

type LoadState = 'loading' | 'ready' | 'failed'

/** 落地页：产品介绍 + 后端 health 状态 */
export function LandingPage() {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadHealth() {
      try {
        const data = await getHealth()
        if (cancelled) {
          return
        }
        setHealth(data)
        setLoadState('ready')
      } catch (error) {
        if (cancelled) {
          return
        }
        const message = error instanceof Error ? error.message : '未知错误'
        setErrorMessage(message)
        setLoadState('failed')
      }
    }

    void loadHealth()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="landing">
      <p className="brand">image100</p>
      <h1>电商商品视觉</h1>
      <p className="tagline">
        面向中小电商卖家的自然语言修图工作台——上传商品图，用一句话说清想要的视觉效果。
      </p>

      <section className="health" aria-live="polite">
        <h2>系统状态</h2>
        {loadState === 'loading' && <p className="muted">正在检测后端连通性…</p>}
        {loadState === 'failed' && (
          <p className="status-error">无法连接后端：{errorMessage}</p>
        )}
        {loadState === 'ready' && health && (
          <ul className="health-list">
            <li>
              <span>整体</span>
              <StatusBadge value={health.status} />
            </li>
            <li>
              <span>PostgreSQL</span>
              <StatusBadge value={health.postgres} />
            </li>
            <li>
              <span>Redis</span>
              <StatusBadge value={health.redis} />
            </li>
          </ul>
        )}
      </section>
    </main>
  )
}

function StatusBadge({ value }: { value: string }) {
  const isOk = value === 'ok'
  const className = isOk ? 'badge ok' : 'badge warn'
  return <span className={className}>{value}</span>
}
