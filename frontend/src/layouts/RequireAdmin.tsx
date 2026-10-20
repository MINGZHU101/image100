import { useQuery } from '@tanstack/react-query'
import { Navigate, Outlet } from 'react-router-dom'

import { authApi } from '@/api/auth'

/** 管理端会话守卫：无 admin Cookie 则回登录页管理员模式。 */
export default function RequireAdmin() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['auth', 'admin', 'me'],
    queryFn: () => authApi.adminMe(),
    retry: false,
    staleTime: 60_000,
  })

  if (isPending) {
    return (
      <div className="text-muted grid min-h-screen place-items-center text-sm">加载中…</div>
    )
  }
  if (isError || !data) {
    return <Navigate to="/auth?as=admin" replace />
  }
  return <Outlet />
}
