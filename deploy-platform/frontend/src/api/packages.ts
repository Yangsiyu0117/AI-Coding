import client from './client'

export interface UpgradePackage {
  id: number
  service_id: number
  service_name: string
  version: string
  file_path: string
  file_md5: string
  file_size: number
  created_at: string | null
}

export function fetchPackages(serviceId?: number): Promise<UpgradePackage[]> {
  const params = serviceId ? { service_id: serviceId } : {}
  return client.get('/packages/', { params }).then((r) => r.data)
}

export function fetchPackage(id: number): Promise<UpgradePackage> {
  return client.get(`/packages/${id}`).then((r) => r.data)
}

export function uploadPackage(formData: FormData): Promise<UpgradePackage> {
  return client.post('/packages/upload', formData, { timeout: 600_000 }).then((r) => r.data)
}

export function deletePackage(id: number): Promise<void> {
  return client.delete(`/packages/${id}`)
}
