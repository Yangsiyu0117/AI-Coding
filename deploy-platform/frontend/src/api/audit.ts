import client from './client'

export interface AuditLogEntry {
  id: number
  user_id: number | null
  action: string
  target_type: string
  target_id: number | null
  detail: string
  ip_address: string
  created_at: string | null
}

export function fetchAuditLogs(params?: {
  user_id?: number
  action?: string
  limit?: number
}): Promise<AuditLogEntry[]> {
  return client.get('/audit/', { params }).then((r) => r.data)
}
