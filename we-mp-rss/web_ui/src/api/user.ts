import http from './http'

export interface UserInfo {
  username: string
  nickname: string
  email: string
  avatar: string
  role: string
  is_active: boolean
  created_at: string
}

export interface UpdateUserParams {
  username?: string
  nickname?: string
  email?: string
  avatar?: string
  password?: string
  is_active?: boolean
}

export const getUserInfo = () => {
  return http.get<{code: number, data: UserInfo}>('/wx/user')
}

export const updateUserInfo = (data: UpdateUserParams) => {
  return http.put<{code: number, message: string}>('/wx/user', data)
}

export interface ChangePasswordParams {
  old_password: string
  new_password: string
}

export const changePassword = (data: ChangePasswordParams) => {
  return http.put<{code: number, message: string}>('/wx/user/password', data, {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    }
  })
}

// 保持旧方法向后兼容
export const changePasswordLegacy = (newPassword: string) => {
  return updateUserInfo({ password: newPassword })
}

export const toggleUserStatus = (active: boolean) => {
  return updateUserInfo({ is_active: active })
}

export const uploadAvatar = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return http.post<{code: number, url: string}>('/wx/user/avatar', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 用户管理相关接口（管理员权限）
export interface UserListResponse {
  id: string
  username: string
  nickname: string
  email: string
  avatar: string
  role: string
  is_active: boolean
  permissions: string[]
  created_at: string
  updated_at: string
}

export interface UserListParams {
  page?: number
  page_size?: number
}

export const getUserList = (params?: UserListParams) => {
  return http.get<{list: UserListResponse[], total: number, page: number, page_size: number}>('/wx/user/list', { params })
}

export interface AddUserParams {
  username: string
  password: string
  nickname?: string
  email?: string
  role?: string
  permissions?: string[]
}

export const addUser = (data: AddUserParams) => {
  return http.post<{code: number, message: string, data?: UserListResponse}>('/wx/user', data)
}

export interface UpdateUserByIdParams {
  nickname?: string
  email?: string
  role?: string
  permissions?: string[]
  is_active?: boolean
}

export const updateUserById = (userId: string, data: UpdateUserByIdParams) => {
  return http.put<{code: number, message: string}>(`/wx/user/${userId}`, data)
}

export const deleteUser = (userId: string) => {
  return http.delete<{code: number, message: string}>(`/wx/user/${userId}`)
}

export const resetUserPassword = (userId: string, newPassword: string) => {
  return http.post<{code: number, message: string}>(`/wx/user/${userId}/reset-password`, {
    new_password: newPassword
  })
}