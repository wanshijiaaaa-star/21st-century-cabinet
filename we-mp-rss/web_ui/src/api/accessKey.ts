import http from './http'

export interface AccessKeyCreateRequest {
  name: string
  description?: string
  permissions?: string[]
  expires_in_days?: number | null
}

export interface AccessKeyResponse {
  id: string
  key: string
  secret?: string
  name: string
  description: string
  permissions: string[]
  is_active: boolean
  created_at: string
  updated_at?: string
  last_used_at?: string
  expires_at?: string
  is_expired?: boolean
}

export interface AccessKeyUpdateRequest {
  name?: string
  description?: string
  permissions?: string[]
  is_active?: boolean
  expires_at?: string
}

// 创建 Access Key
export const createAccessKey = (data: AccessKeyCreateRequest) => {
  return http.post<AccessKeyResponse>('/wx/auth/ak/create', data)
}

// 获取用户的 Access Keys 列表
export const listAccessKeys = () => {
  return http.get<AccessKeyResponse[]>('/wx/auth/ak/list')
}

// 更新 Access Key
export const updateAccessKey = (akId: string, data: AccessKeyUpdateRequest) => {
  return http.put<AccessKeyResponse>(`/wx/auth/ak/${akId}`, data)
}

// 停用 Access Key
export const deactivateAccessKey = (akId: string) => {
  return http.post(`/wx/auth/ak/${akId}/deactivate`)
}

// 删除 Access Key
export const deleteAccessKey = (akId: string) => {
  return http.delete(`/wx/auth/ak/${akId}`)
}
