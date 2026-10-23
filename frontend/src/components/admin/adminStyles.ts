/** 管理端共用样式：与用户端 design token 对齐。 */

export const adminUi = {
  page: 'animate-fade-in space-y-5',
  title: 'text-ink text-xl font-semibold tracking-tight',
  subtitle: 'text-muted mt-1 text-sm',
  panel: 'border-line bg-paper rounded-panel shadow-card border',
  panelPad: 'border-line bg-paper rounded-panel shadow-card border p-5',
  sectionTitle: 'text-ink text-sm font-semibold',
  label: 'text-muted mb-1 block text-xs font-medium',
  field: 'block text-sm',
  input:
    'border-line bg-paper text-ink placeholder:text-faint focus:border-brand rounded-control w-full border px-3 py-2 text-sm outline-none transition',
  inputInline:
    'border-line bg-paper text-ink focus:border-brand rounded-control border px-2.5 py-1.5 text-sm outline-none transition',
  textarea:
    'border-line bg-paper text-ink placeholder:text-faint focus:border-brand rounded-control w-full border px-3 py-2 text-sm outline-none transition',
  select:
    'border-line bg-paper text-ink focus:border-brand rounded-control border px-2.5 py-1.5 text-sm outline-none transition',
  btnPrimary:
    'bg-brand hover:bg-brand-strong rounded-control px-4 py-2 text-sm font-medium text-white shadow-control transition disabled:opacity-50',
  btnInk:
    'bg-ink hover:opacity-90 rounded-control px-4 py-2 text-sm font-medium text-white shadow-control transition disabled:opacity-50',
  btnGhost:
    'border-line text-ink hover:bg-soft rounded-control border px-3 py-1.5 text-sm transition disabled:opacity-40',
  btnDanger:
    'border-danger/40 text-danger hover:bg-danger/5 rounded-control border px-3 py-1.5 text-sm transition',
  btnLink: 'text-brand-strong text-sm font-medium hover:underline',
  tab:
    'rounded-control px-3 py-1.5 text-sm transition',
  tabActive: 'bg-brand-soft text-brand-strong font-medium',
  tabIdle: 'text-muted hover:bg-soft hover:text-ink',
  tableWrap: 'border-line bg-paper overflow-hidden rounded-panel border shadow-card',
  thead: 'bg-soft/80 text-muted',
  th: 'px-3 py-2.5 text-left text-xs font-medium tracking-wide',
  td: 'border-line text-ink border-t px-3 py-2.5 text-sm',
  muted: 'text-muted text-sm',
  faint: 'text-faint text-xs',
  badgeOk: 'bg-success/10 text-success rounded-full px-2 py-0.5 text-xs',
  badgeWarn: 'bg-danger/10 text-danger rounded-full px-2 py-0.5 text-xs',
  badgeBrand: 'bg-brand-soft text-brand-strong rounded-full px-2 py-0.5 text-xs',
} as const
