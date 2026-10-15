import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadAsset } from '../api/assets'
import { createSession } from '../api/sessions'

/** 上传商品图：成功后自动建会话并进入编辑器 */
export function ImageUpload() {
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleFile(file: File | undefined) {
    if (!file) {
      return
    }
    setBusy(true)
    setError('')
    try {
      const asset = await uploadAsset(file)
      const session = await createSession(asset.id)
      navigate(`/editor/${session.id}`)
    } catch (err) {
      const message = err instanceof Error ? err.message : '上传失败'
      setError(message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="upload-block">
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0]
          void handleFile(file)
          event.target.value = ''
        }}
      />
      <button
        type="button"
        className="upload-btn"
        disabled={busy}
        onClick={() => inputRef.current?.click()}
      >
        {busy ? '上传中…' : '上传商品图并开始修图'}
      </button>
      {error && <p className="status-error">{error}</p>}
    </div>
  )
}
