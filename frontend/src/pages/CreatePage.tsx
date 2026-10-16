import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createSession } from '../api/sessions'
import { ProgressBar } from '../components/editor/ProgressBar'
import { useGeneration } from '../hooks/useGeneration'

/** 文生图创作页：Mock/真实切换 → 候选图 → 进入编辑器 */
export function CreatePage() {
  const navigate = useNavigate()
  const gen = useGeneration()
  const [prompt, setPrompt] = useState('白色背景的运动鞋电商主图，居中，光线柔和')
  const [count, setCount] = useState(2)
  const [opening, setOpening] = useState('')

  async function openInEditor(assetId: string) {
    setOpening(assetId)
    try {
      const session = await createSession(assetId)
      navigate(`/editor/${session.id}`)
    } catch (err) {
      setOpening('')
      window.alert(err instanceof Error ? err.message : '创建会话失败')
    }
  }

  return (
    <main className="landing create-page">
      <p className="brand">image100</p>
      <h1>AI 创作</h1>
      <p className="tagline">用一句话生成商品图候选，选一张进入编辑器继续精修。</p>
      <p>
        <Link to="/" className="back-link">
          ← 返回上传入口
        </Link>
      </p>

      <div className="planner-toggle" role="group" aria-label="生图方式">
        <button
          type="button"
          className={`planner-btn${gen.provider === 'mock' ? ' is-active' : ''}`}
          disabled={gen.busy}
          onClick={() => gen.setProvider('mock')}
        >
          Mock
        </button>
        <button
          type="button"
          className={`planner-btn${gen.provider === 'dashscope' ? ' is-active' : ''}`}
          disabled={gen.busy || !gen.dashscopeAvailable}
          onClick={() => gen.setProvider('dashscope')}
        >
          真实生图
        </button>
      </div>

      <form
        className="create-form"
        onSubmit={(event) => {
          event.preventDefault()
          void gen.generate(prompt, count)
        }}
      >
        <textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={4}
          disabled={gen.busy}
        />
        <label className="muted">
          张数
          <select
            value={count}
            disabled={gen.busy}
            onChange={(event) => setCount(Number(event.target.value))}
          >
            {[1, 2, 3, 4].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="upload-btn" disabled={gen.busy || !prompt.trim()}>
          {gen.busy ? '生成中…' : '生成候选图'}
        </button>
      </form>

      <ProgressBar progress={gen.progress} message={gen.message} visible={gen.busy || gen.progress > 0} />
      {gen.error && <p className="status-error">{gen.error}</p>}

      <div className="candidate-grid">
        {gen.assetIds.map((assetId) => (
          <button
            key={assetId}
            type="button"
            className="candidate-card"
            disabled={opening === assetId}
            onClick={() => {
              void openInEditor(assetId)
            }}
          >
            <img src={`/api/assets/${assetId}/file`} alt="候选图" />
            <span>{opening === assetId ? '进入中…' : '用这张进入编辑器'}</span>
          </button>
        ))}
      </div>
    </main>
  )
}
