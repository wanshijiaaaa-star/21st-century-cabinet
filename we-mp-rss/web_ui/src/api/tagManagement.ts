import http from './http'
import type { Tag, TagCreate } from '@/types/tagManagement'

export const listTags = (params?: { offset?: number; limit?: number }) => {
  return http.get<Tag[]>('/wx/tags', { 
    params: {
      offset: params?.offset || 0,
      limit: params?.limit || 100
    }
  })
}

export const getTag = (id: string) => {
  return http.get<Tag>(`/wx/tags/${id}`)
}

export const createTag = (data: TagCreate) => {
  return http.post('/wx/tags', data)
}

export const updateTag = (id: string, data: TagCreate) => {
  return http.put(`/wx/tags/${id}`, data)
}

export const deleteTag = (id: string) => {
  return http.delete(`/wx/tags/${id}`)
}
