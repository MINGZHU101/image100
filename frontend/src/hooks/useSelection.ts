import { useCallback, useState } from 'react'
import {
  DEFAULT_BRUSH_RADIUS,
  type BrushSelection,
  type CanvasSelection,
  type RectSelection,
  type SelectionMode,
} from '../types/selection'

interface UseSelectionResult {
  mode: SelectionMode
  selection: CanvasSelection | null
  draftPoints: number[][]
  setMode: (mode: SelectionMode) => void
  beginStroke: (x: number, y: number) => void
  extendStroke: (x: number, y: number) => void
  endStroke: () => CanvasSelection | null
  beginRect: (x: number, y: number) => void
  updateRect: (x: number, y: number) => void
  endRect: () => CanvasSelection | null
  clear: () => void
  replaceSelection: (next: CanvasSelection | null) => void
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value))
}

/** 选区状态机：矩形替换；笔刷同模式追加并集 */
export function useSelection(
  initial: CanvasSelection | null = null,
): UseSelectionResult {
  const [mode, setModeState] = useState<SelectionMode>('none')
  const [selection, setSelection] = useState<CanvasSelection | null>(initial)
  const [draftPoints, setDraftPoints] = useState<number[][]>([])
  const [rectOrigin, setRectOrigin] = useState<[number, number] | null>(null)

  const setMode = useCallback((next: SelectionMode) => {
    setModeState(next)
    setDraftPoints([])
    setRectOrigin(null)
    // 切换工具时重置选区（Q1/Q2）
    if (next === 'none') {
      return
    }
    setSelection(null)
  }, [])

  const replaceSelection = useCallback((next: CanvasSelection | null) => {
    setSelection(next)
    setDraftPoints([])
    setRectOrigin(null)
  }, [])

  const clear = useCallback(() => {
    setSelection(null)
    setDraftPoints([])
    setRectOrigin(null)
    setModeState('none')
  }, [])

  const beginStroke = useCallback(
    (x: number, y: number) => {
      if (mode !== 'brush') {
        return
      }
      setDraftPoints([[clamp01(x), clamp01(y)]])
    },
    [mode],
  )

  const extendStroke = useCallback(
    (x: number, y: number) => {
      if (mode !== 'brush') {
        return
      }
      setDraftPoints((prev) => [...prev, [clamp01(x), clamp01(y)]])
    },
    [mode],
  )

  const endStroke = useCallback((): CanvasSelection | null => {
    if (mode !== 'brush' || draftPoints.length === 0) {
      setDraftPoints([])
      return selection
    }
    const prevStrokes =
      selection?.type === 'brush' ? selection.strokes : []
    const next: BrushSelection = {
      type: 'brush',
      strokes: [...prevStrokes, draftPoints],
      brush_radius: DEFAULT_BRUSH_RADIUS,
      feather: 0,
    }
    setSelection(next)
    setDraftPoints([])
    return next
  }, [mode, draftPoints, selection])

  const beginRect = useCallback(
    (x: number, y: number) => {
      if (mode !== 'rect') {
        return
      }
      const nx = clamp01(x)
      const ny = clamp01(y)
      setRectOrigin([nx, ny])
      setDraftPoints([
        [nx, ny],
        [nx, ny],
      ])
    },
    [mode],
  )

  const updateRect = useCallback(
    (x: number, y: number) => {
      if (mode !== 'rect' || !rectOrigin) {
        return
      }
      setDraftPoints([rectOrigin, [clamp01(x), clamp01(y)]])
    },
    [mode, rectOrigin],
  )

  const endRect = useCallback((): CanvasSelection | null => {
    if (mode !== 'rect' || !rectOrigin || draftPoints.length < 2) {
      setDraftPoints([])
      setRectOrigin(null)
      return selection
    }
    const [x0, y0] = rectOrigin
    const [x1, y1] = draftPoints[1]
    const left = Math.min(x0, x1)
    const top = Math.min(y0, y1)
    const width = Math.abs(x1 - x0)
    const height = Math.abs(y1 - y0)
    setDraftPoints([])
    setRectOrigin(null)
    if (width < 0.005 || height < 0.005) {
      return selection
    }
    const next: RectSelection = {
      type: 'rect',
      rect: { x: left, y: top, width, height },
      feather: 0,
    }
    setSelection(next)
    return next
  }, [mode, rectOrigin, draftPoints, selection])

  return {
    mode,
    selection,
    draftPoints,
    setMode,
    beginStroke,
    extendStroke,
    endStroke,
    beginRect,
    updateRect,
    endRect,
    clear,
    replaceSelection,
  }
}
