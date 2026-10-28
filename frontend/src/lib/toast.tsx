import { createContext, ReactNode, useCallback, useContext, useState } from 'react'
import { CheckCircle2, XCircle, Info } from 'lucide-react'
type T = { id: number; kind: 'success' | 'error' | 'info'; msg: string }
const Ctx = createContext<{ push: (kind: T['kind'], msg: string) => void }>({ push: () => {} })
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<T[]>([])
  const push = useCallback((kind: T['kind'], msg: string) => {
    const id = Date.now() + Math.random()
    setItems((x) => [...x, { id, kind, msg }])
    setTimeout(() => setItems((x) => x.filter((i) => i.id !== id)), 5000)
  }, [])
  return (
    <Ctx.Provider value={{ push }}>
      {children}
      <div aria-live="polite" className="fixed bottom-4 right-4 z-[60] flex w-80 flex-col gap-2">
        {items.map((t) => (
          <div key={t.id} role={t.kind === 'error' ? 'alert' : 'status'} className="flex items-start gap-2 rounded-lg border bg-white p-3 text-sm shadow-lg dark:border-slate-700 dark:bg-slate-800">
            {t.kind === 'success' ? <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" /> : t.kind === 'error' ? <XCircle className="h-5 w-5 shrink-0 text-red-600" /> : <Info className="h-5 w-5 shrink-0 text-blue-600" />}
            <span>{t.msg}</span>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  )
}
export function useToast() {
  const { push } = useContext(Ctx)
  return {
    success: (m: string) => push('success', m),
    info: (m: string) => push('info', m),
    error: (e: unknown) => push('error', e instanceof Error ? e.message : String(e)),
  }
}
