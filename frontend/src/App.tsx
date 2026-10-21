import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import AccountLayout from '@/layouts/AccountLayout'
import AdminLayout from '@/layouts/AdminLayout'
import RequireAdmin from '@/layouts/RequireAdmin'
import RequireAuth from '@/layouts/RequireAuth'
import WorkbenchLayout from '@/layouts/WorkbenchLayout'
import AccountInvitePage from '@/pages/account/AccountInvitePage'
import AccountLuckyWheelPage from '@/pages/account/AccountLuckyWheelPage'
import AccountOverviewPage from '@/pages/account/AccountOverviewPage'
import AccountPointsPage from '@/pages/account/AccountPointsPage'
import AccountProfilePage from '@/pages/account/AccountProfilePage'
import AccountSecurityPage from '@/pages/account/AccountSecurityPage'
import AdminAdminsPage from '@/pages/admin/AdminAdminsPage'
import AdminAnnouncementsPage from '@/pages/admin/AdminAnnouncementsPage'
import AdminAuditPage from '@/pages/admin/AdminAuditPage'
import AdminBatchPage from '@/pages/admin/AdminBatchPage'
import AdminDashboardPage from '@/pages/admin/AdminDashboardPage'
import AdminInvitesPage from '@/pages/admin/AdminInvitesPage'
import AdminLuckyWheelPage from '@/pages/admin/AdminLuckyWheelPage'
import AdminPointsPage from '@/pages/admin/AdminPointsPage'
import AdminSessionsPage from '@/pages/admin/AdminSessionsPage'
import AdminSettingsPage from '@/pages/admin/AdminSettingsPage'
import AdminUsersPage from '@/pages/admin/AdminUsersPage'
import AuthPage from '@/pages/AuthPage'
import BatchPage from '@/pages/BatchPage'
import CandidatesPage from '@/pages/CandidatesPage'
import CopywritingPage from '@/pages/CopywritingPage'
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

        <Route element={<RequireAdmin />}>
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<AdminDashboardPage />} />
            <Route path="users" element={<AdminUsersPage />} />
            <Route path="points" element={<AdminPointsPage />} />
            <Route path="lucky-wheel" element={<AdminLuckyWheelPage />} />
            <Route path="invites" element={<AdminInvitesPage />} />
            <Route path="sessions" element={<AdminSessionsPage />} />
            <Route path="announcements" element={<AdminAnnouncementsPage />} />
            <Route path="settings" element={<AdminSettingsPage />} />
            <Route path="batch" element={<AdminBatchPage />} />
            <Route path="admins" element={<AdminAdminsPage />} />
            <Route path="audit" element={<AdminAuditPage />} />
          </Route>
        </Route>

        <Route element={<RequireAuth />}>
          <Route element={<WorkbenchLayout />}>
            <Route path="/create" element={<CreatePage />} />
            <Route path="/copywriting" element={<CopywritingPage />} />
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
              <Route path="lucky-wheel" element={<AccountLuckyWheelPage />} />
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
