import type { ReactNode } from 'react'

import { adminUi } from '@/components/admin/adminStyles'

/** 管理端页头：标题 + 说明 + 右侧操作区。 */
export default function AdminPageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className={adminUi.title}>{title}</h2>
        {description ? <p className={adminUi.subtitle}>{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  )
}
