import type { User } from '@/api/auth'

export default function UserAvatar({
  user,
  size = 'sm',
}: {
  user: Pick<User, 'display_name' | 'username' | 'account' | 'avatar_url'> | null
  size?: 'sm' | 'lg'
}) {
  const label = (user?.display_name || user?.username || user?.account || '?').trim()
  const letter = label.slice(0, 1).toUpperCase()
  const box = size === 'lg' ? 'size-16 text-xl' : 'size-5 text-[11px]'

  if (user?.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt=""
        className={`${box} shrink-0 rounded-full object-cover`}
      />
    )
  }

  return (
    <span
      className={`bg-brand-soft text-brand-strong grid ${box} shrink-0 place-items-center rounded-full font-semibold`}
    >
      {letter}
    </span>
  )
}
