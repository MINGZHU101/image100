import { useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'

import BrandMark from '@/components/BrandMark'
import { errorMessage, useAuthActions, useCurrentUser } from '@/hooks/useAuth'

type Mode = 'login' | 'register'
type Rules = { minLength?: number; maxLength?: number; pattern?: string; title?: string }

const COPY: Record<Mode, { title: string; submit: string; switchTo: Mode; switchHint: string }> = {
  login: { title: '登录', submit: '登录', switchTo: 'register', switchHint: '还没有账号？注册' },
  register: {
    title: '创建账号',
    submit: '注册并进入',
    switchTo: 'login',
    switchHint: '已有账号？登录',
  },
}

const ACCOUNT_RULES: Rules = {
  minLength: 3,
  maxLength: 32,
  pattern: '[A-Za-z0-9_]{3,32}',
  title: '3–32 位字母、数字或下划线',
}
const PASSWORD_RULES: Rules = { minLength: 6, maxLength: 64, title: '6–64 位' }

export default function AuthPage() {
  const [params, setParams] = useSearchParams()
  const mode: Mode = params.get('mode') === 'register' ? 'register' : 'login'
  const copy = COPY[mode]

  const navigate = useNavigate()
  const { user, isLoading } = useCurrentUser()
  const { login, register } = useAuthActions()
  const action = mode === 'login' ? login : register

  const [account, setAccount] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [inviteCode, setInviteCode] = useState('')
  const [localError, setLocalError] = useState('')

  if (!isLoading && user) return <Navigate to="/create" replace />

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    setLocalError('')
    if (mode === 'register') {
      if (password !== passwordConfirm) {
        setLocalError('两次输入的密码不一致')
        return
      }
      register.mutate(
        {
          account,
          display_name: displayName,
          password,
          password_confirm: passwordConfirm,
          invite_code: inviteCode.trim() || undefined,
        },
        { onSuccess: () => navigate('/create', { replace: true }) },
      )
      return
    }
    login.mutate(
      {
        account,
        password,
        invite_code: inviteCode.trim() || undefined,
      },
      { onSuccess: () => navigate('/create', { replace: true }) },
    )
  }

  const switchMode = () => {
    action.reset()
    setLocalError('')
    setParams({ mode: copy.switchTo })
  }

  return (
    <div className="relative isolate flex min-h-screen items-center justify-center px-6 py-12">
      <div className="bg-glow absolute inset-x-0 top-0 h-[420px]" aria-hidden />

      <div className="relative w-full max-w-sm">
        <Link to="/" className="text-muted hover:text-ink mb-6 inline-flex items-center gap-2 text-sm">
          <span aria-hidden>←</span> 返回首页
        </Link>

        <div className="border-line bg-paper rounded-panel shadow-panel border p-8">
          <BrandMark size="sm">
            <span className="text-ink text-sm font-semibold">电商商品视觉工作台</span>
          </BrandMark>

          <h1 className="text-ink mt-6 text-2xl font-semibold tracking-tight">{copy.title}</h1>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <Field
              label="账号"
              value={account}
              onChange={setAccount}
              autoComplete="username"
              placeholder="登录用，字母数字下划线"
              rules={mode === 'register' ? ACCOUNT_RULES : undefined}
            />
            {mode === 'register' && (
              <Field
                label="用户名"
                value={displayName}
                onChange={setDisplayName}
                autoComplete="nickname"
                placeholder="展示名称，可中文"
                rules={{ minLength: 1, maxLength: 32 }}
              />
            )}
            <Field
              label="密码"
              type="password"
              value={password}
              onChange={setPassword}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              placeholder="至少 6 位"
              rules={mode === 'register' ? PASSWORD_RULES : undefined}
            />
            {mode === 'register' && (
              <Field
                label="确认密码"
                type="password"
                value={passwordConfirm}
                onChange={setPasswordConfirm}
                autoComplete="new-password"
                placeholder="再次输入密码"
                rules={PASSWORD_RULES}
              />
            )}
            <Field
              label="邀请码（可选）"
              value={inviteCode}
              onChange={setInviteCode}
              autoComplete="off"
              placeholder="五位字母数字"
              required={false}
            />

            {(localError || action.isError) && (
              <p className="text-danger text-sm">{localError || errorMessage(action.error)}</p>
            )}

            <button
              type="submit"
              disabled={action.isPending}
              className="bg-ink hover:bg-dark rounded-control w-full py-2.5 text-sm font-medium text-white transition-colors disabled:opacity-50"
            >
              {action.isPending ? '处理中…' : copy.submit}
            </button>
          </form>

          {mode === 'login' && (
            <button
              type="button"
              disabled={login.isPending}
              onClick={() =>
                login.mutate(
                  { account: 'demo', password: 'demo123' },
                  { onSuccess: () => navigate('/create', { replace: true }) },
                )
              }
              className="border-line text-ink hover:bg-soft rounded-control mt-3 w-full border py-2.5 text-sm font-medium transition-colors disabled:opacity-50"
            >
              演示账号一键登录（demo / demo123）
            </button>
          )}

          <button
            type="button"
            onClick={switchMode}
            className="text-muted hover:text-brand-strong mt-5 text-sm transition-colors"
          >
            {copy.switchHint}
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  autoComplete,
  placeholder,
  rules,
  required = true,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  type?: string
  autoComplete?: string
  placeholder?: string
  rules?: Rules
  required?: boolean
}) {
  return (
    <label className="block">
      <span className="text-muted mb-1.5 block text-sm">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        placeholder={placeholder}
        required={required}
        {...rules}
        className="border-line bg-paper text-ink placeholder:text-faint focus:border-brand rounded-control w-full border px-3.5 py-2.5 text-sm outline-none transition-colors"
      />
    </label>
  )
}
