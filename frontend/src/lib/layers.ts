import type { LayerDocument } from '@/api/sessions'

const BASE = 'layer_main'
const SUBJECT = 'layer_subject'
const BACKGROUND = 'layer_background'

/**
 * 已拆层或有多张图像层时，整图类生成（换背景、扩图等）只挂图片墙。
 * 本仓拆层 id：layer_background / layer_subject。
 */
export function wallOnly(document: LayerDocument): boolean {
  if (document.layers.filter((layer) => layer.kind === 'image').length > 1) return true
  const ids = new Set(document.layers.map((layer) => layer.id))
  if (ids.has(BACKGROUND) && ids.has(SUBJECT)) return true
  return ids.has(BACKGROUND) && !ids.has(BASE)
}
