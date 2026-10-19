/** 选区：相对画布 0～1 归一化 */

export type SelectionMode = 'none' | 'rect' | 'brush'

export interface RectSelection {
  type: 'rect'
  rect: { x: number; y: number; width: number; height: number }
  feather: number
}

export interface BrushSelection {
  type: 'brush'
  strokes: number[][][]
  brush_radius: number
  feather: number
}

export type CanvasSelection = RectSelection | BrushSelection

export const DEFAULT_BRUSH_RADIUS = 0.03
