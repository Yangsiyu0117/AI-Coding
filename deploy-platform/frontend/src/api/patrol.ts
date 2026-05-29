import client from './client'

export interface NodePatrolResult {
  node_id: number
  host_ip: string
  service_name: string
  status: string
  detail: string
  checked_at: string | null
}

export interface PatrolRunResponse {
  environment_id: number
  total_nodes: number
  healthy_nodes: number
  unhealthy_nodes: number
  results: NodePatrolResult[]
  checked_at: string
}

export function runPatrol(environmentId: number, serviceIds?: number[]): Promise<PatrolRunResponse> {
  return client.post('/patrol/run', { environment_id: environmentId, service_ids: serviceIds ?? null }).then((r) => r.data)
}
