import { api } from '@/api/client'
import type { Asset } from '@/api/assets'

export type Ratio = '1:1' | '4:5' | '3:4' | '9:16' | '16:9'

export type RunStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'canceled'

export type Run = {
  id: string
  tool: string
  status: RunStatus
  progress: number
  stage: string
  error: string | null
  prompt: string | null
  candidates: Asset[]
  result: Record<string, unknown>
}

export type GenerateInput = {
  prompt: string
  ratio: Ratio
  count: number
  negative_prompt?: string
  reference_asset_ids?: string[]
  image_model?: string
}

export type ImageProviderOptions = {
  default_provider: 'mock' | 'dashscope'
  dashscope_available: boolean
  providers: Array<'mock' | 'dashscope'>
  default_image_model: string
  image_models: string[]
}

export const RATIO_LABELS: Record<Ratio, string> = {
  '1:1': '方形 1:1',
  '4:5': '竖版 4:5',
  '3:4': '竖版 3:4',
  '9:16': '长图 9:16',
  '16:9': '横版 16:9',
}

export function isTerminal(status: RunStatus) {
  return status === 'succeeded' || status === 'failed' || status === 'canceled'
}

export const runsApi = {
  generate: (input: GenerateInput) => api.post<Run>('/generations', input),
  get: (id: string) => api.get<Run>(`/runs/${id}`),
  providerOptions: () => api.get<ImageProviderOptions>('/generations/provider-options'),
}

/** 创作页展示用短名 */
export function imageModelLabel(model: string): string {
  if (model.includes('2.0')) return '通义万相 2.0'
  if (model.includes('3.0')) return '通义万相 3.0'
  return model
}
