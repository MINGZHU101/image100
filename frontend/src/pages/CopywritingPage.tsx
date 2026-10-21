import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'

import { assetsApi } from '@/api/assets'
import { streamCopywriting } from '@/api/copywriting'
import { errorMessage, isPointsInsufficient } from '@/hooks/useAuth'

const ASSETS_KEY = ['assets', 'copywriting'] as const

export default function CopywritingPage() {
  const queryClient = useQueryClient()
  const [prompt, setPrompt] = useState('')
  const [assetId, setAssetId] = useState('')
  const [stageTitle, setStageTitle] = useState('')
  const [output, setOutput] = useState('')
  const [error, setError] = useState('')
  const [uploadHint, setUploadHint] = useState('')
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const { data: assets = [] } = useQuery({
    queryKey: ASSETS_KEY,
    queryFn: () => assetsApi.list(30),
  })
  const selected = assets.find((item) => item.id === assetId)

  const run = useMutation({
    mutationFn: async () => {
      setError('')
      setOutput('')
      setStageTitle('准备中…')
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      let text = ''
      let finishedOk = false
      await streamCopywriting(
        { prompt: prompt.trim(), asset_id: assetId || undefined },
        (event) => {
          if (event.error) {
            setError(event.error)
            setStageTitle('生成失败')
            return
          }
          if (event.done) {
            finishedOk = true
            setStageTitle('生成完成')
            return
          }
          if (event.title) setStageTitle(event.title)
          if (event.content) {
            text += event.content
            setOutput(text)
          }
        },
        controller.signal,
      )
      // 流正常结束但未收到 done 事件时，也收口标题
      if (!finishedOk && text) setStageTitle('生成完成')
    },
    onError: (err) => {
      setStageTitle('生成失败')
      setError(errorMessage(err))
      if (isPointsInsufficient(err)) {
        window.dispatchEvent(
          new CustomEvent('points-insufficient', { detail: errorMessage(err) }),
        )
      }
    },
  })

  const upload = useMutation({
    mutationFn: (file: File) => assetsApi.upload(file),
    onMutate: () => {
      setUploadHint('上传中…')
      setError('')
    },
    onSuccess: async (asset) => {
      // 先写入缓存再选中，避免下拉选项里还没有新 id
      await queryClient.invalidateQueries({ queryKey: ASSETS_KEY })
      await queryClient.refetchQueries({ queryKey: ASSETS_KEY })
      setAssetId(asset.id)
      setUploadHint(`已选中配图 ${asset.width}×${asset.height}`)
    },
    onError: (err) => {
      setUploadHint('')
      setError(errorMessage(err) || '上传失败')
    },
  })

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-ink text-2xl font-semibold tracking-tight">文案生成</h1>
      <p className="text-muted mt-2 text-sm">
        输入商品提示词，可选配图；成功后扣 40 积分。生成过程分阶段流式展示。
      </p>

      <div className="border-line bg-paper shadow-panel mt-6 space-y-4 rounded-panel border p-5">
        <label className="block">
          <span className="text-muted mb-1.5 block text-sm">产品提示词</span>
          <textarea
            rows={4}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：全自动豆浆机，1 分钟速热，适合独居白领"
            className="border-line focus:border-brand rounded-control w-full border px-3.5 py-2.5 text-sm outline-none"
          />
        </label>

        <div className="flex flex-wrap items-end gap-3">
          <label className="block min-w-[200px] flex-1">
            <span className="text-muted mb-1.5 block text-sm">可选：已有素材</span>
            <select
              value={assetId}
              onChange={(e) => {
                setAssetId(e.target.value)
                setUploadHint(e.target.value ? '已选择素材' : '')
              }}
              className="border-line rounded-control w-full border px-3 py-2 text-sm"
            >
              <option value="">不使用图片</option>
              {assets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.id.slice(0, 8)}… {asset.width}×{asset.height}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={upload.isPending}
            onClick={() => fileInputRef.current?.click()}
            className="border-line hover:bg-soft rounded-control border px-3 py-2 text-sm disabled:opacity-50"
          >
            {upload.isPending ? '上传中…' : '上传图片'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              e.target.value = ''
              if (file) upload.mutate(file)
            }}
          />
        </div>

        {(uploadHint || selected) && (
          <div className="flex items-center gap-3">
            {selected?.url && (
              <img
                src={selected.url}
                alt="配图预览"
                className="border-line size-16 rounded-control border object-cover"
              />
            )}
            <p className="text-muted text-sm">{uploadHint || '已选择配图'}</p>
            {assetId && (
              <button
                type="button"
                className="text-muted text-sm hover:underline"
                onClick={() => {
                  setAssetId('')
                  setUploadHint('')
                }}
              >
                清除配图
              </button>
            )}
          </div>
        )}

        <button
          type="button"
          disabled={!prompt.trim() || run.isPending}
          onClick={() => run.mutate()}
          className="bg-ink hover:bg-dark rounded-control px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {run.isPending ? '生成中…' : '开始生成'}
        </button>
        {run.isPending && (
          <button
            type="button"
            className="text-muted ml-3 text-sm hover:underline"
            onClick={() => abortRef.current?.abort()}
          >
            停止
          </button>
        )}
      </div>

      {(stageTitle || output || error) && (
        <div className="border-line mt-6 rounded-panel border bg-soft/40 p-5">
          {stageTitle && <p className="text-brand-strong text-sm font-medium">{stageTitle}</p>}
          {error && <p className="text-danger mt-2 text-sm">{error}</p>}
          {output && (
            <pre className="text-ink mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed">
              {output}
            </pre>
          )}
          {output && !run.isPending && (
            <button
              type="button"
              className="border-line mt-4 rounded-control border px-3 py-1.5 text-sm"
              onClick={() => navigator.clipboard.writeText(output)}
            >
              复制全文
            </button>
          )}
        </div>
      )}
    </div>
  )
}
