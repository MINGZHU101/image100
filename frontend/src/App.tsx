import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import RequireAuth from '@/layouts/RequireAuth'
import WorkbenchLayout from '@/layouts/WorkbenchLayout'
import AuthPage from '@/pages/AuthPage'
import CandidatesPage from '@/pages/CandidatesPage'
import CreatePage from '@/pages/CreatePage'
import EditorPage from '@/pages/EditorPage'
import LandingPage from '@/pages/LandingPage'
import PlaceholderPage from '@/pages/PlaceholderPage'

function ComingSoon({ title }: { title: string }) {
  return (
    <PlaceholderPage title={title} hint="该功能将在后续版本实现，当前可使用创作与编辑器主路径。" />
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />

        <Route element={<RequireAuth />}>
          <Route element={<WorkbenchLayout />}>
            <Route path="/create" element={<CreatePage />} />
            <Route path="/editor" element={<EditorPage />} />
            <Route path="/editor/:sessionId" element={<EditorPage />} />
            <Route path="/marketing" element={<ComingSoon title="营销图" />} />
            <Route path="/marketing/:sessionId" element={<ComingSoon title="营销图" />} />
            <Route path="/batch" element={<ComingSoon title="批量处理" />} />
            <Route path="/batch/:runId" element={<ComingSoon title="批量处理" />} />
            <Route path="/candidates/:runId" element={<CandidatesPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
