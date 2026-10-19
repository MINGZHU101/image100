import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  getSession,
  patchLayers,
  patchSelection,
  type SessionOut,
} from '../api/sessions'
import { AgentConversation } from '../components/editor/AgentConversation'
import { CanvasStage } from '../components/editor/CanvasStage'
import { EditorToolbar } from '../components/editor/EditorToolbar'
import { LayerPanel } from '../components/editor/LayerPanel'
import { ProgressBar } from '../components/editor/ProgressBar'
import { useAgent } from '../hooks/useAgent'
import { useSelection } from '../hooks/useSelection'
import { useToolRun } from '../hooks/useToolRun'
import type { CanvasSelection, SelectionMode } from '../types/selection'

/** 编辑器页：图层 + 选区 + 工具栏 + Agent */
export function EditorPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [session, setSession] = useState<SessionOut | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const selectionApi = useSelection()

  const syncSelection = useCallback(
    async (next: CanvasSelection | null) => {
      if (!sessionId) {
        return
      }
      try {
        const data = await patchSelection(sessionId, next)
        setSession(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '同步选区失败')
      }
    },
    [sessionId],
  )

  const reloadSession = useCallback(async () => {
    if (!sessionId) {
      return
    }
    const data = await getSession(sessionId)
    setSession(data)
    selectionApi.replaceSelection(data.document.selection)
  }, [sessionId, selectionApi.replaceSelection])

  useEffect(() => {
    if (!sessionId) {
      setError('缺少会话 ID')
      setLoading(false)
      return
    }
    let cancelled = false
    async function load() {
      try {
        const data = await getSession(sessionId!)
        if (!cancelled) {
          setSession(data)
          selectionApi.replaceSelection(data.document.selection)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载失败')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }
    void load()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  const onCompleted = useCallback(async () => {
    try {
      await reloadSession()
    } catch (err) {
      setError(err instanceof Error ? err.message : '刷新会话失败')
    }
  }, [reloadSession])

  const { progress, message, running, error: runError, runTool } = useToolRun({
    sessionId: sessionId ?? '',
    onCompleted,
  })

  const agent = useAgent({
    sessionId: sessionId ?? '',
    onCompleted,
  })

  const canvasLayers = useMemo(() => {
    if (!session) {
      return []
    }
    const stamp = session.updated_at ?? ''
    return session.document.layers.map((layer) => ({
      id: layer.id,
      visible: layer.visible,
      url: `/api/assets/${layer.asset_id}/file?t=${stamp}`,
    }))
  }, [session])

  const hasLayers = (session?.document.layers.length ?? 0) > 0
  const toolsBusy = running || agent.busy

  const handleModeChange = useCallback(
    (mode: SelectionMode) => {
      selectionApi.setMode(mode)
      if (mode === 'rect' || mode === 'brush') {
        void syncSelection(null)
      }
    },
    [selectionApi, syncSelection],
  )

  const handleClearSelection = useCallback(() => {
    selectionApi.clear()
    void syncSelection(null)
  }, [selectionApi, syncSelection])

  const handleEndStroke = useCallback(() => {
    const next = selectionApi.endStroke()
    void syncSelection(next)
  }, [selectionApi, syncSelection])

  const handleEndRect = useCallback(() => {
    const next = selectionApi.endRect()
    void syncSelection(next)
  }, [selectionApi, syncSelection])

  const handleRunTool = useCallback(
    async (name: string, params?: Record<string, unknown>) => {
      if (name === 'adjust_region') {
        await syncSelection(selectionApi.selection)
      }
      void runTool(name, params)
    },
    [runTool, selectionApi.selection, syncSelection],
  )

  const handleToggleVisible = useCallback(
    async (layerId: string, visible: boolean) => {
      if (!sessionId || !session) {
        return
      }
      // 乐观更新
      setSession({
        ...session,
        document: {
          ...session.document,
          layers: session.document.layers.map((layer) =>
            layer.id === layerId ? { ...layer, visible } : layer,
          ),
        },
      })
      try {
        const data = await patchLayers(sessionId, {
          layers: [{ id: layerId, visible }],
        })
        setSession(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '更新图层失败')
        await reloadSession()
      }
    },
    [sessionId, session, reloadSession],
  )

  const handleSelectLayer = useCallback(
    async (layerId: string) => {
      if (!sessionId || !session) {
        return
      }
      // 点选图层 = 设为当前编辑层，并独显该层（其它层隐藏），画布立即变化
      const nextLayers = session.document.layers.map((layer) => ({
        ...layer,
        visible: layer.id === layerId,
      }))
      setSession({
        ...session,
        document: {
          ...session.document,
          layers: nextLayers,
          active_layer_id: layerId,
        },
      })
      try {
        const data = await patchLayers(sessionId, {
          active_layer_id: layerId,
          layers: nextLayers.map((layer) => ({
            id: layer.id,
            visible: layer.visible,
          })),
        })
        setSession(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '切换图层失败')
        await reloadSession()
      }
    },
    [sessionId, session, reloadSession],
  )

  return (
    <div className="editor-page">
      <header className="editor-header">
        <Link to="/" className="back-link">
          ← 返回
        </Link>
        <div>
          <p className="brand">image100</p>
          <h1>{session?.title ?? '编辑器'}</h1>
        </div>
      </header>

      {sessionId && !loading && !error && session && (
        <EditorToolbar
          sessionId={sessionId}
          disabled={toolsBusy}
          selectionMode={selectionApi.mode}
          onSelectionModeChange={handleModeChange}
          onClearSelection={handleClearSelection}
          onRunTool={(name, params) => {
            void handleRunTool(name, params)
          }}
        />
      )}

      <ProgressBar progress={progress} message={message} visible={running || progress > 0} />
      {runError && <p className="status-error">{runError}</p>}

      {loading && <p className="muted">正在加载会话…</p>}
      {error && <p className="status-error">{error}</p>}

      {!loading && !error && session && hasLayers && sessionId && (
        <div className="editor-body editor-body-with-layers">
          <LayerPanel
            layers={session.document.layers}
            activeLayerId={session.document.active_layer_id}
            disabled={toolsBusy}
            onToggleVisible={(id, visible) => {
              void handleToggleVisible(id, visible)
            }}
            onSelect={(id) => {
              void handleSelectLayer(id)
            }}
          />
          <CanvasStage
            layers={canvasLayers}
            canvasWidth={session.document.canvas.width}
            canvasHeight={session.document.canvas.height}
            selectionMode={selectionApi.mode}
            selection={selectionApi.selection}
            draftPoints={selectionApi.draftPoints}
            onBeginStroke={selectionApi.beginStroke}
            onExtendStroke={selectionApi.extendStroke}
            onEndStroke={handleEndStroke}
            onBeginRect={selectionApi.beginRect}
            onUpdateRect={selectionApi.updateRect}
            onEndRect={handleEndRect}
          />
          <AgentConversation
            provider={agent.provider}
            dashscopeAvailable={agent.dashscopeAvailable}
            busy={agent.busy}
            error={agent.error}
            current={agent.current}
            onProviderChange={agent.setProvider}
            onSubmit={(goal) => {
              void agent.submitGoal(goal)
            }}
            onConfirm={() => {
              void agent.confirm()
            }}
            onCancel={() => {
              void agent.cancel()
            }}
          />
        </div>
      )}
    </div>
  )
}
