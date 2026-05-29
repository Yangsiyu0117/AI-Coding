import client from './client'

export interface TaskStep {
  id: number
  task_id: number
  service_id: number
  node_id: number
  step_type: string
  step_order: number
  status: string
  rollback_status: string
  log_output: string
  error_message: string
  retry_count: number
  started_at: string | null
  finished_at: string | null
  service_name: string
  node_ip: string
}

export interface UpgradeTask {
  id: number
  environment_id: number
  title: string
  status: string
  failure_strategy: string
  rollback_status: string
  is_rollback: boolean
  timeout_seconds: number | null
  created_by: number | null
  steps: TaskStep[]
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export interface CreateTaskPayload {
  environment_id: number
  title: string
  service_ids: number[]
  package_ids: number[]
  failure_strategy: string
  timeout_seconds?: number | null
}

export function fetchTasks(environmentId?: number): Promise<UpgradeTask[]> {
  const params = environmentId ? { environment_id: environmentId } : {}
  return client.get('/upgrades/', { params }).then((r) => r.data)
}

export function fetchTask(id: number): Promise<UpgradeTask> {
  return client.get(`/upgrades/${id}`).then((r) => r.data)
}

export function createTask(data: CreateTaskPayload): Promise<UpgradeTask> {
  return client.post('/upgrades/', data).then((r) => r.data)
}

export function startTask(id: number): Promise<{ message: string }> {
  return client.post(`/upgrades/${id}/start`).then((r) => r.data)
}

export function rollbackTask(id: number): Promise<{ message: string }> {
  return client.post(`/upgrades/${id}/rollback`).then((r) => r.data)
}

export function pauseTask(id: number): Promise<{ message: string }> {
  return client.post(`/upgrades/${id}/pause`).then((r) => r.data)
}

export function resumeTask(id: number): Promise<{ message: string }> {
  return client.post(`/upgrades/${id}/resume`).then((r) => r.data)
}

export function stopTask(id: number): Promise<{ message: string }> {
  return client.post(`/upgrades/${id}/stop`).then((r) => r.data)
}

export function retryStep(taskId: number, stepId: number): Promise<{ message: string }> {
  return client.post(`/upgrades/${taskId}/retry-step/${stepId}`)
}

export function deleteTask(id: number): Promise<void> {
  return client.delete(`/upgrades/${id}`)
}
