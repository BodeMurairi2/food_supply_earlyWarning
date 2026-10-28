import { createContext, useContext, type ReactNode } from 'react'
import { api } from '../services/api'
import type { Locations, Metadata } from '../types/api'
import { useApi } from './useApi'

interface AppData {
  metadata: Metadata | null
  locations: Locations | null
  loading: boolean
  error: string | null
  provinceOf: (district: string) => string | undefined
}

const Ctx = createContext<AppData | null>(null)

/** Loads metadata and the province/district list once for the whole app. */
export function AppDataProvider({ children }: { children: ReactNode }) {
  const meta = useApi(api.metadata, [])
  const locs = useApi(api.locations, [])
  const provinceOf = (district: string) =>
    locs.data?.provinces.find((p) => p.districts.includes(district))?.province
  return (
    <Ctx.Provider value={{
      metadata: meta.data,
      locations: locs.data,
      loading: meta.loading || locs.loading,
      error: meta.error || locs.error,
      provinceOf,
    }}>
      {children}
    </Ctx.Provider>
  )
}

export function useAppData() {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAppData must be used inside AppDataProvider')
  return v
}
