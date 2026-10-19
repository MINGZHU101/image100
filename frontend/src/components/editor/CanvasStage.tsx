import { useEffect, useMemo, useRef, useState } from 'react'
import { Stage, Layer, Image as KonvaImage, Rect } from 'react-konva'
import type Konva from 'konva'
import type { CanvasSelection, SelectionMode } from '../../types/selection'
import { SelectionOverlay } from './SelectionOverlay'

export interface CanvasLayerView {
  id: string
  url: string
  visible: boolean
}

interface CanvasStageProps {
  layers: CanvasLayerView[]
  canvasWidth: number
  canvasHeight: number
  selectionMode: SelectionMode
  selection: CanvasSelection | null
  draftPoints: number[][]
  onBeginStroke: (x: number, y: number) => void
  onExtendStroke: (x: number, y: number) => void
  onEndStroke: () => void
  onBeginRect: (x: number, y: number) => void
  onUpdateRect: (x: number, y: number) => void
  onEndRect: () => void
}

/** Konva 画布：多层叠放 + 选区；支持缩放/平移（非选区模式） */
export function CanvasStage({
  layers,
  canvasWidth,
  canvasHeight,
  selectionMode,
  selection,
  draftPoints,
  onBeginStroke,
  onExtendStroke,
  onEndStroke,
  onBeginRect,
  onUpdateRect,
  onEndRect,
}: CanvasStageProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<Konva.Stage>(null)
  const [images, setImages] = useState<Record<string, HTMLImageElement>>({})
  const [size, setSize] = useState({ width: 800, height: 560 })
  const [scale, setScale] = useState(1)
  const drawingRef = useRef(false)

  const selecting = selectionMode === 'rect' || selectionMode === 'brush'
  const layerKey = layers.map((layer) => `${layer.id}:${layer.url}:${layer.visible}`).join('|')

  useEffect(() => {
    let cancelled = false
    const next: Record<string, HTMLImageElement> = {}
    const loaders = layers.map(
      (layer) =>
        new Promise<void>((resolve) => {
          if (!layer.visible || !layer.url) {
            resolve()
            return
          }
          const img = new window.Image()
          img.crossOrigin = 'anonymous'
          img.onload = () => {
            next[layer.id] = img
            resolve()
          }
          img.onerror = () => resolve()
          img.src = layer.url
        }),
    )
    void Promise.all(loaders).then(() => {
      if (!cancelled) {
        setImages(next)
      }
    })
    return () => {
      cancelled = true
    }
  }, [layerKey])

  useEffect(() => {
    const element = containerRef.current
    if (!element) {
      return
    }
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) {
        return
      }
      const { width, height } = entry.contentRect
      setSize({
        width: Math.max(320, Math.floor(width)),
        height: Math.max(320, Math.floor(height)),
      })
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])

  const fitScale = useMemo(() => {
    if (canvasWidth <= 0 || canvasHeight <= 0) {
      return 1
    }
    const padding = 40
    const sx = (size.width - padding) / canvasWidth
    const sy = (size.height - padding) / canvasHeight
    return Math.min(sx, sy, 1)
  }, [canvasWidth, canvasHeight, size.width, size.height])

  useEffect(() => {
    setScale(fitScale)
  }, [fitScale, layerKey])

  const offsetX = (size.width - canvasWidth * scale) / 2
  const offsetY = (size.height - canvasHeight * scale) / 2

  function pointerNormalized(): [number, number] | null {
    const stage = stageRef.current
    if (!stage) {
      return null
    }
    const point = stage.getRelativePointerPosition()
    if (!point) {
      return null
    }
    return [point.x / canvasWidth, point.y / canvasHeight]
  }

  return (
    <div className={`canvas-wrap has-checkerboard${selecting ? ' is-selecting' : ''}`} ref={containerRef}>
      <Stage
        ref={stageRef}
        width={size.width}
        height={size.height}
        scaleX={scale}
        scaleY={scale}
        x={offsetX}
        y={offsetY}
        draggable={!selecting}
        onWheel={(event) => {
          event.evt.preventDefault()
          const stage = stageRef.current
          if (!stage) {
            return
          }
          const oldScale = stage.scaleX()
          const pointer = stage.getPointerPosition()
          if (!pointer) {
            return
          }
          const direction = event.evt.deltaY > 0 ? -1 : 1
          const next = Math.min(4, Math.max(0.1, oldScale * (1 + direction * 0.08)))
          const mousePointTo = {
            x: (pointer.x - stage.x()) / oldScale,
            y: (pointer.y - stage.y()) / oldScale,
          }
          stage.scale({ x: next, y: next })
          stage.position({
            x: pointer.x - mousePointTo.x * next,
            y: pointer.y - mousePointTo.y * next,
          })
          setScale(next)
        }}
        onMouseDown={() => {
          if (!selecting) {
            return
          }
          const coords = pointerNormalized()
          if (!coords) {
            return
          }
          drawingRef.current = true
          if (selectionMode === 'brush') {
            onBeginStroke(coords[0], coords[1])
          } else if (selectionMode === 'rect') {
            onBeginRect(coords[0], coords[1])
          }
        }}
        onMouseMove={() => {
          if (!selecting || !drawingRef.current) {
            return
          }
          const coords = pointerNormalized()
          if (!coords) {
            return
          }
          if (selectionMode === 'brush') {
            onExtendStroke(coords[0], coords[1])
          } else if (selectionMode === 'rect') {
            onUpdateRect(coords[0], coords[1])
          }
        }}
        onMouseUp={() => {
          if (!selecting || !drawingRef.current) {
            return
          }
          drawingRef.current = false
          if (selectionMode === 'brush') {
            onEndStroke()
          } else if (selectionMode === 'rect') {
            onEndRect()
          }
        }}
        onMouseLeave={() => {
          if (!selecting || !drawingRef.current) {
            return
          }
          drawingRef.current = false
          if (selectionMode === 'brush') {
            onEndStroke()
          } else if (selectionMode === 'rect') {
            onEndRect()
          }
        }}
      >
        <Layer>
          {/* 棋盘格提示透明区域 */}
          <Rect
            x={0}
            y={0}
            width={canvasWidth}
            height={canvasHeight}
            fillPatternImage={undefined}
            fill="#e8edf3"
            listening={false}
          />
          {layers.map((layer) => {
            if (!layer.visible) {
              return null
            }
            const image = images[layer.id]
            if (!image) {
              return null
            }
            return (
              <KonvaImage
                key={layer.id}
                image={image}
                width={canvasWidth}
                height={canvasHeight}
              />
            )
          })}
        </Layer>
        <Layer listening={false}>
          <SelectionOverlay
            canvasWidth={canvasWidth}
            canvasHeight={canvasHeight}
            selection={selection}
            draftPoints={draftPoints}
            mode={selectionMode}
          />
        </Layer>
      </Stage>
    </div>
  )
}
