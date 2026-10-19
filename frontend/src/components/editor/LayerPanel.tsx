import type { LayerInfo } from '../../api/sessions'

interface LayerPanelProps {
  layers: LayerInfo[]
  activeLayerId: string | null | undefined
  disabled?: boolean
  onToggleVisible: (layerId: string, visible: boolean) => void
  onSelect: (layerId: string) => void
}

/** 极简图层面板：列表 + 显隐 + 选中（选中层在画布上会加亮） */
export function LayerPanel({
  layers,
  activeLayerId,
  disabled,
  onToggleVisible,
  onSelect,
}: LayerPanelProps) {
  // 面板自上而下显示：顶层在上
  const ordered = [...layers].reverse()

  return (
    <aside className="layer-panel" aria-label="图层面板">
      <p className="layer-panel-title">图层</p>
      <p className="layer-panel-hint">点名称：独显并设为当前层；点显/隐：单独开关该层</p>
      <ul className="layer-list">
        {ordered.map((layer) => {
          const active = layer.id === activeLayerId
          return (
            <li key={layer.id} className="layer-row">
              <button
                type="button"
                className="layer-eye-btn"
                disabled={disabled}
                title={layer.visible ? '隐藏该层' : '显示该层'}
                onClick={() => onToggleVisible(layer.id, !layer.visible)}
              >
                {layer.visible ? '显' : '隐'}
              </button>
              <button
                type="button"
                className={`layer-item${active ? ' is-active' : ''}`}
                disabled={disabled}
                onClick={() => onSelect(layer.id)}
              >
                <span className="layer-name">{layer.name}</span>
                {active && <span className="layer-active-tag">当前</span>}
              </button>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
