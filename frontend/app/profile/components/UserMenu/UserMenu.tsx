'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { post, get } from '@/services/axios'

interface UserInfo {
  display_name: string
  images: { url: string }[]
}

export default function UserMenu() {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [open, setOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  useEffect(() => {
    get<{ user_name: UserInfo }>('/api/get-user-name/')
      .then((r) => setUser(r.user_name))
      .catch(() => {})
  }, [])

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSignOut = async () => {
    setSigningOut(true)
    try {
      await post('/api/logout/', {})
    } catch {}
    router.push('/')
  }

  const initials = (() => {
    const name = user?.display_name?.trim()
    if (!name) return '?'
    const parts = name.split(/\s+/)
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
  })()

  return (
    <div ref={menuRef} className="fixed top-4 right-4 z-50">
      {/* Avatar button */}
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-10 h-10 rounded-full border-2 border-gray-700 hover:border-green transition-colors focus:outline-none focus:ring-2 focus:ring-green bg-gray-800 flex items-center justify-center"
        aria-label="User menu"
      >
        <span className="text-white text-sm font-bold tracking-wide">{initials}</span>
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 mt-2 w-48 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl overflow-hidden">
          {user?.display_name && (
            <div className="px-4 py-3 border-b border-gray-800">
              <p className="text-white text-sm font-medium truncate">{user.display_name}</p>
            </div>
          )}
          <button
            onClick={handleSignOut}
            disabled={signingOut}
            className="w-full text-left px-4 py-3 text-sm text-gray-300 hover:bg-gray-800 hover:text-white transition-colors disabled:opacity-50"
          >
            {signingOut ? 'Signing out…' : 'Sign out'}
          </button>
        </div>
      )}
    </div>
  )
}
