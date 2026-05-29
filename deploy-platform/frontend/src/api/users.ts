import client from './client'

export interface UserInfo {
  id: number
  username: string
  role: string
}

export function fetchUsers(): Promise<UserInfo[]> {
  return client.get('/users/').then((r) => r.data)
}

export function updateUser(id: number, data: { role?: string; password?: string }): Promise<UserInfo> {
  return client.put(`/users/${id}`, data).then((r) => r.data)
}

export function deleteUser(id: number): Promise<void> {
  return client.delete(`/users/${id}`)
}
