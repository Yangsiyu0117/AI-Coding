import client from './client'

export interface Environment {
  id: number
  name: string
  description: string
  ssh_default_port: number
  created_at: string | null
  updated_at: string | null
}

export interface SSHTestResult {
  success: boolean
  message: string
  latency_ms: number
}

export function fetchEnvironments(): Promise<Environment[]> {
  return client.get('/environments/').then((r) => r.data)
}

export function fetchEnvironment(id: number): Promise<Environment> {
  return client.get(`/environments/${id}`).then((r) => r.data)
}

export function createEnvironment(data: {
  name: string
  description?: string
  ssh_default_port?: number
}): Promise<Environment> {
  return client.post('/environments/', data).then((r) => r.data)
}

export function updateEnvironment(
  id: number,
  data: { name?: string; description?: string; ssh_default_port?: number }
): Promise<Environment> {
  return client.put(`/environments/${id}`, data).then((r) => r.data)
}

export function deleteEnvironment(id: number): Promise<void> {
  return client.delete(`/environments/${id}`)
}

export function testSSH(data: {
  host: string
  port: number
  user: string
  password?: string
}): Promise<SSHTestResult> {
  return client.post('/environments/test-ssh', data).then((r) => r.data)
}
