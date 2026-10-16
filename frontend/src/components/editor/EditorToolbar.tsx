import { useEffect, useState } from 'react'
import { exportUrl, listTools, type ToolInfo } from '../../api/tools'

interface EditorToolbarProps {
  sessionId: string
  disabled?: boolean
  onRunTool: (toolName: string, params?: Record<string, unknown>) => void
}

/** 编辑器工具栏：提亮 / 去背景 / 翻转 / 导出 */
export function EditorToolbar({ sessionId, disabled, onRunTool }: EditorToolbarProps) {
  const [tools, setTools] = useState<ToolInfo[]>([])

  useEffect(() => {
    let cancelled = false
    void listTools()
      .then((items) => {
        if (!cancelled) {
          setTools(items)
        }
      })
      .catch(() => {
        // 兜底：后端列表失败时仍展示固定按钮
        if (!cancelled) {
          setTools([
            { name: 'adjust_image', label: '提亮', description: '' },
            { name: 'remove_background', label: '去背景', description: '' },
            { name: 'flip_layer', label: '水平翻转', description: '' },
          ])
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="editor-toolbar">
      {tools.map((tool) => (
        <button
          key={tool.name}
          type="button"
          className="tool-btn"
          disabled={disabled}
          title={tool.description}
          onClick={() => {
            // 提亮默认 brightness=+0.2
            if (tool.name === 'adjust_image') {
              onRunTool(tool.name, { brightness: 0.2 })
              return
            }
            onRunTool(tool.name)
          }}
        >
          {tool.label}
        </button>
      ))}
      <a
        className={`tool-btn tool-btn-export${disabled ? ' is-disabled' : ''}`}
        href={exportUrl(sessionId)}
        download
        aria-disabled={disabled}
        onClick={(event) => {
          if (disabled) {
            event.preventDefault()
          }
        }}
      >
        导出
      </a>
    </div>
  )
}
