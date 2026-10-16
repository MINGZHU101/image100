import { Navigate, Route, Routes } from 'react-router-dom'
import { CreatePage } from './pages/CreatePage'
import { EditorPage } from './pages/EditorPage'
import { LandingPage } from './pages/LandingPage'

/** 路由壳：落地页 + 编辑器 */
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/create" element={<CreatePage />} />
      <Route path="/editor/:sessionId" element={<EditorPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
