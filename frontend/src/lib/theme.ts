import { useSyncExternalStore } from 'react'
export type Theme = 'light' | 'dark'
const listeners = new Set<() => void>()
let current: Theme = (typeof localStorage !== 'undefined' && (localStorage.getItem('ep_theme') as Theme)) || (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
const apply = () => { if (typeof document !== 'undefined') document.documentElement.classList.toggle('dark', current === 'dark') }
apply()
export function setTheme(t: Theme) { current = t; localStorage.setItem('ep_theme', t); apply(); listeners.forEach((l) => l()) }
export function useTheme() {
  const theme = useSyncExternalStore((cb) => { listeners.add(cb); return () => listeners.delete(cb) }, () => current)
  return { theme, setTheme, toggle: () => setTheme(theme === 'dark' ? 'light' : 'dark') }
}
