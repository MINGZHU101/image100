import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  RATIO_LABELS,
  imageModelLabel,
  runsApi,
  type GenerateInput,
  type Ratio,
} from '@/api/runs'

const RATIOS = Object.keys(RATIO_LABELS) as Ratio[]
const COUNTS = [1, 2, 4, 6]

export default function GenerateForm({
  onSubmit,
  pending,
  defaultPrompt = '',
}: {
  onSubmit: (input: GenerateInput) => void
  pending: boolean
  defaultPrompt?: string
}) {
  const [prompt, setPrompt] = useState(defaultPrompt)
  const [ratio, setRatio] = useState<Ratio>('1:1')
  const [count, setCount] = useState(4)
  const [negative, setNegative] = useState('')
  const [advanced, setAdvanced] = useState(false)
  const [imageModel, setImageModel] = useState('')

  const { data: options } = useQuery({
    queryKey: ['generations', 'provider-options'],
    queryFn: () => runsApi.providerOptions(),
    staleTime: 60_000,
  })

  useEffect(() => {
    if (!options) return
    if (!imageModel) setImageModel(options.default_image_model)
  }, [options, imageModel])

  const models = options?.image_models?.length
    ? options.image_models
    : ['qwen-image-2.0-pro-2026-06-22', 'qwen-image-3.0-pro']
  const selectedModel = imageModel || options?.default_image_model || models[0]

  const canSubmit = prompt.trim().length > 0 && !pending

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (!canSubmit) return
        onSubmit({
          prompt: prompt.trim(),
          ratio,
          count,
          negative_prompt: negative.trim() || undefined,
          image_model: selectedModel,
        })
      }}
      className="border-line bg-paper shadow-panel rounded-panel border p-2"
    >
      <textarea
        rows={3}
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault()
            event.currentTarget.form?.requestSubmit()
          }
        }}
        placeholder="描述你想要的画面，例如：白色陶瓷马克杯放在浅木色桌面，晨光从左侧照入。回车生成，Shift+Enter 换行"
        aria-label="画面描述"
        className="text-ink placeholder:text-faint w-full resize-none bg-transparent px-4 pt-3 pb-1 text-[15px] leading-relaxed outline-none"
      />

      <div className="flex flex-wrap items-center gap-2 px-2 pb-1">
        <Segmented
          label="比例"
          options={RATIOS.map((value) => ({ value, label: value }))}
          value={ratio}
          onChange={setRatio}
        />
        <Segmented
          label="数量"
          options={COUNTS.map((value) => ({ value, label: String(value) }))}
          value={count}
          onChange={setCount}
        />
        <Segmented
          label="模型"
          options={models.map((value) => ({
            value,
            label: imageModelLabel(value),
          }))}
          value={selectedModel}
          onChange={setImageModel}
        />

        <button
          type="button"
          onClick={() => setAdvanced((open) => !open)}
          className="text-muted hover:text-ink rounded-control px-2 py-1.5 text-xs font-medium transition-colors"
        >
          {advanced ? '收起排除项' : '排除项'}
        </button>

        <button
          type="submit"
          disabled={!canSubmit}
          className="bg-ink hover:bg-dark rounded-control ml-auto px-4 py-2 text-sm font-medium text-white transition-all duration-150 active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40 disabled:active:scale-100"
        >
          {pending ? '提交中…' : '生成'}
        </button>
      </div>
      <p className="text-faint px-3 pb-2 text-[11px]">
        {pending
          ? '任务已提交，稍后会跳到候选页'
          : `当前模型 ${imageModelLabel(selectedModel)} · 回车生成 · Shift+Enter 换行`}
      </p>

      {advanced && (
        <div className="border-line animate-fade-in mt-1 border-t px-4 py-3">
          <input
            value={negative}
            onChange={(event) => setNegative(event.target.value)}
            placeholder="不希望出现的内容，例如：文字、水印、多余的手"
            aria-label="排除项"
            className="text-ink placeholder:text-faint w-full bg-transparent text-sm outline-none"
          />
        </div>
      )}
    </form>
  )
}

function Segmented<T extends string | number>({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div className="border-line rounded-control flex items-center gap-0.5 border p-0.5">
      <span className="text-faint px-1.5 text-xs">{label}</span>
      {options.map((option) => (
        <button
          key={String(option.value)}
          type="button"
          onClick={() => onChange(option.value)}
          aria-pressed={option.value === value}
          className={`rounded-[6px] px-2 py-1 text-xs font-medium transition-all duration-150 active:scale-95 ${
            option.value === value ? 'bg-ink text-white' : 'text-muted hover:bg-soft hover:text-ink'
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
