import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import AccountLayout from '@/layouts/AccountLayout'
import RequireAuth from '@/layouts/RequireAuth'
import WorkbenchLayout from '@/layouts/WorkbenchLayout'
import AccountInvitePage from '@/pages/account/AccountInvitePage'
import AccountOverviewPage from '@/pages/account/AccountOverviewPage'
import AccountPointsPage from '@/pages/account/AccountPointsPage'
import AccountProfilePage from '@/pages/account/AccountProfilePage'
import AccountSecurityPage from '@/pages/account/AccountSecurityPage'
import AuthPage from '@/pages/AuthPage'
import BatchPage from '@/pages/BatchPage'
import CandidatesPage from '@/pages/CandidatesPage'
import CreatePage from '@/pages/CreatePage'
import EditorPage from '@/pages/EditorPage'
import LandingPage from '@/pages/LandingPage'
import MarketingPage from '@/pages/MarketingPage'

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
            <Route path="/marketing" element={<MarketingPage />} />
            <Route path="/marketing/:sessionId" element={<MarketingPage />} />
            <Route path="/batch" element={<BatchPage />} />
            <Route path="/batch/:runId" element={<BatchPage />} />
            <Route path="/candidates/:runId" element={<CandidatesPage />} />
            <Route path="/account" element={<AccountLayout />}>
              <Route index element={<AccountOverviewPage />} />
              <Route path="profile" element={<AccountProfilePage />} />
              <Route path="points" element={<AccountPointsPage />} />
              <Route path="invite" element={<AccountInvitePage />} />
              <Route path="security" element={<AccountSecurityPage />} />
            </Route>
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
