import { useEffect, useState } from 'react'
import { exportUrl, listTools, type ToolInfo } from '../../api/tools'
import type { SelectionMode } from '../../types/selection'

interface EditorToolbarProps {
  sessionId: string
  disabled?: boolean
  selectionMode: SelectionMode
  onSelectionModeChange: (mode: SelectionMode) => void
  onClearSelection: () => void
  onRunTool: (toolName: string, params?: Record<string, unknown>) => void
}

/** 编辑器工具栏：选区模式 + 修图工具 + 导出 */
export function EditorToolbar({
  sessionId,
  disabled,
  selectionMode,
  onSelectionModeChange,
  onClearSelection,
  onRunTool,
}: EditorToolbarProps) {
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
            { name: 'adjust_region', label: '局部提亮', description: '' },
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
      <div className="toolbar-group" role="group" aria-label="选区">
        <button
          type="button"
          className={`tool-btn${selectionMode === 'rect' ? ' is-active' : ''}`}
          disabled={disabled}
          title="矩形选区"
          onClick={() => {
            onSelectionModeChange(selectionMode === 'rect' ? 'none' : 'rect')
          }}
        >
          矩形选区
        </button>
        <button
          type="button"
          className={`tool-btn${selectionMode === 'brush' ? ' is-active' : ''}`}
          disabled={disabled}
          title="笔刷选区"
          onClick={() => {
            onSelectionModeChange(selectionMode === 'brush' ? 'none' : 'brush')
          }}
        >
          笔刷选区
        </button>
        <button
          type="button"
          className="tool-btn"
          disabled={disabled}
          title="清除选区"
          onClick={onClearSelection}
        >
          清除选区
        </button>
      </div>

      <div className="toolbar-group" role="group" aria-label="修图">
        {tools.map((tool) => (
          <button
            key={tool.name}
            type="button"
            className="tool-btn"
            disabled={disabled}
            title={tool.description}
            onClick={() => {
              // 提亮 / 局部提亮默认 brightness=+0.2
              if (tool.name === 'adjust_image' || tool.name === 'adjust_region') {
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
    </div>
  )
}
