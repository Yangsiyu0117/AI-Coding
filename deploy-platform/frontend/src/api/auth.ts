import client from './client'

export function login(username: string, password: string) {
  return client.post('/auth/login', { username, password })
}
