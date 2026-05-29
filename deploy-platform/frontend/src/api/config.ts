import client from './client'

export interface UploadConfig {
  max_upload_size_mb: number
  allowed_extensions: string[]
}

export interface AppConfig {
  app_name: string
  app_brand: string
  app_title: string
  version: string
}

export function fetchUploadConfig(): Promise<UploadConfig> {
  return client.get('/config/upload').then(r => r.data)
}

export function fetchAppConfig(): Promise<AppConfig> {
  return client.get('/config/app').then(r => r.data)
}

export interface PlatformSettings {
  app_brand: string
  app_title: string
  remote_update_base: string
  max_upload_size_mb: number
  allowed_upload_extensions: string[]
}

export function fetchPlatformSettings(): Promise<PlatformSettings> {
  return client.get('/config/platform').then((r) => r.data)
}

export function savePlatformSettings(data: Partial<PlatformSettings>): Promise<void> {
  return client.put('/config/platform', data)
}
