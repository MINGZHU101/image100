export type ImageProvider = 'mock' | 'dashscope'

export interface ImageProviderOptions {
  default_provider: ImageProvider
  dashscope_available: boolean
  providers: ImageProvider[]
}

export interface GenerationCreateOut {
  generation_id: string
  status: string
}

export interface GenerationRunOut {
  id: string
  prompt: string
  params: { width?: number; height?: number; count?: number }
  image_provider: string
  status: string
  progress: number
  result_asset_ids: string[]
  error: string | null
}

export async function getImageProviderOptions(): Promise<ImageProviderOptions> {
  const response = await fetch('/api/generations/provider-options')
  if (!response.ok) {
    throw new Error(`获取生图选项失败：HTTP ${response.status}`)
  }
  return response.json() as Promise<ImageProviderOptions>
}

export async function createGeneration(body: {
  prompt: string
  width: number
  height: number
  count: number
  image_provider: ImageProvider
}): Promise<GenerationCreateOut> {
  const response = await fetch('/api/generations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`创建生图失败：${response.status} ${text}`)
  }
  return response.json() as Promise<GenerationCreateOut>
}

export async function getGeneration(id: string): Promise<GenerationRunOut> {
  const response = await fetch(`/api/generations/${id}`)
  if (!response.ok) {
    throw new Error(`查询生图失败：HTTP ${response.status}`)
  }
  return response.json() as Promise<GenerationRunOut>
}
