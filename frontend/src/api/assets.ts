/** 资产相关 API */

export interface AssetOut {
  id: string
  storage_key: string
  width: number
  height: number
  mime: string
  created_at: string
  file_url: string
}

export interface AssetListOut {
  items: AssetOut[]
}

/** multipart 上传商品图，字段名 file */
export async function uploadAsset(file: File): Promise<AssetOut> {
  const form = new FormData()
  form.append('file', file)
  const response = await fetch('/api/assets', {
    method: 'POST',
    body: form,
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`上传失败：${response.status} ${text}`)
  }
  return response.json() as Promise<AssetOut>
}

export async function listAssets(): Promise<AssetOut[]> {
  const response = await fetch('/api/assets')
  if (!response.ok) {
    throw new Error(`拉取资产列表失败：HTTP ${response.status}`)
  }
  const data = (await response.json()) as AssetListOut
  return data.items
}
