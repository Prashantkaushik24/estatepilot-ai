import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import { useToast } from './toast'
import type { IntegrationStatus, Paginated } from '../types'

export const useList = <T,>(key: string, path: string, params: Record<string, unknown>, enabled = true) =>
  useQuery({ queryKey: [key, params], queryFn: () => api.get<Paginated<T>>(path, params), enabled, placeholderData: (p) => p })

export const useIntegrations = () => useQuery({ queryKey: ['integrations'], queryFn: () => api.get<IntegrationStatus>('/integrations/status'), staleTime: 10_000 })

/** Mutation helper: toasts success/error and invalidates the given query keys. */
export function useAction<V, R = unknown>(fn: (v: V) => Promise<R>, opts: { success?: string | ((r: R) => string); invalidate?: string[]; onSuccess?: (r: R) => void; onError?: (e: unknown) => void } = {}) {
  const qc = useQueryClient(); const toast = useToast()
  return useMutation({
    mutationFn: fn,
    onSuccess: (r) => {
      opts.invalidate?.forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
      if (opts.success) toast.success(typeof opts.success === 'function' ? opts.success(r) : opts.success)
      opts.onSuccess?.(r)
    },
    onError: (e) => { if (opts.onError) opts.onError(e); else toast.error(e) },
  })
}
