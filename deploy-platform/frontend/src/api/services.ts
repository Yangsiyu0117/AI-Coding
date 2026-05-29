import client from './client'

export interface ServiceNode {
  id: number
  service_id: number
  host_ip: string
  ssh_port: number
  ssh_user: string
  status: string
  created_at: string | null
}

export interface Service {
  id: number
  environment_id: number
  name: string
  type: string
  deploy_path: string
  run_script: string
  start_cmd: string
  stop_cmd: string
  check_cmd: string
  version_cmd: string
  backup_pattern: string
  upgrade_order: number
  depends_on: string
  description: string
  nodes: ServiceNode[]
  created_at: string | null
  updated_at: string | null
}

export interface ServiceType {
  name: string
  label: string
  steps: string[]
  rollbackable: string[]
}

export interface ServiceCreateData {
  environment_id: number
  name: string
  type: string
  deploy_path?: string
  run_script?: string
  start_cmd?: string
  stop_cmd?: string
  check_cmd?: string
  version_cmd?: string
  backup_pattern?: string
  upgrade_order?: number
  depends_on?: string
  description?: string
  nodes?: { host_ip: string; ssh_port?: number; ssh_user?: string; ssh_password?: string }[]
}

export function fetchServiceTypes(): Promise<ServiceType[]> {
  return client.get('/services/types').then((r) => r.data)
}

export function fetchStepLabels(): Promise<Record<string, string>> {
  return client.get('/services/types/step-labels').then((r) => r.data)
}

export function fetchServices(environmentId?: number): Promise<Service[]> {
  const params = environmentId ? { environment_id: environmentId } : {}
  return client.get('/services/', { params }).then((r) => r.data)
}

export function fetchService(id: number): Promise<Service> {
  return client.get(`/services/${id}`).then((r) => r.data)
}

export function createService(data: ServiceCreateData): Promise<Service> {
  return client.post('/services/', data).then((r) => r.data)
}

export function updateService(
  id: number,
  data: Partial<ServiceCreateData>
): Promise<Service> {
  return client.put(`/services/${id}`, data).then((r) => r.data)
}

export function deleteService(id: number): Promise<void> {
  return client.delete(`/services/${id}`)
}

export function addServiceNode(
  serviceId: number,
  data: { host_ip: string; ssh_port?: number; ssh_user?: string; ssh_password?: string }
): Promise<ServiceNode> {
  return client.post(`/services/${serviceId}/nodes`, data).then((r) => r.data)
}

export function updateServiceNode(
  serviceId: number,
  nodeId: number,
  data: { host_ip?: string; ssh_port?: number; ssh_user?: string; ssh_password?: string }
): Promise<ServiceNode> {
  return client.put(`/services/${serviceId}/nodes/${nodeId}`, data).then((r) => r.data)
}

export function importServices(data: ServiceCreateData[]): Promise<Service[]> {
  return client.post('/services/import', data)
}

export function deleteServiceNode(serviceId: number, nodeId: number): Promise<void> {
  return client.delete(`/services/${serviceId}/nodes/${nodeId}`)
}

export function createServiceType(data: {
  name: string
  label: string
  steps: string[]
  rollbackable: string[]
}): Promise<ServiceType> {
  return client.post('/services/types', data).then((r) => r.data)
}

export function updateServiceType(
  name: string,
  data: { label?: string; steps?: string[]; rollbackable?: string[] }
): Promise<ServiceType> {
  return client.put(`/services/types/${encodeURIComponent(name)}`, data).then((r) => r.data)
}

export function deleteServiceType(name: string): Promise<void> {
  return client.delete(`/services/types/${encodeURIComponent(name)}`)
}
