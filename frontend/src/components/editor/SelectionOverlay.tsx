import { Line, Rect } from 'react-konva'
import {
  DEFAULT_BRUSH_RADIUS,
  type CanvasSelection,
} from '../../types/selection'

interface SelectionOverlayProps {
  canvasWidth: number
  canvasHeight: number
  selection: CanvasSelection | null
  draftPoints: number[][]
  mode: 'none' | 'rect' | 'brush'
}

const FILL = 'rgba(95, 152, 173, 0.35)'
const STROKE = '#5f98ad'

/** 选区可视化：已确认选区 + 拖拽中草稿 */
export function SelectionOverlay({
  canvasWidth,
  canvasHeight,
  selection,
  draftPoints,
  mode,
}: SelectionOverlayProps) {
  const brushPx = Math.max(2, Math.min(canvasWidth, canvasHeight) * DEFAULT_BRUSH_RADIUS)

  return (
    <>
      {selection?.type === 'rect' && (
        <Rect
          x={selection.rect.x * canvasWidth}
          y={selection.rect.y * canvasHeight}
          width={selection.rect.width * canvasWidth}
          height={selection.rect.height * canvasHeight}
          fill={FILL}
          stroke={STROKE}
          strokeWidth={2}
          listening={false}
        />
      )}

      {selection?.type === 'brush' &&
        selection.strokes.map((stroke, index) => (
          <Line
            key={`stroke-${index}`}
            points={stroke.flatMap(([x, y]) => [x * canvasWidth, y * canvasHeight])}
            closed={stroke.length > 2}
            fill={stroke.length > 2 ? FILL : undefined}
            stroke={STROKE}
            strokeWidth={brushPx}
            lineCap="round"
            lineJoin="round"
            opacity={0.55}
            listening={false}
          />
        ))}

      {mode === 'rect' && draftPoints.length >= 2 && (
        <Rect
          x={Math.min(draftPoints[0][0], draftPoints[1][0]) * canvasWidth}
          y={Math.min(draftPoints[0][1], draftPoints[1][1]) * canvasHeight}
          width={Math.abs(draftPoints[1][0] - draftPoints[0][0]) * canvasWidth}
          height={Math.abs(draftPoints[1][1] - draftPoints[0][1]) * canvasHeight}
          fill={FILL}
          stroke={STROKE}
          strokeWidth={2}
          dash={[6, 4]}
          listening={false}
        />
      )}

      {mode === 'brush' && draftPoints.length > 0 && (
        <Line
          points={draftPoints.flatMap(([x, y]) => [x * canvasWidth, y * canvasHeight])}
          closed={draftPoints.length > 2}
          fill={draftPoints.length > 2 ? FILL : undefined}
          stroke={STROKE}
          strokeWidth={brushPx}
          lineCap="round"
          lineJoin="round"
          opacity={0.45}
          listening={false}
        />
      )}
    </>
  )
}
