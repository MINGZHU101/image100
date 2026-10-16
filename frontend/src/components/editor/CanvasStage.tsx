import { useEffect, useMemo, useRef, useState } from 'react'
import { Stage, Layer, Image as KonvaImage } from 'react-konva'
import type Konva from 'konva'

interface CanvasStageProps {
  imageUrl: string
  canvasWidth: number
  canvasHeight: number
}

/** Konva 画布：显示主图层，支持滚轮缩放与拖拽平移 */
export function CanvasStage({ imageUrl, canvasWidth, canvasHeight }: CanvasStageProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<Konva.Stage>(null)
  const [image, setImage] = useState<HTMLImageElement | null>(null)
  const [size, setSize] = useState({ width: 800, height: 560 })
  const [scale, setScale] = useState(1)

  useEffect(() => {
    // URL 变化时先清空，避免短暂显示旧图
    setImage(null)
    const img = new window.Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => setImage(img)
    img.src = imageUrl
  }, [imageUrl])

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

  // 初始适配：让整图落在视口内
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
  }, [fitScale, imageUrl])

  const offsetX = (size.width - canvasWidth * scale) / 2
  const offsetY = (size.height - canvasHeight * scale) / 2

  return (
    <div className="canvas-wrap" ref={containerRef}>
      <Stage
        ref={stageRef}
        width={size.width}
        height={size.height}
        scaleX={scale}
        scaleY={scale}
        x={offsetX}
        y={offsetY}
        draggable
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
      >
        <Layer>
          {image && (
            <KonvaImage image={image} width={canvasWidth} height={canvasHeight} />
          )}
        </Layer>
      </Stage>
    </div>
  )
}
